from datetime import datetime, timedelta, timezone

from geoalchemy2.elements import WKTElement

import app.routers.admin as admin_router
from app.models.audit_log import AuditLog
from app.models.notification import Notification, NotificationType
from app.models.observation import IncidentStatus, Observation, ObservationStatus
from app.models.species import Species, SpeciesCategory, SpeciesGroup
from app.models.user import User, UserRole
from app.services.metrics import reset_request_metrics


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


def test_admin_ops_summary_requires_admin(client, employee_token):
    response = client.get(
        "/api/admin/ops/summary",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


def test_admin_ops_summary_returns_expected_sections(client, db, admin_token):
    reset_request_metrics()

    author = _create_user(db, external_id="ops-author-001", email="ops-author-001@nlmk.com")
    species = Species(
        name_ru="Ops species",
        name_latin="Ops species latin",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.typical,
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    observation = Observation(
        author_id=author.id,
        species_id=species.id,
        group=SpeciesGroup.birds.value,
        observed_at=datetime.now(timezone.utc) - timedelta(hours=1),
        location_point=WKTElement("POINT(39.60 52.59)", srid=4326),
        status=ObservationStatus.on_review,
        comment="ops summary test",
        is_incident=True,
        incident_status=IncidentStatus.new,
        safety_checked=True,
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)

    db.add(
        Notification(
            user_id=author.id,
            observation_id=observation.id,
            type=NotificationType.needs_data,
            message="ops notification",
            is_read=False,
        )
    )
    db.add(
        AuditLog(
            action="ops.test",
            actor_user_id=None,
            actor_role=None,
            target_type="system",
            target_id=None,
            outcome="success",
            details={"source": "test"},
            request_id="ops-test-request-id",
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    response = client.get(
        "/api/admin/ops/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert "generated_at" in payload
    assert payload["catalog"]["species_total"] >= 1
    assert payload["pipeline"]["observations_total"] >= 1
    assert payload["pipeline"]["on_review"] >= 1
    assert payload["incidents"]["open_incidents"] >= 1
    assert payload["notifications"]["unread_total"] >= 1
    assert payload["audit"]["events_total"] >= 1
    assert payload["audit"]["events_last_24h"] >= 1
    assert payload["media_pipeline"]["pending"] >= 0
    assert payload["media_pipeline"]["processing"] >= 0
    assert payload["media_pipeline"]["ready"] >= 0
    assert payload["media_pipeline"]["failed"] >= 0
    assert payload["media_pipeline"]["pending_oldest_age_seconds"] >= 0
    assert "cache" in payload
    assert "totals" in payload["cache"]
    assert payload["cache"]["totals"]["stores_total"] >= 0
    assert "metrics" in payload
    assert "requests_total" in payload["metrics"]


def test_admin_media_process_requires_admin(client, employee_token):
    response = client.post(
        "/api/admin/ops/media/process",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


def test_admin_media_process_returns_batch_stats(client, admin_token, monkeypatch):
    monkeypatch.setattr(
        admin_router,
        "run_media_processing_batch",
        lambda db, batch_size: {
            "claimed": 2,
            "ready": 1,
            "requeued": 1,
            "failed": 0,
            "batch_size": batch_size,
        },
    )

    response = client.post(
        "/api/admin/ops/media/process?batch_size=7",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "claimed": 2,
        "ready": 1,
        "requeued": 1,
        "failed": 0,
        "batch_size": 7,
    }
