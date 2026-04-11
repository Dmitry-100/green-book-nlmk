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

mkdir -p backups/db
timestamp="$(date +%Y%m%d_%H%M%S)"
backup_path="backups/db/${POSTGRES_DB}_${timestamp}.sql.gz"

docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$backup_path"

echo "Backup created: $backup_path"
