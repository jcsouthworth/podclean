#!/bin/bash
set -e

# Apply any pending database migrations before starting
alembic upgrade head

# Start Celery beat scheduler in the background
celery -A celery_app beat --loglevel=info &

# Start FastAPI in the foreground
exec uvicorn main:app --host 0.0.0.0 --port 8000
