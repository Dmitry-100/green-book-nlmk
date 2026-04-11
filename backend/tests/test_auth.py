
from app.config import settings
from tests.conftest import make_token


def test_valid_token_is_generated(employee_token):
    assert employee_token is not None


def test_invalid_token_does_not_break_public_health(client):
    response = client.get(
        "/api/health",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 200


def test_token_role_claim_is_honored_in_test_env(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "test")
    admin_like_token = make_token(
        external_id="auth-test-admin-001",
        name="Auth Test Admin",
        email="auth-test-admin-001@nlmk.com",
        role="admin",
    )

    response = client.get(
        "/api/metrics",
        headers={"Authorization": f"Bearer {admin_like_token}"},
    )
    assert response.status_code == 200


def test_token_role_claim_is_ignored_outside_dev_and_test(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    admin_like_token = make_token(
        external_id="auth-prod-admin-001",
        name="Auth Prod Admin",
        email="auth-prod-admin-001@nlmk.com",
        role="admin",
    )

    response = client.get(
        "/api/metrics",
        headers={"Authorization": f"Bearer {admin_like_token}"},
    )
    assert response.status_code == 403


def test_dev_token_endpoint_respects_enable_dev_auth_flag(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "enable_dev_auth", False)

    response = client.post("/api/dev/token")
    assert response.status_code == 403
    assert response.json()["detail"] == "Dev endpoints are disabled"


def test_dev_token_endpoint_returns_access_token_alias(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "enable_dev_auth", True)

    response = client.post("/api/dev/token?role=admin")
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"] == payload["token"]
    assert payload["user"]["role"] == "admin"
