# Observability v2 Runbook

## Быстрые проверки

```bash
# Liveness / readiness
curl -sS http://localhost:8000/api/health
curl -sS http://localhost:8000/api/health/ready
curl -sS http://localhost:8000/api/health/deps

# Runtime metrics (JSON + Prometheus)
curl -sS -H "Authorization: Bearer <admin-token>" http://localhost:8000/api/metrics
curl -sS -H "Authorization: Bearer <admin-token>" http://localhost:8000/api/metrics/prometheus

# Rate-limit friendly perf smoke for local dev
python3 scripts/perf_smoke_ci.py --base-url http://127.0.0.1:8000 --profile local

# Ops snapshot + alerts
curl -sS -H "Authorization: Bearer <admin-token>" http://localhost:8000/api/admin/ops/summary
curl -sS -H "Authorization: Bearer <admin-token>" http://localhost:8000/api/admin/ops/alerts
```

## Что смотреть в первую очередь

1. `api/admin/ops/alerts`:
   - `status=alert` и список `alerts`.
2. `api/admin/ops/summary`:
   - `metrics.error_rate_percent`
   - `metrics.p95_duration_ms`
   - `metrics.p99_duration_ms`
   - `metrics.slow_routes`
   - `pipeline.on_review`
   - `media_pipeline.pending`, `media_pipeline.failed`,
     `media_pipeline.pending_oldest_age_seconds`
   - `cache.totals.degraded_stores`
3. `api/health/ready` и `api/health/deps`:
   - `dependencies` и `dependency_details.*.latency_ms`

## Базовый triage при инциденте

1. Проверить dependency-сигналы:
   - если `database/redis/minio=error`, сначала восстановить зависимость.
2. Проверить нагрузку API:
   - рост `error_rate_percent`, route-level ошибки в `/api/metrics`.
3. Проверить media queue:
   - высокий `pending`/`pending_oldest_age_seconds`/`failed`.
   - при необходимости запустить batch вручную:
     `POST /api/admin/ops/media/process?batch_size=...`
4. Проверить cache-layer:
   - `cache.totals.degraded_stores` и ошибки в Prometheus-метриках cache.
5. После стабилизации:
   - прогнать post-deploy smoke (`scripts/release_smoke.py`).

## Рекомендации для test/staging dashboard

- API SLI:
  - `greenbook_api_requests_total`
  - `greenbook_api_errors_total`
  - `greenbook_api_error_rate_percent`
  - `greenbook_api_duration_ms_average`
  - `greenbook_api_duration_ms_bucket`
  - `greenbook_api_duration_ms_sum`
  - `greenbook_api_duration_ms_count`
- Route hotspots:
  - `greenbook_api_route_requests_total`
  - `greenbook_api_route_errors_total`
  - `greenbook_api_route_duration_ms_average`
  - `greenbook_api_route_duration_ms_bucket`
  - `greenbook_api_route_duration_ms_sum`
  - `greenbook_api_route_duration_ms_count`
- Cache layer:
  - `greenbook_cache_degraded_stores`
  - `greenbook_cache_connect_errors_total`
  - `greenbook_cache_read_errors_total`
  - `greenbook_cache_write_errors_total`
  - `greenbook_cache_fallback_hits_total`

## Perf smoke profiles

- `--profile ci` — полный сценарий для CI/staging. В CI rate limiting отключен,
  поэтому сценарий может делать сотни запросов за короткий интервал.
- `--profile local` — облегченный сценарий для dev-окружения с включенным
  default rate limit. Используйте его для быстрой проверки latency перед ручным
  тестированием.

Оба профиля проверяют `p95` и `p99`; `p99` нужен, чтобы ловить редкие
“длинные хвосты”, которые не всегда видны по среднему времени.

## Health dependency cache

`/api/health/ready` и `/api/health/deps` кешируют результат MinIO-check на
`HEALTH_DEPENDENCY_CACHE_TTL_SECONDS` секунд. Проверка использует
`head_bucket`, а не `list_buckets`, чтобы readiness не зависел от полного
перечисления buckets.
