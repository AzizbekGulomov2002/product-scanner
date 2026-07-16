#!/bin/bash
# Celery worker — embedding background task

set -e
cd "$(dirname "$0")/.."

if [ ! -d venv ]; then
  echo "Avval setup qiling: ./scripts/local-setup.sh"
  exit 1
fi

source venv/bin/activate
source scripts/local-env.sh

echo "==> Celery worker ishga tushmoqda..."
celery -A config worker -l info --concurrency=1
