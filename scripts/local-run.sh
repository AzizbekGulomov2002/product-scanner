#!/bin/bash
# Local ishga tushirish — Django runserver

set -e
cd "$(dirname "$0")/.."

if [ ! -d venv ]; then
  echo "Avval setup qiling: ./scripts/local-setup.sh"
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.local .env
  sed -i '' "s/POSTGRES_USER=macbookairm2/POSTGRES_USER=$(whoami)/" .env 2>/dev/null || \
  sed -i "s/POSTGRES_USER=macbookairm2/POSTGRES_USER=$(whoami)/" .env
fi

source venv/bin/activate
source scripts/local-env.sh

PORT="${1:-8000}"

echo "==> Django runserver: http://localhost:${PORT}/admin/"
echo "    Login: admin / admin123"
echo ""
echo "Bot uchun yangi terminal:"
echo "    ./scripts/local-bot.sh"
echo ""

python manage.py runserver "0.0.0.0:${PORT}"
