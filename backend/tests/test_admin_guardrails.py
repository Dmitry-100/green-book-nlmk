from datetime import datetime, timedelta, timezone

from app.models.audit_log import AuditLog
from app.models.user import User, UserRole


def _create_user(db, external_id: str, role: UserRole = UserRole.employee) -> User:
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


def test_audit_events_compound_filters_and_pagination(client, db, admin_token):
    actor_a = _create_user(db, external_id="audit-filter-actor-a")
    actor_b = _create_user(db, external_id="audit-filter-actor-b")
    now = datetime.now(timezone.utc)

    first = AuditLog(
        action="species.create",
        actor_user_id=actor_a.id,
        actor_role=actor_a.role.value,
        target_type="species",
        target_id=11,
        outcome="success",
        details={"marker": "first"},
        request_id="req-a-1",
        created_at=now - timedelta(hours=2),
    )
    second = AuditLog(
        action="species.create",
        actor_user_id=actor_a.id,
        actor_role=actor_a.role.value,
        target_type="species",
        target_id=12,
        outcome="failure",
        details={"marker": "second"},
        request_id="req-a-2",
        created_at=now - timedelta(hours=1),
    )
    third = AuditLog(
        action="validation.confirm",
        actor_user_id=actor_b.id,
        actor_role=actor_b.role.value,
        target_type="observation",
        target_id=13,
        outcome="success",
        details={"marker": "third"},
        request_id="req-b-1",
        created_at=now,
    )
    db.add_all([first, second, third])
    db.commit()
    db.refresh(first)
    db.refresh(second)
    db.refresh(third)

    filtered = client.get(
        "/api/admin/audit/events",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={
            "action": "species.create",
            "target_type": "species",
            "actor_user_id": actor_a.id,
            "outcome": "failure",
            "request_id": "req-a-2",
            "created_from": (now - timedelta(minutes=90)).isoformat(),
            "created_to": (now + timedelta(minutes=1)).isoformat(),
        },
    )
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert filtered_payload["total"] == 1
    assert len(filtered_payload["items"]) == 1
    assert filtered_payload["items"][0]["id"] == second.id
    assert filtered_payload["items"][0]["details"]["marker"] == "second"

    first_page = client.get(
        "/api/admin/audit/events",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"limit": 2, "skip": 0},
    )
    assert first_page.status_code == 200
    first_page_ids = [item["id"] for item in first_page.json()["items"]]
    assert first_page_ids == [third.id, second.id]

    second_page = client.get(
        "/api/admin/audit/events",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"limit": 2, "skip": 2},
    )
    assert second_page.status_code == 200
    second_page_ids = [item["id"] for item in second_page.json()["items"]]
    assert second_page_ids == [first.id]


def test_audit_purge_rejects_out_of_range_days(client, admin_token):
    too_low = client.post(
        "/api/admin/audit/purge?older_than_days=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert too_low.status_code == 422

    too_high = client.post(
        "/api/admin/audit/purge?older_than_days=36501",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert too_high.status_code == 422


def test_admin_media_process_rejects_invalid_batch_size(client, admin_token):
    too_small = client.post(
        "/api/admin/ops/media/process?batch_size=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert too_small.status_code == 422

    too_large = client.post(
        "/api/admin/ops/media/process?batch_size=501",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert too_large.status_code == 422
