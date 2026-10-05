#!/bin/bash
set -euo pipefail

exec uvicorn itk_academy.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1