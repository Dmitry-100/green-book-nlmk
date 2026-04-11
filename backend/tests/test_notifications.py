from app.models.notification import Notification, NotificationType
from app.models.user import User, UserRole
from tests.conftest import make_token


def _create_user(db, external_id: str, email: str, role: UserRole = UserRole.employee) -> User:
    user = User(
        external_id=external_id,
        display_name=external_id,
        email=email,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_unread_count_cache_invalidates_after_mark_read(client, db):
    user = _create_user(
        db,
        external_id="notif-user-001",
        email="notif-user-001@nlmk.com",
    )
    db.add(
        Notification(
            user_id=user.id,
            observation_id=None,
            type=NotificationType.confirmed,
            message="notification one",
            is_read=False,
        )
    )
    second = Notification(
        user_id=user.id,
        observation_id=None,
        type=NotificationType.needs_data,
        message="notification two",
        is_read=False,
    )
    db.add(second)
    db.commit()
    db.refresh(second)

    token = make_token(
        external_id=user.external_id,
        name=user.display_name,
        email=user.email,
        role=user.role.value,
    )
    headers = {"Authorization": f"Bearer {token}"}

    first_count = client.get("/api/notifications/unread-count", headers=headers)
    assert first_count.status_code == 200
    assert first_count.json()["count"] == 2

    cached_count = client.get("/api/notifications/unread-count", headers=headers)
    assert cached_count.status_code == 200
    assert cached_count.json()["count"] == 2

    mark_read = client.patch(f"/api/notifications/{second.id}/read", headers=headers)
    assert mark_read.status_code == 200

    after_mark_read = client.get("/api/notifications/unread-count", headers=headers)
    assert after_mark_read.status_code == 200
    assert after_mark_read.json()["count"] == 1


def test_list_notifications_can_skip_total_count(client, db):
    user = _create_user(
        db,
        external_id="notif-user-002",
        email="notif-user-002@nlmk.com",
    )
    db.add(
        Notification(
            user_id=user.id,
            observation_id=None,
            type=NotificationType.confirmed,
            message="notification list one",
            is_read=False,
        )
    )
    db.add(
        Notification(
            user_id=user.id,
            observation_id=None,
            type=NotificationType.rejected,
            message="notification list two",
            is_read=False,
        )
    )
    db.commit()

    token = make_token(
        external_id=user.external_id,
        name=user.display_name,
        email=user.email,
        role=user.role.value,
    )
    headers = {"Authorization": f"Bearer {token}"}

    without_total = client.get("/api/notifications?include_total=false", headers=headers)
    assert without_total.status_code == 200
    without_total_data = without_total.json()
    assert len(without_total_data["items"]) == 2
    assert without_total_data["total"] is None

    with_total = client.get("/api/notifications", headers=headers)
    assert with_total.status_code == 200
    with_total_data = with_total.json()
    assert len(with_total_data["items"]) == 2
    assert with_total_data["total"] == 2
