import logging
from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement

from app.models.audit_log import AuditLog
from app.models.observation import Observation, ObservationStatus
from app.models.species import Species, SpeciesCategory, SpeciesGroup
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


def _create_species(db, *, latin: str, group: SpeciesGroup) -> Species:
    species = Species(
        name_ru=f"Species {latin}",
        name_latin=latin,
        group=group,
        category=SpeciesCategory.typical,
    )
    db.add(species)
    db.commit()
    db.refresh(species)
    return species


def _create_observation(db, *, author_id: int, species_id: int, group: str) -> Observation:
    obs = Observation(
        author_id=author_id,
        species_id=species_id,
        group=group,
        observed_at=datetime.now(timezone.utc),
        location_point=WKTElement("POINT(39.60 52.59)", srid=4326),
        status=ObservationStatus.on_review,
        comment="audit test",
        is_incident=False,
        safety_checked=True,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


def test_validation_confirm_emits_audit_event(client, db, caplog):
    caplog.set_level(logging.INFO, logger="app.audit")
    author = _create_user(db, external_id="audit-author-001", email="audit-author-001@nlmk.com")
    species = _create_species(db, latin="AuditBird", group=SpeciesGroup.birds)
    obs = _create_observation(
        db,
        author_id=author.id,
        species_id=species.id,
        group=SpeciesGroup.birds.value,
    )
    eco_token = make_token(
        external_id="audit-eco-001",
        name="Audit Eco",
        email="audit-eco-001@nlmk.com",
        role="ecologist",
    )

    response = client.post(
        f"/api/validation/{obs.id}/confirm",
        headers={"Authorization": f"Bearer {eco_token}"},
        json={},
    )
    assert response.status_code == 200

    matched = [
        record
        for record in caplog.records
        if getattr(record, "audit_action", "") == "validation.confirm"
        and getattr(record, "target_type", "") == "observation"
        and getattr(record, "target_id", None) == obs.id
    ]
    assert matched, "Expected validation.confirm audit event"

    db_row = (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "validation.confirm",
            AuditLog.target_type == "observation",
            AuditLog.target_id == obs.id,
        )
        .first()
    )
    assert db_row is not None
    assert db_row.actor_user_id is not None
    assert db_row.outcome == "success"


def test_species_create_emits_audit_event(client, db, caplog, admin_token):
    caplog.set_level(logging.INFO, logger="app.audit")

    response = client.post(
        "/api/species",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name_ru": "Audit Species",
            "name_latin": "Audit species latin",
            "group": "plants",
            "category": "typical",
        },
    )
    assert response.status_code == 201
    species_id = response.json()["id"]

    matched = [
        record
        for record in caplog.records
        if getattr(record, "audit_action", "") == "species.create"
        and getattr(record, "target_type", "") == "species"
        and getattr(record, "target_id", None) == species_id
    ]
    assert matched, "Expected species.create audit event"
    db_row = (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "species.create",
            AuditLog.target_type == "species",
            AuditLog.target_id == species_id,
        )
        .first()
    )
    assert db_row is not None
    assert db_row.outcome == "success"
