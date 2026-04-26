from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from threading import Lock
from time import monotonic

from app.services.cache import redis_cache_health_snapshot


REQUEST_DURATION_BUCKETS_MS = (5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)


@dataclass
class _LatencyAggregate:
    count: int = 0
    duration_ms_total: float = 0.0
    max_duration_ms: float = 0.0
    bucket_counts: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.bucket_counts:
            self.bucket_counts = [0 for _ in REQUEST_DURATION_BUCKETS_MS]

    def record(self, duration_ms: float) -> None:
        self.count += 1
        self.duration_ms_total += duration_ms
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
        for index, upper_bound in enumerate(REQUEST_DURATION_BUCKETS_MS):
            if duration_ms <= upper_bound:
                self.bucket_counts[index] += 1

    def copy(self) -> "_LatencyAggregate":
        return _LatencyAggregate(
            count=self.count,
            duration_ms_total=self.duration_ms_total,
            max_duration_ms=self.max_duration_ms,
            bucket_counts=list(self.bucket_counts),
        )


@dataclass
class _RouteAggregate:
    errors: int = 0
    latency: _LatencyAggregate = field(default_factory=_LatencyAggregate)

    @property
    def count(self) -> int:
        return self.latency.count

    @property
    def duration_ms_total(self) -> float:
        return self.latency.duration_ms_total

    @property
    def max_duration_ms(self) -> float:
        return self.latency.max_duration_ms


_STARTED_AT = monotonic()
_LOCK = Lock()
_TOTAL_REQUESTS = 0
_TOTAL_ERRORS = 0
_TOTAL_DURATION_MS = 0.0
_STATUS_COUNTS: dict[str, int] = {}
_METHOD_COUNTS: dict[str, int] = {}
_ROUTE_STATS: dict[str, _RouteAggregate] = {}
_GLOBAL_LATENCY = _LatencyAggregate()


def _normalize_route_label(route_path: str | None, fallback_path: str) -> str:
    if route_path:
        return route_path
    return fallback_path or "/unknown"


def _histogram_quantile(quantile: float, latency: _LatencyAggregate) -> float:
    if latency.count == 0:
        return 0.0

    rank = max(1, ceil(latency.count * quantile))
    for upper_bound, cumulative_count in zip(
        REQUEST_DURATION_BUCKETS_MS, latency.bucket_counts, strict=True
    ):
        if cumulative_count >= rank:
            return float(upper_bound)
    return latency.max_duration_ms


def record_request_metric(
    *,
    method: str,
    route_path: str | None,
    fallback_path: str,
    status_code: int,
    duration_ms: float,
) -> None:
    route = _normalize_route_label(route_path, fallback_path)
    if route.startswith("/api/metrics"):
        return

    status_key = str(status_code)
    method_key = method.upper()
    is_error = status_code >= 500

    with _LOCK:
        global _TOTAL_REQUESTS, _TOTAL_ERRORS, _TOTAL_DURATION_MS
        _TOTAL_REQUESTS += 1
        _TOTAL_DURATION_MS += duration_ms
        _GLOBAL_LATENCY.record(duration_ms)
        if is_error:
            _TOTAL_ERRORS += 1

        _STATUS_COUNTS[status_key] = _STATUS_COUNTS.get(status_key, 0) + 1
        _METHOD_COUNTS[method_key] = _METHOD_COUNTS.get(method_key, 0) + 1

        route_entry = _ROUTE_STATS.get(route)
        if route_entry is None:
            route_entry = _RouteAggregate()
            _ROUTE_STATS[route] = route_entry
        route_entry.latency.record(duration_ms)
        if is_error:
            route_entry.errors += 1


def reset_request_metrics() -> None:
    with _LOCK:
        global _TOTAL_REQUESTS, _TOTAL_ERRORS, _TOTAL_DURATION_MS
        _TOTAL_REQUESTS = 0
        _TOTAL_ERRORS = 0
        _TOTAL_DURATION_MS = 0.0
        _STATUS_COUNTS.clear()
        _METHOD_COUNTS.clear()
        _ROUTE_STATS.clear()
        _GLOBAL_LATENCY.count = 0
        _GLOBAL_LATENCY.duration_ms_total = 0.0
        _GLOBAL_LATENCY.max_duration_ms = 0.0
        _GLOBAL_LATENCY.bucket_counts = [0 for _ in REQUEST_DURATION_BUCKETS_MS]


def request_metrics_snapshot() -> dict:
    with _LOCK:
        total_requests = _TOTAL_REQUESTS
        total_errors = _TOTAL_ERRORS
        total_duration_ms = _TOTAL_DURATION_MS
        status_counts = dict(_STATUS_COUNTS)
        method_counts = dict(_METHOD_COUNTS)
        route_items = [
            (route, agg.errors, agg.latency.copy())
            for route, agg in _ROUTE_STATS.items()
        ]
        global_latency = _GLOBAL_LATENCY.copy()

    avg_duration_ms = (
        round(total_duration_ms / total_requests, 2) if total_requests > 0 else 0.0
    )
    error_rate = (
        round((total_errors / total_requests) * 100, 2) if total_requests > 0 else 0.0
    )

    route_items.sort(key=lambda item: item[2].count, reverse=True)
    routes = []
    for route, errors, latency in route_items[:50]:
        routes.append({
            "route": route,
            "requests": latency.count,
            "errors": errors,
            "avg_duration_ms": round(latency.duration_ms_total / latency.count, 2)
            if latency.count > 0
            else 0.0,
            "p95_duration_ms": round(_histogram_quantile(0.95, latency), 2),
            "p99_duration_ms": round(_histogram_quantile(0.99, latency), 2),
            "max_duration_ms": round(latency.max_duration_ms, 2),
        })

    slow_routes = sorted(
        routes,
        key=lambda item: (
            item["p95_duration_ms"],
            item["p99_duration_ms"],
            item["avg_duration_ms"],
        ),
        reverse=True,
    )[:10]

    return {
        "uptime_seconds": int(monotonic() - _STARTED_AT),
        "requests_total": total_requests,
        "errors_total": total_errors,
        "error_rate_percent": error_rate,
        "avg_duration_ms": avg_duration_ms,
        "p95_duration_ms": round(_histogram_quantile(0.95, global_latency), 2),
        "p99_duration_ms": round(_histogram_quantile(0.99, global_latency), 2),
        "max_duration_ms": round(global_latency.max_duration_ms, 2),
        "status_counts": status_counts,
        "method_counts": method_counts,
        "routes": routes,
        "slow_routes": slow_routes,
    }


def _prometheus_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace('"', '\\"')
    )


def request_metrics_prometheus_text() -> str:
    snapshot = request_metrics_snapshot()
    cache_snapshot = redis_cache_health_snapshot()
    with _LOCK:
        global_latency = _GLOBAL_LATENCY.copy()
        route_histograms = [
            (route, agg.latency.copy()) for route, agg in _ROUTE_STATS.items()
        ]

    lines = [
        "# HELP greenbook_api_uptime_seconds Process uptime in seconds.",
        "# TYPE greenbook_api_uptime_seconds gauge",
        f"greenbook_api_uptime_seconds {snapshot['uptime_seconds']}",
        "# HELP greenbook_api_requests_total Total API requests observed.",
        "# TYPE greenbook_api_requests_total counter",
        f"greenbook_api_requests_total {snapshot['requests_total']}",
        "# HELP greenbook_api_errors_total Total API 5xx responses observed.",
        "# TYPE greenbook_api_errors_total counter",
        f"greenbook_api_errors_total {snapshot['errors_total']}",
        "# HELP greenbook_api_error_rate_percent API error rate percentage.",
        "# TYPE greenbook_api_error_rate_percent gauge",
        f"greenbook_api_error_rate_percent {snapshot['error_rate_percent']}",
        "# HELP greenbook_api_duration_ms_average Average request duration (ms).",
        "# TYPE greenbook_api_duration_ms_average gauge",
        f"greenbook_api_duration_ms_average {snapshot['avg_duration_ms']}",
        "# HELP greenbook_api_duration_ms API request duration histogram (ms).",
        "# TYPE greenbook_api_duration_ms histogram",
    ]

    for upper_bound, count in zip(
        REQUEST_DURATION_BUCKETS_MS, global_latency.bucket_counts, strict=True
    ):
        lines.append(f'greenbook_api_duration_ms_bucket{{le="{upper_bound}"}} {count}')
    lines.append(f'greenbook_api_duration_ms_bucket{{le="+Inf"}} {global_latency.count}')
    lines.append(
        f"greenbook_api_duration_ms_sum {round(global_latency.duration_ms_total, 2)}"
    )
    lines.append(f"greenbook_api_duration_ms_count {global_latency.count}")

    lines.extend([
        "# HELP greenbook_api_status_total API responses by HTTP status.",
        "# TYPE greenbook_api_status_total counter",
    ])

    for status_code, count in sorted(snapshot["status_counts"].items()):
        lines.append(
            f'greenbook_api_status_total{{status="{_prometheus_escape(status_code)}"}} {count}'
        )

    lines.extend([
        "# HELP greenbook_api_method_total API requests by HTTP method.",
        "# TYPE greenbook_api_method_total counter",
    ])
    for method, count in sorted(snapshot["method_counts"].items()):
        lines.append(
            f'greenbook_api_method_total{{method="{_prometheus_escape(method)}"}} {count}'
        )

    lines.extend([
        "# HELP greenbook_api_route_requests_total API requests by route label.",
        "# TYPE greenbook_api_route_requests_total counter",
    ])
    for route in snapshot["routes"]:
        route_label = _prometheus_escape(route["route"])
        lines.append(
            f'greenbook_api_route_requests_total{{route="{route_label}"}} '
            f'{route["requests"]}'
        )

    lines.extend([
        "# HELP greenbook_api_route_errors_total API 5xx responses by route label.",
        "# TYPE greenbook_api_route_errors_total counter",
    ])
    for route in snapshot["routes"]:
        route_label = _prometheus_escape(route["route"])
        lines.append(
            f'greenbook_api_route_errors_total{{route="{route_label}"}} '
            f'{route["errors"]}'
        )

    lines.extend([
        "# HELP greenbook_api_route_duration_ms_average Average request duration by route label.",
        "# TYPE greenbook_api_route_duration_ms_average gauge",
    ])
    for route in snapshot["routes"]:
        route_label = _prometheus_escape(route["route"])
        lines.append(
            f'greenbook_api_route_duration_ms_average{{route="{route_label}"}} '
            f'{route["avg_duration_ms"]}'
        )

    lines.extend([
        "# HELP greenbook_api_route_duration_ms API request duration histogram by route label (ms).",
        "# TYPE greenbook_api_route_duration_ms histogram",
    ])
    for route, latency in sorted(route_histograms, key=lambda item: item[0]):
        route_label = _prometheus_escape(route)
        for upper_bound, count in zip(
            REQUEST_DURATION_BUCKETS_MS, latency.bucket_counts, strict=True
        ):
            lines.append(
                f'greenbook_api_route_duration_ms_bucket{{route="{route_label}",'
                f'le="{upper_bound}"}} {count}'
            )
        lines.append(
            f'greenbook_api_route_duration_ms_bucket{{route="{route_label}",'
            f'le="+Inf"}} {latency.count}'
        )
        lines.append(
            f'greenbook_api_route_duration_ms_sum{{route="{route_label}"}} '
            f"{round(latency.duration_ms_total, 2)}"
        )
        lines.append(
            f'greenbook_api_route_duration_ms_count{{route="{route_label}"}} '
            f"{latency.count}"
        )

    totals = cache_snapshot["totals"]
    lines.extend([
        "# HELP greenbook_cache_stores_total Total registered redis-backed caches.",
        "# TYPE greenbook_cache_stores_total gauge",
        f"greenbook_cache_stores_total {totals['stores_total']}",
        "# HELP greenbook_cache_enabled_stores Total enabled redis-backed caches.",
        "# TYPE greenbook_cache_enabled_stores gauge",
        f"greenbook_cache_enabled_stores {totals['enabled_stores']}",
        "# HELP greenbook_cache_degraded_stores Total degraded redis-backed caches.",
        "# TYPE greenbook_cache_degraded_stores gauge",
        f"greenbook_cache_degraded_stores {totals['degraded_stores']}",
        "# HELP greenbook_cache_connect_errors_total Redis connect errors across caches.",
        "# TYPE greenbook_cache_connect_errors_total counter",
        f"greenbook_cache_connect_errors_total {totals['connect_errors_total']}",
        "# HELP greenbook_cache_read_errors_total Redis read errors across caches.",
        "# TYPE greenbook_cache_read_errors_total counter",
        f"greenbook_cache_read_errors_total {totals['read_errors_total']}",
        "# HELP greenbook_cache_write_errors_total Redis write errors across caches.",
        "# TYPE greenbook_cache_write_errors_total counter",
        f"greenbook_cache_write_errors_total {totals['write_errors_total']}",
        "# HELP greenbook_cache_fallback_hits_total Fallback cache hits across caches.",
        "# TYPE greenbook_cache_fallback_hits_total counter",
        f"greenbook_cache_fallback_hits_total {totals['fallback_hits_total']}",
    ])

    lines.extend([
        "# HELP greenbook_cache_store_up Redis availability flag by cache store (1=up, 0=down).",
        "# TYPE greenbook_cache_store_up gauge",
    ])
    for store in cache_snapshot["stores"]:
        labels = (
            f'store="{_prometheus_escape(store["store"])}",'
            f'key_prefix="{_prometheus_escape(store["key_prefix"])}",'
            f'namespace="{_prometheus_escape(store["namespace"])}"'
        )
        connect_attempts = int(store["connect_attempts_total"])
        if not store["enabled"] or connect_attempts == 0:
            up_value = 1
        else:
            up_value = 1 if store["redis_available"] else 0
        lines.append(f"greenbook_cache_store_up{{{labels}}} {up_value}")

    return "\n".join(lines) + "\n"
