#!/bin/bash
# Birinchi marta local setup (Docker kerak emas)

set -e
cd "$(dirname "$0")/.."
PROJECT="$(pwd)"

echo "==> Local setup: $PROJECT"

# 1. .env
if [ ! -f .env ]; then
  cp .env.local .env
  # Mac username ni avtomatik qo'yish
  sed -i '' "s/POSTGRES_USER=macbookairm2/POSTGRES_USER=$(whoami)/" .env 2>/dev/null || \
  sed -i "s/POSTGRES_USER=macbookairm2/POSTGRES_USER=$(whoami)/" .env
  echo "✅ .env yaratildi"
else
  echo "⚠️  .env mavjud, o'zgartirilmadi"
fi

# 2. Virtual environment
if [ ! -d venv ]; then
  echo "==> venv yaratilmoqda..."
  python3 -m venv venv
fi
source venv/bin/activate

# 3. Dependencies
echo "==> Paketlar o'rnatilmoqda (5-10 daqiqa, birinchi marta)..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 4. zbar (barcode uchun, Mac)
if ! brew list zbar &>/dev/null; then
  echo "==> zbar o'rnatilmoqda (barcode)..."
  brew install zbar
fi

# 5. PostgreSQL database
echo "==> Database yaratilmoqda..."
DB_USER=$(grep POSTGRES_USER .env | cut -d= -f2)
DB_NAME=$(grep POSTGRES_DB .env | cut -d= -f2)
psql -h localhost -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || \
  psql -h localhost -d postgres -c "CREATE DATABASE $DB_NAME;"
psql -h localhost -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true

# 6. Django migrate
echo "==> Migrate..."
source scripts/local-env.sh
python manage.py enable_pgvector 2>/dev/null || true
python manage.py migrate --noinput

# 7. Admin user
python manage.py create_admin 2>/dev/null || true

# 8. Media papka
mkdir -p media staticfiles

echo ""
echo "✅ Setup tayyor!"
echo ""
echo "Keyingi qadam:"
echo "  Terminal 1:  ./scripts/local-run.sh"
echo "  Terminal 2:  ./scripts/local-bot.sh"
echo ""
echo "  Admin: http://localhost:8000/admin/  (admin / admin123)"
echo ""
