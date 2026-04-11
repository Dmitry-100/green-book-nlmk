from datetime import datetime, timedelta, timezone

from geoalchemy2.elements import WKTElement

from app.models.observation import Observation, ObservationStatus, SensitiveLevel
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


def _create_observation(
    db,
    *,
    author_id: int,
    group: str,
    status: ObservationStatus,
    sensitive_level: SensitiveLevel,
    lat: float,
    lon: float,
    observed_at: datetime,
) -> Observation:
    obs = Observation(
        author_id=author_id,
        species_id=None,
        group=group,
        observed_at=observed_at,
        location_point=WKTElement(f"POINT({lon} {lat})", srid=4326),
        status=status,
        comment="map behavior test",
        is_incident=False,
        sensitive_level=sensitive_level,
        safety_checked=True,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


def test_map_observations_filters_hidden_and_rounds_blurred_points(client, db):
    author = _create_user(db, external_id="map-author-001")
    now = datetime.now(timezone.utc)
    open_obs = _create_observation(
        db,
        author_id=author.id,
        group="birds",
        status=ObservationStatus.confirmed,
        sensitive_level=SensitiveLevel.open,
        lat=52.591234,
        lon=39.601234,
        observed_at=now - timedelta(minutes=2),
    )
    blurred_obs = _create_observation(
        db,
        author_id=author.id,
        group="plants",
        status=ObservationStatus.confirmed,
        sensitive_level=SensitiveLevel.blurred,
        lat=52.594999,
        lon=39.604999,
        observed_at=now - timedelta(minutes=1),
    )
    _create_observation(
        db,
        author_id=author.id,
        group="mammals",
        status=ObservationStatus.confirmed,
        sensitive_level=SensitiveLevel.hidden,
        lat=52.599999,
        lon=39.609999,
        observed_at=now,
    )
    _create_observation(
        db,
        author_id=author.id,
        group="insects",
        status=ObservationStatus.on_review,
        sensitive_level=SensitiveLevel.open,
        lat=52.580001,
        lon=39.610001,
        observed_at=now,
    )

    response = client.get("/api/map/observations?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 2

    by_id = {
        feature["properties"]["id"]: feature
        for feature in payload["features"]
    }
    assert set(by_id.keys()) == {open_obs.id, blurred_obs.id}

    open_coordinates = by_id[open_obs.id]["geometry"]["coordinates"]
    assert open_coordinates[0] == 39.601234
    assert open_coordinates[1] == 52.591234

    blurred_coordinates = by_id[blurred_obs.id]["geometry"]["coordinates"]
    assert blurred_coordinates[0] == 39.6
    assert blurred_coordinates[1] == 52.59


def test_map_observations_non_confirmed_requires_ecologist_or_admin(client, db):
    author = _create_user(db, external_id="map-author-002")
    _create_observation(
        db,
        author_id=author.id,
        group="birds",
        status=ObservationStatus.on_review,
        sensitive_level=SensitiveLevel.open,
        lat=52.5901,
        lon=39.6001,
        observed_at=datetime.now(timezone.utc),
    )

    employee_token = make_token(
        external_id="map-employee-001",
        name="Map Employee",
        email="map-employee-001@nlmk.com",
        role="employee",
    )
    denied = client.get(
        "/api/map/observations?status=on_review",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert denied.status_code == 403

    eco_token = make_token(
        external_id="map-eco-001",
        name="Map Eco",
        email="map-eco-001@nlmk.com",
        role="ecologist",
    )
    allowed = client.get(
        "/api/map/observations?status=on_review",
        headers={"Authorization": f"Bearer {eco_token}"},
    )
    assert allowed.status_code == 200
    assert len(allowed.json()["features"]) == 1


def test_map_observations_rejects_invalid_bbox_edge_cases(client):
    lon_out_of_range = client.get("/api/map/observations?bbox=181,52.5,182,52.7")
    assert lon_out_of_range.status_code == 400
    assert lon_out_of_range.json()["detail"] == "bbox longitude out of range"

    lat_out_of_range = client.get("/api/map/observations?bbox=39.5,91,39.7,92")
    assert lat_out_of_range.status_code == 400
    assert lat_out_of_range.json()["detail"] == "bbox latitude out of range"

    invalid_bounds = client.get("/api/map/observations?bbox=39.7,52.7,39.5,52.5")
    assert invalid_bounds.status_code == 400
    assert invalid_bounds.json()["detail"] == "bbox bounds are invalid"

    non_numeric = client.get("/api/map/observations?bbox=39.5,abc,39.7,52.7")
    assert non_numeric.status_code == 400
    assert non_numeric.json()["detail"] == "Invalid bbox format"


def test_map_observations_limit_and_ordering(client, db):
    author = _create_user(db, external_id="map-author-003")
    now = datetime.now(timezone.utc)
    oldest = _create_observation(
        db,
        author_id=author.id,
        group="birds",
        status=ObservationStatus.confirmed,
        sensitive_level=SensitiveLevel.open,
        lat=52.5001,
        lon=39.5001,
        observed_at=now - timedelta(days=1),
    )
    newest = _create_observation(
        db,
        author_id=author.id,
        group="birds",
        status=ObservationStatus.confirmed,
        sensitive_level=SensitiveLevel.open,
        lat=52.5002,
        lon=39.5002,
        observed_at=now,
    )

    response = client.get("/api/map/observations?limit=1")
    assert response.status_code == 200
    features = response.json()["features"]
    assert len(features) == 1
    assert features[0]["properties"]["id"] == newest.id
    assert features[0]["properties"]["id"] != oldest.id
