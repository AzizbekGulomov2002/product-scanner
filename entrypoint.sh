#!/bin/sh
set -e

python manage.py enable_pgvector 2>/dev/null || true
python manage.py migrate --noinput
python manage.py create_admin 2>/dev/null || true
python manage.py collectstatic --noinput

exec "$@"
