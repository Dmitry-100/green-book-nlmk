from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement

from app.models.observation import Observation, ObservationStatus
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


def _create_observation(
    db,
    *,
    author_id: int,
    group: str,
    status: ObservationStatus,
    comment: str = "",
) -> Observation:
    obs = Observation(
        author_id=author_id,
        species_id=None,
        group=group,
        observed_at=datetime.now(timezone.utc),
        location_point=WKTElement("POINT(39.60 52.59)", srid=4326),
        status=status,
        comment=comment,
        is_incident=False,
        safety_checked=True,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


def test_list_observations_public_only_confirmed(client, db):
    author = _create_user(db, external_id="obs-access-author", email="obs-access-author@nlmk.com")
    _create_observation(
        db,
        author_id=author.id,
        group="birds",
        status=ObservationStatus.confirmed,
        comment="confirmed",
    )
    _create_observation(
        db,
        author_id=author.id,
        group="birds",
        status=ObservationStatus.on_review,
        comment="on_review",
    )

    public_response = client.get("/api/observations")
    assert public_response.status_code == 200
    public_data = public_response.json()
    assert public_data["total"] == 1
    assert all(item["status"] == "confirmed" for item in public_data["items"])

    forbidden_response = client.get("/api/observations?status=on_review")
    assert forbidden_response.status_code == 403

    eco_token = make_token(
        external_id="obs-eco-001",
        name="Obs Eco",
        email="obs-eco-001@nlmk.com",
        role="ecologist",
    )
    eco_response = client.get(
        "/api/observations?status=on_review",
        headers={"Authorization": f"Bearer {eco_token}"},
    )
    assert eco_response.status_code == 200
    eco_data = eco_response.json()
    assert eco_data["total"] >= 1
    assert any(item["status"] == "on_review" for item in eco_data["items"])


def test_non_confirmed_observation_details_are_restricted(client, db, employee_token):
    author = _create_user(db, external_id="test-user-001", email="test@nlmk.com")
    _create_user(db, external_id="obs-viewer-001", email="obs-viewer-001@nlmk.com")

    obs = _create_observation(
        db,
        author_id=author.id,
        group="plants",
        status=ObservationStatus.on_review,
        comment="private draft",
    )

    anonymous_response = client.get(f"/api/observations/{obs.id}")
    assert anonymous_response.status_code == 404

    other_token = make_token(
        external_id="obs-viewer-001",
        name="Other User",
        email="obs-viewer-001@nlmk.com",
        role="employee",
    )
    other_user_response = client.get(
        f"/api/observations/{obs.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_user_response.status_code == 404

    author_response = client.get(
        f"/api/observations/{obs.id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert author_response.status_code == 200
    assert author_response.json()["id"] == obs.id


def test_observation_lists_can_skip_total_count(client, db, employee_token):
    author = _create_user(db, external_id="test-user-001", email="test@nlmk.com")
    _create_observation(
        db,
        author_id=author.id,
        group="mammals",
        status=ObservationStatus.confirmed,
        comment="for include_total",
    )

    public_response = client.get("/api/observations?include_total=false")
    assert public_response.status_code == 200
    public_data = public_response.json()
    assert len(public_data["items"]) == 1
    assert public_data["total"] is None

    my_response = client.get(
        "/api/observations/my?include_total=false",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert my_response.status_code == 200
    my_data = my_response.json()
    assert len(my_data["items"]) == 1
    assert my_data["total"] is None


def test_list_observations_rejects_unknown_group_filter(client):
    response = client.get("/api/observations?group=unknown")
    assert response.status_code == 422
