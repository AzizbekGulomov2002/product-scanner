#!/bin/bash
# Embedding worker (Celery) — backgroundda ishlaydi
# Mahsulot yaratilganda pending → indexed qiladi
# Ishlatish: ./run-worker.sh

set -e
cd "$(dirname "$0")"

mkdir -p logs

if [ -f logs/celery.pid ] && kill -0 "$(cat logs/celery.pid)" 2>/dev/null; then
  echo "✅ Worker allaqachon ishlayapti (PID: $(cat logs/celery.pid))"
  echo "   Log: tail -f logs/celery.log"
  exit 0
fi

if [ ! -d venv ]; then
  echo "❌ Avval setup: ./scripts/local-setup.sh"
  exit 1
fi

if ! redis-cli ping &>/dev/null; then
  echo "❌ Redis ishlamayapti. Ishga tushiring:"
  echo "   brew services start redis"
  exit 1
fi

source venv/bin/activate
source scripts/local-env.sh

echo "==> Worker backgroundda ishga tushmoqda..."
nohup celery -A config worker -l info --concurrency=1 > logs/celery.log 2>&1 &
echo $! > logs/celery.pid

sleep 2
if kill -0 "$(cat logs/celery.pid)" 2>/dev/null; then
  echo "✅ Worker ishlayapti (PID: $(cat logs/celery.pid))"
  echo "   Log: tail -f logs/celery.log"
  echo "   To'xtatish: ./stop-worker.sh"
else
  echo "❌ Worker ishga tushmadi. Log:"
  tail -20 logs/celery.log
  exit 1
fi
