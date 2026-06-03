#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
PLATFORM="${PLATFORM:-linux/amd64}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/dist/offline}"
BUNDLE_NAME="${BUNDLE_NAME:-green-book-nlmk-offline-$TAG}"
BUNDLE_DIR="$OUTPUT_DIR/$BUNDLE_NAME"
BUNDLE_TAR="$OUTPUT_DIR/$BUNDLE_NAME.tar.gz"

BACKEND_IMAGE="${BACKEND_IMAGE:-green-book-nlmk/backend:$TAG}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-green-book-nlmk/frontend:$TAG}"
DB_IMAGE="${DB_IMAGE:-postgis/postgis:16-3.4}"
REDIS_IMAGE="${REDIS_IMAGE:-redis:7-alpine}"
MINIO_IMAGE="${MINIO_IMAGE:-minio/minio:latest}"

SUPPORT_IMAGES=("$DB_IMAGE" "$REDIS_IMAGE" "$MINIO_IMAGE")
ALL_IMAGES=("$BACKEND_IMAGE" "$FRONTEND_IMAGE" "${SUPPORT_IMAGES[@]}")

require_platform() {
  local image="$1"
  local mode="${2:-strict}"
  local actual
  actual="$(docker image inspect --format '{{.Os}}/{{.Architecture}}{{if .Variant}}/{{.Variant}}{{end}}' "$image" 2>/dev/null || true)"
  if [[ -z "$actual" || "$actual" == "/" ]]; then
    echo "Image $image did not expose a concrete local platform; docker save will enforce $PLATFORM."
    return 0
  fi
  if [[ "$actual" != "$PLATFORM" ]]; then
    if [[ "$mode" == "soft" ]]; then
      echo "Image $image reports platform '$actual'; docker save will enforce $PLATFORM."
      return 0
    fi
    echo "Image $image has platform '$actual', expected '$PLATFORM'." >&2
    exit 1
  fi
}

rm -rf "$BUNDLE_DIR" "$BUNDLE_TAR"
mkdir -p "$BUNDLE_DIR/images" "$BUNDLE_DIR/scripts" "$OUTPUT_DIR"

echo "Target platform: $PLATFORM"

echo "Building backend image: $BACKEND_IMAGE"
docker buildx build --platform "$PLATFORM" --pull --load -t "$BACKEND_IMAGE" "$ROOT_DIR/backend"
require_platform "$BACKEND_IMAGE"

echo "Building frontend image: $FRONTEND_IMAGE"
docker buildx build --platform "$PLATFORM" --pull --load -f "$ROOT_DIR/frontend/Dockerfile.offline" -t "$FRONTEND_IMAGE" "$ROOT_DIR/frontend"
require_platform "$FRONTEND_IMAGE"

for image in "${SUPPORT_IMAGES[@]}"; do
  echo "Pulling support image for $PLATFORM: $image"
  docker pull --platform "$PLATFORM" "$image"
  require_platform "$image" soft
done

echo "Saving images to offline tar..."
docker save --platform "$PLATFORM" -o "$BUNDLE_DIR/images/green-book-nlmk-images.tar" "${ALL_IMAGES[@]}"

cp "$ROOT_DIR/docker-compose.offline.yml" "$BUNDLE_DIR/docker-compose.offline.yml"
cp "$ROOT_DIR/scripts/install_offline_bundle.sh" "$BUNDLE_DIR/install.sh"
cp "$ROOT_DIR/scripts/release_smoke.py" "$BUNDLE_DIR/scripts/release_smoke.py"
chmod +x "$BUNDLE_DIR/install.sh" "$BUNDLE_DIR/scripts/release_smoke.py"

{
  echo "# Offline deploy image references"
  echo "BACKEND_IMAGE=$BACKEND_IMAGE"
  echo "FRONTEND_IMAGE=$FRONTEND_IMAGE"
  echo "DB_IMAGE=$DB_IMAGE"
  echo "REDIS_IMAGE=$REDIS_IMAGE"
  echo "MINIO_IMAGE=$MINIO_IMAGE"
  echo "APP_HOST_PORT=5173"
  echo
  sed \
    -e 's/^APP_ENV=.*/APP_ENV=production/' \
    -e 's/^ENABLE_DEV_AUTH=.*/ENABLE_DEV_AUTH=false/' \
    -e 's/^AUTH_SECRET_KEY=.*/AUTH_SECRET_KEY=change-to-long-random-secret/' \
    -e 's/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=change-to-strong-postgres-password/' \
    -e 's/^DATABASE_URL=.*/DATABASE_URL=postgresql:\/\/greenbook:change-to-strong-postgres-password@db:5432\/greenbook/' \
    -e 's/^MINIO_ROOT_USER=.*/MINIO_ROOT_USER=change-to-minio-user/' \
    -e 's/^MINIO_ROOT_PASSWORD=.*/MINIO_ROOT_PASSWORD=change-to-strong-minio-password/' \
    -e 's/^CORS_ORIGINS=.*/CORS_ORIGINS=http:\/\/localhost:5173/' \
    "$ROOT_DIR/.env.example"
  echo "MEDIA_DIRECT_UPLOAD_ENABLED=false"
} > "$BUNDLE_DIR/.env.offline.example"

{
  echo "TAG=$TAG"
  echo "CREATED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "PLATFORM=$PLATFORM"
  echo "BACKEND_IMAGE=$BACKEND_IMAGE"
  echo "FRONTEND_IMAGE=$FRONTEND_IMAGE"
  echo "DB_IMAGE=$DB_IMAGE"
  echo "REDIS_IMAGE=$REDIS_IMAGE"
  echo "MINIO_IMAGE=$MINIO_IMAGE"
} > "$BUNDLE_DIR/manifest.env"

(
  cd "$BUNDLE_DIR"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum images/green-book-nlmk-images.tar > CHECKSUMS.txt
  else
    shasum -a 256 images/green-book-nlmk-images.tar > CHECKSUMS.txt
  fi
)

cp "$ROOT_DIR/docs/runbooks/offline-deploy.md" "$BUNDLE_DIR/README-offline-deploy.md"

tar -czf "$BUNDLE_TAR" -C "$OUTPUT_DIR" "$BUNDLE_NAME"

echo "Offline bundle is ready:"
echo "$BUNDLE_TAR"
echo
echo "Copy this archive to the server, unpack it, create .env from .env.offline.example, then run:"
echo "./install.sh"
