#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from urllib import error, request


@dataclass
class CheckResult:
    path: str
    status: int | None
    ok: bool
    message: str


def _http_get(base_url: str, path: str, *, bearer_token: str | None = None) -> tuple[int, bytes]:
    url = f"{base_url.rstrip('/')}{path}"
    req = request.Request(url=url, method="GET")
    if bearer_token:
        req.add_header("Authorization", f"Bearer {bearer_token}")

    try:
        with request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read()
    except error.HTTPError as exc:
        return exc.code, exc.read()
    except Exception as exc:
        raise RuntimeError(f"request failed for {url}: {exc}") from exc


def _check_endpoint(
    base_url: str,
    path: str,
    *,
    expected_statuses: set[int],
    bearer_token: str | None = None,
) -> CheckResult:
    try:
        status, body = _http_get(base_url, path, bearer_token=bearer_token)
    except RuntimeError as exc:
        return CheckResult(path=path, status=None, ok=False, message=str(exc))

    if status not in expected_statuses:
        preview = body.decode("utf-8", errors="replace")[:200]
        return CheckResult(
            path=path,
            status=status,
            ok=False,
            message=f"unexpected status {status}, body={preview}",
        )

    return CheckResult(path=path, status=status, ok=True, message="ok")


def _check_ops_alerts(
    base_url: str,
    *,
    bearer_token: str,
    fail_on_alerts: bool,
) -> CheckResult:
    path = "/api/admin/ops/alerts"
    try:
        status, body = _http_get(base_url, path, bearer_token=bearer_token)
    except RuntimeError as exc:
        return CheckResult(path=path, status=None, ok=False, message=str(exc))

    if status != 200:
        preview = body.decode("utf-8", errors="replace")[:200]
        return CheckResult(
            path=path,
            status=status,
            ok=False,
            message=f"unexpected status {status}, body={preview}",
        )

    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as exc:
        return CheckResult(
            path=path,
            status=status,
            ok=False,
            message=f"invalid json payload: {exc}",
        )

    alert_status = str(payload.get("status", ""))
    alerts = payload.get("alerts") or []
    if alert_status == "alert" and fail_on_alerts:
        return CheckResult(
            path=path,
            status=status,
            ok=False,
            message=f"ops alerts status=alert, active={len(alerts)}",
        )

    if alert_status == "alert":
        return CheckResult(
            path=path,
            status=status,
            ok=True,
            message=f"status=alert, active={len(alerts)} (non-blocking)",
        )

    if alert_status != "ok":
        return CheckResult(
            path=path,
            status=status,
            ok=False,
            message=f"unexpected ops alert status={alert_status!r}",
        )

    return CheckResult(path=path, status=status, ok=True, message="status=ok")


def run_smoke(base_url: str, admin_token: str | None, fail_on_ops_alerts: bool) -> int:
    checks: list[CheckResult] = []

    public_checks = [
        ("/api/health", {200}),
        ("/api/health/ready", {200}),
        ("/api/health/deps", {200}),
        ("/api/species?limit=1&include_total=false", {200}),
        ("/api/map/zones", {200}),
    ]
    for path, expected in public_checks:
        checks.append(_check_endpoint(base_url, path, expected_statuses=expected))

    if admin_token:
        admin_checks = [
            ("/api/metrics", {200}),
            ("/api/metrics/prometheus", {200}),
            ("/api/admin/audit/events?limit=1&include_total=false", {200}),
        ]
        for path, expected in admin_checks:
            checks.append(
                _check_endpoint(
                    base_url,
                    path,
                    expected_statuses=expected,
                    bearer_token=admin_token,
                )
            )
        checks.append(
            _check_ops_alerts(
                base_url,
                bearer_token=admin_token,
                fail_on_alerts=fail_on_ops_alerts,
            )
        )
    else:
        print("Admin token was not provided: admin-only checks were skipped.")
        if fail_on_ops_alerts:
            print("Flag --fail-on-ops-alerts ignored because admin token is missing.")

    failed = [item for item in checks if not item.ok]
    for item in checks:
        status = item.status if item.status is not None else "n/a"
        prefix = "PASS" if item.ok else "FAIL"
        print(f"[{prefix}] {item.path} status={status} {item.message}")

    summary = {
        "base_url": base_url,
        "checks_total": len(checks),
        "checks_failed": len(failed),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-deploy API smoke checks")
    parser.add_argument("--base-url", required=True, help="API base URL, e.g. https://api.example.com")
    parser.add_argument("--admin-token", default="", help="Optional bearer token for admin-only checks")
    parser.add_argument(
        "--fail-on-ops-alerts",
        action="store_true",
        help="Fail when /api/admin/ops/alerts returns status=alert (requires --admin-token)",
    )
    args = parser.parse_args()
    token = args.admin_token.strip() or None
    return run_smoke(args.base_url, token, args.fail_on_ops_alerts)


if __name__ == "__main__":
    sys.exit(main())
