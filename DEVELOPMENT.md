# Разработка qStack / qStack Development

> Bilingual guide: **русский** (по умолчанию) / **English**
>
> Каждый раздел представлен на русском языке, затем на английском.

---

## 1. Требования / Prerequisites

### Обязательные инструменты / Required tools

| Инструмент | Версия | Зачем / Purpose |
|---|---|---|
| **Go** | 1.24+ | Основной язык разработки / Main development language |
| **Docker** | 24.0+ | Запуск инфраструктуры и сборка образов / Run infra and build images |
| **docker-compose** | 2.20+ | Оркестрация локальной инфраструктуры / Local infra orchestration |
| **protoc** | 24+ | Генерация gRPC-кода из `.proto` / Generate gRPC code from `.proto` |
| **sqlc** | 1.24+ | Генерация типобезопасного Go-кода из SQL / Generate type-safe Go from SQL |

### Рекомендуемые инструменты / Recommended tools

| Инструмент | Зачем / Purpose |
|---|---|
| **golangci-lint** | Линтинг Go-кода / Go code linting |
| **air** | Hot reload при разработке / Hot reload during development |
| **kind** или **k3d** | Локальный Kubernetes-кластер / Local K8s cluster |
| **VS Code** + Dev Container | Готовое окружение разработки / Pre-configured dev environment |

#### Установка / Installation

**Linux (Ubuntu/Debian):**
```bash
# Go
wget https://go.dev/dl/go1.24.0.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.24.0.linux-amd64.tar.gz

# protoc
sudo apt install -y protobuf-compiler

# sqlc
curl -sSfL https://github.com/sqlc-dev/sqlc/raw/main/install.sh | sh -s -- --bin /usr/local/bin

# golangci-lint
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b /usr/local/bin v1.62.0

# air
go install github.com/cosmtrek/air@latest

# kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.24.0/kind-linux-amd64
chmod +x ./kind && sudo mv ./kind /usr/local/bin/
```

**macOS:**
```bash
brew install go protobuf sqlc golangci-lint
go install github.com/cosmtrek/air@latest
brew install kind
```

**Windows (WSL2):**
```bash
# Используйте WSL2 и следуйте инструкции для Linux
# Use WSL2 and follow the Linux instructions
```

---

## 2. Настройка рабочего пространства / Workspace Setup

### Go workspace

Проект использует Go workspace (`go.work`) для управления несколькими модулями в одном репозитории:

The project uses a Go workspace (`go.work`) to manage multiple modules in a single repository:

```
qStack/
├── go.work              # Workspace файл
├── pkg/                 # Общий SDK
│   └── go.mod
├── services/
│   ├── api/             # qstack-api
│   │   └── go.mod
│   ├── compute/         # qstack-compute
│   │   └── go.mod
│   ├── storage/         # qstack-storage
│   │   └── go.mod
│   ├── network/         # qstack-network
│   │   └── go.mod
│   ├── image/           # qstack-image
│   │   └── go.mod
│   ├── billing/         # qstack-billing
│   │   └── go.mod
│   ├── backup/          # qstack-backup
│   │   └── go.mod
│   └── ai/              # qstack-ai
│       └── go.mod
└── agent/               # qstack-agent
    └── go.mod
```

#### Инициализация workspace / Initialize workspace

```bash
# Клонирование / Clone
git clone <repo-url> qStack
cd qStack

# Инициализация workspace
go work init
go work use ./pkg ./services/api ./services/compute ./services/storage \
    ./services/network ./services/image ./services/billing \
    ./services/backup ./services/ai ./agent

# Проверка — все зависимости должны разрешиться
go work sync
```

#### Обновление workspace после добавления нового модуля / After adding a new module

```bash
go work use ./services/new-service
go work sync
```

---

## 3. Локальная инфраструктура / Local Infrastructure

### Запуск с docker-compose / Run with docker-compose

Проект включает `docker-compose.yml` с полной инфраструктурой для локальной разработки:

The project includes a `docker-compose.yml` with full infrastructure for local development:

```yaml
# Основные сервисы / Main services
services:
  postgres:     # PostgreSQL (все схемы сервисов)
  nats:         # NATS (event bus, 3-узловой кластер)
  ca:           # Внутренний CA для mTLS
  prometheus:   # Метрики / Metrics
  grafana:      # Дашборды / Dashboards
  loki:         # Сбор логов / Log aggregation
  glitchtip:    # Трекинг ошибок / Error tracking
```

```bash
# Запуск всей инфраструктуры / Start all infrastructure
make dev-up
# или / or
docker compose up -d

# Проверка статуса / Check status
docker compose ps

# Просмотр логов / View logs
docker compose logs -f postgres
docker compose logs -f nats

# Остановка / Stop
make dev-down
# или / or
docker compose down

# Полная очистка (включая volumes) / Full cleanup including volumes
docker compose down -v
```

### Доступ к инфраструктуре / Accessing infrastructure

| Сервис | Локальный адрес / Local address | Учётные данные / Credentials |
|---|---|---|
| PostgreSQL | `localhost:5432` | `postgres` / `qstack_dev` |
| NATS | `localhost:4222` | — |
| Prometheus | `http://localhost:9090` | — |
| Grafana | `http://localhost:3000` | `admin` / `admin` |
| GlitchTip | `http://localhost:8081` | См. `.env` / See `.env` |

---

## 4. Разработка отдельных сервисов / Developing Individual Services

### Структура сервиса / Service structure

Каждый сервис имеет собственную структуру:

Each service has its own structure:

```
services/compute/
├── cmd/qstack-compute/
│   └── main.go           # Точка входа / Entry point
├── internal/
│   ├── api/              # gRPC-сервер / gRPC server
│   ├── handler/          # Обработчики событий / Event handlers
│   ├── repository/       # Работа с БД / Database access
│   ├── domain/           # Доменные модели / Domain models
│   └── saga/             # Оркестрация сága / Saga orchestration
├── sql/
│   └── queries/          # SQL-запросы для sqlc
├── schema/
│   └── 001_init.sql     # Миграции / Migrations
├── go.mod
└── Dockerfile
```

### Запуск одного сервиса / Running a single service

```bash
# Перейти в каталог сервиса / Change to service directory
cd services/compute

# Запуск напрямую / Run directly
go run ./cmd/qstack-compute

# С конфигурационным файлом / With config file
QSTACK_CONFIG=../configs/compute.dev.yaml go run ./cmd/qstack-compute
```

### Переменные окружения / Environment variables

Каждый сервис считывает конфигурацию из переменных окружения и YAML-файла:

Each service reads configuration from environment variables and YAML file:

```bash
# Общие переменные / Common variables
QSTACK_CONFIG=../configs/compute.dev.yaml
QSTACK_LOG_LEVEL=debug

# Подключение к базе данных / Database connection
QSTACK_DB_HOST=localhost
QSTACK_DB_PORT=5432
QSTACK_DB_USER=postgres
QSTACK_DB_PASS=qstack_dev
QSTACK_DB_SCHEMA=compute_schema

# Подключение к NATS / NATS connection
QSTACK_NATS_URL=nats://localhost:4222

# Адрес gRPC / gRPC address
QSTACK_GRPC_ADDR=:50051
```

---

## 5. Hot Reload с air / Hot Reload with air

### Установка / Installation

```bash
go install github.com/cosmtrek/air@latest
```

### Использование / Usage

```bash
# В каталоге сервиса / In the service directory
cd services/compute
air

# Air автоматически следит за изменениями файлов и перезапускает сервис
# Air automatically watches for file changes and restarts the service
```

### Конфигурация air / Air configuration

Создайте `.air.toml` в корне проекта или в каталоге сервиса:

Create `.air.toml` in the project root or service directory:

```toml
root = "."
testdata_dir = "testdata"
tmp_dir = "tmp"

[build]
  cmd = "go build -o tmp/main ./cmd/qstack-compute"
  bin = "tmp/main"
  include_ext = ["go", "mod", "sum"]
  exclude_dir = ["tmp", "vendor"]
  log = "air.log"
  delay = 1000  # ms
```

> **Совет:** Запустите сначала инфраструктуру (`make dev-up`), затем `air` для каждого сервиса, который вы разрабатываете.

> **Tip:** Start infrastructure first (`make dev-up`), then run `air` for each service you're developing.

---

## 6. Миграции базы данных / Database Migrations

### Структура миграций / Migration structure

Каждый сервис хранит миграции в своём каталоге:

Each service stores migrations in its own directory:

```
services/
├── compute/
│   └── schema/
│       ├── 001_init.sql
│       └── 002_add_hosts.sql
├── storage/
│   └── schema/
│       └── 001_init.sql
└── ...
```

### Запуск миграций / Running migrations

```bash
# Все миграции / All services
make dev-migrate

# Один сервис / Single service
cd services/compute
QSTACK_DB_HOST=localhost QSTACK_DB_PASS=qstack_dev \
    go run ./cmd/qstack-compute migrate

# Откат на одну миграцию / Rollback one step
go run ./cmd/qstack-compute migrate -down

# Проверка статуса / Check status
go run ./cmd/qstack-compute migrate status
```

### Генерация кода с sqlc / Generate code with sqlc

После изменения SQL-запросов или схемы перегенерируйте Go-код:

After changing SQL queries or schema, regenerate Go code:

```bash
# Генерация для одного сервиса / Generate for one service
cd services/compute
sqlc generate

# Генерация для всех сервисов / Generate for all services
make dev-sqlc
```

Файл конфигурации `sqlc.yaml` находится в каждом сервисе:

Each service has its own `sqlc.yaml` configuration file:

```yaml
version: "2"
sql:
  - engine: "postgresql"
    schema: "schema"
    queries: "sql/queries"
    db_url: "postgres://postgres:qstack_dev@localhost:5432/qstack?sslmode=disable"
    gen:
      go:
        package: "repository"
        out: "internal/repository"
        schema: "compute_schema"
```

---

## 7. Генерация gRPC-кода / gRPC Code Generation

### Протобуф / Protobuf

Все `.proto` файлы находятся в каталоге `proto/`:

All `.proto` files are located in `proto/`:

```
proto/
├── compute/
│   ├── vm.proto
│   └── host.proto
├── storage/
│   └── volume.proto
└── ...
```

### Генерация / Generate

```bash
# Генерация gRPC-кода для всех сервисов / Generate for all services
make dev-proto

# Или вручную / Or manually
cd proto
protoc --go_out=../pkg/grpc \
       --go-grpc_out=../pkg/grpc \
       --proto_path=. \
       compute/vm.proto
```

---

## 8. Тестирование / Running Tests

```bash
# Все тесты (unit + integration) / All tests (unit + integration)
make dev-test

# Тесты одного сервиса / Tests for one service
cd services/compute
go test ./... -v

# Только unit-тесты / Unit tests only
go test ./... -v -short

# Интеграционные тесты (требуют docker-compose) / Integration tests (requires docker-compose)
go test ./... -v -race -tags=integration

# Тесты с покрытием / Tests with coverage
go test ./... -coverprofile=coverage.out
go tool cover -html=coverage.out

# Тесты с бенчмарками / Benchmarks
go test ./... -bench=. -benchmem
```

> **Важно:** Интеграционные тесты подключаются к PostgreSQL и NATS, запущенным через docker-compose. Убедитесь, что инфраструктура запущена перед запуском интеграционных тестов.

> **Important:** Integration tests connect to PostgreSQL and NATS running via docker-compose. Make sure infrastructure is up before running integration tests.

---

## 9. Линтинг / Linting

```bash
# Линтинг всего проекта / Lint entire project
make dev-lint

# Линтинг одного сервиса / Lint one service
cd services/compute
golangci-lint run

# Автоисправление / Auto-fix
golangci-lint run --fix

# Линтинг протобуф-файлов / Lint proto files
protolint lint proto/
```

Конфигурация линтера находится в `.golangci.yml`:

Linter configuration is in `.golangci.yml`:

```yaml
linters:
  enable:
    - errcheck
    - gosec
    - gosimple
    - govet
    - staticcheck
    - unused
```

---

## 10. Сборка Docker-образов / Building Docker Images

### Одиночный сервис / Single service

```bash
# Сборка одного образа / Build one image
docker build -t qstack/compute:dev -f services/compute/Dockerfile services/compute

# Сборка с кэшем / Build with cache
docker build --build-arg GOFLAGS="-tags=dev" -t qstack/compute:dev services/compute
```

### Все сервисы / All services

```bash
# Сборка всех образов / Build all images
make docker-build

# Сборка и пуш в registry / Build and push
make docker-push
```

### Multistage-билд / Multistage build

Каждый `Dockerfile` использует multistage сборку:

Each `Dockerfile` uses multistage build:

```dockerfile
# Stage 1: Build
FROM golang:1.24-alpine AS builder
WORKDIR /build
COPY . .
RUN CGO_ENABLED=0 go build -o /qstack-compute ./cmd/qstack-compute

# Stage 2: Runtime
FROM alpine:3.20
COPY --from=builder /qstack-compute /usr/local/bin/
CMD ["qstack-compute"]
```

---

## 11. Развёртывание в локальный Kubernetes / Deploying to Local K8s

### kind (Kubernetes in Docker)

```bash
# Создание кластера / Create cluster
make kind-up
# или / or
kind create cluster --name qstack-dev --config kind-config.yaml

# Проверка кластера / Verify cluster
kubectl cluster-info --context kind-qstack-dev
kubectl get nodes
```

### k3d

```bash
# Создание кластера / Create cluster
make k3d-up
# или / or
k3d cluster create qstack-dev --servers 1 --agents 2
```

### Развёртывание / Deploy

```bash
# Загрузить образы в кластер / Load images into cluster (kind)
kind load docker-image qstack/api:dev qstack/compute:dev --name qstack-dev

# Развёртывание инфраструктуры / Deploy infrastructure
kubectl apply -f k8s/common/
kubectl apply -f k8s/api/
kubectl apply -f k8s/compute/
kubectl apply -f k8s/storage/
kubectl apply -f k8s/network/
kubectl apply -f k8s/image/
kubectl apply -f k8s/billing/
kubectl apply -f k8s/backup/
kubectl apply -f k8s/ai/

# Или одной командой / Or with one command
make kind-deploy

# Проверка / Verify
kubectl get pods -A
kubectl logs -l app=qstack-api
```

### E2E-тесты / E2E tests

```bash
# Запуск E2E-тестов против локального кластера / Run E2E tests against local cluster
make kind-e2e

# Очистка / Cleanup
make kind-down
# или / or
kind delete cluster --name qstack-dev
```

### kind-config.yaml

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
    extraPortMappings:
      - containerPort: 80
        hostPort: 80
        protocol: TCP
      - containerPort: 443
        hostPort: 443
        protocol: TCP
  - role: worker
  - role: worker
```

---

## 12. Режим отладки / Debug Mode

### Переменные окружения / Environment variables

| Переменная / Variable | Описание / Description |
|---|---|
| `QSTACK_DEBUG=1` | Расширенное логирование, отключение автоматического открытия circuit breaker, увеличенные таймауты / Extra logging, disable circuit breaker open state, longer timeouts |
| `QSTACK_MOCK_PROVIDER=1` | Использовать mock-реализацию libvirt вместо реального гипервизора / Use mock libvirt instead of real hypervisor |
| `QSTACK_FAKETIME=1` | Симуляция прохождения времени для тестов биллинга и бэкапов / Simulate time passage for billing and backup tests |

### Пример использования / Usage example

```bash
# Отладка с mock-провайдером / Debug with mock provider
QSTACK_DEBUG=1 QSTACK_MOCK_PROVIDER=1 go run ./cmd/qstack-compute

# Отладка с фиктивным временем / Debug with fake time
QSTACK_DEBUG=1 QSTACK_FAKETIME=1 go run ./cmd/qstack-billing
```

### Демонстрация / Demo

```bash
# Полный режим отладки / Full debug mode
export QSTACK_DEBUG=1
export QSTACK_MOCK_PROVIDER=1
export QSTACK_LOG_LEVEL=debug
export QSTACK_FAKETIME=1

make dev-up
cd services/compute && air
```

---

## 13. Быстрый старт / Quick Start

```bash
# 1. Клонировать / Clone
git clone <repo-url> qStack && cd qStack

# 2. Настроить workspace / Setup workspace
go work init && go work use ./pkg ./services/... ./agent && go work sync

# 3. Установить dev-инструменты / Install dev tools
go install github.com/cosmtrek/air@latest

# 4. Запустить инфраструктуру / Start infrastructure
make dev-up

# 5. Запустить миграции / Run migrations
make dev-migrate

# 6. Сгенерировать код / Generate code
make dev-sqlc
make dev-proto

# 7. Запустить сервис для разработки / Start developing
cd services/compute && air
```

---

## 14. Справочник по Makefile / Makefile Reference

| Целевая команда / Target | Описание / Description |
|---|---|
| `make dev-up` | Запустить локальную инфраструктуру / Start local infrastructure |
| `make dev-down` | Остановить инфраструктуру / Stop infrastructure |
| `make dev-test` | Запустить все тесты / Run all tests |
| `make dev-lint` | Запустить линтинг / Run linting |
| `make dev-migrate` | Выполнить миграции БД / Run database migrations |
| `make dev-sqlc` | Сгенерировать код sqlc / Generate sqlc code |
| `make dev-proto` | Сгенерировать gRPC-код / Generate gRPC code |
| `make docker-build` | Собрать все Docker-образы / Build all Docker images |
| `make docker-push` | Собрать и отправить образы / Build and push images |
| `make kind-up` | Создать кластер kind / Create kind cluster |
| `make kind-deploy` | Развернуть в kind / Deploy to kind |
| `make kind-e2e` | Запустить E2E-тесты / Run E2E tests |
| `make kind-down` | Удалить кластер kind / Delete kind cluster |

---

## 15. Troubleshooting / Устранение проблем

### Проблемы с Go workspace / Go workspace issues

```bash
# Синхронизация зависимостей / Sync dependencies
go work sync

# Обновление go.work / Refresh go.work
go work edit -use=./services/api ./services/compute
```

### Проблемы с PostgreSQL / PostgreSQL issues

```bash
# Пересоздать БД / Recreate database
docker compose down -v
docker compose up -d postgres
sleep 5
make dev-migrate
```

### Проблемы с NATS / NATS issues

```bash
# Перезапуск NATS / Restart NATS
docker compose restart nats
docker compose logs -f nats
```

### Очистка проекта / Clean project

```bash
# Полная очистка / Full cleanup
make dev-down
docker compose down -v
rm -rf services/*/tmp
go clean -cache -modcache
```
