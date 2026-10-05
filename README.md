# ITK Academy — Events Aggregator

Backend сервис-агрегатор над Events Provider API.

## Стек

- Python 3.11+, FastAPI
- SQLAlchemy 2.0 (async), Alembic, PostgreSQL
- Celery (worker + beat), брокер — PostgreSQL
- uv, ruff, pytest

## Локальный запуск

```bash
uv sync
cp .env.example .env  # заполнить значения
uv run uvicorn itk_academy.main:app --reload