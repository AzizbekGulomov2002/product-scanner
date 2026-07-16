#!/bin/bash
# PostgreSQL + pgvector setup (Ubuntu/Debian)
# Usage:
#   sudo ./deploy/setup-postgres.sh
# Optional env overrides:
#   DB_NAME=product_searcher DB_USER=ps_user DB_PASSWORD=secret sudo -E ./deploy/setup-postgres.sh

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo $0"
  exit 1
fi

DB_NAME="${DB_NAME:-product_searcher}"
DB_USER="${DB_USER:-ps_user}"
DB_PASSWORD="${DB_PASSWORD:-ChangeMeStrongPass123}"

echo "==> Installing PostgreSQL + build deps for pgvector"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y postgresql postgresql-contrib libpq-dev build-essential git

# Detect installed major version (e.g. 16)
PG_VER="$(psql --version | awk '{print $3}' | cut -d. -f1)"
apt-get install -y "postgresql-server-dev-${PG_VER}" || apt-get install -y postgresql-server-dev-all

echo "==> Starting PostgreSQL"
systemctl enable postgresql
systemctl start postgresql

echo "==> Installing pgvector extension"
TMP_DIR="$(mktemp -d)"
git clone --depth 1 https://github.com/pgvector/pgvector.git "$TMP_DIR/pgvector"
cd "$TMP_DIR/pgvector"
make
make install
cd /
rm -rf "$TMP_DIR"

echo "==> Creating role + database"
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
  ELSE
    ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';
  END IF;
END
\$\$;

SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec

GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

echo "==> Enabling vector extension"
sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 <<SQL
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER};
SQL

# Allow local password auth for app user (keep peer for postgres OS user)
PG_HBA="/etc/postgresql/${PG_VER}/main/pg_hba.conf"
if [ -f "$PG_HBA" ]; then
  if ! grep -q "product-scanner local auth" "$PG_HBA"; then
    echo "" >> "$PG_HBA"
    echo "# product-scanner local auth" >> "$PG_HBA"
    echo "local   ${DB_NAME}   ${DB_USER}                     scram-sha-256" >> "$PG_HBA"
    echo "host    ${DB_NAME}   ${DB_USER}   127.0.0.1/32   scram-sha-256" >> "$PG_HBA"
    echo "host    ${DB_NAME}   ${DB_USER}   ::1/128        scram-sha-256" >> "$PG_HBA"
    systemctl reload postgresql
  fi
fi

echo ""
echo "✅ PostgreSQL ready"
echo "   DB_NAME=${DB_NAME}"
echo "   DB_USER=${DB_USER}"
echo "   DB_PASSWORD=${DB_PASSWORD}"
echo ""
echo "Put these into .env:"
echo "POSTGRES_DB=${DB_NAME}"
echo "POSTGRES_USER=${DB_USER}"
echo "POSTGRES_PASSWORD=${DB_PASSWORD}"
echo "POSTGRES_HOST=localhost"
echo "POSTGRES_PORT=5432"
