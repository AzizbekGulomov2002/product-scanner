#!/bin/bash
# Barcha loglarni kuzatish

cd "$(dirname "$0")/.."
docker compose logs -f
