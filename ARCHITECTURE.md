# Архитектура qStack

Распределённый оркестратор облачных виртуальных машин на Go с декларативным подходом (приведение желаемого состояния к фактическому). Полная микросервисная архитектура: каждый компонент — независимый сервис с собственным `go.mod`, бинарником, схемой PostgreSQL и деплоем.

---

## Обзор микросервисной архитектуры

qStack разбит на 9 независимых микросервисов. API Gateway — единственная точка входа (REST), действующая как stateless фасада. Сложные многошаговые операции (создание VM) оркестрируются через паттерн Sagas. Сервисы общаются по gRPC (синхронно) и NATS (асинхронно), каждый хранит данные в собственной схеме PostgreSQL.

**Принципы:**

- **Собственная кодовая база** — каждый сервис имеет свой `go.mod`, `Dockerfile`, сборку
- **Изоляция данных** — PostgreSQL-схема на сервис, кросс-сервисный доступ только через gRPC/NATS
- **gRPC + mTLS** — синхронные вызовы между сервисами, взаимная аутентификация по сертификатам
- **NATS + NKey + TLS** — событийная шина, асинхронная коммуникация
- **Sagas** — распределённые транзакции (создание VM: Storage → Network → Compute)
- **Независимый деплой** — каждый сервис разворачивается, масштабируется и откатывается отдельно
- **Автономные гипервизоры** — при падении control plane запущенные VM продолжают работать

---

## Границы сервисов

| Сервис | Реплики | Схема БД | Ответственность |
|--------|---------|----------|-----------------|
| **qstack-api** | 3+ (stateless) | — | REST API Gateway, Auth (JWT), Dashboard, валидация, оркестрация Sagas |
| **qstack-compute** | 1 active (leader) | `compute_schema` | VM, Hosts, Clusters, Reconciler, Scheduler, Live Migration, HA |
| **qstack-storage** | 1 | `storage_schema` | Пул хранилищ, Вolumes, Snapshots, Attach/Detach |
| **qstack-network** | 1 | `network_schema` | Сети, IPAM, Subnets, DHCP, MAC |
| **qstack-image** | 1 | `image_schema` | Образы VM, Build/Convert, синхронизация кэша |
| **qstack-billing** | 1 | `billing_schema` | Тенанты, Тарифы, Usage Meter, Инвойсы, Квоты |
| **qstack-backup** | 1 | `backup_schema` | Расписание бэкапов, Restore, Verify, Retention |
| **qstack-ai** | 1 | `ai_schema` | Advisor, Predictor, AutoHeal, Assistant Chat |
| **qstack-agent** | N (на каждый хост) | — | Локальный libvirt, heartbeat, мониторинг ресурсов |

---

## Структура монорепозитория

```
qStack/
├── pkg/                       # Общий SDK (типы, gRPC, helpers)
│   ├── types/                 # Общие доменные типы
│   ├── grpc/                  # Определения gRPC + генерируемый код
│   ├── nats/                  # NATS helpers (connect, publish, subscribe)
│   ├── ca/                    # Внутренняя PKI (подписание, ротация certs)
│   └── config/                # Общие типы конфигурации
├── services/                  # Микросервисы (каждый со своим go.mod)
│   ├── api/                   # qstack-api
│   ├── compute/               # qstack-compute
│   ├── storage/               # qstack-storage
│   ├── network/               # qstack-network
│   ├── image/                 # qstack-image
│   ├── billing/               # qstack-billing
│   ├── backup/                # qstack-backup
│   └── ai/                    # qstack-ai
├── agent/                     # qstack-agent (на гипервизорах)
├── dashboards/                # Web UI (PCI-DSS разделение)
│   ├── admin/                 # Admin Dashboard (инфра, биллинг, аудит)
│   └── user/                  # User Dashboard (VM, образы, ресурсы)
├── configs/                   # YAML-конфигурации
├── k8s/                       # Kubernetes манифесты
├── proto/                     # Protobuf определения
├── docker-compose.yml         # Локальная разработка
├── go.work                    # Monorepo workspace
└── Makefile
```

Каждая папка сервиса содержит: `cmd/`, `internal/`, `go.mod`, `Dockerfile`.

---

## Стек коммуникаций

| Направление | Протокол | Безопасность | Назначение |
|-------------|----------|-------------|------------|
| CLI/Dashboard → API | REST HTTPS | JWT auth | Входящие запросы |
| API → Сервисы | gRPC | mTLS (внутр. CA) | Синхронные RPC |
| API → Сервисы | NATS | NKey + TLS 1.3 | Асинхронная делегация |
| Scheduler → Agents | gRPC mTLS | Mutual TLS, per-agent certs | Команды, синхронизация состояния |
| Agents → Events | NATS | NKey + TLS 1.3 | Heartbeat, метрики, события VM |
| Leader Election | PG advisory locks | SCRAM-SHA-256, TLS | Выбор лидера (Compute) |
| Межсервисные события | NATS | Subject-based permissions | Cross-service (billing, backup, AI) |

**gRPC mTLS:** Каждый агент получает уникальный X.509 сертификат (подписан внутренним CA). Валидация по CN = hostname, автоматическая ротация каждые 24ч.

**NATS NKey:** Каждый агент — уникальный NKey (ed25519). Subject-based permissions ограничивают доступ агента к собственным командам.

---

## Схемы баз данных

ПостgreSQL (единый экземпляр), отдельные схемы для каждого сервиса. Кросс-сервисный доступ к данным только через gRPC/NATS, прямые запросы к чужим схемам запрещены.

| Сервис | Схема | Основные сущности |
|--------|-------|-------------------|
| qstack-compute | `compute_schema` | VM, Hosts, Clusters, желаемое/фактическое состояние |
| qstack-storage | `storage_schema` | Storage Pools, Volumes, Snapshots |
| qstack-network | `network_schema` | Networks, Subnets, IPAM, DHCP leases, MAC |
| qstack-image | `image_schema` | Image CRUD, Build tasks, Cache |
| qstack-billing | `billing_schema` | Tenants, Rate Plans, Usage Meter, Invoices, Quota |
| qstack-backup | `backup_schema` | Backup schedules, Snapshots, Restore jobs, Verification |
| qstack-ai | `ai_schema` | Advisor rules, Predictions, AutoHeal actions, Chat history |

API Gateway и Agent не хранят состояние в БД (stateless и state-на-хосте соответственно).

---

## Сетевая сегментация гипервизоров

| Сеть | Назначение | NIC/VLAN | Протокол |
|------|-----------|----------|----------|
| **Management** | Agent ↔ Control Plane (gRPC, NATS) | eth0 / VLAN 10 | TCP 443, 4222 |
| **Migration** | Live migration (хост ↔ хост) | eth1 / VLAN 20 (dedicated 10G+) | TCP 49152-49215 (QEMU) |
| **Storage** | Hypervisor → Ceph/iSCSI (block I/O) | eth2 / VLAN 30 (dedicated 25G+) | RBD 6789, iSCSI 3260 |
| **Guest** | Трафик VM (изолирован от хоста) | virtio / VLAN-tagged | Трафик VM |

---

## Высокоуровневая диаграмма

```
                    ┌──────────────────────────────────────────────────────────────┐
                    │              Control Plane (K8s — Microservices)             │
                    │                                                              │
                    │  ┌────────────────────────────────────────────────────────┐  │
                    │  │          qstack-api (3+ replicas, stateless)           │  │
                    │  │     Gin Router · Auth · Dashboard · gRPC · Sagas       │  │
                    │  └─────────────────┬───────────────┬──────────────────────┘  │
                    │                    │ gRPC (mTLS)   │ gRPC (mTLS)            │
                    │  ┌─────────────────┼───────────────┼──────────────────────┐ │
                    │  │ ┌───────────────▼───────┐ ┌────▼────────────────────┐ │ │
                    │  │ │  qstack-compute       │ │  qstack-storage          │ │ │
                    │  │ │  (1 active leader)     │ │  (1 replica)             │ │ │
                    │  │ │  VM · Hosts · Clusters │ │  Pools · Volumes · Snap  │ │ │
                    │  │ │  Scheduler · Live Mig  │ │                          │ │ │
                    │  │ └───────────────────────┘ └──────────────────────────┘ │ │
                    │  │ ┌───────────────────────┐ ┌──────────────────────────┐ │ │
                    │  │ │  qstack-network        │ │  qstack-image            │ │ │
                    │  │ │  Networks · IPAM · DHCP│ │  Images · Builds · Cache │ │ │
                    │  │ └───────────────────────┘ └──────────────────────────┘ │ │
                    │  │ ┌───────────────────────┐ ┌──────────────────────────┐ │ │
                    │  │ │  qstack-billing        │ │  qstack-backup           │ │ │
                    │  │ │  Tenants · Meter · INV │ │  Schedule · Restore · Ver│ │ │
                    │  │ └───────────────────────┘ └──────────────────────────┘ │ │
                    │  │ ┌───────────────────────┐                             │ │
                    │  │ │  qstack-ai             │                             │ │
                    │  │ │  Advisor · Predictor   │                             │ │
                    │  │ └───────────────────────┘                             │ │
                    │  └──────────────────────────────────────────────────────┘ │
                    │                                                              │
                    │  ┌──────────────┐  ┌──────────┐  ┌──────┐  ┌────────┐      │
                    │  │ PostgreSQL   │  │ NATS (3x)│  │ CA   │  │ OTEL   │      │
                    │  │ (per-schema) │  │ (events) │  │mTLS  │  │ traces │      │
                    │  └──────────────┘  └──────────┘  └──────┘  └────────┘      │
                    └──────────────────────────┬───────────────────────────────────┘
                                               │ gRPC + NATS
                    ┌──────────────┐    ┌──────┴───────┐    ┌──────────────┐
                    │ Datacenter A │    │ Datacenter B │    │ Datacenter C │
                    │ Cluster "prod"│   │  "staging"   │    │  "dev"       │
                    │ Agent 1 + VMs │   │ Agent 1 + VMs│    │ Agent 1 + VMs│
                    │ Agent 2 + VMs │   │ Agent 2 + VMs│    │ Agent 2 + VMs│
                    └──────────────┘    └──────────────┘    └──────────────┘
```
