from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.rate_limit import RateLimitMiddleware
from tests.conftest import make_token


def _build_test_client(
    monkeypatch,
    *,
    requests_per_window: int = 1,
    auth_requests_per_window: int | None = None,
    trusted_proxies: tuple[str, ...] = (),
) -> TestClient:
    monkeypatch.setattr(
        RateLimitMiddleware,
        "_init_redis_client",
        staticmethod(lambda: None),
    )

    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=requests_per_window,
        window_seconds=60,
        auth_requests_per_window=auth_requests_per_window,
        trusted_proxies=trusted_proxies,
    )

    @app.get("/limited")
    def limited():
        return {"ok": True}

    @app.post("/api/auth/login")
    def login():
        return {"ok": True}

    return TestClient(app)


def test_rate_limit_applies_to_anonymous_by_ip(monkeypatch):
    client = _build_test_client(monkeypatch, requests_per_window=1)

    first = client.get("/limited")
    assert first.status_code == 200

    second = client.get("/limited")
    assert second.status_code == 429
    assert second.json()["detail"] == "Too many requests"


def test_rate_limit_isolated_per_authenticated_user(monkeypatch):
    client = _build_test_client(monkeypatch, requests_per_window=1)
    token_user_1 = make_token(
        external_id="rate-user-001",
        name="Rate User 1",
        email="rate-user-001@nlmk.com",
        role="employee",
    )
    token_user_2 = make_token(
        external_id="rate-user-002",
        name="Rate User 2",
        email="rate-user-002@nlmk.com",
        role="employee",
    )

    first_user_first_request = client.get(
        "/limited",
        headers={"Authorization": f"Bearer {token_user_1}"},
    )
    assert first_user_first_request.status_code == 200

    second_user_first_request = client.get(
        "/limited",
        headers={"Authorization": f"Bearer {token_user_2}"},
    )
    assert second_user_first_request.status_code == 200

    first_user_second_request = client.get(
        "/limited",
        headers={"Authorization": f"Bearer {token_user_1}"},
    )
    assert first_user_second_request.status_code == 429

    second_user_second_request = client.get(
        "/limited",
        headers={"Authorization": f"Bearer {token_user_2}"},
    )
    assert second_user_second_request.status_code == 429


def test_spoofed_forwarded_for_does_not_bypass_limit(monkeypatch):
    client = _build_test_client(monkeypatch, requests_per_window=1)

    first = client.get("/limited", headers={"X-Forwarded-For": "10.0.0.1"})
    assert first.status_code == 200

    # Без доверенного прокси заголовок игнорируется: новый XFF не даёт
    # нового bucket'а.
    second = client.get("/limited", headers={"X-Forwarded-For": "10.0.0.2"})
    assert second.status_code == 429


def test_forwarded_for_honored_only_from_trusted_proxy(monkeypatch):
    client = _build_test_client(
        monkeypatch,
        requests_per_window=1,
        trusted_proxies=("testclient",),
    )

    first = client.get("/limited", headers={"X-Forwarded-For": "10.0.0.1"})
    assert first.status_code == 200

    # Тот же реальный клиент за прокси: лимит общий.
    second = client.get("/limited", headers={"X-Forwarded-For": "spoofed, 10.0.0.1"})
    assert second.status_code == 429

    # Другой реальный клиент за тем же прокси получает свой bucket.
    other = client.get("/limited", headers={"X-Forwarded-For": "10.0.0.2"})
    assert other.status_code == 200


def test_auth_paths_use_stricter_network_limit(monkeypatch):
    client = _build_test_client(
        monkeypatch,
        requests_per_window=100,
        auth_requests_per_window=2,
    )
    token = make_token(external_id="rate-auth-001")

    assert client.post("/api/auth/login").status_code == 200
    # Bearer-токен не даёт отдельного bucket'а на auth-эндпоинтах.
    assert (
        client.post(
            "/api/auth/login", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 200
    )
    third = client.post("/api/auth/login")
    assert third.status_code == 429
    assert third.headers["X-RateLimit-Limit"] == "2"

    # Обычные пути продолжают работать по основному лимиту.
    assert client.get("/limited").status_code == 200
