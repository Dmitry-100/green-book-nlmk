#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

RETENTION_DAYS="${AUDIT_LOG_RETENTION_DAYS:-180}"
DRY_RUN="false"
SKIP_BACKUP="false"
SKIP_PURGE="false"

usage() {
  echo "Usage: $0 [--dry-run] [--days <N>] [--skip-backup] [--skip-purge]"
  echo
  echo "Examples:"
  echo "  $0 --dry-run"
  echo "  $0 --days 120"
  echo "  $0 --skip-backup"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    --days)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --days"
        usage
        exit 1
      fi
      RETENTION_DAYS="$2"
      shift 2
      ;;
    --skip-backup)
      SKIP_BACKUP="true"
      shift
      ;;
    --skip-purge)
      SKIP_PURGE="true"
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

if [[ ! "$RETENTION_DAYS" =~ ^[0-9]+$ ]] || [[ "$RETENTION_DAYS" -lt 1 ]]; then
  echo "Invalid retention days: $RETENTION_DAYS"
  exit 1
fi

echo "Starting maintenance (dry_run=$DRY_RUN, retention_days=$RETENTION_DAYS)..."

if [[ "$SKIP_BACKUP" != "true" ]]; then
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[dry-run] backup step skipped (would run: ./scripts/backup_db.sh)"
  else
    ./scripts/backup_db.sh
  fi
fi

if [[ "$SKIP_PURGE" != "true" ]]; then
  if [[ "$DRY_RUN" == "true" ]]; then
    ./scripts/purge_audit_logs.sh --days "$RETENTION_DAYS" --dry-run
  else
    ./scripts/purge_audit_logs.sh --days "$RETENTION_DAYS"
  fi
fi

echo "Maintenance complete."
