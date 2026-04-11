# Release Checklist (Test/Staging)

## 1) Перед деплоем

- `main`/release-ветка зелёная в `CI`.
- Миграции применимы (`alembic upgrade head` в CI migration smoke).
- Подготовлены secrets для staging workflow:
  - `STAGING_SSH_HOST`
  - `STAGING_SSH_PORT` (опционально)
  - `STAGING_SSH_USER`
  - `STAGING_SSH_PRIVATE_KEY`
  - `STAGING_APP_DIR`
  - `STAGING_BASE_URL`
  - `SMOKE_ADMIN_TOKEN` (для admin smoke)

## 2) Build / publish образов

- Запустить workflow: `CD Build Publish`
- Проверить, что backend/frontend образы опубликованы в GHCR:
  - `ghcr.io/<owner>/green-book-nlmk/backend:<tag>`
  - `ghcr.io/<owner>/green-book-nlmk/frontend:<tag>`

## 3) Deploy в staging

- Запустить workflow: `Deploy Staging`
- Параметры:
  - `image_tag` (опционально)
  - `run_migrations=true`
  - `fail_on_ops_alerts=true` (или `false` для неблокирующего smoke)
- Workflow выполняет:
  1. pull новых образов
  2. миграции (`alembic upgrade head`)
  3. переключение backend/frontend на новый image tag
  4. post-deploy smoke

## 4) Проверки после деплоя

- `scripts/release_smoke.py` проходит на staging.
- smoke покрывает базовые health/deps checks и admin checks (при наличии токена).
- `/api/health/ready` возвращает `ready`.
- `/api/admin/ops/alerts` не содержит критичных сигналов
  (или осознанно принят риск, если запуск был с `fail_on_ops_alerts=false`).
- В `ops/summary` нет аномального роста:
  - `error_rate_percent`
  - `media_pipeline.pending`
  - `media_pipeline.failed`
  - `cache.totals.degraded_stores`

## 5) Rollback

- Если smoke/job падает после переключения, workflow пытается rollback
  на предыдущие backend/frontend image refs.
- После rollback повторно выполнить smoke и зафиксировать инцидент в changelog.

## 6) Регулярная репетиция rollback

- Запускать `.github/workflows/deploy-rehearsal.yml` (manual или по расписанию).
- Rehearsal-контур использует:
  - `docker-compose.rehearsal.yml` для `db/redis/minio` (без host-портов),
  - `docker-compose.staging.yml` для backend/frontend с настраиваемыми `STAGING_BACKEND_PORT` / `STAGING_FRONTEND_PORT`.
- Workflow поднимает изолированный rehearsal-контур, выполняет:
  1. good deploy
  2. smoke
  3. bad deploy (симуляция деградации)
  4. rollback
  5. smoke после rollback
- Результат публикуется как artifact `deploy-rehearsal-summary`.
