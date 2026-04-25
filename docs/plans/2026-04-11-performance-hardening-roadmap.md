# Performance Hardening Roadmap (2026-04-11)

Цель: ускорить API/SPA при росте объёма наблюдений, сохранив стабильность и безопасность production-конфигурации.

## P0 — Срочно

- [x] Исправить парсинг env-списков (`CORS_ORIGINS`, MIME): поддержка CSV и JSON.
- [x] Провести нагрузочные замеры API на синтетическом наборе 100k наблюдений.
- [x] Сравнить production-профили (`uvicorn workers=1/2/4`) и зафиксировать безопасный дефолт.
  - Итог: `workers=2` — стабильный баланс.
  - `workers=4` быстрее, но при стресс-нагрузке возникали редкие `500` (требует отдельного расследования и тюнинга лимитов БД/пула).
- [x] Добавить кеш повторяющихся bbox-запросов карты (`/api/map/observations`) с коротким TTL.

## P1 — Высокий приоритет

- [x] Ускорить сериализацию/выдачу тяжёлого `map`-ответа:
  - `GET /api/map/observations` теперь отдаётся байтовым JSON через `orjson`;
  - добавлен short TTL cache по ключу `(group, bbox, limit)` для `confirmed`.
  - контрольный замер на 100k synthetic rows (workers=2):
    - без кеша (`MAP_OBSERVATIONS_CACHE_TTL_SECONDS=0`): `avg ~152.6ms`, `p95 ~448.9ms`, `~151.8 rps`;
    - с кешем (`MAP_OBSERVATIONS_CACHE_TTL_SECONDS=10`): `avg ~11.7ms`, `p95 ~15.4ms`, `~1923.9 rps`.
- [x] Расширить тот же подход на `/api/gamification/stats`:
  - разделён cache: base aggregates (`TTLCache`) + heatmap по `heatmap_limit` (`KeyedTTLCache`);
  - сериализация ответа переведена на `orjson` bytes-response;
  - фильтр heatmap выровнен под partial-index (`sensitive_level IN ('open','blurred')`).
  - контрольный замер на 100k synthetic rows (workers=2):
    - до изменений, `TTL=0`: `avg ~1454.6ms`, `p95 ~2088.3ms`, `~10.3 rps`;
    - после изменений, `TTL=0`: `avg ~1190.0ms`, `p95 ~1722.0ms`, `~12.6 rps`;
    - до изменений, `TTL=30`: `avg ~63.0ms`, `p95 ~314.7ms`, `~245.7 rps`;
    - после изменений, `TTL=30`: `avg ~5.7ms`, `p95 ~8.3ms`, `~2576.3 rps`.
- [x] Применить аналогичный приём к `/api/dashboard/summary`:
  - переход на `orjson` bytes-response без изменения бизнес-логики и user-specific расчёта `on_review`;
  - контрольный замер на 100k synthetic rows (workers=2, cache TTL=20):
    - до изменений: `avg ~23.4ms`, `p95 ~177.2ms`, `~999.7 rps`;
    - после изменений: `avg ~15.5ms`, `p95 ~116.2ms`, `~1495.8 rps`.
- [x] Перепроверить редкие `500` при `workers=4` на обновлённом коде:
  - воспроизведение под нагрузкой не подтвердилось (`500/1200` при `concurrency=64`);
  - на текущем профиле `workers=4` стабильно быстрее `workers=2` для map-query:
    - `workers=2`: `avg ~141.4ms`, `p95 ~320.5ms`, `~164.6 rps`;
    - `workers=4`: `avg ~72.1ms`, `p95 ~153.7ms`, `~315.7 rps`.
  - решение: оставить дефолт `UVICORN_WORKERS=2` как консервативный, для production-релиза под CPU `>=4` рекомендовать `4` после smoke-проверки.
- [x] Вынести сценарии профилирования в CI (perf smoke):
  - добавлен `scripts/perf_smoke_ci.py` с порогами p95 и проверкой `failures=0` по ключевым эндпоинтам;
  - `.github/workflows/ci.yml` обновлён: старт локального API и запуск perf smoke после backend-тестов.

## P2 — Средний приоритет

- [x] Оптимизировать частоту map-запросов на клиенте:
  - добавлен query-key на фронте (group/status/bbox/limit) и suppression дубликатов;
  - bbox квантуется до `4` знаков для снижения запросов от микродвижений карты;
  - динамический `limit` по zoom (`600/900/1200`) для контроля плотности и объёма ответа;
  - сохранён abort in-flight запросов при смене фильтров/границ.
- [x] Дополнительно контролировать плотность маркеров/кластеров на уровне UI для очень плотных участков:
  - клиентский downsampling точек для отрисовки маркеров по масштабу (`500/800/1200`);
  - увеличение `gridSize` кластеризации при высокой плотности;
  - ограничение списка наблюдений в сайдбаре (`250`) с подсказкой о truncation.
- [x] Уточнить индексную стратегию для горячих фильтров (по фактическим запросам/`EXPLAIN ANALYZE`):
  - `map`-запросы подтверждены по плану: используются partial-indexes
    `ix_observations_map_visible_observed_at` (+ bbox filter), текущая стратегия оставлена;
  - для `gamification` база переписана на более дешёвую агрегацию:
    - убран отдельный `distinct species_id` запрос (подсчёт `confirmed_species` теперь из `group by species_id`);
    - `seasonal_dynamics` переписан с `count(distinct)` на двухшаговый `group by (month, species_id) -> count(*)`.
  - по результатам проверки новые постоянные индексы не добавлялись (временный тестовый индекс удалён из dev БД).
- [x] Подготовить отдельный “perf profile” для docker-compose (production-like):
  - добавлен `docker-compose.perf.yml` (production-like backend command, workers, расширенный DB pool, rate-limit off для профилирования).

### Доп. результаты после P2-оптимизаций (100k synthetic rows, workers=2, rate-limit off)

- `GET /api/gamification/stats?heatmap_limit=1200`, `TTL=0`:
  - до SQL-оптимизации base/seasonal: `avg ~1190.0ms`, `p95 ~1722.0ms`, `~12.6 rps`;
  - после SQL-оптимизации: `avg ~642.5ms`, `p95 ~917.2ms`, `~27.4 rps`.
- `GET /api/gamification/stats?include_heatmap=false`, `TTL=0`:
  - после SQL-оптимизации: `avg ~518.8ms`, `p95 ~910.0ms`, `~33.2 rps`.

## Метрики контроля

- `GET /api/map/observations` (bbox + limit=1200): p95, p99, throughput.
- `GET /api/dashboard/summary`: p95 и стабильность при конкуренции.
- Доля ошибок `5xx` под нагрузкой: целевое значение `0`.

## P3 — Frontend runtime (2026-04-11)

- [x] Добавить lightweight GET cache + request dedupe на клиенте:
  - `frontend/src/api/client.ts`: `getCached(...)` + in-flight dedupe для одинаковых ключей.
- [x] Убрать лишние сетевые запросы при навигации:
  - `MainLayout`: polling unread оставлен, но запросы больше не триггерятся на каждый `route.fullPath`;
  - добавлен min-interval + in-flight guard для `/api/notifications/unread-count`.
- [x] Кэшировать часто используемые read-only конфиги:
  - `config/ymaps` кэшируется на клиенте (`ttl=1h`), переиспользуется между `Map`/`EcoPassport`.
  - backend `/api/config/ymaps` теперь отдаёт `Cache-Control: public, max-age`.
- [x] Ускорить повторные открытия тяжёлых экранов:
  - `HomeView`: `dashboard/summary` кэш `15s` (scope по пользователю);
  - `EcoPassport`: `gamification/stats` кэш `30s`, species-gallery source кэш `5m`, загрузка данных параллельно.
- [x] Раскатать кэш `species`-запросов по пользовательским flow:
  - `SpeciesList`, `Observe`, `Identify`, `ExpertQueue`, `Admin` переведены на `getCached(...)` для повторяющихся запросов по группе/фильтрам.
- [x] Убрать дубли загрузки SDK карт:
  - добавлен общий singleton loader `frontend/src/services/ymapsLoader.ts` для Яндекс.Карт.
  - `ObserveView` тоже переведён на общий loader + кэш `config/ymaps`.

### Ожидаемый эффект P3

- Меньше лишних API-вызовов при обычной навигации между страницами (`Home`, `Map`, `Passport`, профиль).
- Быстрее повторный вход на экраны с картой и дашбордом за счёт cache-hit + dedupe.
- Более стабильное время рендера при бурстах навигации (исключены параллельные дубликаты одних и тех же GET).

## P4 — Backend read-list caching (2026-04-11)

- [x] Добавить server-side cache для `/api/species`:
  - `KeyedTTLCache` по ключу фильтров (`group/category/search/skip/limit`);
  - инвалидация при `create/update/delete` вида.
- [x] Добавить server-side cache для `/api/validation/queue`:
  - `KeyedTTLCache` по ключу (`status/skip/limit`);
  - инвалидация на смене статуса (`confirm/reject/request-data`);
  - дополнительная инвалидация при изменении наблюдений в релевантных статусах (`create`, `attach media`, `update needs_data`).
- [x] Добавить управляемые TTL-конфиги:
  - `SPECIES_LIST_CACHE_TTL_SECONDS` (default `120`);
  - `VALIDATION_QUEUE_CACHE_TTL_SECONDS` (default `15`).

### Проверки P4

- backend unit/integration:
  - `test_species_list_cache_invalidates_after_create`
  - `test_validation_queue_cache_invalidates_on_status_change`
- полный backend suite: `51 passed`.

### Контрольные метрики P4 (workers=2, rate-limit off, 100k synthetic)

- `GET /api/species?group=birds&limit=200`:
  - `TTL=0`: `avg ~53.1ms`, `p95 ~149.1ms`, `~351.8 rps`;
  - `TTL=120`: `avg ~23.1ms`, `p95 ~91.3ms`, `~817.4 rps`.
- `GET /api/species?limit=200`:
  - `TTL=0`: `avg ~55.8ms`, `p95 ~123.5ms`, `~338.7 rps`;
  - `TTL=120`: `avg ~19.4ms`, `p95 ~51.3ms`, `~969.2 rps`.
- `GET /api/validation/queue?status=on_review&limit=50`:
  - `TTL=0`: `avg ~52.6ms`, `p95 ~108.1ms`, `~350.7 rps`;
  - `TTL=15`: `avg ~29.2ms`, `p95 ~90.0ms`, `~652.7 rps`.

## P5 — Count-elision для list endpoints (2026-04-11)

- [x] Добавить опциональный query-параметр `include_total` (default `true`) для:
  - `/api/species`
  - `/api/observations`
  - `/api/observations/my`
  - `/api/validation/queue`
- [x] Убрать обязательность `total` в list-схемах (теперь `int | null`), чтобы можно было пропускать `COUNT(*)`.
- [x] Обновить cache keys в backend для list-cache:
  - `/api/species`: key включает `include_total`;
  - `/api/validation/queue`: key включает `include_total`.
- [x] Перевести фронтовые запросы, где `total` не используется, на `include_total=false`:
  - `Identify`, `Observe`, `ExpertQueue`, `EcoPassport`, `Admin`, `MyObservations`.
- [x] Добавить тесты:
  - `test_species_list_include_total_false_uses_separate_cache_key`
  - `test_validation_queue_include_total_false_uses_separate_cache_key`
  - `test_observation_lists_can_skip_total_count`

### Проверки P5

- `ruff check` — ok.
- backend tests: `54 passed`.
- frontend build: ok.

### Контрольные метрики P5 (workers=2, rate-limit off, clean profile)

Замер: `120 requests`, `concurrency=20`, warmup `10`, `statuses={200:120}`.

- `GET /api/species?limit=200`:
  - `include_total=true`: `avg ~30.6ms`, `p95 ~97.0ms`, `~627.1 rps`;
  - `include_total=false`: `avg ~11.7ms`, `p95 ~16.2ms`, `~1555.0 rps`.
- `GET /api/observations?limit=200`:
  - `include_total=true`: `avg ~83.4ms`, `p95 ~203.0ms`, `~218.3 rps`;
  - `include_total=false`: `avg ~66.4ms`, `p95 ~123.8ms`, `~283.0 rps`.
- `GET /api/observations/my?limit=50`:
  - `include_total=true`: `avg ~28.7ms`, `p95 ~69.3ms`, `~581.9 rps`;
  - `include_total=false`: `avg ~19.9ms`, `p95 ~27.0ms`, `~700.1 rps`.
- `GET /api/validation/queue?status=on_review&limit=50`:
  - `include_total=true`: `avg ~19.9ms`, `p95 ~50.3ms`, `~803.2 rps`;
  - `include_total=false`: `avg ~17.1ms`, `p95 ~25.1ms`, `~972.4 rps`.

## P6 — Notifications polling offload (2026-04-11)

- [x] Добавить server-side cache для `GET /api/notifications/unread-count`:
  - `KeyedTTLCache` по `user_id`;
  - TTL через новый env `NOTIFICATION_UNREAD_CACHE_TTL_SECONDS` (default `10`).
- [x] Добавить инвалидацию unread-cache:
  - при `PATCH /api/notifications/{id}/read`;
  - при создании уведомлений в `validation` (`confirm/reject/request-data`).
- [x] Обновить конфиги:
  - `backend/app/config.py`
  - `.env.example`
  - `docker-compose.perf.yml`
- [x] Добавить тесты:
  - `test_unread_count_cache_invalidates_after_mark_read`
  - `test_validation_invalidates_author_unread_count_cache`

### Проверки P6

- `ruff check` — ok.
- backend tests: `56 passed`.

### Эффект P6

- Основной эффект — снижение лишних `COUNT(*)` при регулярном polling из UI:
  - без cache: запрос в БД выполняется на каждый hit;
  - с cache: при стабильной нагрузке повторные запросы в пределах TTL обслуживаются из памяти процесса.

## P7 — Media access query path (2026-04-11)

- [x] Упростить DB-path для выдачи observation media:
  - в `media_serve` проверка доступа по `s3_key/thumbnail_key` переведена с двух SQL-запросов на один `join`.
  - применено к обоим маршрутам:
    - `GET /api/media/observations/{filename}`
    - `GET /api/media/thumbnails/{filename}`
- [x] Проверки:
  - `tests/test_media_access.py`, `tests/test_media_processing.py`, `tests/test_media_validation.py` — green.
  - полный backend suite — `56 passed`.

### Эффект P7

- Меньше запросов к БД на каждый запрос защищённого media-ресурса.
- На страницах со списками наблюдений и thumbnail-превью уменьшается DB-overhead при скролле и повторных открытиях.

## P8 — Notifications list count-elision (2026-04-11)

- [x] Добавить `include_total` (default `true`) для `GET /api/notifications`.
- [x] Обновить schema: `NotificationListResponse.total -> int | null`.
- [x] Добавить тест:
  - `test_list_notifications_can_skip_total_count`.

### Проверки P8

- `ruff check` — ok.
- backend tests — `57 passed`.

## P9 — Architecture follow-up: runtime metrics (2026-04-11)

- [x] Добавить внутренний runtime-слой метрик запросов:
  - счётчики `requests/errors/status/method`;
  - агрегаты latency по route-шаблонам.
- [x] Интегрировать сбор метрик в `RequestLoggingMiddleware`.
- [x] Добавить защищённый endpoint:
  - `GET /api/metrics` (только `admin`).
- [x] Добавить тесты:
  - `test_metrics_endpoint_requires_admin`
  - `test_metrics_endpoint_collects_request_stats`

### Проверки P9

- `ruff check` — ok.
- backend tests — `59 passed`.

## P10 — Architecture follow-up: persistent audit trail (2026-04-11)

- [x] Добавить персистентный audit log в БД:
  - новая таблица `audit_logs` (модель + Alembic migration);
  - индексы для операционных фильтров (`action`, `actor_user_id`, `target_type/target_id`, `created_at`).
- [x] Расширить `audit_event(...)`:
  - сохранение события в таблицу `audit_logs` (кроме structured logging);
  - запись `request_id` из контекста запроса.
- [x] Подключить DB-персистентность в существующих точках audit:
  - `species` (`create/update/delete`);
  - `validation` (`confirm/reject/request-data`, включая `noop`);
  - `admin` (`zones/import`).
- [x] Добавить admin endpoint для чтения audit trail:
  - `GET /api/admin/audit/events`;
  - фильтры: `action`, `target_type`, `actor_user_id`, `outcome`, `request_id`, `created_from`, `created_to`;
  - пагинация: `skip/limit`, поддержка `include_total`.
- [x] Добавить/обновить тесты:
  - `tests/test_audit_logging.py` проверяет persistence в `audit_logs`;
  - `tests/test_audit_api.py` проверяет ACL + фильтры/`include_total`.

### Проверки P10

- `ruff check` — ok.
- backend tests (dockerized) — `61 passed`.

## P11 — Frontend admin audit console (2026-04-11)

- [x] Расширить `AdminView` вкладкой `Аудит`:
  - таблица audit-событий (время, action, actor, target, outcome, details, request_id);
  - server-side пагинация;
  - фильтры по `action`, `target_type`, `actor_user_id`, `outcome`, `request_id`.
- [x] Добавить обновление/сброс фильтров и короткий client cache для повторных открытий вкладки.
- [x] Добавить cache invalidation audit-вкладки после админ-действий (`species create/delete`, `zones import`).

### Проверки P11

- frontend build — ok.

## P12 — Audit retention and maintenance (2026-04-11)

- [x] Добавить управляемый retention-порог:
  - новый env/config `AUDIT_LOG_RETENTION_DAYS` (default `180`).
- [x] Добавить admin maintenance endpoint:
  - `POST /api/admin/audit/purge`;
  - режимы `dry_run=true/false`;
  - параметры: `older_than_days` (default из конфига);
  - результат: `candidates/deleted/cutoff`.
- [x] Логировать факт реальной очистки в audit trail:
  - action: `admin.audit_purge`.
- [x] Добавить операторский скрипт:
  - `scripts/purge_audit_logs.sh` (`--dry-run`, `--days N`).
- [x] Обновить тесты API:
  - ACL для purge endpoint;
  - сценарий dry-run и реального удаления.

### Проверки P12

- backend tests (dockerized) — `63 passed`.

## P13 — Rate limiting fairness (2026-04-11)

- [x] Улучшить идентификацию клиента в `RateLimitMiddleware`:
  - для авторизованных запросов использовать `JWT sub` (`user:<sub>`) вместо общего IP-бакета;
  - fallback на `x-forwarded-for`/`client.host` для анонимных или невалидных токенов.
- [x] Добавить тесты middleware:
  - лимит по IP для анонимных запросов;
  - изоляция лимитов между разными авторизованными пользователями.

### Проверки P13

- backend tests (dockerized) — `65 passed`.

## P14 — Ops automation: migrations + daily maintenance (2026-04-11)

- [x] Добавить единый скрипт применения миграций:
  - `scripts/migrate_db.sh` (PostGIS ensure + `alembic upgrade head` + вывод текущей revision).
- [x] Добавить ежедневный maintenance-runner:
  - `scripts/maintenance_daily.sh` (backup + purge audit retention);
  - режим `--dry-run`, опции `--days`, `--skip-backup`, `--skip-purge`.
- [x] Обновить эксплуатационную документацию:
  - runbook для миграций;
  - runbook для ежедневного maintenance;
  - пример `cron`.
- [x] Добавить scheduled CI smoke для maintenance:
  - `.github/workflows/maintenance-smoke.yml` (`workflow_dispatch` + weekly schedule).

### Проверки P14

- `./scripts/migrate_db.sh` — green (`revision=d3e4f5a6b7c8`).
- `./scripts/maintenance_daily.sh --dry-run` — green.
- `./scripts/maintenance_daily.sh --skip-backup` — green.
- backend tests (dockerized) — `65 passed`.

## P15 — Release smoke automation (2026-04-11)

- [x] Добавить post-deploy smoke script:
  - `scripts/release_smoke.py`;
  - проверки `health`, `ready`, `species`, `map/zones`;
  - опциональные admin-checks (`metrics`, `admin/audit/events`) при наличии bearer token.
- [x] Добавить workflow ручного запуска smoke после релиза:
  - `.github/workflows/post-deploy-smoke.yml` (`workflow_dispatch`, input `base_url`).
- [x] Обновить docs/runbook по post-deploy проверкам.

### Проверки P15

- local script run against `http://localhost:8000` — green (`checks_total=4`).
- local script run with admin token — green (`checks_total=6`).

## P16 — CI release gates hardening (2026-04-11)

- [x] Интегрировать release smoke в основной CI backend job:
  - после старта локального API и perf-smoke;
  - проверка публичных endpoint-ов через `scripts/release_smoke.py`.
- [x] Обновить runbook с пометкой про CI release smoke.

### Проверки P16

- локальный запуск `scripts/release_smoke.py` (public) — green.

## P17 — Admin ops summary endpoint (2026-04-11)

- [x] Добавить admin endpoint `GET /api/admin/ops/summary`:
  - агрегаты по каталогу/очереди валидации/инцидентам/уведомлениям;
  - агрегаты по audit trail (`total`, `last_24h`);
  - встроенный runtime metrics snapshot.
- [x] Добавить тесты:
  - ACL (`employee` -> `403`);
  - корректность структуры и базовых агрегатов ответа.
- [x] Обновить API/runbook documentation.

### Проверки P17

- backend tests (dockerized) — `67 passed`.

## P18 — Admin UI ops snapshot (2026-04-11)

- [x] Подключить `GET /api/admin/ops/summary` во фронт:
  - сводные ops-карточки в admin audit tab (каталог, очередь, инциденты, аудит 24ч, API error rate);
  - ручное обновление сводки;
  - короткий client-cache и инвалидация после админ-операций.
- [x] Обновить поведение вкладки `Аудит`:
  - одновременная загрузка audit-ленты и ops summary;
  - refresh summary после purge/import.

### Проверки P18

- frontend build — ok.
- backend tests (dockerized) — `67 passed`.

## P19 — Scheduled ops heartbeat (2026-04-11)

- [x] Добавить периодический heartbeat workflow:
  - `.github/workflows/ops-heartbeat.yml` (каждые 6 часов + manual dispatch);
  - использует `scripts/release_smoke.py`.
- [x] Добавить безопасный fallback:
  - если `OPS_BASE_URL` не задан и input пустой — job корректно пропускается.
- [x] Обновить документацию по secrets (`OPS_BASE_URL`, `SMOKE_ADMIN_TOKEN`).

### Проверки P19

- smoke script (local) — green.

## P20 — Auth env hardening for CI/test (2026-04-11)

- [x] Уточнить policy role-resolution в auth:
  - role claim из JWT учитывается в `development` и `test`;
  - в остальных env role claim игнорируется (fallback role из БД).
- [x] Добавить тесты:
  - `test` env: admin-role claim даёт доступ к admin endpoint;
  - `production` env: admin-role claim не повышает права.

### Проверки P20

- backend tests (dockerized) — `69 passed`.

## P21 — Ops alerting snapshot (2026-04-11)

- [x] Добавить admin endpoint `GET /api/admin/ops/alerts`:
  - вычисление сигналов по порогам:
    - `on_review > OPS_ALERT_ON_REVIEW_THRESHOLD`
    - `open_incidents > OPS_ALERT_OPEN_INCIDENTS_THRESHOLD`
    - `error_rate_percent > OPS_ALERT_ERROR_RATE_PERCENT_THRESHOLD`
  - ответ со статусом (`ok|alert`), списком активных алертов, snapshot и thresholds.
- [x] Добавить/обновить конфиги:
  - `backend/app/config.py`
  - `.env.example`
- [x] Добавить backend тесты:
  - ACL для `employee` (`403`);
  - сценарий `status=ok`;
  - сценарий `status=alert` с тремя типами сигналов.
- [x] Подключить `ops/alerts` в admin UI:
  - блок «Пороговые оповещения» во вкладке `Аудит`;
  - ручной refresh вместе с ops summary;
  - short client cache + инвалидация после admin-операций.
- [x] Расширить release smoke:
  - admin-check `/api/admin/ops/alerts`;
  - новый флаг `--fail-on-ops-alerts`;
  - scheduled heartbeat (`ops-heartbeat.yml`) запускает smoke с блокирующей проверкой пороговых сигналов.

### Проверки P21

- `ruff check app/routers/admin.py tests/test_admin_ops_alerts.py` — ok.
- backend tests (dockerized) — `72 passed`.
- frontend build — ok.

## P22 — Media pipeline: single-pass processing + image guardrails (2026-04-11)

- [x] Усилить image guardrails в backend-config:
  - `MEDIA_MAX_IMAGE_DIMENSION` (default `2560`);
  - `MEDIA_MAX_IMAGE_PIXELS` (default `24_000_000`);
  - `MEDIA_THUMBNAIL_SIZE` (default `400`).
- [x] Обновить media-service:
  - проверка pixel-budget до обработки;
  - auto-resize крупных изображений по длинной стороне;
  - thumbnail generation из уже обработанного изображения (без повторного `get_object`).
- [x] Ускорить attach-flow:
  - `POST /api/observations/{id}/media` теперь строит optimized-image и thumbnail в одном decode-pass.
- [x] Добавить/обновить unit tests:
  - resize по `MEDIA_MAX_IMAGE_DIMENSION`;
  - отказ при превышении `MEDIA_MAX_IMAGE_PIXELS`;
  - проверка, что thumbnail строится без повторного fetch из S3.

### Проверки P22

- `ruff check app/services/media.py app/routers/observations.py tests/test_media_processing.py` — ok.
- `pytest -q tests/test_media_processing.py` — ok.
- backend tests (dockerized) — ok.

## P23 — Dev auth endpoint hardening (2026-04-11)

- [x] Ужесточить gate для `POST /api/dev/token`:
  - endpoint теперь учитывает не только `APP_ENV=development`, но и `ENABLE_DEV_AUTH=true`.
- [x] Добавить совместимый формат ответа:
  - `access_token` + `token_type=bearer`;
  - сохранён alias `token` для обратной совместимости.
- [x] Добавить backend тесты:
  - `ENABLE_DEV_AUTH=false` -> `403`;
  - проверка формата `access_token/token_type`.

### Проверки P23

- `ruff check app/routers/dev_auth.py tests/test_auth.py` — ok.
- `pytest -q tests/test_auth.py` — ok.
- backend tests (dockerized) — ok.

## P24 — Query validation hardening for map/observation filters (2026-04-11)

- [x] Ужесточить валидацию `group` query-параметра:
  - `GET /api/observations` принимает только `SpeciesGroup` enum;
  - `GET /api/map/observations` принимает только `SpeciesGroup` enum.
- [x] Сохранить прежнюю бизнес-логику фильтрации:
  - фильтр по группе применяется через `group.value` к строковому полю `Observation.group`;
  - cache key в map-router нормализован к строковому value enum.
- [x] Добавить тесты на негативные сценарии:
  - `group=unknown` -> `422` для `/api/observations`;
  - `group=unknown` -> `422` для `/api/map/observations`.

### Проверки P24

- `ruff check app/routers/map.py app/routers/observations.py tests/test_map_validation.py tests/test_observations_access.py` — ok.
- `pytest -q tests/test_map_validation.py tests/test_observations_access.py` — ok.
- backend tests (dockerized) — ok.

## P25 — Enum hardening for identifier/export filters (2026-04-11)

- [x] Ужесточить валидацию `group` в identifier:
  - `GET /api/identifier/tree` принимает `SpeciesGroup` вместо произвольной строки.
- [x] Ужесточить валидацию `group` в export:
  - `GET /api/export/observations` принимает `SpeciesGroup` вместо произвольной строки.
- [x] Добавить тесты:
  - `group=unknown` -> `422` для identifier/export;
  - happy-path c валидной группой для identifier/export.

### Проверки P25

- `ruff check app/routers/identifier.py app/routers/export.py tests/test_query_validation.py` — ok.
- `pytest -q tests/test_query_validation.py` — ok.
- backend tests (dockerized) — ok.

## P26 — UTC-aware datetime cleanup (2026-04-11)

- [x] Убрать deprecated `datetime.utcnow()` в runtime-коде:
  - `backend/app/routers/export.py`
  - `backend/app/routers/gamification.py`
- [x] Привести month-window в monthly challenge к timezone-aware UTC datetime.
- [x] Обновить demo seed:
  - `reviewed_at` использует `datetime.now(timezone.utc)`.

### Проверки P26

- `ruff check app/routers/export.py app/routers/gamification.py app/seed/seed_demo.py` — ok.
- `pytest -q tests/test_query_validation.py tests/test_gamification_stats.py tests/test_gamification_service.py` — ok.
- backend tests (dockerized) — ok.

## P27 — Identifier suggest payload hardening (2026-04-11)

- [x] Ввести явную схему запроса для `POST /api/identifier/suggest`:
  - `species_ids` — список `int > 0`, `min_length=1`, `max_length=100`.
- [x] Защититься от дублирующихся идентификаторов:
  - validator отклоняет payload с повторяющимися `species_ids`.
- [x] Добавить тесты:
  - пустой список -> `422`;
  - дубликаты -> `422`;
  - валидный payload -> `200`.

### Проверки P27

- `ruff check app/routers/identifier.py tests/test_query_validation.py` — ok.
- `pytest -q tests/test_query_validation.py` — ok.
- backend tests (dockerized) — ok.

## P28 — Frontend quality gate (Vitest + CI) (2026-04-11)

- [x] Поднять unit test stack для frontend:
  - добавить `vitest` в devDependencies;
  - добавить script `test:unit`.
- [x] Добавить первые unit tests для критичного клиентского runtime:
  - `frontend/src/api/client.ts` (cache/dedupe/invalidation).
- [x] Включить frontend unit tests в CI:
  - job `frontend` выполняет `npm run test:unit` перед build.
- [x] Обновить roadmap-checks по фактическому прогону.

Ожидаемый эффект:
- раннее обнаружение регрессий frontend-логики (без ручной проверки UI);
- более стабильный релизный цикл на стадии тестирования.

Риски:
- flaky tests при неправильной изоляции in-memory кэша;
- увеличение времени CI.

Критерии готовности:
- `npm run test:unit` стабильно green локально и в CI;
- минимум один критичный модуль frontend покрыт позитивными и негативными кейсами;
- frontend job в CI блокирует merge при падении unit tests.

### Проверки P28

- `npm run test:unit` — `4 passed`.
- `npm run build` — ok.

## P29 — Redis shared cache for hot reads

- [x] Перенести ключевые read-cache c in-memory на Redis:
  - [x] `/api/map/observations` (Redis-backed cache + in-memory fallback)
  - [x] `/api/dashboard/summary` (Redis-backed cache + in-memory fallback)
  - [x] `/api/gamification/stats` (Redis-backed cache + in-memory fallback)
  - [x] `/api/species` (pilot: Redis-backed cache + in-memory fallback)
  - [x] `/api/validation/queue` (Redis-backed cache + in-memory fallback)
- [x] Добавить versioned cache keys и управляемую инвалидацию.
- [x] Добавить тесты на инвалидацию и согласованность выдачи при `workers > 1`.
  - [x] unit tests для Redis cache service (доступность Redis + fallback path).
  - [x] unit tests для versioned invalidation и shared-cache поведения между воркерами.

Ожидаемый эффект:
- одинаковое cache-поведение на нескольких воркерах/инстансах;
- снижение нагрузки на БД при горизонтальном масштабировании.

Риски:
- stale-данные при неполной инвалидации;
- рост сложности cache-key management.

Критерии готовности:
- Redis cache реально используется на целевых endpoint;
- инвалидация покрыта тестами;
- p95 не хуже базового профиля на контрольном нагрузочном прогоне.

### Проверки P29 (этап 1: species pilot)

- `ruff check app/services/cache.py app/routers/species.py tests/test_cache_service.py` — ok.
- `pytest -q tests/test_cache_service.py tests/test_species.py` — `13 passed`.
- backend tests (dockerized) — `88 passed`.

### Проверки P29 (этап 2: validation + map)

- `ruff check app/routers/validation.py app/routers/map.py tests/test_validation_flow.py tests/test_map_validation.py` — ok.
- `pytest -q tests/test_validation_flow.py tests/test_map_validation.py` — `16 passed`.
- backend tests (dockerized) — `88 passed`.

### Проверки P29 (этап 3: dashboard + gamification)

- `ruff check app/routers/dashboard.py app/routers/gamification.py tests/test_dashboard_summary.py tests/test_gamification_stats.py` — ok.
- `pytest -q tests/test_dashboard_summary.py tests/test_gamification_stats.py` — `4 passed`.
- backend tests (dockerized) — `88 passed`.

### Проверки P29 (этап 4: versioned keys + managed invalidation)

- `ruff check app/services/cache.py app/config.py app/routers/species.py app/routers/validation.py app/routers/map.py app/routers/dashboard.py app/routers/gamification.py tests/test_cache_service.py` — ok.
- `pytest -q tests/test_cache_service.py tests/test_species.py tests/test_validation_flow.py tests/test_map_validation.py tests/test_dashboard_summary.py tests/test_gamification_stats.py` — `35 passed`.
- backend tests (dockerized) — `90 passed`.

## P30 — Async media pipeline

- [x] Вынести optimize/thumbnail в фоновый pipeline (queue + worker).
  - DB-backed queue на `obs_media` (`processing_status/next_retry_at`);
  - batch processor `app/services/media_pipeline.py`;
  - worker script `backend/scripts/media_worker.py`.
- [x] Добавить статус обработки медиа и retry policy.
  - статусы: `pending/processing/ready/failed`;
  - retry policy: `MEDIA_PROCESSING_MAX_ATTEMPTS`, `MEDIA_PROCESSING_RETRY_BACKOFF_SECONDS`.
- [x] Интегрировать состояние обработки в API/админ-операции.
  - `ObservationResponse.media[*]` расширен полями обработки;
  - `GET /api/admin/ops/summary` дополнен `media_pipeline`;
  - добавлен admin trigger `POST /api/admin/ops/media/process`.

Ожидаемый эффект:
- быстрый ответ attach endpoint под пиковыми загрузками;
- более устойчивая обработка больших батчей фото.

Риски:
- рассинхрон статусов между БД и объектным хранилищем;
- сложность retry/idempotency.

Критерии готовности:
- тяжелая медиа-обработка не выполняется синхронно в запросе пользователя;
- есть наблюдаемый queue backlog и retry статистика;
- есть тесты на success/fail/retry сценарии.

### Проверки P30

- `ruff check app/models/observation.py app/schemas/observation.py app/config.py app/services/media_pipeline.py app/routers/observations.py app/routers/admin.py tests/test_media_pipeline.py tests/test_admin_ops_summary.py migrations/versions/e6f7a8b9c0d1_add_obs_media_processing_queue.py` — ok.
- `pytest -q tests/test_media_pipeline.py tests/test_admin_ops_summary.py tests/test_media_access.py tests/test_dashboard_summary.py` — `10 passed`.
- backend tests (dockerized) — `95 passed`.
- `alembic upgrade head` + `alembic current` — `e6f7a8b9c0d1 (head)`.

## P31 — Observability v2

- [x] Добавить Prometheus-friendly метрики.
  - `GET /api/metrics/prometheus` (admin-only);
  - экспорт route-level API метрик + cache-health метрик.
- [x] Расширить alerting правила (error rate, queue lag, cache health).
  - добавлены сигналы:
    - `media_queue_depth_high`
    - `media_queue_lag_high`
    - `media_processing_failed_high`
    - `cache_backend_degraded`
  - расширены пороги через env/config.
- [x] Обновить health/readiness сигналами критичных зависимостей.
  - `GET /api/health/ready` теперь отдаёт `dependency_details` (latency/error) + cache totals;
  - добавлен `GET /api/health/deps` для расширенного dependency snapshot.
- [x] Подготовить dashboard + runbook для test/staging.
  - добавлен runbook `docs/runbooks/observability-v2.md` с triage-потоком и списком ключевых метрик;
  - README обновлён по новым endpoint/thresholds.

Ожидаемый эффект:
- более раннее обнаружение деградаций;
- ускорение диагностики инцидентов.

Риски:
- шумные алерты;
- дублирование существующих метрик при плохой консолидации.

Критерии готовности:
- метрики доступны в machine-readable формате;
- есть рабочие алерты на ключевые operational сигналы;
- runbook позволяет пройти типовой incident triage.

### Проверки P31

- `ruff check app/services/cache.py app/services/metrics.py app/routers/metrics.py app/routers/health.py app/routers/admin.py app/config.py tests/test_metrics.py tests/test_health.py tests/test_admin_ops_alerts.py tests/test_admin_ops_summary.py tests/test_cache_service.py` — ok.
- `pytest -q tests/test_metrics.py tests/test_health.py tests/test_admin_ops_alerts.py tests/test_admin_ops_summary.py tests/test_cache_service.py` — `21 passed`.
- backend tests (dockerized) — `99 passed`.
- `python3 scripts/release_smoke.py --base-url http://localhost:8000 --admin-token "<token>"` — green (`checks_total=9`, включая `/api/health/deps` и `/api/metrics/prometheus`).

## P32 — CD to test/staging

- [x] Автоматизировать build/publish Docker images.
  - добавлен workflow `.github/workflows/cd-build-publish.yml` (GHCR publish).
- [x] Добавить deploy workflow в test/staging с миграциями.
  - добавлен workflow `.github/workflows/deploy-staging.yml`;
  - поддержка `run_migrations=true/false`;
  - image-based compose: `docker-compose.staging.yml`.
- [x] Встроить post-deploy smoke + rollback path.
  - post-deploy smoke встроен в `deploy-staging.yml` (`scripts/release_smoke.py`);
  - rollback job переключает staging на previous backend/frontend image refs при падении smoke.
- [x] Зафиксировать release checklist.
  - добавлен runbook `docs/runbooks/release-checklist.md`.

Ожидаемый эффект:
- предсказуемые и быстрые релизы без ручного дрейфа;
- снижение человеческих ошибок при выкладке.

Риски:
- некорректный rollback при несовместимых миграциях;
- environment drift между local и staging.

Критерии готовности:
- deploy в test/staging выполняется одним workflow;
- миграции и smoke обязательны;
- rollback сценарий протестирован.

### Проверки P32

- `python3`-валидация YAML workflow (`.github/workflows/*.yml`) — ok.
- `BACKEND_IMAGE=... FRONTEND_IMAGE=... docker compose -f docker-compose.staging.yml config` — ok.
- основной `CI` дополнен job-ами `workflow-config` и `security-fast` для ранней проверки workflow/compose и restore-drill интерфейса.
- добавлен rehearsal workflow `.github/workflows/deploy-rehearsal.yml` + скрипт `scripts/staging_deploy_rehearsal.sh` для регулярной проверки rollback-сценария.
- rehearsal-контур изолирован от локального dev-стека: `db/redis/minio` вынесены в `docker-compose.rehearsal.yml` (без host-портов), а `docker-compose.staging.yml` поддерживает `STAGING_BACKEND_PORT`/`STAGING_FRONTEND_PORT`.

## P33 — Backup / restore drill

- [x] Регулярно выполнять restore drill из актуального backup.
  - добавлен scheduled workflow `.github/workflows/restore-drill.yml`.
- [x] Измерить и задокументировать RTO/RPO.
  - добавлен скрипт `scripts/restore_drill.sh`, который пишет summary JSON с `rto_seconds/rpo_seconds`.
- [x] Проверять post-restore работоспособность API smoke-сценарием.
  - `restore_drill.sh` встроенно запускает `scripts/release_smoke.py` после восстановления.

Ожидаемый эффект:
- подтвержденная аварийная готовность, а не только формальный backup.

Риски:
- вскрытие несовместимостей при restore;
- повышенные операционные затраты на drill.

Критерии готовности:
- restore reproducible на test контуре;
- RTO/RPO зафиксированы;
- после restore smoke-check проходит полностью.

### Проверки P33

- `python3`-валидация YAML workflow (`.github/workflows/*.yml`) — ok.
- `./scripts/restore_drill.sh --help` — ok.

## P34 — Security/dev hygiene wave

- [x] Включить dependency scanning в CI (backend/frontend).
  - добавлен workflow `.github/workflows/security-scans.yml`:
    - backend `pip-audit`
    - frontend `npm audit`
- [x] Добавить secret scanning для репозитория и workflow.
  - в `security-scans.yml` добавлен `gitleaks`.
- [x] Завершить tightening dev/demo endpoint policy (без интеграции SSO).
  - dev-auth остаётся строго под `APP_ENV=development && ENABLE_DEV_AUTH=true` (P23);
  - production config validation сохраняет блокирующие проверки небезопасных дефолтов.
- [x] Провести ревизию MinIO/media access policy.
  - добавлен runbook `docs/runbooks/media-access-policy.md`.

Ожидаемый эффект:
- снижение supply-chain и конфигурационных рисков;
- более чистый security baseline перед переходом в корпоративную инфраструктуру.

Риски:
- ложноположительные срабатывания сканеров и шум в CI;
- частичные несовместимости с текущим dev-flow.

Критерии готовности:
- security checks встроены в CI gating;
- секреты не проходят в репозиторий;
- dev endpoints и media policy документированы и проверены тестами.

### Проверки P34

- `python3`-валидация YAML workflow (`.github/workflows/*.yml`) — ok.
- `pytest -q tests/test_auth.py tests/test_media_access.py tests/test_config_security.py` — green (dev-auth/media/config security сценарии).

## P35 — Test coverage visibility gate

- [x] Зафиксировать coverage как обязательный CI-артефакт для backend.
  - в `backend` dev-deps добавлен `pytest-cov`;
  - backend job в `.github/workflows/ci.yml` запускает `pytest` с `--cov=app --cov-report=xml:../coverage/backend-coverage.xml`;
  - coverage XML публикуется в artifact `backend-coverage`.
- [x] Добавить frontend coverage-артефакт в CI.
  - frontend использует `@vitest/coverage-v8` и script `npm run test:unit:coverage`;
  - frontend job публикует `frontend/coverage/lcov.info` в artifact `frontend-coverage`.
- [x] Добавить unit-тесты для критичного frontend runtime загрузки карт.
  - добавлен `frontend/src/services/ymapsLoader.test.ts`:
    - already-loaded path;
    - dedupe concurrent loads;
    - retry после script-load error.
- [x] Расширить CI hygiene-проверки вокруг rehearsal-контура.
  - `workflow-config` валидирует `docker-compose.rehearsal.yml`;
  - `security-fast` проверяет CLI-интерфейс `scripts/staging_deploy_rehearsal.sh --help`.

Ожидаемый эффект:
- прозрачный baseline покрытия backend по каждому CI-прогону;
- более раннее обнаружение поломок ops-скриптов и rehearsal-конфигурации.

Риски:
- рост длительности backend CI job из-за coverage instrumentation;
- необходимость периодически обновлять пороги/политику quality gate по мере роста покрытия.

Критерии готовности:
- coverage-артефакты формируются в каждом backend/frontend CI run;
- compose/скрипты rehearsal проверяются на уровне CI-конфигов.

### Проверки P35

- `python3`-валидация YAML workflow (`.github/workflows/*.yml`) — ok.
- `docker compose -f docker-compose.rehearsal.yml config` — ok.
- `./scripts/staging_deploy_rehearsal.sh --help` — ok.
- dockerized smoke-проверка coverage-инструмента: `pytest -q tests/test_health.py --cov=app --cov-report=term` — green.
- `npm run test:unit:coverage` — green, `frontend/coverage/lcov.info` сформирован.

## P36 — Backend critical observations test wave

- [x] Закрыть пробелы тестов для критичных observation-endpoint'ов.
  - добавлен `backend/tests/test_observations_workflow.py`:
    - `POST /api/observations`: safety gate, incident validation, species-group override;
    - `PATCH /api/observations/{id}`: guardrails (author/status) + успешный update сценарий;
    - social-flow: comments/likes endpoints на подтверждённом наблюдении;
    - media attach guardrails: duplicate keys, max media limit, storage runtime error mapping.
- [x] Прогнать regression-поднабор по связанным сценариям.
  - observation access + workflow + media validation + query validation.

Ожидаемый эффект:
- снижение риска регрессий в ключевом пользовательском flow создания/доработки наблюдений;
- покрытие ранее слабых веток `observations`-роутера тестами поведения.

Риски:
- рост длительности backend test-suite;
- необходимость поддерживать фикстуры при эволюции observation-модели.

Критерии готовности:
- новые observation workflow тесты стабильно green;
- связанный regression-набор green без flaky-падений.

### Проверки P36

- `pytest -q tests/test_observations_workflow.py` (dockerized) — `8 passed`.
- `pytest -q tests/test_observations_access.py tests/test_observations_workflow.py tests/test_media_validation.py tests/test_query_validation.py` (dockerized) — `21 passed`.

## P37 — Gamification + validation test hardening

- [x] Добавить endpoint-тесты на основные gamification-сценарии.
  - новый файл `backend/tests/test_gamification_endpoints.py`:
    - `leaderboard` с period-фильтрами;
    - `profile` aggregation (points, achievements, discoveries, collection);
    - `species discoverer` none + filled paths;
    - `fact-of-day` empty + eligible paths;
    - `challenge` empty + found paths;
    - `quiz` empty + valid options path.
- [x] Закрыть пробелы validation по правам и idempotent-веткам.
  - новый файл `backend/tests/test_validation_permissions.py`:
    - role guardrails (`queue/confirm/reject/request-data`);
    - idempotent `reject` без дублирования notifications;
    - noop `request-data` в `needs_data` без лишних notifications.
- [x] Прогнать расширенный regression-поднабор вокруг gamification/validation/observations.

Ожидаемый эффект:
- лучшее покрытие пользовательских и модераторских сценариев без изменения runtime-кода;
- снижение риска незаметных регрессий в сложных workflow ветках.

Риски:
- рост времени тестового контура;
- потенциальная чувствительность тестов к будущей эволюции payload-контрактов.

Критерии готовности:
- новые тесты стабильно green;
- связанный regression-поднабор green;
- стиль/линт новых тестов проходит.

### Проверки P37

- `pytest -q tests/test_gamification_endpoints.py tests/test_validation_permissions.py` (dockerized) — `10 passed`.
- `pytest -q tests/test_gamification_stats.py tests/test_gamification_service.py tests/test_validation_flow.py tests/test_validation_permissions.py tests/test_observations_workflow.py` (dockerized) — `26 passed`.
- `ruff check tests/test_gamification_endpoints.py tests/test_validation_permissions.py` (dockerized) — green.

## P38 — Admin API hardening test wave

- [x] Покрыть `admin.zones_import` позитивные и негативные сценарии.
  - добавлен `backend/tests/test_admin_zones_import.py`:
    - role guardrail (`admin` only);
    - validation ошибок (`extension`, invalid JSON, empty features);
    - happy-path import с проверкой записей `site_zones` и audit event `admin.zones_import`.
- [x] Усилить тесты guardrails для `admin.audit` и `admin.ops`.
  - добавлен `backend/tests/test_admin_guardrails.py`:
    - compound filters + pagination/ordering для `GET /api/admin/audit/events`;
    - query validation для `POST /api/admin/audit/purge` (`older_than_days` bounds);
    - query validation для `POST /api/admin/ops/media/process` (`batch_size` bounds).
- [x] Прогнать расширенный admin regression-поднабор.

Ожидаемый эффект:
- снижение риска регрессий в админских эксплуатационных сценариях;
- более надёжная валидация входов на admin endpoint'ах.

Риски:
- увеличение времени test-suite;
- возможная чувствительность тестов к изменению формата admin payload.

Критерии готовности:
- новые admin тесты стабильно green;
- связанный admin regression-поднабор green;
- стиль/линт новых тестов проходит.

### Проверки P38

- `pytest -q tests/test_admin_zones_import.py tests/test_admin_guardrails.py` (dockerized) — `8 passed`.
- `pytest -q tests/test_admin_ops_summary.py tests/test_admin_ops_alerts.py tests/test_audit_api.py tests/test_admin_zones_import.py tests/test_admin_guardrails.py` (dockerized) — `20 passed`.
- `ruff check tests/test_admin_zones_import.py tests/test_admin_guardrails.py` (dockerized) — green.

## P39 — Notifications/export/map edge-case test wave

- [x] Усилить coverage notifications edge-cases.
  - добавлен `backend/tests/test_notifications_edge_cases.py`:
    - list scope/sorting/pagination для текущего пользователя;
    - `mark-read` на чужом notification не меняет состояние чужих данных;
    - idempotent `mark-read` на своём notification.
- [x] Покрыть поведение `export` endpoint на уровне XLSX-контракта.
  - добавлен `backend/tests/test_export_behavior.py`:
    - role guardrail (только ecologist/admin);
    - проверка filter-сценария (`group` + `status`) и XLSX headers/content;
    - сценарий с `species_id=None` (пустая species-ячейка).
- [x] Добавить map-behavior тесты с фокусом на чувствительность/валидацию.
  - добавлен `backend/tests/test_map_behavior.py`:
    - hidden points не выдаются, blurred координаты округляются;
    - `status != confirmed` требует ecologist/admin;
    - bbox edge-cases (range/order/format);
    - `limit` + sorting по `observed_at desc`.
- [x] Прогнать расширенный regression-поднабор по связанным роутерам.

Ожидаемый эффект:
- меньше риска регрессий в пользовательских сценариях уведомлений, карт и экспортов;
- более формализованный API-контракт для XLSX export и spatial query validation.

Риски:
- рост времени тестового набора;
- возможная чувствительность тестов к изменениям формата export/map payload.

Критерии готовности:
- новые tests green;
- связанный regression-набор green;
- style checks для новых тестов green.

### Проверки P39

- `pytest -q tests/test_notifications_edge_cases.py tests/test_export_behavior.py tests/test_map_behavior.py` (dockerized) — `10 passed`.
- `pytest -q tests/test_notifications.py tests/test_notifications_edge_cases.py tests/test_map_validation.py tests/test_map_behavior.py tests/test_query_validation.py tests/test_export_behavior.py` (dockerized) — `27 passed`.
- `ruff check tests/test_notifications_edge_cases.py tests/test_export_behavior.py tests/test_map_behavior.py` (dockerized) — green.

## P40 — Catalog content QA and bioacoustics wave

- [x] Нормализовать латинские названия для животных:
  - птицы: 0/48 неполных названий;
  - герпетофауна: 0/14;
  - млекопитающие: 0/23.
- [x] Расширить аудиоконтент карточек:
  - 50 видов со звуками;
  - новые точные записи для белоспинного дятла и сапсана после уточнения биномиальных названий.
- [x] Добавить backend-аудит качества каталога:
  - `latin_name_exact_species`;
  - `latin_name_needs_review`;
  - `latin_name_suspicious_chars`;
  - разбивка по группам и примеры записей для экспертной доработки.
- [x] Вывести показатель качества латинских названий в admin ops summary.

Ожидаемый эффект:
- каталог становится пригоднее для поиска внешних фото/звуков и экспертной проверки;
- спорные родовые/семейные записи не маскируются под готовые видовые определения;
- администратор видит контентный долг без SQL-доступа.

Риски:
- часть растений, грибов и насекомых нельзя безопасно уточнить без эксперта;
- автоматическая проверка не заменяет таксономическую рецензию.

Критерии готовности:
- все животные, птицы и герпетофауна имеют биномиальные латинские названия;
- admin summary показывает качество каталога;
- тесты защищают новый контракт summary.

### Проверки P40

- `ruff check app/services/catalog_quality.py app/routers/admin.py tests/test_admin_ops_summary.py` (dockerized) — green.
- `pytest tests/test_admin_ops_summary.py tests/test_species.py tests/test_species_content_review.py` (dockerized) — `18 passed`.
- `npm run test:unit` — `7 passed`.
- `npm run build` — ok.
- live API `/api/admin/ops/summary`: `132/207` точных латинских названий, `75` требуют уточнения, `0` с подозрительными символами.

## P41 — Catalog Latin script hygiene

- [x] Убрать явные не-ASCII опечатки из латинских родовых названий без изменения таксономического уровня:
  - `Еryngium` → `Eryngium`;
  - `Diānthus` → `Dianthus`;
  - `Pýrola` → `Pyrola`;
  - `Aesсhna` → `Aeshna`;
  - `Сheilosia` → `Cheilosia`.
- [x] Сохранить честный статус родовых/семейных записей как `needs_review`, не превращая их в виды без экспертного подтверждения.
- [x] Зафиксировать сценарий в content-review тесте.

Ожидаемый эффект:
- внешние поиски, аудио/фото-пайплайн и ручная экспертиза перестают спотыкаться о кириллицу внутри латинских имён;
- QA-сигнал `latin_name_suspicious_chars` становится чистым и пригодным для мониторинга новых ошибок.

Риски:
- это исправляет только технические символы, а не завершает экспертную таксономию растений/грибов/насекомых.

Критерии готовности:
- `latin_name_suspicious_chars = 0` в live admin summary;
- число `latin_name_needs_review` остаётся осмысленным и не скрывает родовые записи.

### Проверки P41

- `pytest tests/test_species_content_review.py tests/test_admin_ops_summary.py tests/test_species.py` (dockerized) — `18 passed`.
- `ruff check app/seed/content_review_20260417.py tests/test_species_content_review.py app/services/catalog_quality.py tests/test_admin_ops_summary.py` (dockerized) — green.
- DB audit: `0` записей с не-ASCII символами в `name_latin`, `75` записей ещё требуют экспертного уточнения.

## P42 — Catalog quality workbench

- [x] Добавить детальную admin-ручку качества каталога:
  - `GET /api/admin/catalog/quality`;
  - admin-only доступ;
  - параметр `limit` для количества кандидатов на экспертную проверку;
  - полный payload: totals, exact/needs-review/suspicious, разбивка по группам, список записей.
- [x] Вывести рабочий блок качества в разделе администрирования видов:
  - сводка `exact/total`;
  - число записей на проверку и подозрительных символов;
  - разбивка по группам;
  - таблица кандидатов с быстрым переходом в карточку вида.
- [x] Синхронизировать cache invalidation после добавления/удаления видов.

Ожидаемый эффект:
- контентная доработка каталога становится управляемой из UI, без SQL и ручного чтения ops summary;
- следующие волны таксономической чистки можно вести по конкретному списку и группам;
- администратор быстрее видит новые ошибки после правок справочника.

Риски:
- список остаётся диагностическим, а не редактором таксономии;
- часть оставшихся записей требует экспертного источника, поэтому автоматические замены здесь намеренно не выполняются.

Критерии готовности:
- endpoint доступен только admin;
- admin UI показывает полный список кандидатов в пределах `limit`;
- live API возвращает `0` suspicious chars и актуальный backlog.

### Проверки P42

- `pytest tests/test_admin_ops_summary.py tests/test_species_content_review.py tests/test_species.py -q` (dockerized) — `20 passed`.
- `ruff check app/routers/admin.py app/services/catalog_quality.py tests/test_admin_ops_summary.py` (dockerized) — green.
- `npm run test:unit` — `7 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.
- live API `/api/admin/catalog/quality?limit=200`: `207` видов, `132` точных латинских названия, `75` требуют уточнения, `0` с подозрительными символами.

## P43 — Species catalog CSV export for expert review

- [x] Добавить admin-only экспорт каталога:
  - `GET /api/admin/catalog/export`;
  - CSV с BOM для удобного открытия в Excel;
  - поля `id`, русское/латинское название, группа, категория, охранный статус, фото, аудио и quality-флаги.
- [x] Добавить фильтр `needs_review=true`:
  - экспортируются только записи без точного биномиального латинского названия;
  - сохраняются признаки `latin_name_quality` и `latin_name_suspicious_chars`.
- [x] Подключить кнопку CSV-выгрузки в admin quality-блоке.

Ожидаемый эффект:
- экспертную правку каталога можно вести в привычном табличном формате;
- остается единый источник правды в системе, а выгрузка служит рабочим листом для согласования;
- уменьшается риск ручных SQL-выборок и расхождений между UI и контентным backlog.

Риски:
- это пока экспорт, не массовый импорт обратно;
- CSV не решает вопрос авторских прав на медиа, только помогает ревизии.

Критерии готовности:
- endpoint закрыт ролью admin;
- CSV открывается как attachment и содержит ожидаемые колонки;
- `needs_review=true` на live базе возвращает 75 строк.

### Проверки P43

- `pytest tests/test_admin_ops_summary.py tests/test_species_content_review.py tests/test_species.py -q` (dockerized) — `22 passed`.
- `ruff check app/routers/admin.py app/services/catalog_quality.py tests/test_admin_ops_summary.py` (dockerized) — green.
- `npm run test:unit` — `7 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.
- live API `/api/admin/catalog/export?needs_review=true`: attachment `species-catalog-needs-review.csv`, `75` строк.

## P44 — CSV import preview for catalog review

- [x] Добавить безопасный preview-импорт экспертного CSV:
  - `POST /api/admin/catalog/import/preview`;
  - admin-only доступ;
  - проверка `.csv`, UTF-8/UTF-8 BOM и обязательной колонки `id`;
  - dry-run без записи в БД.
- [x] Вынести разбор CSV в отдельный сервис:
  - нормализация строковых полей;
  - проверка `group`, `category`, `is_poisonous`, `photo_urls`, `audio_url`;
  - сравнение с текущей записью вида;
  - отчет по изменениям, неизмененным строкам и ошибкам.
- [x] Подключить UI-предпросмотр в admin quality-блоке:
  - загрузка CSV;
  - сводка по строкам;
  - таблица будущих изменений;
  - таблица ошибок.

Ожидаемый эффект:
- эксперт может править выгрузку в таблице, а администратор видит последствия до изменения базы;
- снижается риск случайной порчи справочника при массовых правках;
- появляется фундамент для следующего шага: подтвержденного массового применения правок.

Риски:
- пока нет apply-режима, только проверка;
- CSV остается чувствительным к ручным изменениям колонок, поэтому ошибки показываются построчно.

Критерии готовности:
- preview endpoint не меняет БД;
- ошибки строк не блокируют анализ остальных строк;
- UI показывает changes/errors понятно для администратора.

### Проверки P44

- `pytest tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py tests/test_species_content_review.py tests/test_species.py -q` (dockerized) — `25 passed`.
- `ruff check app/services/catalog_import.py app/services/catalog_quality.py app/routers/admin.py tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py` (dockerized) — green.
- `npm run test:unit` — `7 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P45 — Confirmed CSV catalog apply

- [x] Добавить применение проверенного CSV:
  - `POST /api/admin/catalog/import/apply`;
  - повторное использование preview-валидации;
  - отказ, если в CSV есть ошибки;
  - обновление только реально измененных полей.
- [x] Сохранить операционную трассируемость:
  - audit event `admin.catalog_import_apply`;
  - filename, total/changing/unchanged/applied counts в details;
  - инвалидация кеша списка видов после массового обновления.
- [x] Подключить UI-действие после чистого preview:
  - кнопка `Применить CSV` появляется только при `error_rows = 0` и наличии изменений;
  - перед применением есть подтверждение;
  - после применения обновляются список видов и quality summary.

Ожидаемый эффект:
- экспертные правки можно провести полным циклом: выгрузка → правка → preview → подтвержденное применение;
- массовое обновление перестает быть ручной SQL-операцией;
- история изменений остается видимой в audit log.

Риски:
- пока нет versioning/rollback отдельной пачки, поэтому применять нужно после внимательного preview;
- CSV apply обновляет справочник по `id`, поэтому файл должен быть из актуальной выгрузки.

Критерии готовности:
- apply endpoint не применяет CSV с ошибками;
- успешный apply меняет только поля из preview;
- UI не предлагает применить ошибочный файл.

### Проверки P45

- `pytest tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py tests/test_species_content_review.py tests/test_species.py -q` (dockerized) — `27 passed`.
- `ruff check app/services/catalog_import.py app/services/catalog_quality.py app/routers/admin.py tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py` (dockerized) — green.
- `npm run test:unit` — `7 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P46 — CSV import batch history and rollback

- [x] Добавить модель и миграцию batch-истории:
  - `catalog_import_batches`;
  - статус `applied / rolled_back`;
  - actor/rollback actor;
  - счетчики строк;
  - JSON-снимок `before/after` по каждой измененной записи.
- [x] Расширить apply-контур:
  - `POST /api/admin/catalog/import/apply` теперь возвращает `batch_id`;
  - создается batch-запись до commit;
  - audit event содержит `batch_id`.
- [x] Добавить admin API истории и отката:
  - `GET /api/admin/catalog/import/batches`;
  - `POST /api/admin/catalog/import/batches/{batch_id}/rollback`;
  - rollback разрешен только для `applied`;
  - rollback проверяет, что текущие значения все еще совпадают с `after`, чтобы не затереть более поздние ручные правки.
- [x] Подключить UI:
  - история последних CSV-импортов в admin quality-блоке;
  - статус пачки;
  - кнопка отката для примененных batch.

Ожидаемый эффект:
- массовые CSV-правки становятся обратимыми;
- администратор видит историю контентных пачек без SQL;
- снижается страх перед экспертными массовыми обновлениями справочника.

Риски:
- rollback откатывает только batch, если после него строки не менялись;
- для сложных цепочек редактирования позже может понадобиться более полноценное content versioning.

Критерии готовности:
- apply создает batch и возвращает `batch_id`;
- rollback восстанавливает `before`-значения и меняет статус batch;
- повторный rollback отклоняется;
- live DB мигрирована до head.

### Проверки P46

- `pytest tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py tests/test_species_content_review.py tests/test_species.py -q` (dockerized) — `29 passed`.
- `ruff check app/models/catalog_import.py app/services/catalog_import.py app/services/catalog_quality.py app/routers/admin.py tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py migrations/versions/a1b2c3d4e5f6_add_catalog_import_batches.py` (dockerized) — green.
- `npm run test:unit` — `7 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.
- `alembic upgrade head` (dockerized live DB) — applied `a1b2c3d4e5f6`.
- live API `/api/admin/catalog/import/batches?limit=10`: `0` batch, endpoint доступен.

## P47 — CSV import batch detail review

- [x] Добавить detail endpoint для batch-истории:
  - `GET /api/admin/catalog/import/batches/{batch_id}`;
  - возвращает metadata batch и полный список `changes`.
- [x] Покрыть контракт тестом:
  - apply создает batch;
  - detail возвращает `before/after` по измененным полям.
- [x] Подключить UI-просмотр:
  - кнопка `Детали` в истории CSV-импортов;
  - таблица измененных видов;
  - поля, старые и новые значения.

Ожидаемый эффект:
- администратор видит содержимое batch до отката;
- rollback становится проверяемым действием, а не слепой кнопкой;
- контентные пачки легче обсуждать с экспертом.

Риски:
- detail показывает технические имена полей; позже можно добавить человекочитаемые labels.

Критерии готовности:
- detail endpoint закрыт admin-role;
- detail возвращает изменения batch;
- UI показывает выбранный batch рядом с историей.

### Проверки P47

- `pytest tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py tests/test_species_content_review.py tests/test_species.py -q` (dockerized) — `30 passed`.
- `ruff check app/models/catalog_import.py app/services/catalog_import.py app/services/catalog_quality.py app/routers/admin.py tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py migrations/versions/a1b2c3d4e5f6_add_catalog_import_batches.py` (dockerized) — green.
- `npm run test:unit` — `7 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P48 — Human-readable CSV import review labels

- [x] Вынести форматирование CSV import preview/detail в frontend-helper:
  - `formatCatalogImportFields`;
  - `formatCatalogImportDelta`;
  - человекочитаемые labels для полей справочника.
- [x] Улучшить отображение значений:
  - `null`, `undefined` и пустая строка показываются как `пусто`;
  - boolean показывается как `да/нет`;
  - массивы URL показываются через `;`.
- [x] Подключить helper в admin quality-блоке:
  - preview изменений;
  - batch detail;
  - rollback review.

Ожидаемый эффект:
- администратор и эксперт читают изменения без знания внутренних имен полей;
- снижается риск ошибочного применения или отката CSV-пачки;
- UX контентной ревизии становится ближе к редакционному инструменту.

Риски:
- labels живут на frontend; при добавлении новых CSV-полей нужно обновлять словарь.

Критерии готовности:
- formatter покрыт unit-тестами;
- admin build проходит;
- backend regression по CSV import не сломан.

### Проверки P48

- `npm run test:unit` — `10 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.
- `pytest tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py -q` (dockerized) — `16 passed`.
- `ruff check app/models/catalog_import.py app/services/catalog_import.py app/routers/admin.py tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py` (dockerized) — green.

## P49 — CSV import batch history filters and pagination

- [x] Добавить backend-фильтр истории CSV batch:
  - `GET /api/admin/catalog/import/batches?status=applied`;
  - `GET /api/admin/catalog/import/batches?status=rolled_back`;
  - сохранение существующих `skip/limit`.
- [x] Зафиксировать контракт тестом:
  - примененная batch;
  - откатанная batch;
  - фильтр по статусу;
  - пагинация `skip=1&limit=1`.
- [x] Подключить UI:
  - select `Все / Примененные / Откатанные`;
  - pagination по истории batch;
  - сброс открытых деталей при смене фильтра или страницы.

Ожидаемый эффект:
- история CSV-импортов остается управляемой при росте числа batch;
- администратор быстрее находит примененные или уже откатанные пачки;
- UI не грузит длинную историю одним запросом.

Риски:
- фильтры пока минимальные; позже могут понадобиться поиск по файлу, дате и автору.

Критерии готовности:
- API корректно считает `total` после фильтра;
- UI сохраняет корректную страницу и статус;
- build и regression tests проходят.

### Проверки P49

- `pytest tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py -q` (dockerized) — `17 passed`.
- `ruff check app/models/catalog_import.py app/services/catalog_import.py app/routers/admin.py tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py` (dockerized) — green.
- `npm run test:unit` — `10 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P50 — Portable species audio assets

- [x] Перевести аудио карточек с внешних URL на переносимые локальные assets:
  - `backend/media/species-audio/*`;
  - seed пишет `/api/media/species-audio/<file>`;
  - `SOURCES.md` фиксирует источник, автора и лицензию.
- [x] Добавить публичную раздачу аудио через backend:
  - `GET /api/media/species-audio/{filename}`;
  - content-type для `ogg`, `oga`, `mp3`, `wav`;
  - fallback MinIO/local disk сохраняет общий подход `/api/media`.
- [x] Защитить переносимость тестами:
  - все `AUDIO_UPDATES` используют локальный `/api/media/species-audio/`;
  - каждый локальный файл существует в репозитории;
  - route отдаёт audio response с диска.
- [x] Актуализировать live DB:
  - `50` видов со звуками;
  - `0` внешних `audio_url`;
  - `49` уникальных файлов, один файл используется для двух вариантов названия стрижа.

Ожидаемый эффект:
- запуск с другого компьютера после `git pull` получает тот же набор голосов видов без ручной загрузки внешних файлов;
- карточки открываются стабильнее в демо/туннеле, потому что аудио не зависит от Wikimedia/Xeno-canto latency;
- права и атрибуция не теряются при переносе.

Риски:
- аудио добавляет около `38 MB` к репозиторию;
- часть файлов имеет лицензии Xeno-canto `NonCommercial`/`NoDerivs`, их нужно учитывать при публичном коммерческом использовании;
- при будущей замене записей нужно синхронизировать `LOCAL_AUDIO_FILES`, `AUDIO_UPDATES` и `SOURCES.md`.

Критерии готовности:
- локальные аудиофайлы лежат в Git;
- seed не пишет внешние `http` audio URL;
- live DB и новый dev seed ведут себя одинаково.

### Проверки P50

- `pytest tests/test_species_content_review.py tests/test_media_access.py tests/test_species.py -q` (dockerized) — `18 passed`.
- `ruff check app/routers/media_serve.py app/seed/content_review_20260417.py tests/test_species_content_review.py tests/test_media_access.py tests/test_species.py` (dockerized) — green.
- `python -m app.seed.content_review_20260417` (dockerized live DB) — applied, `updated: 54`.
- SQL check live DB: `local_audio=50`, `external_audio=0`, `total_audio=50`.
- Runtime media check: `GET /api/media/species-audio/parus-major.ogg` — `200 audio/ogg`; `GET /api/media/species-audio/vulpes-vulpes.ogg` — `200 audio/ogg`.

## P51 — Homepage community spotlight

- [x] Расширить `/api/dashboard/summary` community-блоком:
  - `active_observers`;
  - `leaderboard_period`;
  - top-3 `leaders` по сумме баллов.
- [x] Покрыть backend-контракт тестом:
  - summary возвращает лидеров в правильном порядке;
  - `active_observers` считается по авторам наблюдений;
  - существующие stats/fact/challenge не ломаются.
- [x] Добавить на главную блок `Друиды компании`:
  - краткий текст о сообществе;
  - топ-3 участников;
  - ссылка на полный рейтинг в профиле.

Ожидаемый эффект:
- главная становится живее и лучше поддерживает возвращаемость;
- пользователи видят социальное подтверждение и понятную мотивацию добавлять наблюдения;
- для демо появляется быстрый рассказ про вовлечение сотрудников.

Риски:
- пока рейтинг общий за всё время; позже может понадобиться переключатель месяц/квартал;
- при пустой геймификации блок будет скрыт или покажет пустое состояние.

Критерии готовности:
- community payload возвращается вместе с dashboard summary;
- frontend build проходит;
- блок не требует отдельного запроса к leaderboard.

### Проверки P51

- `pytest tests/test_dashboard_summary.py tests/test_species_content_review.py tests/test_media_access.py tests/test_species.py -q` (dockerized) — `19 passed`.
- `ruff check app/routers/dashboard.py app/routers/media_serve.py app/seed/content_review_20260417.py tests/test_dashboard_summary.py tests/test_species_content_review.py tests/test_media_access.py tests/test_species.py` (dockerized) — green.
- `npm run test:unit` — `10 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P52 — Species audio discoverability

- [x] Прокинуть `audio_url` в `recent_species` внутри `/api/dashboard/summary`.
- [x] Добавить визуальный маркер `Есть голос`:
  - в карточках списка видов;
  - в карточках новых видов на главной.
- [x] Покрыть backend-контракт тестом:
  - `recent_species` возвращает локальный `audio_url`;
  - существующие dashboard stats/community/fact/challenge не ломаются.

Ожидаемый эффект:
- пользователю проще найти виды с голосами без захода в каждую карточку;
- ценность аудио становится видимой уже на главной и в каталоге;
- новый локальный аудио-пайплайн получает понятную точку входа в интерфейсе.

Риски:
- бейдж пока бинарный: не показывает источник, лицензию или тип звука;
- при большом числе тегов на маленьких карточках может понадобиться компактный icon-only вариант.

Критерии готовности:
- `audio_url` присутствует в dashboard summary для новых видов;
- список видов и главная показывают бейдж для видов со звуком;
- frontend build и backend regression проходят.

### Проверки P52

- `pytest tests/test_dashboard_summary.py tests/test_species_content_review.py tests/test_media_access.py tests/test_species.py -q` (dockerized) — `19 passed`.
- `ruff check app/routers/dashboard.py app/routers/media_serve.py app/seed/content_review_20260417.py tests/test_dashboard_summary.py tests/test_species_content_review.py tests/test_media_access.py tests/test_species.py` (dockerized) — green.
- `npm run test:unit` — `10 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P53 — Species audio catalog filter

- [x] Добавить API-фильтр каталога:
  - `GET /api/species?has_audio=true`;
  - `has_audio=false` возвращает виды без аудио;
  - cache key списка учитывает audio-фильтр.
- [x] Подключить фильтр в UI справочника:
  - checkbox `С голосом`;
  - запрос каталога передаёт `has_audio=true`;
  - frontend cache key не смешивает обычный список и список со звуками.
- [x] Зафиксировать поведение backend-тестом:
  - тест сначала падал на старом API, потому что query param игнорировался;
  - после реализации возвращается только вид с локальным `audio_url`.

Ожидаемый эффект:
- аудиоконтент становится не только украшением карточек, но и навигационным сценарием;
- на демо можно быстро показать все виды, у которых уже есть голоса;
- пользователю проще изучать птиц, млекопитающих и других животных через звук.

Риски:
- фильтр пока простой бинарный; позже можно добавить отдельные фильтры по группе звуков, лицензии или качеству записи;
- при дальнейшей пагинации UI надо будет сохранить `has_audio` в URL.

Критерии готовности:
- API возвращает только виды с заполненным `audio_url`;
- каталог фильтруется без перезагрузки страницы;
- regression tests и frontend build проходят.

### Проверки P53

- `pytest tests/test_species.py tests/test_dashboard_summary.py tests/test_species_content_review.py tests/test_media_access.py -q` (dockerized) — `20 passed`.
- `ruff check app/routers/species.py app/routers/dashboard.py app/routers/media_serve.py app/seed/content_review_20260417.py tests/test_species.py tests/test_dashboard_summary.py tests/test_species_content_review.py tests/test_media_access.py` (dockerized) — green.
- `npm run test:unit` — `10 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.
- Runtime check: `GET /api/species?has_audio=true&limit=3` — `total=50`, первые элементы имеют локальные `/api/media/species-audio/*` URL.

## P54 — Field-guide sections on species detail

- [x] Добавить frontend-helper `buildSpeciesEditorialSections`:
  - собирает блоки из `biotopes`, `season_info`, `do_dont_rules`;
  - чистит пробелы;
  - скрывает пустые значения.
- [x] Покрыть helper unit-тестом по TDD:
  - сначала тест падал на отсутствующем helper;
  - после реализации проверяет порядок и фильтрацию пустых секций.
- [x] Подключить редакционные блоки в карточку вида:
  - `Где искать`;
  - `Когда наблюдать`;
  - `Как действовать`.

Ожидаемый эффект:
- карточка вида становится ближе к полевой памятке, а не только справочной анкете;
- уже имеющиеся данные `biotopes`, `season_info`, `do_dont_rules` становятся видимыми пользователю;
- следующие редакционные улучшения можно добавлять через один helper, не раздувая Vue-шаблон условиями.

Риски:
- качество текста зависит от заполненности текущих полей каталога;
- часть видов покажет только один-два блока, пока экспертная ревизия не завершена.

Критерии готовности:
- пустые поля не создают пустых UI-блоков;
- карточка вида показывает доступные полевые подсказки;
- frontend unit tests и build проходят.

### Проверки P54

- `vitest run src/utils/speciesEditorialSections.test.ts` — `2 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P55 — Editorial fields in expert CSV workflow

- [x] Расширить CSV export/import справочника редакционными полями:
  - `season_info`;
  - `biotopes`;
  - `description`;
  - `do_dont_rules`.
- [x] Сохранить безопасный контур preview/apply/rollback:
  - preview показывает изменения по новым полям;
  - apply обновляет только измененные значения;
  - batch history хранит `before/after` для отката.
- [x] Обновить человекочитаемые labels в admin UI:
  - `Сезонность`;
  - `Местообитания`;
  - `Описание`;
  - `Памятка`.

Ожидаемый эффект:
- экспертная доработка карточек теперь покрывает не только таксономию и медиа, но и полезные полевые подсказки;
- можно массово наполнить блоки P54 через CSV без ручного SQL;
- экспорт становится рабочим листом для редакционной рецензии.

Риски:
- длинные описания в CSV неудобны для Excel, но безопаснее текущего ручного редактирования;
- текстовые поля требуют экспертной вычитки, автоматическая валидация проверяет только длину и пустые значения.

Критерии готовности:
- export содержит новые колонки;
- import preview видит изменения в редакционных полях;
- frontend labels показывают понятные названия;
- regression tests и build проходят.

### Проверки P55

- `pytest tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py -q` (dockerized) — `18 passed`.
- `ruff check app/services/catalog_import.py app/routers/admin.py tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py` (dockerized) — green.
- `npm run test:unit` — `12 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P56 — Manual species editing in admin UI

- [x] Добавить frontend-helper для формы редактирования:
  - сбор формы из строки вида;
  - нормализация пустых текстов в `null`;
  - разбор списка фото из textarea по строкам или `;`.
- [x] Подключить ручное редактирование в admin UI:
  - кнопка `Править` в таблице видов;
  - диалог с базовыми, редакционными, фото- и аудио-полями;
  - сохранение через `PUT /api/species/{id}`;
  - инвалидация кешей каталога, admin quality, ops и audit.
- [x] Зафиксировать backend regression:
  - `PUT` принимает редакционные поля;
  - audit event `species.update` содержит список изменённых полей.

Ожидаемый эффект:
- мелкие правки карточек можно делать сразу в админке, без CSV-цикла;
- редакционная доработка становится быстрее при точечных исправлениях;
- CSV остаётся инструментом массовых правок, а UI закрывает ежедневную работу.

Риски:
- форма пока без rich-text и без отдельного предпросмотра карточки;
- длинные описания удобнее готовить вне админки и вставлять готовым текстом.

Критерии готовности:
- админ может открыть вид, изменить поля и сохранить;
- список и quality summary обновляются после сохранения;
- frontend helper и backend PUT покрыты тестами;
- build проходит.

### Проверки P56

- `vitest run src/utils/speciesAdminForm.test.ts` — `3 passed`.
- `pytest tests/test_species.py::test_update_species_accepts_editorial_fields -q` (dockerized) — `1 passed`.
- `ruff check tests/test_species.py` (dockerized) — green.
- `pytest tests/test_species.py tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py -q` (dockerized) — `33 passed`.
- `ruff check app/routers/species.py app/routers/admin.py app/services/catalog_import.py tests/test_species.py tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py` (dockerized) — green.
- `npm run test:unit` — `15 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P57 — Full species creation form in admin UI

- [x] Расширить форму добавления вида до полноценной карточки:
  - базовые поля;
  - охранный статус;
  - сезонность;
  - местообитания;
  - описание;
  - памятка;
  - фото;
  - аудио metadata.
- [x] Переиспользовать общий frontend-helper формы:
  - `buildEmptySpeciesForm`;
  - `buildSpeciesUpdatePayload`;
  - одинаковая нормализация create/edit payload.
- [x] Зафиксировать backend regression:
  - `POST /api/species` принимает полную карточку;
  - ответ возвращает редакционные, фото- и аудио-поля.

Ожидаемый эффект:
- новый вид можно завести сразу как готовую карточку, без отдельного CSV или последующего редактирования;
- add/edit формы ведут себя одинаково;
- снижается риск неполных записей при ручном пополнении каталога.

Риски:
- форма стала длиннее; позже стоит разбить её на вкладки `Основное / Контент / Медиа`;
- проверки URL остаются backend-валидацией, frontend пока только нормализует ввод.

Критерии готовности:
- форма добавления содержит те же рабочие поля, что и форма редактирования;
- после успешного создания форма сбрасывается;
- backend и frontend regression проходят.

### Проверки P57

- `vitest run src/utils/speciesAdminForm.test.ts` — `4 passed`.
- `pytest tests/test_species.py::test_create_species_accepts_full_editorial_card -q` (dockerized) — `1 passed`.
- `pytest tests/test_species.py tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py -q` (dockerized) — `34 passed`.
- `ruff check app/routers/species.py app/routers/admin.py app/services/catalog_import.py tests/test_species.py tests/test_admin_catalog_import.py tests/test_admin_ops_summary.py` (dockerized) — green.
- `npm run test:unit` — `16 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P58 — Species admin form tabs

- [x] Разбить длинные add/edit диалоги вида на вкладки:
  - `Основное`;
  - `Контент`;
  - `Медиа`.
- [x] Вынести конфигурацию вкладок в общий frontend-helper:
  - add/edit используют один набор вкладок;
  - тест фиксирует порядок и подписи.
- [x] Улучшить состояние формы:
  - при открытии add/edit активируется вкладка `Основное`;
  - при успешном создании форма сбрасывается вместе с активной вкладкой.

Ожидаемый эффект:
- админка становится менее перегруженной визуально;
- ручное создание и редактирование видов проще объяснить пользователю;
- будущие поля можно добавлять в понятные группы, не удлиняя один общий список.

Риски:
- форма стала зависеть от Element Plus tabs, но сборка уже подтверждает автоподключение компонента;
- пока нет отдельного предпросмотра карточки перед сохранением.

Критерии готовности:
- обе формы используют одинаковые вкладки;
- вкладка сбрасывается при открытии формы;
- unit tests и frontend build проходят.

### Проверки P58

- `vitest run src/utils/speciesAdminForm.test.ts` — `5 passed`.
- `npm run test:unit` — `17 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P59 — Species admin card preview

- [x] Добавить frontend-helper предпросмотра:
  - нормализует текущие значения формы;
  - выбирает первое фото из textarea;
  - показывает наличие аудио и название записи.
- [x] Подключить preview в add/edit диалогах:
  - фото или иконка группы;
  - русское и латинское название;
  - группа, категория, статус, аудио, ядовитость;
  - описание и полевые подсказки.
- [x] Покрыть helper unit-тестом:
  - проверка trimming;
  - проверка первого фото;
  - проверка audio badge data.

Ожидаемый эффект:
- администратор видит будущую карточку до сохранения;
- снижается риск некрасивых длинных строк, пустых названий и ошибочных media URL;
- add/edit формы становятся ближе к редакторскому интерфейсу, а не к сырой БД-форме.

Риски:
- предпросмотр компактный и не является pixel-perfect копией публичной карточки;
- аудио пока отображается как метка, без встроенного плеера в preview.

Критерии готовности:
- preview обновляется по текущим значениям формы;
- add/edit показывают один и тот же формат preview;
- unit tests и frontend build проходят.

### Проверки P59

- `vitest run src/utils/speciesAdminForm.test.ts` — `6 passed`.
- `npm run test:unit` — `18 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P60 — Admin species list filters

- [x] Добавить helper для query-параметров admin-списка:
  - `search`;
  - `group`;
  - `category`;
  - `has_audio`;
  - стабильный cache key.
- [x] Подключить фильтры над таблицей видов:
  - поиск по русскому/латинскому названию;
  - группа;
  - категория;
  - `С голосом`;
  - сброс фильтров.
- [x] Показать счётчик:
  - найдено всего;
  - если результатов больше лимита, сколько показано.

Ожидаемый эффект:
- администратор быстро находит нужный вид для ручной правки;
- таблица перестаёт быть “первые 200 записей” без навигации;
- аудиоконтент можно быстро проверить и редактировать из админки.

Риски:
- пока нет полноценной пагинации списка видов в admin UI; при `total > 200` показывается ограничение;
- поиск с одним символом намеренно не отправляется, потому что backend требует минимум 2 символа.

Критерии готовности:
- UI-фильтры используют существующий `/api/species`;
- cache key учитывает все фильтры;
- unit tests и frontend build проходят.

### Проверки P60

- `vitest run src/utils/speciesAdminForm.test.ts` — `8 passed`.
- `npm run test:unit` — `20 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P61 — Admin species list pagination

- [x] Добавить pagination-параметры в helper admin-списка видов:
  - `page`;
  - `pageSize`;
  - вычисление `skip`;
  - cache key учитывает страницу и размер страницы.
- [x] Подключить пагинацию в admin UI:
  - список видов грузится страницами по `50` записей;
  - фильтры и поиск сбрасывают страницу на первую;
  - переключение страниц переиспользует cache/dedupe слой `/api/species`.
- [x] Убрать ограничение “показаны первые 200” из рабочего сценария:
  - счетчик показывает общее число найденных записей;
  - при нескольких страницах отображается текущая страница.

Ожидаемый эффект:
- администратор может дойти до любой записи каталога без изменения фильтров;
- таблица не грузит весь справочник одним запросом при росте каталога;
- фильтры, поиск и аудио-проверка остаются совместимыми с server-side pagination.

Риски:
- пока страница не отражается в URL, поэтому при reload админка возвращается на первую страницу;
- при удалении последней записи на странице может потребоваться ручной переход назад, если каталог сильно сократился.

Критерии готовности:
- helper строит корректные `skip/limit`;
- UI сбрасывает страницу при изменении фильтров;
- unit tests и frontend build проходят.

### Проверки P61

- `vitest run src/utils/speciesAdminForm.test.ts` — `9 passed`.
- `npm run test:unit` — `25 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P62 — Admin species URL state

- [x] Добавить helper-контракт для URL-состояния admin-списка:
  - сбор чистого query из `search/group/category/has_audio/page`;
  - сохранение чужих query-параметров;
  - очистка пустых и невалидных значений.
- [x] Добавить восстановление состояния из URL:
  - `species_search`;
  - `species_group`;
  - `species_category`;
  - `species_has_audio`;
  - `species_page`.
- [x] Подключить sync в admin UI:
  - фильтры и поиск пишут состояние в URL;
  - смена страницы пишет `species_page`;
  - refresh или открытие ссылки восстанавливает фильтры и страницу;
  - browser back/forward применяет URL-состояние к таблице.

Ожидаемый эффект:
- администратор может отправить ссылку на конкретный отфильтрованный список;
- refresh больше не сбрасывает рабочую позицию в каталоге;
- контентная ревизия становится удобнее при длинных списках видов.

Риски:
- URL хранит только состояние списка видов, а не открытый edit-dialog;
- query-параметры админки могут со временем потребовать namespace-дисциплины для других вкладок.

Критерии готовности:
- URL helper покрыт unit-тестами;
- AdminView восстанавливает состояние до первого запроса списка;
- frontend unit tests и build проходят.

### Проверки P62

- `vitest run src/utils/speciesAdminForm.test.ts` — `12 passed`.
- `npm run test:unit` — `28 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P63 — Admin species page self-healing

- [x] Добавить helper для нормализации текущей страницы после изменения `total`:
  - текущая страница не может быть меньше `1`;
  - текущая страница не может быть больше последней доступной;
  - пустой результат возвращает страницу `1`.
- [x] Подключить self-healing в загрузку admin-списка:
  - если после удаления/фильтрации текущая страница стала недоступной, UI обновляет URL;
  - затем выполняет один повторный запрос на последнюю существующую страницу.
- [x] Сохранить совместимость с URL-state P62:
  - слишком большая `species_page` в ссылке больше не оставляет таблицу пустой;
  - после коррекции URL показывает фактическую страницу.

Ожидаемый эффект:
- администратор не попадает в пустую таблицу после удаления последнего вида на странице;
- ссылки с устаревшим номером страницы мягко корректируются;
- постраничная работа с каталогом становится устойчивее к изменениям данных.

Риски:
- correction делает один дополнительный запрос в редком случае недоступной страницы;
- если несколько администраторов одновременно массово меняют каталог, страница может корректироваться чаще.

Критерии готовности:
- helper покрыт unit-тестом;
- AdminView корректирует страницу и URL до повторной загрузки;
- frontend unit tests и build проходят.

### Проверки P63

- `vitest run src/utils/speciesAdminForm.test.ts` — `13 passed`.
- `npm run test:unit` — `29 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P64 — Admin species quality badges

- [x] Добавить frontend-helper быстрых quality-сигналов для строки вида:
  - `нет фото`;
  - `нет описания`;
  - `нет аудио`.
- [x] Покрыть helper unit-тестами:
  - неполная карточка возвращает три бейджа;
  - заполненная карточка не показывает предупреждений.
- [x] Вывести бейджи в admin species table:
  - отдельная колонка `Пробелы`;
  - warning/info tags для недостающих материалов;
  - короткое состояние `заполнено`, когда быстрых пробелов нет.

Ожидаемый эффект:
- администратор видит контентные пробелы без открытия каждой карточки;
- ускоряется ручная доводка каталога после импорта/экспертной ревизии;
- аудио/фото/описания становятся операционными критериями качества, а не скрытыми полями.

Риски:
- бейджи проверяют только быстрые бинарные признаки, не качество текста или лицензии медиа;
- при дальнейшем расширении критериев нужно не перегрузить таблицу.

Критерии готовности:
- quality helper покрыт unit-тестами;
- таблица видов показывает бейджи для текущей страницы;
- frontend unit tests и build проходят.

### Проверки P64

- `vitest run src/utils/speciesAdminForm.test.ts` — `15 passed`.
- `npm run test:unit` — `31 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P65 — Admin species quality-gap filters

- [x] Добавить backend-фильтр `quality_gap` в `/api/species`:
  - `missing_photo`;
  - `missing_description`;
  - `missing_audio`.
- [x] Учесть фильтр в species list cache key:
  - локальный TTL cache;
  - Redis-backed cache.
- [x] Покрыть backend-контракт тестами:
  - каждый тип пробела возвращает только подходящие виды;
  - неизвестное значение отклоняется FastAPI/Pydantic-валидацией.
- [x] Расширить admin species URL/helper state:
  - query-параметр `species_quality_gap`;
  - восстановление состояния после refresh/back/forward;
  - очистка невалидных значений.
- [x] Подключить UI-фильтр `Пробел` в admin species table:
  - `Без фото`;
  - `Без описания`;
  - `Без аудио`;
  - конфликт `Без аудио` + `С голосом` автоматически нормализуется.

Ожидаемый эффект:
- администратор получает рабочие очереди на доведение контента без ручного просмотра всех страниц;
- можно быстро отфильтровать виды без фото, описаний или голосов и закрывать пробелы партиями;
- URL-ссылки на конкретные очереди качества можно передавать между участниками ревизии.

Риски:
- `missing_description` проверяет только пустоту текста, а не полноту/качество описания;
- `missing_photo` считает массив фото как бинарный признак и не валидирует доступность URL;
- при добавлении новых quality-критериев нужно следить, чтобы панель фильтров не стала перегруженной.

Критерии готовности:
- `/api/species` принимает `quality_gap` и корректно валидирует значения;
- cache key различает одинаковые списки с разными quality-gap фильтрами;
- admin UI сохраняет фильтр в URL и не допускает противоречивые audio-фильтры;
- backend/frontend проверки и frontend build проходят.

### Проверки P65

- `docker compose exec -T backend pytest tests/test_species.py -q` — `18 passed`.
- `docker compose exec -T backend ruff check app/routers/species.py tests/test_species.py` — green.
- `vitest run src/utils/speciesAdminForm.test.ts` — `16 passed`.
- `npm run test:unit` — `32 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P66 — Admin content-gap counters

- [x] Расширить catalog quality snapshot счетчиками контентных пробелов:
  - `missing_photo`;
  - `missing_description`;
  - `missing_audio`.
- [x] Переиспользовать эти счетчики в:
  - `GET /api/admin/catalog/quality`;
  - `GET /api/admin/ops/summary`.
- [x] Добавить frontend-helper для стабильного списка quality-gap счетчиков.
- [x] Вывести кликабельные очереди качества в admin-блоке каталога:
  - счетчик `без фото`;
  - счетчик `без описания`;
  - счетчик `без аудио`;
  - клик включает соответствующий фильтр `Пробел` в таблице видов;
  - повторный клик снимает активный фильтр.

Ожидаемый эффект:
- администратор сразу видит объем контентного долга по фото, описаниям и аудио;
- переход от сводки к рабочей очереди занимает один клик;
- quality-gap фильтры P65 получают понятный entry point в интерфейсе.

Риски:
- счетчики остаются бинарными и не проверяют качество текста, лицензию или доступность URL;
- при очень большом каталоге snapshot пока считает показатели синхронно вместе с quality-блоком.

Критерии готовности:
- backend snapshot возвращает `content_gap_counts` во всех catalog quality payload;
- UI-счетчики синхронизируются с фильтром таблицы видов;
- backend/frontend проверки и frontend build проходят.

### Проверки P66

- `docker compose exec -T backend pytest tests/test_admin_ops_summary.py::test_admin_catalog_quality_returns_review_candidates tests/test_admin_ops_summary.py::test_admin_ops_summary_returns_expected_sections -q` — `2 passed`.
- `docker compose exec -T backend pytest tests/test_admin_ops_summary.py tests/test_species.py -q` — `26 passed`.
- `docker compose exec -T backend ruff check app/services/catalog_quality.py tests/test_admin_ops_summary.py` — green.
- `vitest run src/utils/speciesAdminForm.test.ts` — `17 passed`.
- `npm run test:unit` — `33 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P67 — Quality-gap CSV exports

- [x] Расширить `GET /api/admin/catalog/export` параметром `quality_gap`:
  - `missing_photo`;
  - `missing_description`;
  - `missing_audio`;
  - неизвестные значения отклоняются FastAPI/Pydantic-валидацией.
- [x] Сохранить совместимость с текущим `needs_review` export:
  - без `quality_gap` поведение прежнее;
  - при совместном использовании фильтры применяются как пересечение.
- [x] Добавить стабильные имена файлов:
  - `species-catalog-missing-photo.csv`;
  - `species-catalog-missing-description.csv`;
  - `species-catalog-missing-audio.csv`;
  - при пересечении с `needs_review` имя дополняется `needs-review`.
- [x] Подключить кнопку `CSV очереди` в admin quality-блоке:
  - активна только при выбранном фильтре `Пробел`;
  - выгружает текущую quality-gap очередь для ручной доработки.

Ожидаемый эффект:
- очереди “без фото/описания/аудио” можно отдавать на заполнение отдельными CSV-файлами;
- контентная ревизия становится переносимой между машинами и участниками команды;
- администратор получает быстрый путь от счетчика пробелов к файлу для массовой работы.

Риски:
- CSV не проверяет доступность внешних ссылок и качество текста, только выгружает текущий срез;
- если пользователь поменял фильтр таблицы, но не выбрал `Пробел`, кнопка очереди остается недоступной.

Критерии готовности:
- backend export фильтрует строки по выбранному content gap;
- invalid `quality_gap` возвращает `422`;
- admin UI формирует корректный запрос и имя файла для активной очереди;
- backend/frontend проверки и frontend build проходят.

### Проверки P67

- `docker compose exec -T backend pytest tests/test_admin_ops_summary.py::test_admin_catalog_export_returns_quality_gap_csv tests/test_admin_ops_summary.py::test_admin_catalog_export_rejects_unknown_quality_gap -q` — `2 passed`.
- `docker compose exec -T backend ruff check app/routers/admin.py tests/test_admin_ops_summary.py` — green.
- `vitest run src/utils/speciesAdminForm.test.ts` — `18 passed`.
- `docker compose exec -T backend pytest tests/test_admin_ops_summary.py tests/test_species.py -q` — `28 passed`.
- `docker compose exec -T backend ruff check app/routers/admin.py app/routers/species.py app/services/catalog_quality.py tests/test_admin_ops_summary.py tests/test_species.py` — green.
- `npm run test:unit` — `34 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.

## P68 — Short-description quality queue

- [x] Добавить новый quality-gap `short_description`:
  - описание есть;
  - после trim короче `120` символов;
  - пустые описания остаются в отдельной очереди `missing_description`.
- [x] Расширить `/api/species`:
  - server-side filter `quality_gap=short_description`;
  - cache key продолжает учитывать выбранный quality-gap.
- [x] Расширить catalog quality snapshot:
  - `content_gap_counts.short_description`;
  - показатель доступен в `/api/admin/catalog/quality` и `/api/admin/ops/summary`.
- [x] Расширить CSV export очередей:
  - `quality_gap=short_description`;
  - файл `species-catalog-short-description.csv`.
- [x] Подключить новый сигнал в admin UI:
  - option `Короткое описание` в фильтре `Пробел`;
  - счетчик в quality-блоке;
  - бейдж `короткое описание` в таблице видов.

Ожидаемый эффект:
- редактор видит не только пустые карточки, но и “тонкие” описания, которые формально заполнены;
- можно отдельно выгружать очередь на текстовую доработку;
- качество карточек растет без ручного просмотра всех видов.

Риски:
- порог `120` символов эвристический и может потребовать настройки после редакторской пробы;
- короткое описание не всегда плохое для очевидных видов, поэтому это warning, а не blocker.

Критерии готовности:
- backend фильтрует short-description очередь отдельно от missing-description;
- quality counters и CSV export поддерживают новый gap;
- admin UI показывает новый фильтр, счетчик и бейдж;
- backend/frontend проверки и frontend build проходят.

### Проверки P68

- `docker compose exec -T backend pytest tests/test_species.py::test_list_species_with_quality_gap_filters tests/test_admin_ops_summary.py::test_admin_catalog_quality_returns_review_candidates tests/test_admin_ops_summary.py::test_admin_catalog_export_returns_quality_gap_csv tests/test_admin_ops_summary.py::test_admin_ops_summary_returns_expected_sections -q` — `4 passed`.
- `docker compose exec -T backend ruff check app/routers/admin.py app/routers/species.py app/services/catalog_quality.py tests/test_admin_ops_summary.py tests/test_species.py` — green.
- `vitest run src/utils/speciesAdminForm.test.ts` — `19 passed`.
- `docker compose exec -T backend pytest tests/test_admin_ops_summary.py tests/test_species.py -q` — `28 passed`.
- `npm run test:unit` — `35 passed`.
- `npm run build` — ok; прежнее предупреждение Vite про `/api/media/species-pdf/page23_img07.png` остаётся runtime-resolved.
