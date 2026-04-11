from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement

from app.models.notification import Notification, NotificationType
from app.models.observation import Observation, ObservationStatus
from app.models.species import Species, SpeciesCategory, SpeciesGroup
from app.models.user import User, UserRole
from tests.conftest import make_token


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


def _create_observation(
    db,
    *,
    author_id: int,
    species_id: int | None,
    group: str,
    status: ObservationStatus,
) -> Observation:
    obs = Observation(
        author_id=author_id,
        species_id=species_id,
        group=group,
        observed_at=datetime.now(timezone.utc),
        location_point=WKTElement("POINT(39.61 52.58)", srid=4326),
        status=status,
        comment="validation permission test",
        is_incident=False,
        safety_checked=True,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


def test_validation_queue_requires_privileged_role(client, db):
    author = _create_user(db, external_id="val-role-author")
    species = _create_species(db, latin="ValRoleSpecies", group=SpeciesGroup.birds)
    _create_observation(
        db,
        author_id=author.id,
        species_id=species.id,
        group=SpeciesGroup.birds.value,
        status=ObservationStatus.on_review,
    )

    employee_token = make_token(
        external_id="val-role-employee",
        name="Val Employee",
        email="val-role-employee@nlmk.com",
        role="employee",
    )
    response = client.get(
        "/api/validation/queue",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Role employee not allowed"


def test_validation_actions_require_privileged_role(client, db):
    author = _create_user(db, external_id="val-action-author")
    species = _create_species(db, latin="ValActionSpecies", group=SpeciesGroup.plants)
    obs = _create_observation(
        db,
        author_id=author.id,
        species_id=species.id,
        group=SpeciesGroup.plants.value,
        status=ObservationStatus.on_review,
    )
    employee_token = make_token(
        external_id="val-action-employee",
        name="Val Employee",
        email="val-action-employee@nlmk.com",
        role="employee",
    )
    headers = {"Authorization": f"Bearer {employee_token}"}

    confirm_response = client.post(
        f"/api/validation/{obs.id}/confirm",
        json={},
        headers=headers,
    )
    assert confirm_response.status_code == 403
    assert confirm_response.json()["detail"] == "Role employee not allowed"

    reject_response = client.post(
        f"/api/validation/{obs.id}/reject",
        json={"comment": "not enough quality"},
        headers=headers,
    )
    assert reject_response.status_code == 403
    assert reject_response.json()["detail"] == "Role employee not allowed"

    request_data_response = client.post(
        f"/api/validation/{obs.id}/request-data",
        json={"comment": "need more details"},
        headers=headers,
    )
    assert request_data_response.status_code == 403
    assert request_data_response.json()["detail"] == "Role employee not allowed"


def test_reject_is_idempotent_without_extra_notifications(client, db):
    author = _create_user(db, external_id="val-reject-author")
    species = _create_species(db, latin="ValRejectSpecies", group=SpeciesGroup.fungi)
    obs = _create_observation(
        db,
        author_id=author.id,
        species_id=species.id,
        group=SpeciesGroup.fungi.value,
        status=ObservationStatus.on_review,
    )
    eco_token = make_token(
        external_id="val-reject-eco",
        name="Val Eco",
        email="val-reject-eco@nlmk.com",
        role="ecologist",
    )
    headers = {"Authorization": f"Bearer {eco_token}"}

    first = client.post(
        f"/api/validation/{obs.id}/reject",
        json={"comment": "insufficient evidence"},
        headers=headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/validation/{obs.id}/reject",
        json={"comment": "same status retry"},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["status"] == ObservationStatus.rejected.value

    db.refresh(obs)
    assert obs.status == ObservationStatus.rejected
    rejected_notifications = (
        db.query(Notification)
        .filter(
            Notification.observation_id == obs.id,
            Notification.type == NotificationType.rejected,
        )
        .count()
    )
    assert rejected_notifications == 1


def test_request_data_noop_on_needs_data_does_not_create_notification(client, db):
    author = _create_user(db, external_id="val-request-author")
    species = _create_species(db, latin="ValRequestSpecies", group=SpeciesGroup.mammals)
    obs = _create_observation(
        db,
        author_id=author.id,
        species_id=species.id,
        group=SpeciesGroup.mammals.value,
        status=ObservationStatus.needs_data,
    )
    eco_token = make_token(
        external_id="val-request-eco",
        name="Val Eco",
        email="val-request-eco@nlmk.com",
        role="ecologist",
    )

    response = client.post(
        f"/api/validation/{obs.id}/request-data",
        json={"comment": "still need more info"},
        headers={"Authorization": f"Bearer {eco_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == ObservationStatus.needs_data.value

    notifications_count = (
        db.query(Notification)
        .filter(
            Notification.observation_id == obs.id,
            Notification.type == NotificationType.needs_data,
        )
        .count()
    )
    assert notifications_count == 0
