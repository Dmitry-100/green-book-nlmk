#!/usr/bin/env python3
from __future__ import annotations

import argparse
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    values = sorted(values)
    rank = p * (len(values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(values) - 1)
    weight = rank - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _request_once(base_url: str, path: str, timeout: float) -> tuple[bool, float, int, int]:
    url = f"{base_url.rstrip('/')}{path}"
    start = time.perf_counter()
    status = 0
    size = 0
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = response.read()
            status = response.status
            size = len(payload)
        return 200 <= status < 400, (time.perf_counter() - start) * 1000, status, size
    except urllib.error.HTTPError as exc:
        try:
            payload = exc.read()
        except Exception:
            payload = b""
        status = exc.code or 0
        size = len(payload)
        return False, (time.perf_counter() - start) * 1000, status, size
    except (urllib.error.URLError, TimeoutError):
        return False, (time.perf_counter() - start) * 1000, status, size


def run_profile(
    *,
    base_url: str,
    path: str,
    requests: int,
    concurrency: int,
    warmup: int,
    timeout: float,
) -> None:
    for _ in range(max(0, warmup)):
        _request_once(base_url, path, timeout)

    latencies_ms: list[float] = []
    success = 0
    failures = 0
    bytes_total = 0
    status_counts: dict[int, int] = {}

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_request_once, base_url, path, timeout)
            for _ in range(requests)
        ]
        for future in as_completed(futures):
            ok, latency_ms, status, size = future.result()
            latencies_ms.append(latency_ms)
            bytes_total += size
            status_counts[status] = status_counts.get(status, 0) + 1
            if ok:
                success += 1
            else:
                failures += 1
    elapsed = time.perf_counter() - start

    throughput = success / elapsed if elapsed > 0 else 0.0
    avg_ms = statistics.mean(latencies_ms) if latencies_ms else 0.0
    p50_ms = _percentile(latencies_ms, 0.50)
    p95_ms = _percentile(latencies_ms, 0.95)
    p99_ms = _percentile(latencies_ms, 0.99)
    min_ms = min(latencies_ms) if latencies_ms else 0.0
    max_ms = max(latencies_ms) if latencies_ms else 0.0

    print(f"PATH: {path}")
    print(
        f"  requests={requests} concurrency={concurrency} "
        f"success={success} failures={failures}"
    )
    print(f"  statuses={dict(sorted(status_counts.items()))}")
    print(
        f"  latency_ms avg={avg_ms:.2f} p50={p50_ms:.2f} p95={p95_ms:.2f} "
        f"p99={p99_ms:.2f} min={min_ms:.2f} max={max_ms:.2f}"
    )
    print(
        f"  throughput_rps={throughput:.2f} bytes_total={bytes_total} "
        f"duration_s={elapsed:.2f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simple concurrent API profiling tool for local tuning."
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--path",
        action="append",
        required=True,
        help="Endpoint path (can be repeated), e.g. /api/dashboard/summary",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=200,
        help="Total requests per path (default: 200)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=20,
        help="Concurrent workers per path (default: 20)",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
        help="Warm-up requests per path before measuring (default: 5)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Single request timeout in seconds (default: 5.0)",
    )

    args = parser.parse_args()
    print(f"BASE_URL: {args.base_url}")
    for path in args.path:
        run_profile(
            base_url=args.base_url,
            path=path,
            requests=args.requests,
            concurrency=args.concurrency,
            warmup=args.warmup,
            timeout=args.timeout,
        )


if __name__ == "__main__":
    main()
