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

# Дампы содержат персональные данные: каталог по умолчанию остаётся локальным,
# но его можно (и в проде нужно) вынести за пределы синхронизируемых папок
# (Google Drive и т.п.) через BACKUP_DIR.
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/db}"
mkdir -p "$BACKUP_DIR"

case "$BACKUP_DIR" in
  *"Google Drive"*|*GoogleDrive*|*Dropbox*|*OneDrive*|*"Yandex.Disk"*)
    echo "WARNING: BACKUP_DIR находится в облачно-синхронизируемой папке." >&2
    echo "WARNING: незашифрованный дамп уйдёт в облако — задайте BACKUP_AGE_RECIPIENT или BACKUP_PASSPHRASE." >&2
    ;;
esac

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_path="$BACKUP_DIR/${POSTGRES_DB}_${timestamp}.sql.gz"

dump() {
  docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip
}

if [[ -n "${BACKUP_AGE_RECIPIENT:-}" ]]; then
  command -v age >/dev/null || { echo "ERROR: BACKUP_AGE_RECIPIENT задан, но age не установлен" >&2; exit 1; }
  backup_path="${backup_path}.age"
  dump | age -r "$BACKUP_AGE_RECIPIENT" -o "$backup_path"
elif [[ -n "${BACKUP_PASSPHRASE:-}" ]]; then
  backup_path="${backup_path}.enc"
  dump | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_PASSPHRASE -out "$backup_path"
else
  echo "WARNING: бэкап создаётся без шифрования (нет BACKUP_AGE_RECIPIENT/BACKUP_PASSPHRASE)." >&2
  dump > "$backup_path"
fi

chmod 600 "$backup_path"
echo "Backup created: $backup_path"
