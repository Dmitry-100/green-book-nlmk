#!/usr/bin/env bash
set -euo pipefail

COUNT="${1:-100000}"
MODE="seed"
if [[ "${1:-}" == "--cleanup" ]]; then
  MODE="cleanup"
fi

if [[ "$MODE" == "cleanup" ]]; then
  docker compose exec db psql -U greenbook -d greenbook -c \
    "DELETE FROM observations WHERE comment = '[perf-bench]'; ANALYZE observations;"
  echo "Removed synthetic benchmark observations."
  exit 0
fi

if ! [[ "$COUNT" =~ ^[0-9]+$ ]]; then
  echo "Usage: ./scripts/perf_seed_observations.sh [count]"
  echo "   or: ./scripts/perf_seed_observations.sh --cleanup"
  exit 1
fi

docker compose exec db psql -U greenbook -d greenbook -c "
DELETE FROM observations WHERE comment = '[perf-bench]';
WITH users_pool AS (
  SELECT array_agg(id) AS ids FROM users
), species_pool AS (
  SELECT array_agg(id) AS ids, array_agg(\"group\"::text) AS groups FROM species
)
INSERT INTO observations (
  author_id,
  species_id,
  \"group\",
  observed_at,
  location_point,
  status,
  comment,
  is_incident,
  sensitive_level,
  safety_checked
)
SELECT
  u.ids[1 + ((g - 1) % array_length(u.ids, 1))],
  s.ids[1 + ((g - 1) % array_length(s.ids, 1))],
  s.groups[1 + ((g - 1) % array_length(s.ids, 1))],
  now() - (((random() * 365 * 24 * 60)::int)::text || ' minutes')::interval,
  ST_SetSRID(ST_MakePoint(39.50 + random() * 0.25, 52.50 + random() * 0.20), 4326),
  CASE
    WHEN random() < 0.90 THEN 'confirmed'::observationstatus
    WHEN random() < 0.95 THEN 'on_review'::observationstatus
    ELSE 'needs_data'::observationstatus
  END,
  '[perf-bench]',
  FALSE,
  CASE
    WHEN random() < 0.03 THEN 'hidden'::sensitivelevel
    WHEN random() < 0.12 THEN 'blurred'::sensitivelevel
    ELSE 'open'::sensitivelevel
  END,
  TRUE
FROM generate_series(1, ${COUNT}) AS g
CROSS JOIN users_pool AS u
CROSS JOIN species_pool AS s;
ANALYZE observations;
"

docker compose exec db psql -U greenbook -d greenbook -c "
SELECT
  count(*) FILTER (WHERE comment = '[perf-bench]') AS bench_rows,
  count(*) FILTER (WHERE comment = '[perf-bench]' AND status = 'confirmed') AS bench_confirmed,
  count(*) FILTER (
    WHERE comment = '[perf-bench]'
      AND status = 'confirmed'
      AND sensitive_level IN ('open', 'blurred')
  ) AS bench_confirmed_visible
FROM observations;
"
