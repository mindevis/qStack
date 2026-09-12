# qStack — Дистрибутивный Оркестратор Облачных Виртуальных Машин

[![Go](https://img.shields.io/badge/Go-1.24+-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![NATS](https://img.shields.io/badge/NATS-Event%20Bus-4E2A8E?style=flat&logo=nats)](https://nats.io/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat)](LICENSE)

qStack — дистрибутивный оркестратор облачных виртуальных машин на Go с декларативным подходом (примирение желаемого и фактического состояния). Полная микросервисная архитектура: каждый компонент — независимый сервис со собственным `go.mod`, бинарным файлом, схемой базы данных и развёртыванием. API Gateway выступает в роли stateless фасада, оркестрируя сложные потоки (например, создание ВМ) через Sagas.

## 🏗 Архитектура

Подробная архитектурная документация: **[ARCHITECTURE.md](./ARCHITECTURE.md)**

```
                        ┌─────────────────────────────────────────┐
                        │           API Gateway (qstack-api)      │
                        │  REST / JWT Auth / Admin+User Dashboards │
                        └──────────────┬──────────────────────────┘
                                        │ gRPC mTLS / NATS Events
            ┌───────────────────────────┼───────────────────────────┐
            │                           │                           │
     ┌──────▼──────┐          ┌─────────▼────────┐         ┌───────▼───────┐
     │  Compute    │          │    Storage       │         │    Network    │
     │  Scheduler  │◄───────►│    Volumes       │◄──────►│   IPAM/DHCP   │
     │  Live Mig.  │          │    Snapshots     │         │   Subnets     │
     └──────┬──────┘          └─────────────────┘         └───────────────┘
            │                                                      │
     ┌──────▼──────┐          ┌─────────▼────────┐         ┌───────▼───────┐
     │   Image     │          │     Billing      │         │    Backup     │
     │  Builds     │          │  Usage/Quota     │         │  Snapshots    │
     └──────┬──────┘          │  Invoices        │         │  Restore      │
            │                 └─────────────────┘         └───────────────┘
     ┌──────▼──────┐                                    ┌───────▼───────┐
     │     AI      │                                    │    Agent      │
     │  Predictor  │                                    │  (per host)   │
     │  Advisor    │                                    │  libvirt KVM  │
     └─────────────┘                                    └───────────────┘
```

## 📦 Сервисы

| Сервис | Реплики | Схема БД | Ответственность |
|--------|---------|----------|-----------------|
| **qstack-api** | 3+ (stateless) | — | REST API Gateway, JWT Auth, Админ и Пользовательские панели, Валидация, Оркестрация Sagas |
| **qstack-compute** | 1 (leader) | `compute_schema` | ВМ, Хосты, Кластеры, Примиритель, Планировщик, Live Migration, HA |
| **qstack-storage** | 1 | `storage_schema` | Пулы, Томы, Снимки, Подключение/Отключение |
| **qstack-network** | 1 | `network_schema` | Сети, IPAM, Подсети, DHCP, MAC |
| **qstack-image** | 1 | `image_schema` | CRUD образов, Сборка/Конвертация, Кэш |
| **qstack-billing** | 1 | `billing_schema` | Тенанты, Тарифы, Метрика использования, Счета, Квоты |
| **qstack-backup** | 1 | `backup_schema` | Расписание резервного копирования, Снимки, Восстановление, Проверка |
| **qstack-ai** | 1 | `ai_schema` | Консультант, Предиктор, Автоисцеление, Ассистент-чат |
| **qstack-agent** | N (на хост) | — | Локальное управление libvirt, Heartbeat, Отчётность ресурсов |

## 🛠 Технологический стек

| Компонент | Технология | Обоснование |
|-----------|-----------|-------------|
| **Язык** | Go | Производительность, конкурентность, стандарт для облачных инструментов |
| **Гипервизор** | libvirt (libvirt-go) | KVM/QEMU, локальная виртуализация |
| **API Gateway** | gin | Быстрый, функциональный, встроенный роутинг |
| **Межсервисный** | gRPC + protobuf | Синхронные RPC, сгенерированные клиенты, mTLS |
| **Event Bus** | NATS + NKey | Асинхронные события, pub/sub, TLS 1.3 |
| **CLI** | cobra | Стандарт для CLI инструментов на Go |
| **База данных** | PostgreSQL + sqlc | Типобезопасный SQL, схемы на сервис |
| **Паттерн состояния** | Desired/Actual reconciliation | Декларативный (как Terraform/K8s) |
| **Панель (Пользователь)** | React + TypeScript + Ant Design + Vite | Управление ВМ, самообслуживание |
| **Панель (Админ)** | React + TypeScript + Ant Design + Vite | Инфраструктура, биллинг, аудит (PCI-DSS) |
| **Конфигурация** | YAML манифесты | Читаемость, в стиле Kubernetes |
| **Логи** | slog (stdlib) + OpenTelemetry | Структурированное JSON-логирование, распределённая трассировка |
| **Отслеживание ошибок** | GlitchTip (self-hosted Sentry) | Stack traces, группировка ошибок, трекинг релизов |
| **Оркестрация** | Kubernetes | Целевая платформа развёртывания |
| **Распределённые TX** | Sagas (orchestration) | Мульти-сервисные транзакции (создание ВМ) |
| **CI/CD** | GitHub Actions → kind → k3d | Тестирование + деплой на K8s-кластеры |

## 🚀 Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Go 1.24+

### Запуск локальной среды

```bash
# Клонирование репозитория
git clone https://github.com/mindevis/qStack.git
cd qStack

# Запуск всей инфраструктуры и сервисов
docker-compose up -d

# Проверка состояния сервисов
docker-compose ps
```

Инфраструктура включает: PostgreSQL, NATS, GlitchTip, все 9 микросервисов и два веб-интерфейса (Admin + User).

### Компиляция из исходников

```bash
# Настройка workspace
go work init
go work use ./services/... ./agent/ ./pkg/

# Сборка всех сервисов
make build-all

# Запуск тестов
make test-all
```

Дополнительную информацию по настройке локальной разработки см. в **[DEVELOPMENT.md](./DEVELOPMENT.md)**.

## 📚 Документация

| Документ | Описание |
|----------|----------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Архитектура системы, дизайн микросервисов, протоколы |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Настройка среды разработки, локальная отладка |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Правила внесения вкладов, код-ревью |

---

# qStack — Distributed Cloud VM Orchestrator

**qStack** is a distributed cloud VM orchestrator built in Go with a declarative approach (desired/actual state reconciliation). Full microservice architecture: every component is an independent service with its own `go.mod`, binary, database schema, and deployment. API Gateway acts as a stateless facade, orchestrating complex flows (like VM creation) via Sagas.

## 🏗 Architecture

See **[ARCHITECTURE.md](./ARCHITECTURE.md)** for detailed architecture documentation.

### Services

| Service | Replicas | DB Schema | Responsibility |
|---------|----------|-----------|-----------------|
| **qstack-api** | 3+ (stateless) | — | REST API Gateway, JWT Auth, Admin+User Dashboards, Validation, Saga orchestration |
| **qstack-compute** | 1 (leader) | `compute_schema` | VMs, Hosts, Clusters, Reconciler, Scheduler, Live Migration, HA |
| **qstack-storage** | 1 | `storage_schema` | Pools, Volumes, Snapshots, Attach/Detach |
| **qstack-network** | 1 | `network_schema` | Networks, IPAM, Subnets, DHCP, MAC |
| **qstack-image** | 1 | `image_schema` | Image CRUD, Build/Convert tasks, Cache sync |
| **qstack-billing** | 1 | `billing_schema` | Tenants, Rate Plans, Usage Meter, Invoices, Quota |
| **qstack-backup** | 1 | `backup_schema` | Backup scheduling, Snapshots, Restore, Verify |
| **qstack-ai** | 1 | `ai_schema` | Advisor, Predictor, AutoHeal, Assistant chat |
| **qstack-agent** | N (per host) | — | Local libvirt management, heartbeat, resource reporting |

### Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Language** | Go | Performance, concurrency, cloud tooling standard |
| **Hypervisor** | libvirt (libvirt-go) | KVM/QEMU, local virtualization |
| **API Gateway** | gin | Fast, feature-rich, built-in routing |
| **Service-to-Service** | gRPC + protobuf | Sync RPC, generated clients, mTLS |
| **Event Bus** | NATS + NKey | Async events, pub/sub, TLS 1.3 |
| **CLI** | cobra | Standard for Go CLI tools |
| **Database** | PostgreSQL + sqlc | Type-safe SQL, per-service schemas |
| **State Pattern** | Desired/Actual reconciliation | Declarative (like Terraform/K8s) |
| **Dashboard (User)** | React + TypeScript + Ant Design + Vite | Tenant VM management, self-service |
| **Dashboard (Admin)** | React + TypeScript + Ant Design + Vite | Infrastructure, billing, audit (PCI-DSS) |
| **Config** | YAML manifests | Readability, Kubernetes-style |
| **Logs** | slog (stdlib) + OpenTelemetry | Structured JSON logging, distributed tracing |
| **Error Tracking** | GlitchTip (self-hosted Sentry) | Stack traces, error grouping, release tracking |
| **Orchestration** | Kubernetes | Control plane deployment target |
| **Distributed TX** | Sagas (orchestration) | Multi-service transactions (create VM) |
| **CI/CD** | GitHub Actions → kind → k3d | Test + deploy to K8s clusters |

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Go 1.24+

### Running Local Development Environment

```bash
# Clone the repository
git clone https://github.com/mindevis/qStack.git
cd qStack

# Start all infrastructure and services
docker-compose up -d

# Check services status
docker-compose ps
```

The stack includes: PostgreSQL, NATS, GlitchTip, all 9 microservices, and two web dashboards (Admin + User).

### Building from Source

```bash
# Initialize workspace
go work init
go work use ./services/... ./agent/ ./pkg/

# Build all services
make build-all

# Run tests
make test-all
```

For detailed local development setup, see **[DEVELOPMENT.md](./DEVELOPMENT.md)**.

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, microservice design, protocols |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Development environment setup, local debugging |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Contribution guidelines, code review process |
