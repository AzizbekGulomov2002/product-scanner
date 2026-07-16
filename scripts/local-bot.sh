#!/bin/bash
# Faqat Telegram bot

set -e
cd "$(dirname "$0")/.."

if [ ! -d venv ]; then
  echo "Avval setup qiling: ./scripts/local-setup.sh"
  exit 1
fi

source venv/bin/activate
source scripts/local-env.sh
python -m bot.main
