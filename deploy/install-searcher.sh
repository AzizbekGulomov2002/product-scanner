#!/bin/bash
# searcher.service o'rnatish (Ubuntu/Debian server)
# Ishlatish: sudo ./deploy/install-searcher.sh /opt/product-searcher

set -euo pipefail

APP_DIR="${1:-/home/product-scanner}"
SERVICE_NAME="searcher.service"
RUN_USER="${RUN_USER:-root}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Root bilan ishga tushiring: sudo $0 $APP_DIR"
  exit 1
fi

if [ ! -f "$APP_DIR/scripts/run-searcher.sh" ]; then
  echo "Loyiha topilmadi: $APP_DIR"
  echo "Masalan: sudo $0 /home/product-scanner"
  exit 1
fi

chmod +x "$APP_DIR/scripts/run-searcher.sh"
mkdir -p "$APP_DIR/logs"
chown -R "$RUN_USER:$RUN_USER" "$APP_DIR" || true

# systemd unit — replace placeholder path with real APP_DIR
sed "s|/home/product-scanner|$APP_DIR|g; s|/opt/product-searcher|$APP_DIR|g" \
  "$APP_DIR/deploy/searcher.service" \
  | sed "s|User=root|User=$RUN_USER|; s|User=www-data|User=$RUN_USER|" \
  | sed "s|Group=root|Group=$RUN_USER|; s|Group=www-data|Group=$RUN_USER|" \
  > "/etc/systemd/system/$SERVICE_NAME"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo ""
echo "✅ $SERVICE_NAME o'rnatildi"
echo ""
echo "Keyingi qadamlar:"
echo "  1) .env ni tahrirlang:"
echo "     nano $APP_DIR/.env"
echo ""
echo "     ALLOWED_HOSTS=SERVER_IP,localhost"
echo "     BACKEND_URL=http://SERVER_IP:8888"
echo "     DEBUG=False"
echo ""
echo "  2) Migratsiya va static:"
echo "     cd $APP_DIR && source venv/bin/activate"
echo "     python manage.py migrate"
echo "     python manage.py collectstatic --noinput"
echo ""
echo "  3) Ishga tushirish:"
echo "     sudo systemctl start $SERVICE_NAME"
echo "     sudo systemctl status $SERVICE_NAME"
echo ""
echo "  Loglar:"
echo "     tail -f $APP_DIR/logs/gunicorn-error.log"
echo "     tail -f $APP_DIR/logs/bot.log"
echo "     journalctl -u $SERVICE_NAME -f"
