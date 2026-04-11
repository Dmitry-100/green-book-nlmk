#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-greenbook}"
POSTGRES_DB="${POSTGRES_DB:-greenbook}"

echo "Ensuring PostGIS extension in '$POSTGRES_DB'..."
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "CREATE EXTENSION IF NOT EXISTS postgis;"

echo "Applying Alembic migrations to head..."
docker compose exec -T backend alembic upgrade head

echo "Current Alembic revision:"
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -c \
  "SELECT version_num FROM alembic_version;"

echo "Migration complete."
