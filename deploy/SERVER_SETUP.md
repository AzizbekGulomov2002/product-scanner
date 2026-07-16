# Server setup (Ubuntu)

App path: `/home/product-scanner`  
Port: `8888`  
One service: web (Gunicorn) + Telegram bot

---

## 1. Pull latest code

```bash
cd /home/product-scanner
git pull origin main
```

## 2. PostgreSQL + pgvector

```bash
sudo chmod +x deploy/*.sh scripts/run-searcher.sh

sudo DB_NAME=product_searcher \
     DB_USER=ps_user \
     DB_PASSWORD='ChangeMeStrongPass123' \
     ./deploy/setup-postgres.sh
```

## 3. .env

```bash
cd /home/product-scanner
cp -n .env.example .env
nano .env
```

Minimal values:

```env
SECRET_KEY=some-long-random-string
DEBUG=False
ALLOWED_HOSTS=159.223.19.109,localhost,127.0.0.1

POSTGRES_DB=product_searcher
POSTGRES_USER=ps_user
POSTGRES_PASSWORD=ChangeMeStrongPass123
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

CELERY_TASK_ALWAYS_EAGER=False

TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
BACKEND_URL=http://159.223.19.109:8888
WEBAPP_URL=http://159.223.19.109:8888

GUNICORN_BIND=0.0.0.0:8888
GUNICORN_WORKERS=1
GUNICORN_TIMEOUT=180
```

(IP ni o‘z server IP ga almashtiring.)

## 4. Python deps + migrate

```bash
cd /home/product-scanner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python manage.py enable_pgvector
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py create_admin
mkdir -p logs media
```

## 5. systemd (bitta service)

```bash
sudo RUN_USER=root ./deploy/install-searcher.sh /home/product-scanner
sudo systemctl restart searcher
sudo systemctl enable searcher
sudo ufw allow 8888/tcp
sudo systemctl status searcher
```

## 6. Check

```bash
curl -I http://127.0.0.1:8888/
journalctl -u searcher -f
```

Admin: `http://SERVER_IP:8888/admin/` → `admin` / `admin123`

---

## Daily commands

```bash
sudo systemctl restart searcher
sudo systemctl status searcher
journalctl -u searcher -f
tail -f /home/product-scanner/logs/bot.log
```

---

## One-shot (hammasini birga)

```bash
cd /home/product-scanner
git pull origin main

sudo SERVER_IP=159.223.19.109 \
     BOT_TOKEN=YOUR_BOT_TOKEN \
     DB_PASSWORD='ChangeMeStrongPass123' \
     ./deploy/setup-server.sh /home/product-scanner
```
