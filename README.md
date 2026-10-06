# ITK Academy — Events Aggregator

Backend сервис-агрегатор над Events Provider API.

## Что это

Сервис выступает промежуточным слоем между клиентами и внешним Events Provider API. Добавляет:

- **Кэширование** — события хранятся в локальной PostgreSQL, фоновый воркер синхронизирует их раз в день.
- **Удобный REST API** — привычная page/page_size пагинация вместо cursor-based, фильтр по дате.
- **Валидацию** — проверка статуса события, дедлайна, доступности места перед регистрацией.
- **Регистрацию и отмену** — проксирует запросы, хранит `ticket_id` локально.
- **Наблюдаемость** — JSON-логи с `request_id`, Prometheus-метрики, опционально Sentry.

## Стек

- Python 3.11+, FastAPI, Uvicorn
- SQLAlchemy 2.0 (async) + Alembic + PostgreSQL
- Celery (worker + beat), брокер — PostgreSQL (kombu SQLAlchemy transport)
- httpx — асинхронный HTTP-клиент
- structlog — JSON-логи
- Sentry — отлов ошибок (опционально)
- Prometheus — метрики
- uv, ruff, pytest

## API

Полная документация — по `/docs` после запуска (Swagger UI).

| Метод | URL | Описание |
|---|---|---|
| GET | `/api/health` | Health-check |
| GET | `/api/events` | Список событий (пагинация, `date_from`) |
| GET | `/api/events/{id}` | Детали события |
| GET | `/api/events/{id}/seats` | Свободные места (кэш 30 сек) |
| POST | `/api/tickets` | Регистрация на событие |
| DELETE | `/api/tickets/{id}` | Отмена регистрации |
| POST | `/api/sync/trigger` | Ручной запуск синхронизации |
| GET | `/metrics` | Prometheus-метрики |

## Архитектура

Проект разделён на слои — каждый знает только про следующий снизу:

```
┌─────────────────────────────────────────────┐
│  API (FastAPI)                              │  HTTP, Pydantic-схемы
│  api/                                       │  → вызывает usecases
├─────────────────────────────────────────────┤
│  Services / Usecases                        │  бизнес-логика
│  services/                                  │  → repositories + внешний клиент
├─────────────────────────────────────────────┤
│  Repositories (Protocol + SQLAlchemy)       │  доступ к данным
│  repositories/                              │  → ORM-модели
├─────────────────────────────────────────────┤
│  Domain entities                            │  чистые dataclass'ы
│  domain/                                    │  (без зависимостей от SQLAlchemy)
├─────────────────────────────────────────────┤
│  DB (SQLAlchemy models, UoW)                │  PostgreSQL
│  models/, db/                               │
└─────────────────────────────────────────────┘
```

**Ключевые принципы:**

- **Бизнес-логика не знает про БД.** Usecases работают с domain-entities (`domain/entities.py`) и Protocol'ами (`repositories/protocols.py`), а не с ORM-моделями.
- **Репозитории делают `flush()`, а не `commit()`.** Транзакцию фиксирует `UnitOfWork` (`db/uow.py`) в usecase.
- **Клиент внешнего API — Protocol.** Usecases зависят от `services/ports.py::EventsProvider`, а не от конкретного `EventsProviderClient`.
- **Ошибки провайдера маппятся в HTTP в эндпоинтах**, а не в сервисном слое.

```
src/itk_academy/
├── api/                    FastAPI: роутеры, схемы, middleware, DI
│   ├── v1/
│   │   ├── deps.py         зависимости (репозитории, usecases, UoW)
│   │   ├── events.py       GET /events, /events/{id}, /seats
│   │   ├── tickets.py      POST /tickets, DELETE /tickets/{id}
│   │   ├── sync.py         POST /sync/trigger
│   │   └── schemas/        Pydantic-схемы ответов
│   └── middleware.py       request_id
├── core/
│   ├── cache.py            TTL-кэш
│   └── logging.py          structlog
├── db/
│   ├── base.py             DeclarativeBase
│   ├── session.py          engine, session factory
│   └── uow.py              UnitOfWork
├── domain/
│   └── entities.py         PlaceEntity, EventEntity, TicketEntity, SyncMetadataEntity
├── events_provider/        клиент внешнего API
│   ├── client.py           EventsProviderClient
│   ├── dto.py              DTO + parse_* функции
│   ├── paginator.py        EventsPaginator
│   └── exceptions.py
├── models/                 SQLAlchemy-модели
├── repositories/           Protocol + SQLAlchemy-реализации
├── services/               usecases (бизнес-логика)
│   ├── ports.py            Protocol внешнего клиента
│   ├── seats.py            GetSeatsUsecase
│   ├── sync.py             SyncEventsUsecase (батч-upsert)
│   └── tickets.py          CreateTicketUsecase, CancelTicketUsecase
└── worker/                 Celery app + tasks
```

## Переменные окружения

См. `.env.example`. В проде задаются через панель платформы LMS.

- `DATABASE_URL` — `postgresql+asyncpg://user:pass@host:5432/db`
- `EVENTS_PROVIDER_URL` — URL провайдера (локально — `https://events-provider.dev-2.python-labs.ru`, в кластере — внутренний DNS)
- `EVENTS_PROVIDER_API_KEY` — ключ из LMS-профиля
- `SENTRY_DSN` — опционально, для отлова ошибок в проде
- `SYNC_HOUR_UTC` — час запуска ежедневной синхронизации (по умолчанию 2)
- `TIMEZONE` — часовой пояс для интерпретации `date_from` (по умолчанию `Europe/Moscow`)

## Локальный запуск

```bash
uv sync
cp .env.example .env   # заполнить значения
docker compose up -d   # поднять Postgres
uv run alembic upgrade head
uv run uvicorn itk_academy.main:app --reload
```

Открой http://localhost:8000/docs.

### Фоновый воркер (отдельно от uvicorn)

Терминал 1 — worker:

```bash
uv run celery -A itk_academy.worker.celery_app worker -P solo -l INFO
```

Терминал 2 — beat (расписание):

Linux/macOS:
```bash
uv run celery -A itk_academy.worker.celery_app beat -l INFO -s /tmp/celerybeat-schedule
```

Windows (PowerShell):
```powershell
uv run celery -A itk_academy.worker.celery_app beat -l INFO
```

Или одним процессом: `celery ... worker -B -P solo`.

## Тесты

```bash
uv run pytest
```

Тесты интеграции используют `testcontainers` — Docker должен быть запущен. В CI используется сервисный Postgres.

## Линтер

```bash
uv run ruff check --fix .
uv run ruff format .
```

## Docker

```bash
docker build -t itk-academy:local .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://itk:itk@host.docker.internal:5432/itk" \
  -e EVENTS_PROVIDER_API_KEY="..." \
  itk-academy:local
```

Образ запускает три процесса через `run.sh`: Celery worker, Celery beat, Uvicorn.

## CI/CD

На push в `main` GitHub Actions:

1. `lint` — ruff check + ruff format --check
2. `test` — pytest с Postgres 16
3. `build` — multi-arch образ → ghcr.io
4. `deploy` — POST в LMS API

Деплой не стартует, если `lint` или `test` упали.