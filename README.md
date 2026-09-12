# qStack — Дистрибутивный Оркестратор Облачных Виртуальных Машин

[![Go](https://img.shields.io/badge/Go-1.24+-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![NATS](https://img.shields.io/badge/NATS-Event%20Bus-4E2A8E?style=flat&logo=nats)](https://nats.io/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat)](LICENSE)

Распределённый облачный оркестратор виртуальных машин на Go с декларативным подходом (desired/actual state reconciliation). Полная микросервисная архитектура: 9 независимых сервисов, собственная схема БД на каждый, mTLS между ними, async события через NATS JetStream.

**Default runtime: Talos Linux** (immutable K8s) | Также работает на любом Kubernetes (EKS/GKE/AKS/k3s/k0s).

## 📖 Документация

| Ресурс | Описание |
|--------|----------|
| **[GitHub Pages](https://mindevis.github.io/qStack/)** | Интерактивная документация: архитектура, сервисы, API, deployment |
| **[GitHub Wiki](https://github.com/mindevis/qStack/wiki)** | Полная документация: схемы БД, gRPC API, NATS events, contributing |
| [CHANGELOG.md](./CHANGELOG.md) | История версий |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Правила внесения вклада |

## 🚀 Быстрый старт

```bash
git clone https://github.com/mindevis/qStack.git && cd qStack

# Локальная инфраструктура (infra + все сервисы)
docker-compose up -d

# Сборка
make build-all && make test-all
```

Детальная настройка разработки → **[Development](https://github.com/mindevis/qStack/wiki/Development)**

## 🏗 Сервисы (9 microservices)

| Сервис | Реплики | Ответственность |
|--------|---------|-----------------|
| **qstack-api** | 3+ (stateless) | API Gateway, Auth (JWT), Dashboards (PCI-DSS: Admin/User), Saga orchestration |
| **qstack-compute** | 1 (leader) | VMs, Hosts, Clusters, Scheduler, Live Migration, HA |
| **qstack-storage** | 1 | Pools, Volumes, Snapshots (Libvirt, Ceph RBD, iSCSI) |
| **qstack-network** | 1 | Networks, IPAM, Subnets, DHCP |
| **qstack-image** | 1 | Image CRUD, Build/Convert, Vulnerability scanning |
| **qstack-billing** | 1 | Tenants, Usage Meter, Invoices, Stripe, Quota |
| **qstack-backup** | 1 | Backup scheduling, Restore, Verify |
| **qstack-ai** | 1 | Advisor, Predictor, AutoHeal, Assistant |
| **qstack-agent** | N (per host) | Hypervisor agent (libvirt, heartbeat, resource reporting) |

## 🛠 Стек

Go · libvirt/KVM · gRPC mTLS · NATS JetStream · PostgreSQL + sqlc · Gin · React (Vite + Ant Design) · OpenTelemetry · Prometheus/Grafana/Loki · GlitchTip · OpenBao/Vault · Talos Linux / K8s

---

# qStack — Distributed Cloud VM Orchestrator

Distributed cloud VM orchestrator on Go with declarative approach (desired/actual state reconciliation). Full microservice architecture: 9 independent services, own DB schema per service, mTLS between them, async events via NATS JetStream.

**Default runtime: Talos Linux** (immutable K8s) | Also runs on any Kubernetes (EKS/GKE/AKS/k3s/k0s).

## 📖 Documentation

| Resource | Description |
|----------|-------------|
| **[GitHub Pages](https://mindevis.github.io/qStack/)** | Interactive docs: architecture, services, API, deployment |
| **[GitHub Wiki](https://github.com/mindevis/qStack/wiki)** | Full docs: DB schemas, gRPC API, NATS events, contributing |
| [CHANGELOG.md](./CHANGELOG.md) | Version history |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Contribution guidelines |

## 🚀 Quick Start

```bash
git clone https://github.com/mindevis/qStack.git && cd qStack

# Local infrastructure (infra + all services)
docker-compose up -d

# Build & test
make build-all && make test-all
```

Detailed dev setup → **[Development](https://github.com/mindevis/qStack/wiki/Development)**

## 🏗 Services (9 microservices)

| Service | Replicas | Responsibility |
|---------|----------|----------------|
| **qstack-api** | 3+ (stateless) | API Gateway, Auth (JWT), Dashboards (PCI-DSS: Admin/User), Saga orchestration |
| **qstack-compute** | 1 (leader) | VMs, Hosts, Clusters, Scheduler, Live Migration, HA |
| **qstack-storage** | 1 | Pools, Volumes, Snapshots (Libvirt, Ceph RBD, iSCSI) |
| **qstack-network** | 1 | Networks, IPAM, Subnets, DHCP |
| **qstack-image** | 1 | Image CRUD, Build/Convert, Vulnerability scanning |
| **qstack-billing** | 1 | Tenants, Usage Meter, Invoices, Stripe, Quota |
| **qstack-backup** | 1 | Backup scheduling, Restore, Verify |
| **qstack-ai** | 1 | Advisor, Predictor, AutoHeal, Assistant |
| **qstack-agent** | N (per host) | Hypervisor agent (libvirt, heartbeat, resource reporting) |

## 🛠 Stack

Go · libvirt/KVM · gRPC mTLS · NATS JetStream · PostgreSQL + sqlc · Gin · React (Vite + Ant Design) · OpenTelemetry · Prometheus/Grafana/Loki · GlitchTip · OpenBao/Vault · Talos Linux / K8s
