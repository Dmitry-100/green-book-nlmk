#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.offline.yml}"
IMAGE_TAR="${IMAGE_TAR:-images/green-book-nlmk-images.tar}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"
RUN_SEED="${RUN_SEED:-true}"
SKIP_LOAD="${SKIP_LOAD:-false}"
EXPECTED_PLATFORM=""

if [[ -f "manifest.env" ]]; then
  EXPECTED_PLATFORM="$(
    awk -F= '$1 == "PLATFORM" {print $2}' manifest.env | tail -n 1
  )"
fi

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Options:
  --skip-load        Do not run docker load.
  --skip-migrations  Do not run Alembic migrations.
  --skip-seed        Do not seed catalog/reference data.
  -h, --help         Show this help.

Environment:
  APP_HOST_PORT      External HTTP port for frontend/nginx (default: 5173).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-load)
      SKIP_LOAD=true
      shift
      ;;
    --skip-migrations)
      RUN_MIGRATIONS=false
      shift
      ;;
    --skip-seed)
      RUN_SEED=false
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! -f ".env" ]]; then
  echo "Missing .env. Create it first:" >&2
  echo "  cp .env.offline.example .env" >&2
  echo "  vi .env" >&2
  exit 1
fi

COMPOSE=(docker compose -f "$COMPOSE_FILE" --env-file .env)

normalize_arch() {
  case "$1" in
    x86_64) printf 'amd64' ;;
    aarch64) printf 'arm64' ;;
    *) printf '%s' "$1" ;;
  esac
}

if [[ -n "$EXPECTED_PLATFORM" ]]; then
  DOCKER_OS="$(docker info --format '{{.OSType}}' 2>/dev/null || uname -s | tr '[:upper:]' '[:lower:]')"
  DOCKER_ARCH="$(docker info --format '{{.Architecture}}' 2>/dev/null || uname -m)"
  DOCKER_ARCH="$(normalize_arch "$DOCKER_ARCH")"
  CURRENT_PLATFORM="$DOCKER_OS/$DOCKER_ARCH"
  if [[ "$CURRENT_PLATFORM" != "$EXPECTED_PLATFORM" ]]; then
    echo "Warning: bundle platform is $EXPECTED_PLATFORM, Docker host reports $CURRENT_PLATFORM." >&2
    echo "The loaded images may not run on this server." >&2
  fi
fi

env_value() {
  local key="$1"
  local default_value="$2"
  local value
  value="$(
    awk -F= -v key="$key" '
      $0 !~ /^[[:space:]]*#/ && $1 == key {
        sub(/^[^=]*=/, "")
        gsub(/^"|"$/, "")
        gsub(/^'\''|'\''$/, "")
        print
      }
    ' .env | tail -n 1
  )"
  if [[ -n "$value" ]]; then
    printf '%s' "$value"
  else
    printf '%s' "$default_value"
  fi
}

if [[ "$SKIP_LOAD" != "true" ]]; then
  if [[ ! -f "$IMAGE_TAR" ]]; then
    echo "Image archive not found: $IMAGE_TAR" >&2
    exit 1
  fi
  echo "Loading Docker images from $IMAGE_TAR..."
  docker load -i "$IMAGE_TAR"
fi

echo "Validating compose config..."
"${COMPOSE[@]}" config -q

echo "Starting support services..."
"${COMPOSE[@]}" up -d db redis minio

POSTGRES_USER="$(env_value POSTGRES_USER greenbook)"
POSTGRES_DB="$(env_value POSTGRES_DB greenbook)"

echo "Waiting for Postgres..."
for _ in {1..60}; do
  if "${COMPOSE[@]}" exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
"${COMPOSE[@]}" exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null

echo "Waiting for Redis and MinIO TCP ports..."
"${COMPOSE[@]}" run --rm --no-deps backend python - <<'PY'
import socket
import sys
import time

targets = [("redis", 6379), ("minio", 9000)]
for host, port in targets:
    last_error = None
    for _ in range(60):
        try:
            with socket.create_connection((host, port), timeout=2):
                break
        except OSError as exc:
            last_error = exc
            time.sleep(2)
    else:
        print(f"{host}:{port} is not reachable: {last_error}", file=sys.stderr)
        sys.exit(1)
PY

if [[ "$RUN_MIGRATIONS" == "true" ]]; then
  echo "Ensuring PostGIS extension..."
  "${COMPOSE[@]}" exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS postgis;"

  echo "Applying Alembic migrations..."
  "${COMPOSE[@]}" run --rm backend alembic upgrade head
fi

if [[ "$RUN_SEED" == "true" ]]; then
  echo "Seeding catalog and reference data..."
  "${COMPOSE[@]}" run --rm backend python -m app.seed.run_seed
  "${COMPOSE[@]}" run --rm backend python -m app.seed.seed_tree
  "${COMPOSE[@]}" run --rm backend python -m app.seed.seed_achievements
fi

echo "Starting application..."
"${COMPOSE[@]}" up -d backend media-worker frontend

APP_HOST_PORT="$(env_value APP_HOST_PORT 5173)"
if command -v curl >/dev/null 2>&1; then
  echo "Waiting for readiness via http://127.0.0.1:${APP_HOST_PORT}/api/health/ready ..."
  for _ in {1..60}; do
    if curl -fsS "http://127.0.0.1:${APP_HOST_PORT}/api/health/ready" >/dev/null 2>&1; then
      echo "Ready."
      break
    fi
    sleep 2
  done
fi

"${COMPOSE[@]}" ps

echo
echo "Application URL: http://127.0.0.1:${APP_HOST_PORT}"
echo "API health:       http://127.0.0.1:${APP_HOST_PORT}/api/health"
