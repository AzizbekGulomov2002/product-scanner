#!/bin/bash
# Full new-server bootstrap for Product Scanner
# Usage (as root):
#   curl not required — copy repo first, then:
#   sudo SERVER_IP=1.2.3.4 BOT_TOKEN=xxx ./deploy/setup-server.sh /home/product-scanner

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo SERVER_IP=... BOT_TOKEN=... $0 /path/to/app"
  exit 1
fi

APP_DIR="${1:-/home/product-scanner}"
SERVER_IP="${SERVER_IP:-}"
BOT_TOKEN="${BOT_TOKEN:-}"
RUN_USER="${RUN_USER:-root}"
DB_NAME="${DB_NAME:-product_searcher}"
DB_USER="${DB_USER:-ps_user}"
DB_PASSWORD="${DB_PASSWORD:-ChangeMeStrongPass123}"
SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"

if [ -z "$SERVER_IP" ]; then
  echo "Set SERVER_IP, e.g.:"
  echo "  sudo SERVER_IP=159.223.19.109 BOT_TOKEN=123:ABC $0 $APP_DIR"
  exit 1
fi

if [ ! -d "$APP_DIR" ]; then
  echo "App dir not found: $APP_DIR"
  echo "Clone first:"
  echo "  git clone https://github.com/AzizbekGulomov2002/product-scanner.git $APP_DIR"
  exit 1
fi

echo "==> System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  python3 python3-venv python3-pip python3-dev \
  libzbar0 libgl1 libglib2.0-0 \
  redis-server curl ufw

echo "==> Swap (2G) if missing"
if ! swapon --show | grep -q .; then
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> Redis"
systemctl enable redis-server
systemctl start redis-server

echo "==> PostgreSQL + pgvector"
DB_NAME="$DB_NAME" DB_USER="$DB_USER" DB_PASSWORD="$DB_PASSWORD" \
  bash "$APP_DIR/deploy/setup-postgres.sh"

echo "==> Python venv + deps"
cd "$APP_DIR"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Writing .env"
cat > "$APP_DIR/.env" <<EOF
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${SERVER_IP},localhost,127.0.0.1

POSTGRES_DB=${DB_NAME}
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=True

TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
BACKEND_URL=http://${SERVER_IP}:8888
WEBAPP_URL=http://${SERVER_IP}:8888

CONFIDENCE_HIGH=0.88
CONFIDENCE_MEDIUM=0.82
CONFIDENCE_MIN_GAP=0.06
REALTIME_CONFIDENCE_HIGH=0.80
REALTIME_CONFIDENCE_MIN=0.72
REALTIME_CONFIDENCE_MIN_GAP=0.04
SEARCH_TOP_K=5

CLIP_MODEL=ViT-B-32
CLIP_PRETRAINED=openai

GUNICORN_BIND=0.0.0.0:8888
GUNICORN_WORKERS=1
GUNICORN_TIMEOUT=180
EOF

echo "==> Migrate + static + admin"
python manage.py enable_pgvector 2>/dev/null || true
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py create_admin 2>/dev/null || true
mkdir -p "$APP_DIR/logs" "$APP_DIR/media"

echo "==> Firewall"
ufw allow OpenSSH || true
ufw allow 8888/tcp || true
ufw --force enable || true

echo "==> systemd service"
chmod +x "$APP_DIR/scripts/run-searcher.sh" "$APP_DIR/deploy/"*.sh
RUN_USER="$RUN_USER" bash "$APP_DIR/deploy/install-searcher.sh" "$APP_DIR"

# Ensure 1 worker in unit file
sed -i 's/GUNICORN_WORKERS=2/GUNICORN_WORKERS=1/' /etc/systemd/system/searcher.service || true
systemctl daemon-reload
systemctl restart searcher
systemctl enable searcher

echo ""
echo "✅ Server ready"
echo "   App:   http://${SERVER_IP}:8888/"
echo "   Admin: http://${SERVER_IP}:8888/admin/  (admin / admin123)"
echo "   Status: systemctl status searcher"
echo "   Logs:   journalctl -u searcher -f"
