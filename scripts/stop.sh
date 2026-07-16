#!/bin/bash
# Tizimni to'xtatish

cd "$(dirname "$0")/.."
docker compose down
echo "✅ To'xtatildi."
