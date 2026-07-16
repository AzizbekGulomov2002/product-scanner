#!/bin/bash
# .env ni qo'lda yaratish (setup.sh o'rniga)

cd "$(dirname "$0")/.."

SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")

cat > .env << EOF
SECRET_KEY=${SECRET_KEY}
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,web,0.0.0.0

POSTGRES_DB=product_searcher
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
BACKEND_URL=http://web:8000

CONFIDENCE_HIGH=0.85
CONFIDENCE_MEDIUM=0.70
SEARCH_TOP_K=5

CLIP_MODEL=ViT-B-32
CLIP_PRETRAINED=openai
EOF

echo "✅ .env yaratildi: $(pwd)/.env"
echo "   TELEGRAM_BOT_TOKEN ni .env da almashtiring."
