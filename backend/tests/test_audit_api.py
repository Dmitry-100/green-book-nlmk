from datetime import datetime, timedelta, timezone

from app.models.audit_log import AuditLog


def test_audit_events_endpoint_requires_admin(client, employee_token):
    response = client.get(
        "/api/admin/audit/events",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


def test_audit_events_endpoint_filters_and_include_total(client, admin_token):
    create_species = client.post(
        "/api/species",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name_ru": "Audit API Species",
            "name_latin": "Audit api species latin",
            "group": "plants",
            "category": "typical",
        },
    )
    assert create_species.status_code == 201
    request_id = create_species.headers.get("X-Request-ID")
    assert request_id

    with_total = client.get(
        f"/api/admin/audit/events?action=species.create&request_id={request_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert with_total.status_code == 200
    with_total_data = with_total.json()
    assert with_total_data["total"] == 1
    assert len(with_total_data["items"]) == 1
    event = with_total_data["items"][0]
    assert event["action"] == "species.create"
    assert event["target_type"] == "species"
    assert event["request_id"] == request_id
    assert event["details"]["group"] == "plants"

    without_total = client.get(
        "/api/admin/audit/events?action=species.create&include_total=false",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert without_total.status_code == 200
    without_total_data = without_total.json()
    assert without_total_data["total"] is None
    assert len(without_total_data["items"]) >= 1


def test_audit_purge_endpoint_requires_admin(client, employee_token):
    response = client.post(
        "/api/admin/audit/purge",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


def test_audit_purge_dry_run_and_delete(client, db, admin_token):
    old_event = AuditLog(
        action="test.old",
        actor_user_id=None,
        actor_role=None,
        target_type="maintenance",
        target_id=1,
        outcome="success",
        details={"source": "test"},
        request_id=None,
        created_at=datetime.now(timezone.utc) - timedelta(days=400),
    )
    fresh_event = AuditLog(
        action="test.fresh",
        actor_user_id=None,
        actor_role=None,
        target_type="maintenance",
        target_id=2,
        outcome="success",
        details={"source": "test"},
        request_id=None,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add_all([old_event, fresh_event])
    db.commit()

    dry_run = client.post(
        "/api/admin/audit/purge?older_than_days=180&dry_run=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dry_run.status_code == 200
    dry_run_data = dry_run.json()
    assert dry_run_data["dry_run"] is True
    assert dry_run_data["candidates"] >= 1
    assert dry_run_data["deleted"] == 0
    assert db.query(AuditLog).filter(AuditLog.action == "test.old").count() == 1
    assert db.query(AuditLog).filter(AuditLog.action == "test.fresh").count() == 1

    purge = client.post(
        "/api/admin/audit/purge?older_than_days=180&dry_run=false",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert purge.status_code == 200
    purge_data = purge.json()
    assert purge_data["dry_run"] is False
    assert purge_data["deleted"] >= 1
    assert db.query(AuditLog).filter(AuditLog.action == "test.old").count() == 0
    assert db.query(AuditLog).filter(AuditLog.action == "test.fresh").count() == 1

    purge_audit_event = (
        db.query(AuditLog)
        .filter(AuditLog.action == "admin.audit_purge")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert purge_audit_event is not None
    assert purge_audit_event.details["deleted"] >= 1
