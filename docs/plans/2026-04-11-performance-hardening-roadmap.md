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
