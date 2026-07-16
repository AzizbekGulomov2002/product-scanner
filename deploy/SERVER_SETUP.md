# New server setup (PostgreSQL + Product Scanner)

Recommended VPS: **2+ vCPU / 4+ GB RAM** (CLIP needs memory).

---

## Option A — one command (recommended)

```bash
# 1) Clone
cd /home
git clone https://github.com/AzizbekGulomov2002/product-scanner.git
cd product-scanner

# 2) Bootstrap everything (Postgres + pgvector + venv + .env + systemd)
sudo SERVER_IP=YOUR_SERVER_IP \
     BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN \
     DB_PASSWORD='StrongPasswordHere' \
     ./deploy/setup-server.sh /home/product-scanner
```

Replace:
- `YOUR_SERVER_IP` → e.g. `159.223.19.109`
- `YOUR_TELEGRAM_BOT_TOKEN` → BotFather token
- `StrongPasswordHere` → DB password

Then open: `http://YOUR_SERVER_IP:8888/`

---

## Option B — step by step

### 1. System packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-dev \
  libzbar0 libgl1 libglib2.0-0 redis-server git curl ufw
sudo systemctl enable --now redis-server
```

### 2. PostgreSQL + pgvector

```bash
cd /home/product-scanner
sudo DB_NAME=product_searcher \
     DB_USER=ps_user \
     DB_PASSWORD='StrongPasswordHere' \
     ./deploy/setup-postgres.sh
```

### 3. App + .env

```bash
cd /home/product-scanner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

Required `.env` values:

```env
DEBUG=False
ALLOWED_HOSTS=YOUR_SERVER_IP,localhost,127.0.0.1

POSTGRES_DB=product_searcher
POSTGRES_USER=ps_user
POSTGRES_PASSWORD=StrongPasswordHere
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

TELEGRAM_BOT_TOKEN=...
BACKEND_URL=http://YOUR_SERVER_IP:8888
WEBAPP_URL=http://YOUR_SERVER_IP:8888

CELERY_TASK_ALWAYS_EAGER=True
GUNICORN_WORKERS=1
GUNICORN_BIND=0.0.0.0:8888
GUNICORN_TIMEOUT=180
```

### 4. Migrate

```bash
source venv/bin/activate
python manage.py enable_pgvector
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py create_admin
```

### 5. systemd (web + bot, one service, port 8888)

```bash
sudo RUN_USER=root ./deploy/install-searcher.sh /home/product-scanner
sudo systemctl start searcher
sudo systemctl enable searcher
sudo ufw allow 8888/tcp
sudo systemctl status searcher
```

---

## Useful commands

```bash
sudo systemctl restart searcher
sudo systemctl status searcher
journalctl -u searcher -f
tail -f /home/product-scanner/logs/gunicorn-error.log
tail -f /home/product-scanner/logs/bot.log

# DB check
sudo -u postgres psql -d product_searcher -c '\dx'
```

---

## Moving from old server → new server

1. On **new** server: run Option A (setup-server.sh).
2. On **old** server (optional data dump):

```bash
# products + media
pg_dump -U ps_user -h localhost product_searcher > product_searcher.sql
tar czf media.tgz -C /home/product-scanner media
```

3. Copy to new server and restore:

```bash
# on new server
psql -U ps_user -h localhost -d product_searcher < product_searcher.sql
tar xzf media.tgz -C /home/product-scanner
sudo systemctl restart searcher
```

If starting fresh: skip dump — use Bulk Import (Excel + ZIP) on the new server.

---

## Notes

- Code uses **PostgreSQL + pgvector** only (not SQLite).
- `CELERY_TASK_ALWAYS_EAGER=True` = no separate Celery process (lighter).
- `GUNICORN_WORKERS=1` = lower RAM usage (good for 4 GB VPS).
- Do not run many other Django/bots on the same small VPS as CLIP.
