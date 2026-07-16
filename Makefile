.PHONY: server bot worker stop-worker setup

# Django server
server:
	./run-server.sh

# Telegram bot
bot:
	./run-bot.sh

# Embedding worker (background) — mahsulot pending → indexed
worker:
	./run-worker.sh

stop-worker:
	./stop-worker.sh

# Birinchi marta setup
setup:
	./scripts/local-setup.sh

# Docker (ixtiyoriy)
up:
	docker compose up --build -d

down:
	docker compose down

migrate:
	python manage.py migrate

reindex:
	python manage.py reindex_all
