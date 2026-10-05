#!/bin/bash
set -euo pipefail

# Применяем миграции, только если задан DATABASE_URL
if [ -n "${DATABASE_URL:-}" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

exec uvicorn itk_academy.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1