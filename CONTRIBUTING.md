# Руководство по вкладу в qStack / Contributing to qStack

> **Default language:** Русский (Russian) • [English version below](#contributing-to-qstack)

---

## Русский

### Обзор

qStack — это монорепозиторий микросервисов на Go. Код организован следующим образом:

| Директория | Описание |
|---|---|
| `services/` | Микросервисы, каждый в своей поддиректории |
| `pkg/` | Общий код, используемый несколькими сервисами |
| `agent/` | Агентный слой, независимая компонента |

---

### 1. Настройка среды разработки

Подробная инструкция по настройке окружения доступна в **[DEVELOPMENT.md](DEVELOPMENT.md)**. Кратко:

1. Установите **Go 1.23+**
2. Установите **Docker** и **Docker Compose**
3. Клонируйте репозиторий
4. Установите [golangci-lint](https://golangci-lint.run/usage/install/)
5. Запустите локальную среду через Docker Compose:

```bash
docker compose up -d
```

---

### 2. Стиль кода

#### Go

- Следуйте [Effective Go](https://go.dev/doc/effective_go) и [Uber Go Style Guide](https://github.com/uber-go/guide/blob/master/style.md).
- Форматируйте код через `gofmt` / `goimports`.
- Используйте `golangci-lint` для статического анализа. В конфигурации проекта (`golangci.yml`) определены включённые линтеры.
- Запустите линтинг перед коммитом:

```bash
golangci-lint run ./...
```

#### Именование

- Пакеты — `snake_case`, одно слово, краткое и точное.
- Публичные идентификаторы — `PascalCase`.
- Приватные идентификаторы — `camelCase`.
- Константы — `UpperCamelCase` или `ALL_CAPS_SNAKE` для магических чисел.

#### Организация импортов

Группируйте импорты в три блока (пустая строка между ними):

1. Стандартная библиотека Go
2. Внешние зависимости
3. Внутренние импорты qStack

Используйте `goimports` для автоматической сортировки.

---

### 3. Формат коммитов (Conventional Commits)

Все коммиты должны следовать формату [Conventional Commits](https://www.conventionalcommits.org/ru/v1.0.0/):

```
<тип>(<область>): <описание>

[тело коммита — необязательно]

[подвал — необязательно]
```

**Типы:**

| Тип | Описание |
|---|---|
| `feat` | Новая функциональность |
| `fix` | Исправление ошибки |
| `docs` | Только документация |
| `style` | Форматирование, точки, пробелы (без изменений логики) |
| `refactor` | Рефакторинг кода |
| `test` | Добавление или изменение тестов |
| `chore` | Обновление сборки, конфигурации, зависимости |
| `perf` | Улучшение производительности |
| `ci` | Изменения CI/CD |

**Область** — сервис или компонент (`auth`, `api`, `pkg`, `agent`, `docker`).

**Примеры:**

```
feat(auth): добавить OAuth2 поддержку для входа
fix(api): исправить десериализацию JSON в запросах с пагинацией
docs: обновить руководство по вступлению
refactor(pkg): вынести валидацию email в отдельную функцию
test(agent): добавить интеграционные тесты для обработчика задач
```

**BREAKING CHANGE:** укажите в подвале:

```
feat(api): изменить формат ответа API

BREAKING CHANGE: поле `data` теперь массив, не объект
```

---

### 4. Ветки: соглашения об именовании

| Тип ветки | Формат | Пример |
|---|---|---|
| Фича | `feature/<описание>` | `feature/oauth2-login` |
| Исправление | `fix/<описание>` | `fix/json-deserialization` |
| Рефакторинг | `refactor/<описание>` | `refactor/email-validation` |
| Документация | `docs/<описание>` | `docs/contributing-guide` |
| Служебная | `chore/<описание>` | `chore/update-dependencies` |

Ветки создавайте из `main`. Короткие описания через дефис, английский язык.

---

### 5. Процесс Merge Request / Pull Request

1. **Создайте ветку** из `main` по соглашению выше.
2. **Напишите код** с тестами.
3. **Запустите линтинг и тесты:**

```bash
golangci-lint run ./...
go test ./...
```

4. **Сделайте коммиты** в формате Conventional Commits.
5. **Откройте Pull Request** с заполненным шаблоном:
   - Краткое описание изменений
   - Связанные задачи (ссылки на issue)
   - Список breaking-изменений, если есть
   - Скриншоты для UI-изменений (если применимо)

6. **Code Review:** PR не объединяется без одобрения хотя бы одного ревьюера.
7. **CI должен быть зелёным** перед merge.
8. После слияния удалите ветку.

**Merge strategy:** Squash and merge для фич, Rebase merge для исправлений.

---

### 6. Тестирование

#### Требования

- Покрытие тестами ≥ **80 %** для новой функциональности.
- Юнит-тесты для чистой логики.
- Интеграционные тесты для взаимодействия с БД и внешними API.

#### Запуск тестов

```bash
# Все тесты
go test ./...

# Тесты конкретного сервиса
cd services/auth && go test ./...

# С покрытием
go test -cover ./...

# Проверка порога покрытия
go test -coverprofile=coverage.out ./... && go tool cover -func=coverage.out
```

#### Тестовые зависимости

Для интеграционных тестов используйте локальные сервисы из Docker Compose или моки. Не подключайтесь к продакшену.

---

### 7. Docker Compose: локальная разработка

Проект использует Docker Compose для запуска зависимостей (БД, кэш, брокер сообщений и т.д.).

```bash
# Запуск всех зависимостей
docker compose up -d

# Статус
docker compose ps

# Логи конкретного сервиса
docker compose logs -f postgres

# Остановка
docker compose down

# Пересоздание с чистыми данными
docker compose down -v && docker compose up -d
```

Для разработки отдельного сервиса:

```bash
# Запустить только зависимости, без самого сервиса
docker compose up -d

# Запустить сервис локально (Go hot-reload)
cd services/auth && air   # или go run ./...
```

Сервисы слушают порты, определённые в `docker-compose.yml`. Проверьте маппинг портов в конфигурации.

---

### 8. Конвенции кодирования

#### Обработка ошибок

- Никогда не игнорируйте ошибки. Используйте `if err != nil`.
- Оберните ошибки с контекстом: `fmt.Errorf("calling auth service: %w", err)`.
- В критических путях логгируйте ошибки с уровнем `error`.

#### Логирование

- Структурированное логирование через `slog` или `zap`.
- Уровень `debug` — детали для разработчиков.
- Уровень `info` — важные события.
- Уровень `warn` — обратимые проблемы.
- Уровень `error` — необратимые ошибки.

#### API

- RESTful endpoints с версионированием: `/api/v1/...`.
- Пагинация: `?page=1&limit=20`.
- Ответы: `{"status": "ok", "data": {...}}` или `{"status": "error", "message": "..."}`.
- Открыть OpenAPI/Swagger спецификацию для каждого сервиса.

#### Конфигурация

- Чтение через переменные окружения или `.env` (не коммитить `.env`).
- Валидация конфигурации на старте.
- Таймауты и retry-policy должны быть конфигурируемыми.

#### Безопасность

- Никаких секретов в коде или Git. Используйте `.env` и variable secrets.
- Валидируйте входные данные на границе.
- Аутентификация через JWT с валидацией подписи.
- Rate limiting на публичных эндпоинтах.

---

### 9. Чек-лист перед отправкой PR

- [ ] Код отформатирован (`gofmt`, `goimports`)
- [ ] `golangci-lint` прошёл без ошибок
- [ ] Тесты написаны и проходят
- [ ] Покрытие тестами ≥ 80 % для нового кода
- [ ] Коммиты в формате Conventional Commits
- [ ] Локальный Docker Compose запущен, всё работает
- [ ] Документация обновлена (если применимо)
- [ ] Breaking changes описаны

---

<hr>

---

## Contributing to qStack

### Overview

qStack is a Go microservice monorepo. The codebase is organized as follows:

| Directory | Description |
|---|---|
| `services/` | Microservices, each in its own subdirectory |
| `pkg/` | Shared code used by multiple services |
| `agent/` | Agent layer, a standalone component |

---

### 1. Development Environment Setup

For detailed setup instructions, see **[DEVELOPMENT.md](DEVELOPMENT.md)**. In short:

1. Install **Go 1.23+**
2. Install **Docker** and **Docker Compose**
3. Clone the repository
4. Install [golangci-lint](https://golangci-lint.run/usage/install/)
5. Start the local environment with Docker Compose:

```bash
docker compose up -d
```

---

### 2. Code Style

#### Go

- Follow [Effective Go](https://go.dev/doc/effective_go) and [Uber Go Style Guide](https://github.com/uber-go/guide/blob/master/style.md).
- Format code with `gofmt` / `goimports`.
- Use `golangci-lint` for static analysis. The project's `golangci.yml` defines the enabled linters.
- Run linting before committing:

```bash
golangci-lint run ./...
```

#### Naming

- Packages — `snake_case`, single word, short and precise.
- Exported identifiers — `PascalCase`.
- Unexported identifiers — `camelCase`.
- Constants — `UpperCamelCase` or `ALL_CAPS_SNAKE` for magic numbers.

#### Import Organization

Group imports into three blocks (empty line between blocks):

1. Go standard library
2. External dependencies
3. Internal qStack imports

Use `goimports` for automatic sorting.

---

### 3. Commit Message Format (Conventional Commits)

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>(<scope>): <description>

[body — optional]

[footer — optional]
```

**Types:**

| Type | Description |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, whitespace (no logic changes) |
| `refactor` | Code refactoring |
| `test` | Adding or changing tests |
| `chore` | Build, config, dependencies |
| `perf` | Performance improvement |
| `ci` | CI/CD changes |

**Scope** — service or component (`auth`, `api`, `pkg`, `agent`, `docker`).

**Examples:**

```
feat(auth): add OAuth2 support for login
fix(api): fix JSON deserialization in paginated requests
docs: update contributing guide
refactor(pkg): extract email validation into separate function
test(agent): add integration tests for task handler
```

**BREAKING CHANGE:** declare in the footer:

```
feat(api): change API response format

BREAKING CHANGE: `data` field is now an array, not an object
```

---

### 4. Branch Naming Conventions

| Branch type | Format | Example |
|---|---|---|
| Feature | `feature/<description>` | `feature/oauth2-login` |
| Bugfix | `fix/<description>` | `fix/json-deserialization` |
| Refactor | `refactor/<description>` | `refactor/email-validation` |
| Documentation | `docs/<description>` | `docs/contributing-guide` |
| Chore | `chore/<description>` | `chore/update-dependencies` |

Create branches from `main`. Use kebab-case, English, short descriptions.

---

### 5. Pull Request Process

1. **Create a branch** from `main` following the naming conventions above.
2. **Write code** with tests.
3. **Run linter and tests:**

```bash
golangci-lint run ./...
go test ./...
```

4. **Commit** using Conventional Commits format.
5. **Open a Pull Request** with the template filled:
   - Short description of changes
   - Related issues (links)
   - List of breaking changes, if any
   - Screenshots for UI changes (if applicable)

6. **Code Review:** PR must be approved by at least one reviewer.
7. **CI must pass** before merging.
8. **Delete the branch** after merging.

**Merge strategy:** Squash and merge for features, Rebase merge for fixes.

---

### 6. Testing

#### Requirements

- Test coverage ≥ **80 %** for new functionality.
- Unit tests for pure logic.
- Integration tests for database and external API interactions.

#### Running Tests

```bash
# All tests
go test ./...

# Tests for a specific service
cd services/auth && go test ./...

# With coverage
go test -cover ./...

# Check coverage threshold
go test -coverprofile=coverage.out ./... && go tool cover -func=coverage.out
```

#### Test Dependencies

Use local Docker Compose services or mocks for integration tests. Never connect to production.

---

### 7. Docker Compose: Development Workflow

The project uses Docker Compose to run dependencies (database, cache, message broker, etc.).

```bash
# Start all dependencies
docker compose up -d

# Status
docker compose ps

# Logs for a specific service
docker compose logs -f postgres

# Stop
docker compose down

# Recreate with clean state
docker compose down -v && docker compose up -d
```

For developing a single service:

```bash
# Start dependencies only
docker compose up -d

# Run the service locally (hot-reload)
cd services/auth && air   # or go run ./...
```

Services listen on ports defined in `docker-compose.yml`. Check port mappings in the configuration.

---

### 8. Coding Conventions

#### Error Handling

- Never ignore errors. Use `if err != nil`.
- Wrap errors with context: `fmt.Errorf("calling auth service: %w", err)`.
- Log errors at `error` level on critical paths.

#### Logging

- Structured logging via `slog` or `zap`.
- `debug` — developer-level details.
- `info` — important events.
- `warn` — recoverable issues.
- `error` — irreversible failures.

#### API

- RESTful endpoints with versioning: `/api/v1/...`.
- Pagination: `?page=1&limit=20`.
- Responses: `{"status": "ok", "data": {...}}` or `{"status": "error", "message": "..."}`.
- Maintain OpenAPI/Swagger specs per service.

#### Configuration

- Read from environment variables or `.env` (never commit `.env`).
- Validate configuration at startup.
- Timeouts and retry-policy must be configurable.

#### Security

- No secrets in code or Git. Use `.env` and secret management.
- Validate input at boundaries.
- Authentication via JWT with signature validation.
- Rate limiting on public endpoints.

---

### 9. Pre-PR Checklist

- [ ] Code formatted (`gofmt`, `goimports`)
- [ ] `golangci-lint` passes cleanly
- [ ] Tests written and passing
- [ ] Test coverage ≥ 80 % for new code
- [ ] Commits follow Conventional Commits
- [ ] Local Docker Compose running, everything works
- [ ] Documentation updated (if applicable)
- [ ] Breaking changes described
