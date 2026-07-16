#!/bin/bash
# Background worker ni to'xtatish

cd "$(dirname "$0")"

if [ ! -f logs/celery.pid ]; then
  echo "Worker ishlamayapti."
  exit 0
fi

PID=$(cat logs/celery.pid)
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "✅ Worker to'xtatildi (PID: $PID)"
else
  echo "Worker allaqachon to'xtagan."
fi
rm -f logs/celery.pid
