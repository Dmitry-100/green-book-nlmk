#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_FILE=""
SKIP_BACKUP=false
BASE_URL="http://localhost:8000"
ADMIN_TOKEN="${SMOKE_ADMIN_TOKEN:-}"
FAIL_ON_OPS_ALERTS=false
OUTPUT_FILE=""
RUN_MIGRATIONS=true

usage() {
  cat <<'EOF'
Usage: ./scripts/restore_drill.sh [options]

Options:
  --backup-file <path>       Use existing backup file (.sql/.sql.gz)
  --skip-backup              Do not create a new backup (uses --backup-file or latest in backups/db)
  --base-url <url>           Base URL for smoke checks (default: http://localhost:8000)
  --admin-token <token>      Optional admin token for admin smoke checks
  --fail-on-ops-alerts       Fail smoke when /api/admin/ops/alerts returns status=alert
  --skip-migrations          Skip running migrations after restore
  --output <path>            Write drill summary JSON to file
  -h, --help                 Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup-file)
      BACKUP_FILE="${2:-}"
      shift 2
      ;;
    --skip-backup)
      SKIP_BACKUP=true
      shift
      ;;
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --admin-token)
      ADMIN_TOKEN="${2:-}"
      shift 2
      ;;
    --fail-on-ops-alerts)
      FAIL_ON_OPS_ALERTS=true
      shift
      ;;
    --skip-migrations)
      RUN_MIGRATIONS=false
      shift
      ;;
    --output)
      OUTPUT_FILE="${2:-}"
      shift 2
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

resolve_latest_backup() {
  local latest
  latest="$(ls -1t backups/db/*.sql.gz backups/db/*.sql 2>/dev/null | head -n1 || true)"
  if [[ -z "$latest" ]]; then
    echo "No backup files found in backups/db"
    exit 1
  fi
  echo "$latest"
}

file_mtime_epoch() {
  local path="$1"
  python3 - "$path" <<'PY'
import os
import sys
print(int(os.path.getmtime(sys.argv[1])))
PY
}

if [[ "$SKIP_BACKUP" == false ]]; then
  backup_output="$(./scripts/backup_db.sh)"
  echo "$backup_output"
  if [[ -z "$BACKUP_FILE" ]]; then
    BACKUP_FILE="$(echo "$backup_output" | sed -n 's/^Backup created: //p' | tail -n1)"
  fi
fi

if [[ -z "$BACKUP_FILE" ]]; then
  BACKUP_FILE="$(resolve_latest_backup)"
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

BACKUP_MTIME_EPOCH="$(file_mtime_epoch "$BACKUP_FILE")"
RESTORE_STARTED_EPOCH="$(date +%s)"

echo "Starting restore drill using backup: $BACKUP_FILE"
./scripts/restore_db.sh "$BACKUP_FILE"

if [[ "$RUN_MIGRATIONS" == true ]]; then
  ./scripts/migrate_db.sh
fi

SMOKE_CMD=(python3 scripts/release_smoke.py --base-url "$BASE_URL")
if [[ -n "$ADMIN_TOKEN" ]]; then
  SMOKE_CMD+=(--admin-token "$ADMIN_TOKEN")
fi
if [[ "$FAIL_ON_OPS_ALERTS" == true ]]; then
  SMOKE_CMD+=(--fail-on-ops-alerts)
fi
"${SMOKE_CMD[@]}"

RESTORE_FINISHED_EPOCH="$(date +%s)"
RTO_SECONDS=$((RESTORE_FINISHED_EPOCH - RESTORE_STARTED_EPOCH))
RPO_SECONDS=$((RESTORE_STARTED_EPOCH - BACKUP_MTIME_EPOCH))
if [[ "$RPO_SECONDS" -lt 0 ]]; then
  RPO_SECONDS=0
fi

export BACKUP_FILE
export BASE_URL
export RUN_MIGRATIONS
export FAIL_ON_OPS_ALERTS
export RTO_SECONDS
export RPO_SECONDS
export RESTORE_STARTED_EPOCH
export RESTORE_FINISHED_EPOCH

SUMMARY_JSON="$(python3 - <<'PY'
import json
import os

summary = {
    "backup_file": os.environ["BACKUP_FILE"],
    "base_url": os.environ["BASE_URL"],
    "run_migrations": os.environ["RUN_MIGRATIONS"].lower() == "true",
    "fail_on_ops_alerts": os.environ["FAIL_ON_OPS_ALERTS"].lower() == "true",
    "restore_started_epoch": int(os.environ["RESTORE_STARTED_EPOCH"]),
    "restore_finished_epoch": int(os.environ["RESTORE_FINISHED_EPOCH"]),
    "rto_seconds": int(os.environ["RTO_SECONDS"]),
    "rpo_seconds": int(os.environ["RPO_SECONDS"]),
}
print(json.dumps(summary, ensure_ascii=False))
PY
)"

echo "Restore drill summary: $SUMMARY_JSON"

if [[ -n "$OUTPUT_FILE" ]]; then
  mkdir -p "$(dirname "$OUTPUT_FILE")"
  printf "%s\n" "$SUMMARY_JSON" > "$OUTPUT_FILE"
  echo "Summary written to: $OUTPUT_FILE"
fi
