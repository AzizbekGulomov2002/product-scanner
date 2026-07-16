#!/bin/bash
# To'liq tozalash (DB va media ham o'chadi)

cd "$(dirname "$0")/.."
read -p "Barcha ma'lumotlar o'chadi. Davom etasizmi? (y/N): " confirm
if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
  docker compose down -v
  echo "✅ To'liq tozalandi."
else
  echo "Bekor qilindi."
fi
