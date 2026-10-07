#!/bin/bash
set -euo pipefail

# Применяем миграции, только если задан DATABASE_URL
if [ -n "${DATABASE_URL:-}" ]; then
    echo "Running database migrations..."
    alembic upgrade head

    echo "Starting celery worker and beat..."
    celery -A itk_academy.worker.celery_app worker -P solo -l INFO &
    celery -A itk_academy.worker.celery_app beat -l INFO -s /tmp/celerybeat-schedule &
else
    echo "DATABASE_URL not set — running without celery."
fi

echo "Starting uvicorn..."
uvicorn itk_academy.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1 &

# Если любой из процессов упадёт — падает и контейнер, платформа перезапустит.
wait -n
exit $?