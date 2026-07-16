#!/bin/bash
# Product Searcher — ishga tushirish

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -f .env ]; then
  echo "❌ .env topilmadi. Avval setup qiling:"
  echo "   ./scripts/setup.sh"
  exit 1
fi

if ! command -v docker &>/dev/null; then
  echo "❌ Docker topilmadi."
  echo ""
  echo "Mac uchun o'rnatish:"
  echo "  https://www.docker.com/products/docker-desktop/"
  echo ""
  echo "O'rnatgach Docker Desktop ni oching va qayta urinib ko'ring."
  exit 1
fi

echo "==> Docker image build qilinmoqda (birinchi marta 5-10 daqiqa)..."
docker compose up --build -d

echo ""
echo "==> Xizmatlar holati:"
docker compose ps

echo ""
echo "✅ Tayyor!"
echo ""
echo "  Admin panel:       http://localhost:8000/admin/"
echo "  Realtime skaner:   http://localhost:8000/"
echo "  Login:             admin / admin123"
echo ""
echo "  Loglar:            docker compose logs -f"
echo "  To'xtatish:        docker compose down"
echo ""
