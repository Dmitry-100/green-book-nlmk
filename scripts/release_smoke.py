#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib import error, request


@dataclass
class CheckResult:
    path: str
    status: int | None
    ok: bool
    message: str


def _http_request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    bearer_token: str | None = None,
    json_payload: dict | None = None,
) -> tuple[int, bytes]:
    url = f"{base_url.rstrip('/')}{path}"
    body = None
    if json_payload is not None:
        body = json.dumps(json_payload).encode("utf-8")
    req = request.Request(url=url, method=method, data=body)
    if json_payload is not None:
        req.add_header("Content-Type", "application/json")
    if bearer_token:
        req.add_header("Authorization", f"Bearer {bearer_token}")

    try:
        with request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read()
    except error.HTTPError as exc:
        return exc.code, exc.read()
    except Exception as exc:
        raise RuntimeError(f"request failed for {url}: {exc}") from exc


def _http_get(base_url: str, path: str, *, bearer_token: str | None = None) -> tuple[int, bytes]:
    return _http_request(base_url, path, bearer_token=bearer_token)


def _json_request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    bearer_token: str | None = None,
    json_payload: dict | None = None,
) -> tuple[int, dict]:
    status, body = _http_request(
        base_url,
        path,
        method=method,
        bearer_token=bearer_token,
        json_payload=json_payload,
    )
    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
    except Exception as exc:
        raise RuntimeError(f"invalid json from {path}: {exc}") from exc
    return status, payload


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


def _admin_login(
    base_url: str,
    *,
    admin_login: str | None,
    admin_password: str | None,
) -> CheckResult:
    if not admin_login or not admin_password:
        return CheckResult(
            path="/api/auth/login",
            status=None,
            ok=False,
            message="admin login/password were not provided",
        )
    try:
        status, payload = _json_request(
            base_url,
            "/api/auth/login",
            method="POST",
            json_payload={"login": admin_login, "password": admin_password},
        )
    except RuntimeError as exc:
        return CheckResult(path="/api/auth/login", status=None, ok=False, message=str(exc))
    if status != 200 or not payload.get("access_token"):
        return CheckResult(
            path="/api/auth/login",
            status=status,
            ok=False,
            message=f"admin login failed: {payload}",
        )
    return CheckResult(
        path="/api/auth/login",
        status=status,
        ok=True,
        message=payload["access_token"],
    )


def _run_write_workflow(base_url: str, *, admin_token: str) -> list[CheckResult]:
    checks: list[CheckResult] = []
    stamp = int(datetime.now(timezone.utc).timestamp())
    login = f"smoke_{stamp}"
    password = f"Smoke-{stamp}-password"
    display_name = "Smoke Test User"

    try:
        status, payload = _json_request(
            base_url,
            "/api/auth/register",
            method="POST",
            json_payload={
                "login": login,
                "password": password,
                "display_name": display_name,
                "personal_data_notice_accepted": True,
            },
        )
        user_id = payload.get("user", {}).get("id")
    except RuntimeError as exc:
        checks.append(CheckResult("/api/auth/register", None, False, str(exc)))
        return checks
    checks.append(
        CheckResult(
            "/api/auth/register",
            status,
            status == 201 and bool(user_id),
            "registered pending user" if user_id else f"unexpected payload={payload}",
        )
    )
    if not user_id:
        return checks

    for path in (
        f"/api/admin/users/{user_id}/approve",
        f"/api/admin/users/{user_id}/anonymize",
    ):
        if path.endswith("/anonymize"):
            continue
        status, payload = _json_request(
            base_url,
            path,
            method="POST",
            bearer_token=admin_token,
        )
        checks.append(
            CheckResult(
                path,
                status,
                status == 200 and payload.get("approval_status") == "approved",
                "approved smoke user",
            )
        )

    status, payload = _json_request(
        base_url,
        "/api/auth/login",
        method="POST",
        json_payload={"login": login, "password": password},
    )
    user_token = payload.get("access_token")
    checks.append(
        CheckResult(
            "/api/auth/login",
            status,
            status == 200 and bool(user_token),
            "smoke user logged in" if user_token else f"unexpected payload={payload}",
        )
    )
    if not user_token:
        return checks

    status, species_payload = _json_request(
        base_url,
        "/api/species?limit=1&include_total=false",
    )
    species_items = species_payload.get("items") or []
    species = species_items[0] if species_items else None
    checks.append(
        CheckResult(
            "/api/species?limit=1&include_total=false",
            status,
            status == 200 and species is not None,
            "selected smoke species" if species else "no species available",
        )
    )
    if species is None:
        return checks

    status, obs_payload = _json_request(
        base_url,
        "/api/observations",
        method="POST",
        bearer_token=user_token,
        json_payload={
            "group": species["group"],
            "species_id": species["id"],
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "lat": 52.5567,
            "lon": 39.5924,
            "comment": "Post-deploy smoke observation",
            "safety_checked": True,
        },
    )
    obs_id = obs_payload.get("id")
    checks.append(
        CheckResult(
            "/api/observations",
            status,
            status == 201 and bool(obs_id),
            "created smoke observation" if obs_id else f"unexpected payload={obs_payload}",
        )
    )
    if not obs_id:
        return checks

    status, confirm_payload = _json_request(
        base_url,
        f"/api/validation/{obs_id}/confirm",
        method="POST",
        bearer_token=admin_token,
        json_payload={
            "species_id": species["id"],
            "comment": "Post-deploy smoke confirmation",
            "sensitive_level": "open",
        },
    )
    checks.append(
        CheckResult(
            f"/api/validation/{obs_id}/confirm",
            status,
            status == 200 and confirm_payload.get("status") == "confirmed",
            "confirmed smoke observation",
        )
    )

    status, public_payload = _json_request(
        base_url,
        f"/api/observations?species_id={species['id']}&limit=20",
    )
    public_ids = {item.get("id") for item in public_payload.get("items", [])}
    checks.append(
        CheckResult(
            f"/api/observations?species_id={species['id']}&limit=20",
            status,
            status == 200 and obs_id in public_ids,
            "confirmed observation is publicly visible",
        )
    )

    status, _ = _json_request(
        base_url,
        f"/api/admin/users/{user_id}/anonymize",
        method="POST",
        bearer_token=admin_token,
    )
    checks.append(
        CheckResult(
            f"/api/admin/users/{user_id}/anonymize",
            status,
            status == 200,
            "anonymized smoke user; confirmed observation remains for audit",
        )
    )
    return checks


def run_smoke(
    base_url: str,
    admin_token: str | None,
    fail_on_ops_alerts: bool,
    *,
    admin_login: str | None = None,
    admin_password: str | None = None,
    exercise_write_workflow: bool = False,
) -> int:
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

    if not admin_token and (admin_login or admin_password):
        login_result = _admin_login(
            base_url,
            admin_login=admin_login,
            admin_password=admin_password,
        )
        if login_result.ok:
            admin_token = login_result.message
            login_result.message = "admin login ok"
        checks.append(login_result)

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
        if exercise_write_workflow:
            checks.extend(_run_write_workflow(base_url, admin_token=admin_token))
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
    parser.add_argument("--admin-login", default="", help="Optional admin login for auth smoke")
    parser.add_argument("--admin-password", default="", help="Optional admin password for auth smoke")
    parser.add_argument(
        "--exercise-write-workflow",
        action="store_true",
        help="Register, approve, submit and confirm a smoke observation (writes data)",
    )
    parser.add_argument(
        "--fail-on-ops-alerts",
        action="store_true",
        help="Fail when /api/admin/ops/alerts returns status=alert (requires --admin-token)",
    )
    args = parser.parse_args()
    token = args.admin_token.strip() or None
    return run_smoke(
        args.base_url,
        token,
        args.fail_on_ops_alerts,
        admin_login=args.admin_login.strip() or None,
        admin_password=args.admin_password.strip() or None,
        exercise_write_workflow=args.exercise_write_workflow,
    )


if __name__ == "__main__":
    sys.exit(main())
