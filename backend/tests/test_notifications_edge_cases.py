from datetime import datetime, timedelta, timezone

from app.models.notification import Notification, NotificationType
from app.models.user import User, UserRole
from tests.conftest import make_token


def _create_user(db, *, external_id: str, role: UserRole = UserRole.employee) -> User:
    user = User(
        external_id=external_id,
        display_name=external_id,
        email=f"{external_id}@nlmk.com",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_notifications_list_is_scoped_sorted_and_paginates(client, db):
    now = datetime.now(timezone.utc)
    user = _create_user(db, external_id="notif-edge-owner")
    other_user = _create_user(db, external_id="notif-edge-other")

    db.add_all(
        [
            Notification(
                user_id=user.id,
                observation_id=None,
                type=NotificationType.confirmed,
                message="older",
                is_read=False,
                created_at=now - timedelta(minutes=3),
            ),
            Notification(
                user_id=user.id,
                observation_id=None,
                type=NotificationType.needs_data,
                message="middle",
                is_read=False,
                created_at=now - timedelta(minutes=2),
            ),
            Notification(
                user_id=user.id,
                observation_id=None,
                type=NotificationType.rejected,
                message="newest",
                is_read=False,
                created_at=now - timedelta(minutes=1),
            ),
            Notification(
                user_id=other_user.id,
                observation_id=None,
                type=NotificationType.confirmed,
                message="foreign",
                is_read=False,
                created_at=now,
            ),
        ]
    )
    db.commit()

    token = make_token(
        external_id=user.external_id,
        name=user.display_name,
        email=user.email,
        role=user.role.value,
    )
    headers = {"Authorization": f"Bearer {token}"}

    first_page = client.get("/api/notifications?skip=0&limit=2", headers=headers)
    assert first_page.status_code == 200
    first_page_data = first_page.json()
    assert first_page_data["total"] == 3
    assert [item["message"] for item in first_page_data["items"]] == ["newest", "middle"]

    second_page = client.get("/api/notifications?skip=2&limit=2", headers=headers)
    assert second_page.status_code == 200
    second_page_data = second_page.json()
    assert second_page_data["total"] == 3
    assert [item["message"] for item in second_page_data["items"]] == ["older"]


def test_mark_read_ignores_foreign_notification(client, db):
    owner = _create_user(db, external_id="notif-edge-owner-2")
    foreign = _create_user(db, external_id="notif-edge-foreign")
    foreign_notif = Notification(
        user_id=foreign.id,
        observation_id=None,
        type=NotificationType.needs_data,
        message="foreign unread",
        is_read=False,
    )
    db.add(foreign_notif)
    db.commit()
    db.refresh(foreign_notif)

    owner_token = make_token(
        external_id=owner.external_id,
        name=owner.display_name,
        email=owner.email,
        role=owner.role.value,
    )
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    patch_response = client.patch(
        f"/api/notifications/{foreign_notif.id}/read",
        headers=owner_headers,
    )
    assert patch_response.status_code == 200
    assert patch_response.json() == {"ok": True}

    db.refresh(foreign_notif)
    assert foreign_notif.is_read is False

    foreign_token = make_token(
        external_id=foreign.external_id,
        name=foreign.display_name,
        email=foreign.email,
        role=foreign.role.value,
    )
    foreign_headers = {"Authorization": f"Bearer {foreign_token}"}
    foreign_unread = client.get("/api/notifications/unread-count", headers=foreign_headers)
    assert foreign_unread.status_code == 200
    assert foreign_unread.json()["count"] == 1


def test_mark_read_is_idempotent_for_same_notification(client, db):
    user = _create_user(db, external_id="notif-edge-owner-3")
    notif = Notification(
        user_id=user.id,
        observation_id=None,
        type=NotificationType.confirmed,
        message="to read once",
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    token = make_token(
        external_id=user.external_id,
        name=user.display_name,
        email=user.email,
        role=user.role.value,
    )
    headers = {"Authorization": f"Bearer {token}"}

    first_patch = client.patch(f"/api/notifications/{notif.id}/read", headers=headers)
    second_patch = client.patch(f"/api/notifications/{notif.id}/read", headers=headers)
    assert first_patch.status_code == 200
    assert second_patch.status_code == 200

    unread = client.get("/api/notifications/unread-count", headers=headers)
    assert unread.status_code == 200
    assert unread.json()["count"] == 0
