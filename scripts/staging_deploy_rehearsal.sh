#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROJECT_NAME="${PROJECT_NAME:-greenbook-rehearsal}"
STAGING_BACKEND_PORT="${STAGING_BACKEND_PORT:-18000}"
STAGING_FRONTEND_PORT="${STAGING_FRONTEND_PORT:-15173}"
BASE_URL="http://127.0.0.1:${STAGING_BACKEND_PORT}"
OUTPUT_FILE=""
RUN_MIGRATIONS=true
CLEANUP_STACK=true
STAGING_COMPOSE_FILE="${STAGING_COMPOSE_FILE:-docker-compose.staging.yml}"
REHEARSAL_SUPPORT_COMPOSE_FILE="${REHEARSAL_SUPPORT_COMPOSE_FILE:-docker-compose.rehearsal.yml}"

GOOD_BACKEND_IMAGE="green-book-backend:rehearsal-good"
BAD_BACKEND_IMAGE="green-book-backend:rehearsal-bad"
FRONTEND_IMAGE="green-book-frontend:rehearsal-good"

usage() {
  cat <<'EOF'
Usage: ./scripts/staging_deploy_rehearsal.sh [options]

Options:
  --base-url <url>         Base URL for smoke checks (default: http://127.0.0.1:18000)
  --output <path>          Write rehearsal summary JSON
  --skip-migrations        Skip migration step
  --keep-stack             Keep rehearsal services after script completion
  -h, --help               Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --output)
      OUTPUT_FILE="${2:-}"
      shift 2
      ;;
    --skip-migrations)
      RUN_MIGRATIONS=false
      shift
      ;;
    --keep-stack)
      CLEANUP_STACK=false
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

cleanup() {
  if [[ "$CLEANUP_STACK" != true ]]; then
    echo "Keeping rehearsal stack (requested with --keep-stack)."
    return
  fi

  echo "Cleaning rehearsal stack..."
  docker compose -p "$PROJECT_NAME" -f "$STAGING_COMPOSE_FILE" down -v --remove-orphans > /dev/null 2>&1 || true
  docker compose -p "$PROJECT_NAME" -f "$REHEARSAL_SUPPORT_COMPOSE_FILE" down -v --remove-orphans > /dev/null 2>&1 || true
}

trap cleanup EXIT

wait_health() {
  local expected="$1" # up|down
  local timeout_sec="${2:-60}"
  local start
  start="$(date +%s)"

  while true; do
    if curl -fsS "$BASE_URL/api/health" > /dev/null 2>&1; then
      if [[ "$expected" == "up" ]]; then
        return 0
      fi
    else
      if [[ "$expected" == "down" ]]; then
        return 0
      fi
    fi

    if (( "$(date +%s)" - start >= timeout_sec )); then
      return 1
    fi
    sleep 2
  done
}

echo "Rehearsal project: $PROJECT_NAME"
echo "Building rehearsal images..."
docker build -t "$GOOD_BACKEND_IMAGE" ./backend
docker build -t "$FRONTEND_IMAGE" ./frontend
cat <<'EOF' | docker build -t "$BAD_BACKEND_IMAGE" -f - .
FROM alpine:3.20
RUN echo "intentionally bad backend image for rollback rehearsal"
CMD ["sh", "-c", "echo bad image && exit 1"]
EOF

echo "Starting supporting services..."
docker compose -p "$PROJECT_NAME" -f "$REHEARSAL_SUPPORT_COMPOSE_FILE" up -d db redis minio

echo "Deploying good backend image..."
export BACKEND_IMAGE="$GOOD_BACKEND_IMAGE"
export FRONTEND_IMAGE="$FRONTEND_IMAGE"
export STAGING_BACKEND_PORT
export STAGING_FRONTEND_PORT
docker compose -p "$PROJECT_NAME" -f "$STAGING_COMPOSE_FILE" up -d backend

if ! wait_health up 90; then
  echo "Good deployment did not become healthy in time."
  exit 1
fi

if [[ "$RUN_MIGRATIONS" == true ]]; then
  echo "Applying migrations on rehearsal stack..."
  docker compose -p "$PROJECT_NAME" -f "$STAGING_COMPOSE_FILE" run --rm backend alembic upgrade head
fi

echo "Running baseline smoke..."
python3 scripts/release_smoke.py --base-url "$BASE_URL"

PREV_BACKEND_IMAGE="$(
  docker compose -p "$PROJECT_NAME" -f "$STAGING_COMPOSE_FILE" ps -q backend \
    | xargs -r docker inspect --format '{{.Config.Image}}' \
    | head -n1
)"
if [[ -z "$PREV_BACKEND_IMAGE" ]]; then
  echo "Could not detect previous backend image."
  exit 1
fi

echo "Switching to bad backend image to trigger rollback..."
export BACKEND_IMAGE="$BAD_BACKEND_IMAGE"
docker compose -p "$PROJECT_NAME" -f "$STAGING_COMPOSE_FILE" up -d backend || true

bad_deploy_failed=false
if wait_health down 45; then
  bad_deploy_failed=true
fi

if [[ "$bad_deploy_failed" != true ]]; then
  echo "Bad deployment did not fail as expected."
  exit 1
fi

echo "Rolling back to previous backend image: $PREV_BACKEND_IMAGE"
export BACKEND_IMAGE="$PREV_BACKEND_IMAGE"
docker compose -p "$PROJECT_NAME" -f "$STAGING_COMPOSE_FILE" up -d backend

if ! wait_health up 90; then
  echo "Rollback did not recover backend health in time."
  exit 1
fi

echo "Running post-rollback smoke..."
python3 scripts/release_smoke.py --base-url "$BASE_URL"

export PROJECT_NAME
export BASE_URL
export PREV_BACKEND_IMAGE
export GOOD_BACKEND_IMAGE
export BAD_BACKEND_IMAGE
export RUN_MIGRATIONS

SUMMARY_JSON="$(python3 - <<'PY'
import json
import os

summary = {
    "project_name": os.environ["PROJECT_NAME"],
    "base_url": os.environ["BASE_URL"],
    "run_migrations": os.environ["RUN_MIGRATIONS"].lower() == "true",
    "good_backend_image": os.environ["GOOD_BACKEND_IMAGE"],
    "bad_backend_image": os.environ["BAD_BACKEND_IMAGE"],
    "rollback_target_image": os.environ["PREV_BACKEND_IMAGE"],
    "rollback_successful": True,
}
print(json.dumps(summary, ensure_ascii=False))
PY
)"
echo "Rehearsal summary: $SUMMARY_JSON"

if [[ -n "$OUTPUT_FILE" ]]; then
  mkdir -p "$(dirname "$OUTPUT_FILE")"
  printf "%s\n" "$SUMMARY_JSON" > "$OUTPUT_FILE"
  echo "Summary written to: $OUTPUT_FILE"
fi
