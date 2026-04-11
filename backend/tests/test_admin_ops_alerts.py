from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement

import app.routers.admin as admin_router
from app.config import settings
from app.models.observation import IncidentStatus, Observation, ObservationStatus
from app.models.species import Species, SpeciesCategory, SpeciesGroup
from app.models.user import User, UserRole
from app.services.metrics import record_request_metric, reset_request_metrics


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


def test_admin_ops_alerts_requires_admin(client, employee_token):
    response = client.get(
        "/api/admin/ops/alerts",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


def test_admin_ops_alerts_returns_ok_when_below_thresholds(client, admin_token, monkeypatch):
    reset_request_metrics()
    monkeypatch.setattr(settings, "ops_alert_on_review_threshold", 999999)
    monkeypatch.setattr(settings, "ops_alert_open_incidents_threshold", 999999)
    monkeypatch.setattr(settings, "ops_alert_error_rate_percent_threshold", 100.0)
    monkeypatch.setattr(settings, "ops_alert_media_pending_threshold", 999999)
    monkeypatch.setattr(
        settings, "ops_alert_media_pending_age_seconds_threshold", 999999
    )
    monkeypatch.setattr(settings, "ops_alert_media_failed_threshold", 999999)
    monkeypatch.setattr(settings, "ops_alert_cache_degraded_stores_threshold", 999999)

    response = client.get(
        "/api/admin/ops/alerts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["alerts"] == []


def test_admin_ops_alerts_detects_threshold_violations(client, db, admin_token, monkeypatch):
    reset_request_metrics()

    author = _create_user(
        db,
        external_id="ops-alert-author-001",
        email="ops-alert-author-001@nlmk.com",
    )
    species = Species(
        name_ru="Ops alert species",
        name_latin="Ops alert species latin",
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
        observed_at=datetime.now(timezone.utc),
        location_point=WKTElement("POINT(39.60 52.59)", srid=4326),
        status=ObservationStatus.on_review,
        comment="ops alerts test",
        is_incident=True,
        incident_status=IncidentStatus.new,
        safety_checked=True,
    )
    db.add(observation)
    db.commit()

    record_request_metric(
        method="GET",
        route_path="/api/test",
        fallback_path="/api/test",
        status_code=500,
        duration_ms=10.0,
    )
    record_request_metric(
        method="GET",
        route_path="/api/test",
        fallback_path="/api/test",
        status_code=200,
        duration_ms=10.0,
    )

    monkeypatch.setattr(settings, "ops_alert_on_review_threshold", 0)
    monkeypatch.setattr(settings, "ops_alert_open_incidents_threshold", 0)
    monkeypatch.setattr(settings, "ops_alert_error_rate_percent_threshold", 0.0)
    monkeypatch.setattr(settings, "ops_alert_media_pending_threshold", 999999)
    monkeypatch.setattr(
        settings, "ops_alert_media_pending_age_seconds_threshold", 999999
    )
    monkeypatch.setattr(settings, "ops_alert_media_failed_threshold", 999999)
    monkeypatch.setattr(settings, "ops_alert_cache_degraded_stores_threshold", 999999)

    response = client.get(
        "/api/admin/ops/alerts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "alert"
    codes = {item["code"] for item in payload["alerts"]}
    assert "validation_queue_high" in codes
    assert "open_incidents_high" in codes
    assert "api_error_rate_high" in codes


def test_admin_ops_alerts_detects_media_and_cache_signals(
    client, admin_token, monkeypatch
):
    monkeypatch.setattr(
        admin_router,
        "_build_ops_summary_payload",
        lambda db: {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline": {"on_review": 0},
            "incidents": {"open_incidents": 0},
            "metrics": {"error_rate_percent": 0.0},
            "media_pipeline": {
                "pending": 12,
                "processing": 1,
                "ready": 0,
                "failed": 3,
                "pending_oldest_age_seconds": 1200,
            },
            "cache": {"totals": {"degraded_stores": 2}},
        },
    )
    monkeypatch.setattr(settings, "ops_alert_on_review_threshold", 999999)
    monkeypatch.setattr(settings, "ops_alert_open_incidents_threshold", 999999)
    monkeypatch.setattr(settings, "ops_alert_error_rate_percent_threshold", 100.0)
    monkeypatch.setattr(settings, "ops_alert_media_pending_threshold", 1)
    monkeypatch.setattr(settings, "ops_alert_media_pending_age_seconds_threshold", 10)
    monkeypatch.setattr(settings, "ops_alert_media_failed_threshold", 0)
    monkeypatch.setattr(settings, "ops_alert_cache_degraded_stores_threshold", 0)

    response = client.get(
        "/api/admin/ops/alerts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "alert"
    codes = {item["code"] for item in payload["alerts"]}
    assert "media_queue_depth_high" in codes
    assert "media_queue_lag_high" in codes
    assert "media_processing_failed_high" in codes
    assert "cache_backend_degraded" in codes
