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
RETENTION_DAYS="${AUDIT_LOG_RETENTION_DAYS:-180}"
DRY_RUN="false"

usage() {
  echo "Usage: $0 [--days <N>] [--dry-run]"
  echo
  echo "Examples:"
  echo "  $0 --dry-run"
  echo "  $0 --days 90"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --days)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --days"
        usage
        exit 1
      fi
      RETENTION_DAYS="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ ! "$RETENTION_DAYS" =~ ^[0-9]+$ ]]; then
  echo "Invalid --days value: $RETENTION_DAYS"
  exit 1
fi

if [[ "$RETENTION_DAYS" -lt 1 ]]; then
  echo "--days must be >= 1"
  exit 1
fi

TABLE_EXISTS="$(
  docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -c \
    "SELECT to_regclass('public.audit_logs') IS NOT NULL;"
)"
TABLE_EXISTS="$(echo "$TABLE_EXISTS" | tr -d '[:space:]')"
if [[ "$TABLE_EXISTS" != "t" ]]; then
  echo "audit_logs table not found in database '$POSTGRES_DB'. Apply migrations first."
  exit 0
fi

if [[ "$DRY_RUN" == "true" ]]; then
  docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c \
    "SELECT count(*) AS candidates FROM audit_logs WHERE created_at < now() - interval '${RETENTION_DAYS} days';"
  echo "Dry run complete (retention: ${RETENTION_DAYS} days)."
  exit 0
fi

docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c \
  "WITH deleted AS (
     DELETE FROM audit_logs
      WHERE created_at < now() - interval '${RETENTION_DAYS} days'
      RETURNING 1
   )
   SELECT count(*) AS deleted FROM deleted;"

echo "Purge complete (retention: ${RETENTION_DAYS} days)."
