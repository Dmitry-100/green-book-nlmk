#!/usr/bin/env python3
from __future__ import annotations

import argparse
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass


@dataclass(frozen=True)
class PerfCase:
    path: str
    requests: int
    concurrency: int
    warmup: int
    p95_budget_ms: float
    p99_budget_ms: float


CASES: tuple[PerfCase, ...] = (
    PerfCase(
        path="/api/health",
        requests=80,
        concurrency=8,
        warmup=3,
        p95_budget_ms=200.0,
        p99_budget_ms=350.0,
    ),
    PerfCase(
        path="/api/dashboard/summary",
        requests=120,
        concurrency=12,
        warmup=5,
        p95_budget_ms=700.0,
        p99_budget_ms=1100.0,
    ),
    PerfCase(
        path="/api/gamification/stats?include_heatmap=false",
        requests=120,
        concurrency=12,
        warmup=5,
        p95_budget_ms=900.0,
        p99_budget_ms=1400.0,
    ),
    PerfCase(
        path="/api/map/observations?bbox=39.45,52.48,39.78,52.72&status=confirmed&limit=400",
        requests=120,
        concurrency=12,
        warmup=5,
        p95_budget_ms=1200.0,
        p99_budget_ms=1800.0,
    ),
)


def _case_for_profile(case: PerfCase, profile: str) -> PerfCase:
    if profile == "ci":
        return case
    if profile == "local":
        return PerfCase(
            path=case.path,
            requests=min(case.requests, 20),
            concurrency=min(case.concurrency, 4),
            warmup=min(case.warmup, 2),
            p95_budget_ms=case.p95_budget_ms,
            p99_budget_ms=case.p99_budget_ms,
        )
    raise ValueError(f"Unsupported perf profile: {profile}")


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = p * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def _request_once(base_url: str, path: str, timeout: float) -> tuple[bool, float, int]:
    url = f"{base_url.rstrip('/')}{path}"
    started = time.perf_counter()
    status = 0
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            _ = response.read()
            status = response.status
        ok = 200 <= status < 400
    except urllib.error.HTTPError as exc:
        status = exc.code or 0
        ok = False
    except (urllib.error.URLError, TimeoutError):
        ok = False
    return ok, (time.perf_counter() - started) * 1000, status


def _run_case(base_url: str, case: PerfCase, timeout: float) -> tuple[dict, list[str]]:
    for _ in range(max(0, case.warmup)):
        _request_once(base_url, case.path, timeout)

    latencies: list[float] = []
    success = 0
    failures = 0
    statuses: dict[int, int] = {}
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=case.concurrency) as executor:
        futures = [
            executor.submit(_request_once, base_url, case.path, timeout)
            for _ in range(case.requests)
        ]
        for future in as_completed(futures):
            ok, latency_ms, status = future.result()
            latencies.append(latency_ms)
            statuses[status] = statuses.get(status, 0) + 1
            if ok:
                success += 1
            else:
                failures += 1
    elapsed = time.perf_counter() - started

    avg_ms = statistics.mean(latencies) if latencies else 0.0
    p95_ms = _percentile(latencies, 0.95)
    p99_ms = _percentile(latencies, 0.99)
    max_ms = max(latencies) if latencies else 0.0
    throughput = success / elapsed if elapsed > 0 else 0.0
    report = {
        "path": case.path,
        "requests": case.requests,
        "concurrency": case.concurrency,
        "success": success,
        "failures": failures,
        "statuses": dict(sorted(statuses.items())),
        "avg_ms": avg_ms,
        "p95_ms": p95_ms,
        "p99_ms": p99_ms,
        "max_ms": max_ms,
        "throughput_rps": throughput,
    }

    errors: list[str] = []
    if failures > 0:
        errors.append(f"{case.path}: failures={failures} statuses={report['statuses']}")
    if p95_ms > case.p95_budget_ms:
        errors.append(
            f"{case.path}: p95={p95_ms:.2f}ms exceeds budget {case.p95_budget_ms:.2f}ms"
        )
    if p99_ms > case.p99_budget_ms:
        errors.append(
            f"{case.path}: p99={p99_ms:.2f}ms exceeds budget {case.p99_budget_ms:.2f}ms"
        )

    return report, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CI perf smoke for critical API endpoints."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="API base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=8.0,
        help="Single request timeout in seconds (default: 8.0)",
    )
    parser.add_argument(
        "--profile",
        choices=("ci", "local"),
        default="ci",
        help=(
            "Load profile: ci keeps full thresholds/load, local stays below the "
            "default dev rate limit (default: ci)"
        ),
    )
    args = parser.parse_args()

    print(f"BASE_URL: {args.base_url}")
    print(f"PROFILE: {args.profile}")
    all_errors: list[str] = []
    for case in CASES:
        active_case = _case_for_profile(case, args.profile)
        report, errors = _run_case(args.base_url, active_case, args.timeout)
        print(f"PATH: {report['path']}")
        print(
            f"  requests={report['requests']} concurrency={report['concurrency']} "
            f"success={report['success']} failures={report['failures']}"
        )
        print(f"  statuses={report['statuses']}")
        print(
            f"  latency_ms avg={report['avg_ms']:.2f} p95={report['p95_ms']:.2f} "
            f"p99={report['p99_ms']:.2f} max={report['max_ms']:.2f} "
            f"budgets_p95_p99={active_case.p95_budget_ms:.2f}/{active_case.p99_budget_ms:.2f}"
        )
        print(f"  throughput_rps={report['throughput_rps']:.2f}")
        all_errors.extend(errors)

    if all_errors:
        print("PERF_SMOKE_FAILED:")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print("PERF_SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
