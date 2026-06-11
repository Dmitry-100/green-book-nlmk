from jose import jwt

from app.config import settings
from app.models.user import User, UserApprovalStatus, UserRole
from app.services.passwords import hash_password


def test_register_creates_approved_employee_without_email(client, db):
    response = client.post(
        "/api/auth/register",
        json={
            "login": "ivanov_dm",
            "password": "strong-password",
            "display_name": "ИД",
            "personal_data_notice_accepted": True,
            "privacy_notice_version": settings.privacy_notice_version,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["user"]["role"] == "employee"
    assert payload["user"]["approval_status"] == "approved"
    assert payload["user"]["public_name"] == "ИД"
    assert payload["user"]["email"] is None
    assert "можно войти" in payload["message"].lower()

    user = db.query(User).filter(User.login == "ivanov_dm").one()
    assert user.password_hash
    assert user.password_hash != "strong-password"
    assert user.email is None
    assert user.privacy_notice_version == settings.privacy_notice_version
    assert user.privacy_notice_accepted_at is not None
    assert user.approved_at is not None
    assert user.approved_by_id is None


def test_registered_user_can_login_immediately_and_receives_cookie(client):
    client.post(
        "/api/auth/register",
        json={
            "login": "petrov_am",
            "password": "strong-password",
            "display_name": "ПА",
            "personal_data_notice_accepted": True,
            "privacy_notice_version": settings.privacy_notice_version,
        },
    )

    response = client.post(
        "/api/auth/login",
        json={"login": "petrov_am", "password": "strong-password"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["approval_status"] == "approved"
    assert "gb_session=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]

    token_payload = jwt.decode(
        payload["access_token"],
        settings.auth_secret_key,
        algorithms=[settings.auth_algorithm],
    )
    assert token_payload["sub"] == "local:petrov_am"
    assert token_payload["typ"] == "access"
    assert "name" not in token_payload
    assert "email" not in token_payload


def test_me_accepts_session_cookie(client):
    register_response = client.post(
        "/api/auth/register",
        json={
            "login": "cookie_user",
            "password": "strong-password",
            "display_name": "CU",
            "personal_data_notice_accepted": True,
            "privacy_notice_version": settings.privacy_notice_version,
        },
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/api/auth/login",
        json={"login": "cookie_user", "password": "strong-password"},
    )
    assert login_response.status_code == 200

    me_response = client.get("/api/auth/me")

    assert me_response.status_code == 200
    assert me_response.json()["display_name"] == "CU"


def test_logout_clears_stale_session_cookie(client):
    client.cookies.set("gb_session", "stale.invalid.token")

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "gb_session=" in response.headers["set-cookie"]


def test_register_rejects_email_payload(client):
    response = client.post(
        "/api/auth/register",
        json={
            "login": "email_payload",
            "password": "strong-password",
            "display_name": "EP",
            "email": "email_payload@example.com",
            "personal_data_notice_accepted": True,
            "privacy_notice_version": settings.privacy_notice_version,
        },
    )

    assert response.status_code == 422


def test_register_rejects_display_name_with_personal_or_reserved_data(client):
    base_payload = {
        "login": "bad_display",
        "password": "strong-password",
        "personal_data_notice_accepted": True,
        "privacy_notice_version": settings.privacy_notice_version,
    }
    for display_name in ["ivan@example.com", "+7 900 111-22-33", "Главный эколог", "НЛМК admin"]:
        response = client.post(
            "/api/auth/register",
            json={**base_payload, "login": f"bad_{abs(hash(display_name))}", "display_name": display_name},
        )
        assert response.status_code == 422


def test_privacy_notice_endpoint_returns_current_version(client):
    response = client.get("/api/privacy/notice")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == settings.privacy_notice_version
    assert payload["operator_name"]
    assert payload["data_categories"]


def test_legacy_pending_user_can_login_after_backfill(client, db):
    user = User(
        external_id="local:sidorov_ir",
        login="sidorov_ir",
        password_hash=hash_password("strong-password"),
        display_name="СИ",
        role=UserRole.employee,
        approval_status=UserApprovalStatus.pending,
    )
    db.add(user)
    db.commit()

    login_response = client.post(
        "/api/auth/login",
        json={"login": "sidorov_ir", "password": "strong-password"},
    )
    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"] == payload["token"]
    assert payload["user"]["role"] == "employee"


def test_registration_rejects_role_in_payload(client):
    response = client.post(
        "/api/auth/register",
        json={
            "login": "role_hacker",
            "password": "strong-password",
            "display_name": "Role Hacker",
            "role": "admin",
            "personal_data_notice_accepted": True,
            "privacy_notice_version": settings.privacy_notice_version,
        },
    )

    assert response.status_code == 422


def test_admin_can_change_role_but_ecologist_cannot_assign_admin(
    client,
    db,
    admin_token,
    ecologist_token,
):
    user = User(
        external_id="local:role_target",
        login="role_target",
        password_hash=hash_password("strong-password"),
        display_name="Role Target",
        role=UserRole.employee,
        approval_status=UserApprovalStatus.approved,
    )
    db.add(user)
    db.commit()

    ecologist_response = client.post(
        f"/api/admin/users/{user.id}/set-role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {ecologist_token}"},
    )
    assert ecologist_response.status_code == 403

    admin_response = client.post(
        f"/api/admin/users/{user.id}/set-role",
        json={"role": "ecologist"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_response.status_code == 200
    assert admin_response.json()["role"] == "ecologist"
