from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.rate_limit import RateLimitMiddleware
from tests.conftest import make_token


def _build_test_client(monkeypatch, *, requests_per_window: int = 1) -> TestClient:
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
    )

    @app.get("/limited")
    def limited():
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
