# ITK Academy — Events Aggregator

Backend сервис-агрегатор над Events Provider API.

## Что это

Сервис выступает промежуточным слоем между клиентами и внешним Events Provider API. Добавляет:

- **Кэширование** — события хранятся в локальной PostgreSQL, фоновый воркер синхронизирует их раз в день.
- **Удобный REST API** — привычная page/page_size пагинация вместо cursor-based, фильтр по дате.
- **Валидацию** — проверка статуса события, дедлайна, доступности места перед регистрацией.
- **Регистрацию и отмену** — проксирует запросы, хранит `ticket_id` локально.

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

## Переменные окружения

См. `.env.example`. В проде задаются через панель платформы LMS.

- `DATABASE_URL` — `postgresql+asyncpg://user:pass@host:5432/db`
- `EVENTS_PROVIDER_URL` — URL провайдера (локально — `https://events-provider.dev-2.python-labs.ru`, в кластере — внутренний DNS)
- `EVENTS_PROVIDER_API_KEY` — ключ из LMS-профиля
- `SENTRY_DSN` — опционально, для отлова ошибок в проде
- `SYNC_HOUR_UTC` — час запуска ежедневной синхронизации (по умолчанию 2)

## Локальный запуск

```bash
uv sync
cp .env.example .env   # заполнить значения
docker compose up -d   # поднять Postgres
uv run alembic upgrade head
uv run uvicorn itk_academy.main:app --reload