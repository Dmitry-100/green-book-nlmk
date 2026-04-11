from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement

from app.models.gamification import UserPoints
from app.models.observation import Observation, ObservationStatus, SensitiveLevel
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


def _create_species(db, *, latin: str, group: SpeciesGroup, category: SpeciesCategory = SpeciesCategory.typical) -> Species:
    species = Species(
        name_ru=f"Species {latin}",
        name_latin=latin,
        group=group,
        category=category,
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
    status: ObservationStatus = ObservationStatus.on_review,
) -> Observation:
    obs = Observation(
        author_id=author_id,
        species_id=species_id,
        group=group,
        observed_at=datetime.now(timezone.utc),
        location_point=WKTElement("POINT(39.61 52.58)", srid=4326),
        status=status,
        comment="validation flow test",
        is_incident=False,
        safety_checked=True,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


def test_confirm_is_idempotent_and_awards_points_once(client, db):
    author = _create_user(db, external_id="val-author-001", email="val-author-001@nlmk.com")
    species = _create_species(
        db,
        latin="ValSpeciesOne",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.rare,
    )
    obs = _create_observation(
        db,
        author_id=author.id,
        species_id=species.id,
        group=SpeciesGroup.birds.value,
    )
    eco_token = make_token(
        external_id="val-eco-001",
        name="Val Eco",
        email="val-eco-001@nlmk.com",
        role="ecologist",
    )
    headers = {"Authorization": f"Bearer {eco_token}"}

    first_confirm = client.post(f"/api/validation/{obs.id}/confirm", json={}, headers=headers)
    assert first_confirm.status_code == 200

    second_confirm = client.post(f"/api/validation/{obs.id}/confirm", json={}, headers=headers)
    assert second_confirm.status_code == 200

    points_rows = db.query(UserPoints).filter(UserPoints.observation_id == obs.id).all()
    assert len(points_rows) == 1


def test_reject_after_confirm_returns_conflict(client, db):
    author = _create_user(db, external_id="val-author-002", email="val-author-002@nlmk.com")
    species = _create_species(db, latin="ValSpeciesTwo", group=SpeciesGroup.plants)
    obs = _create_observation(
        db,
        author_id=author.id,
        species_id=species.id,
        group=SpeciesGroup.plants.value,
    )
    eco_token = make_token(
        external_id="val-eco-002",
        name="Val Eco",
        email="val-eco-002@nlmk.com",
        role="ecologist",
    )
    headers = {"Authorization": f"Bearer {eco_token}"}

    confirm_response = client.post(
        f"/api/validation/{obs.id}/confirm",
        json={"sensitive_level": SensitiveLevel.open.value},
        headers=headers,
    )
    assert confirm_response.status_code == 200

    reject_response = client.post(
        f"/api/validation/{obs.id}/reject",
        json={"comment": "too late"},
        headers=headers,
    )
    assert reject_response.status_code == 409

    request_data_response = client.post(
        f"/api/validation/{obs.id}/request-data",
        json={"comment": "need more details"},
        headers=headers,
    )
    assert request_data_response.status_code == 409


def test_confirm_updates_group_from_selected_species(client, db):
    author = _create_user(db, external_id="val-author-003", email="val-author-003@nlmk.com")
    initial_species = _create_species(db, latin="ValSpeciesThree", group=SpeciesGroup.plants)
    target_species = _create_species(db, latin="ValSpeciesFour", group=SpeciesGroup.birds)
    obs = _create_observation(
        db,
        author_id=author.id,
        species_id=initial_species.id,
        group=SpeciesGroup.plants.value,
    )
    eco_token = make_token(
        external_id="val-eco-003",
        name="Val Eco",
        email="val-eco-003@nlmk.com",
        role="ecologist",
    )
    headers = {"Authorization": f"Bearer {eco_token}"}

    response = client.post(
        f"/api/validation/{obs.id}/confirm",
        json={
            "species_id": target_species.id,
            "comment": "species corrected",
            "sensitive_level": SensitiveLevel.blurred.value,
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["species_id"] == target_species.id
    assert data["group"] == SpeciesGroup.birds.value

    db.refresh(obs)
    assert obs.species_id == target_species.id
    assert obs.group == SpeciesGroup.birds.value


def test_validation_rejects_blank_or_too_long_comments(client, db):
    author = _create_user(db, external_id="val-author-004", email="val-author-004@nlmk.com")
    species = _create_species(db, latin="ValSpeciesFive", group=SpeciesGroup.insects)
    obs = _create_observation(
        db,
        author_id=author.id,
        species_id=species.id,
        group=SpeciesGroup.insects.value,
    )
    eco_token = make_token(
        external_id="val-eco-004",
        name="Val Eco",
        email="val-eco-004@nlmk.com",
        role="ecologist",
    )
    headers = {"Authorization": f"Bearer {eco_token}"}

    blank_comment_response = client.post(
        f"/api/validation/{obs.id}/request-data",
        json={"comment": "   "},
        headers=headers,
    )
    assert blank_comment_response.status_code == 422

    too_long_comment_response = client.post(
        f"/api/validation/{obs.id}/reject",
        json={"comment": "x" * 2001},
        headers=headers,
    )
    assert too_long_comment_response.status_code == 422


def test_confirm_rejects_invalid_species_id(client, db):
    author = _create_user(db, external_id="val-author-005", email="val-author-005@nlmk.com")
    obs = _create_observation(
        db,
        author_id=author.id,
        species_id=None,
        group=SpeciesGroup.fungi.value,
    )
    eco_token = make_token(
        external_id="val-eco-005",
        name="Val Eco",
        email="val-eco-005@nlmk.com",
        role="ecologist",
    )
    headers = {"Authorization": f"Bearer {eco_token}"}

    response = client.post(
        f"/api/validation/{obs.id}/confirm",
        json={"species_id": 0},
        headers=headers,
    )
    assert response.status_code == 422


def test_validation_queue_cache_invalidates_on_status_change(client, db):
    author = _create_user(db, external_id="val-author-006", email="val-author-006@nlmk.com")
    species = _create_species(db, latin="ValSpeciesSix", group=SpeciesGroup.birds)
    obs = _create_observation(
        db,
        author_id=author.id,
        species_id=species.id,
        group=SpeciesGroup.birds.value,
        status=ObservationStatus.on_review,
    )
    eco_token = make_token(
        external_id="val-eco-006",
        name="Val Eco",
        email="val-eco-006@nlmk.com",
        role="ecologist",
    )
    headers = {"Authorization": f"Bearer {eco_token}"}

    on_review_before = client.get("/api/validation/queue?status=on_review", headers=headers)
    assert on_review_before.status_code == 200
    assert any(item["id"] == obs.id for item in on_review_before.json()["items"])

    request_data_response = client.post(
        f"/api/validation/{obs.id}/request-data",
        json={"comment": "need clearer photo"},
        headers=headers,
    )
    assert request_data_response.status_code == 200

    on_review_after = client.get("/api/validation/queue?status=on_review", headers=headers)
    assert on_review_after.status_code == 200
    assert all(item["id"] != obs.id for item in on_review_after.json()["items"])

    needs_data_queue = client.get("/api/validation/queue?status=needs_data", headers=headers)
    assert needs_data_queue.status_code == 200
    assert any(item["id"] == obs.id for item in needs_data_queue.json()["items"])


def test_validation_queue_include_total_false_uses_separate_cache_key(client, db):
    author = _create_user(db, external_id="val-author-007", email="val-author-007@nlmk.com")
    species = _create_species(db, latin="ValSpeciesSeven", group=SpeciesGroup.birds)
    _create_observation(
        db,
        author_id=author.id,
        species_id=species.id,
        group=SpeciesGroup.birds.value,
        status=ObservationStatus.on_review,
    )
    eco_token = make_token(
        external_id="val-eco-007",
        name="Val Eco",
        email="val-eco-007@nlmk.com",
        role="ecologist",
    )
    headers = {"Authorization": f"Bearer {eco_token}"}

    without_total = client.get(
        "/api/validation/queue?status=on_review&limit=37&include_total=false",
        headers=headers,
    )
    assert without_total.status_code == 200
    without_total_data = without_total.json()
    assert len(without_total_data["items"]) >= 1
    assert without_total_data["total"] is None

    with_total = client.get("/api/validation/queue?status=on_review&limit=37", headers=headers)
    assert with_total.status_code == 200
    with_total_data = with_total.json()
    assert len(with_total_data["items"]) >= 1
    assert with_total_data["total"] >= 1


def test_validation_invalidates_author_unread_count_cache(client, db):
    author = _create_user(db, external_id="val-author-008", email="val-author-008@nlmk.com")
    species = _create_species(db, latin="ValSpeciesEight", group=SpeciesGroup.plants)
    obs = _create_observation(
        db,
        author_id=author.id,
        species_id=species.id,
        group=SpeciesGroup.plants.value,
        status=ObservationStatus.on_review,
    )
    eco_token = make_token(
        external_id="val-eco-008",
        name="Val Eco",
        email="val-eco-008@nlmk.com",
        role="ecologist",
    )
    author_token = make_token(
        external_id=author.external_id,
        name=author.display_name,
        email=author.email,
        role=author.role.value,
    )
    eco_headers = {"Authorization": f"Bearer {eco_token}"}
    author_headers = {"Authorization": f"Bearer {author_token}"}

    unread_before = client.get("/api/notifications/unread-count", headers=author_headers)
    assert unread_before.status_code == 200
    assert unread_before.json()["count"] == 0

    confirm_response = client.post(
        f"/api/validation/{obs.id}/confirm",
        json={},
        headers=eco_headers,
    )
    assert confirm_response.status_code == 200

    unread_after = client.get("/api/notifications/unread-count", headers=author_headers)
    assert unread_after.status_code == 200
    assert unread_after.json()["count"] == 1
