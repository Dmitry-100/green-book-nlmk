from app.models.user import User, UserApprovalStatus, UserRole
from app.services.passwords import hash_password


def test_register_creates_pending_employee(client, db):
    response = client.post(
        "/api/auth/register",
        json={
            "login": "ivanov_dm",
            "password": "strong-password",
            "display_name": "Иванов Дмитрий Максимович",
            "email": "ivanov@example.com",
            "personal_data_notice_accepted": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["user"]["role"] == "employee"
    assert payload["user"]["approval_status"] == "pending"
    assert payload["user"]["public_name"] == "ИД"

    user = db.query(User).filter(User.login == "ivanov_dm").one()
    assert user.password_hash
    assert user.password_hash != "strong-password"


def test_pending_user_cannot_login(client):
    client.post(
        "/api/auth/register",
        json={
            "login": "petrov_am",
            "password": "strong-password",
            "display_name": "Петров Алексей Михайлович",
            "personal_data_notice_accepted": True,
        },
    )

    response = client.post(
        "/api/auth/login",
        json={"login": "petrov_am", "password": "strong-password"},
    )

    assert response.status_code == 403
    assert "ожидает подтверждения" in response.json()["detail"]


def test_admin_can_approve_user_and_user_can_login(client, db, admin_token):
    user = User(
        external_id="local:sidorov_ir",
        login="sidorov_ir",
        password_hash=hash_password("strong-password"),
        display_name="Сидоров Иван Романович",
        role=UserRole.employee,
        approval_status=UserApprovalStatus.pending,
    )
    db.add(user)
    db.commit()

    approve_response = client.post(
        f"/api/admin/users/{user.id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["approval_status"] == "approved"

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
