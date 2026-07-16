#!/bin/bash
# Production: Gunicorn (8888) + Celery worker + Telegram bot — bitta process guruhi
# systemd: searcher.service

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p logs

if [ ! -d venv ]; then
  echo "venv topilmadi. Avval: python3 -m venv venv && pip install -r requirements.txt"
  exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# macOS (local test)
if [ "$(uname)" = "Darwin" ]; then
  export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"
fi

PORT="${GUNICORN_PORT:-8888}"
BIND="${GUNICORN_BIND:-0.0.0.0:${PORT}}"
WORKERS="${GUNICORN_WORKERS:-1}"
THREADS="${GUNICORN_THREADS:-4}"
TIMEOUT="${GUNICORN_TIMEOUT:-180}"

PIDS=()

cleanup() {
  echo "==> To'xtatilmoqda..."
  for pid in "${PIDS[@]}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}

trap cleanup SIGTERM SIGINT EXIT

echo "==> Gunicorn (gthread): http://${BIND}"
# gthread => bitta process, ko'p thread. Bitta sekin so'rov (skanner/embedding)
# boshqa so'rovlarni (admin Save) bloklamaydi. CLIP modeli faqat 1 marta yuklanadi.
gunicorn config.wsgi:application \
  --bind "$BIND" \
  --workers "$WORKERS" \
  --worker-class gthread \
  --threads "$THREADS" \
  --timeout "$TIMEOUT" \
  --access-logfile "$ROOT/logs/gunicorn-access.log" \
  --error-logfile "$ROOT/logs/gunicorn-error.log" \
  --capture-output \
  --enable-stdio-inheritance &
PIDS+=($!)

# Celery worker faqat EAGER=False bo'lganda (alohida process = qo'shimcha CLIP nusxa).
# 2GB serverda EAGER=True tavsiya etiladi — embedding gunicorn ichida thread da ishlaydi,
# CLIP modeli bitta nusxa bo'lib, OOM/swap bo'lmaydi.
EAGER="$(printf '%s' "${CELERY_TASK_ALWAYS_EAGER:-False}" | tr '[:upper:]' '[:lower:]')"
if [ "$EAGER" != "true" ] && [ "$EAGER" != "1" ] && [ "$EAGER" != "yes" ]; then
  echo "==> Celery worker"
  celery -A config worker -l info --concurrency=1 --max-tasks-per-child=20 \
    >> "$ROOT/logs/celery.log" 2>&1 &
  PIDS+=($!)
fi

echo "==> Telegram bot"
python -m bot.main >> "$ROOT/logs/bot.log" 2>&1 &
PIDS+=($!)

echo "==> Barcha jarayonlar ishga tushdi (PIDs: ${PIDS[*]})"

# Birorta jarayon tushsa — hammasini to'xtat
wait -n
EXIT=$?
echo "==> Jarayon tugadi, chiqish kodi: $EXIT"
exit "$EXIT"
