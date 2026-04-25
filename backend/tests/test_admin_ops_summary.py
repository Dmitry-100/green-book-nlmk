import csv
import io
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


def test_admin_catalog_quality_requires_admin(client, employee_token):
    response = client.get(
        "/api/admin/catalog/quality",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


def test_admin_catalog_quality_returns_review_candidates(client, db, admin_token):
    exact_bird = Species(
        name_ru="Quality exact bird",
        name_latin="Parus major",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.typical,
        photo_urls=["https://example.com/parus.jpg"],
        description=(
            "Complete species card with enough editorial detail to pass the "
            "short-description threshold for the admin quality queue. It also "
            "mentions field marks, habitat context, and seasonal behavior."
        ),
        audio_url="/api/media/species-audio/parus-major.ogg",
    )
    genus_plant = Species(
        name_ru="Quality genus plant",
        name_latin="Acer",
        group=SpeciesGroup.plants,
        category=SpeciesCategory.typical,
        description="Needs taxonomy review, but has text.",
    )
    family_insect = Species(
        name_ru="Quality family insect",
        name_latin="Formicidae",
        group=SpeciesGroup.insects,
        category=SpeciesCategory.typical,
        photo_urls=["https://example.com/formicidae.jpg"],
        description=" ",
        audio_url="/api/media/species-audio/formicidae.ogg",
    )
    db.add_all([exact_bird, genus_plant, family_insect])
    db.commit()
    db.refresh(genus_plant)
    db.refresh(family_insect)

    response = client.get(
        "/api/admin/catalog/quality?limit=50",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "generated_at" in payload
    assert payload["species_total"] == 3
    assert payload["latin_name_exact_species"] == 1
    assert payload["latin_name_needs_review"] == 2
    assert payload["latin_name_suspicious_chars"] == 0
    assert payload["latin_name_needs_review_by_group"] == {
        "insects": 1,
        "plants": 1,
    }
    assert payload["content_gap_counts"] == {
        "missing_photo": 1,
        "missing_description": 1,
        "missing_audio": 1,
        "short_description": 1,
    }
    assert payload["latin_name_needs_review_examples"] == [
        {
            "id": genus_plant.id,
            "name_ru": "Quality genus plant",
            "name_latin": "Acer",
            "group": "plants",
        },
        {
            "id": family_insect.id,
            "name_ru": "Quality family insect",
            "name_latin": "Formicidae",
            "group": "insects",
        },
    ]


def test_admin_catalog_export_requires_admin(client, employee_token):
    response = client.get(
        "/api/admin/catalog/export",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


def test_admin_catalog_export_returns_needs_review_csv(client, db, admin_token):
    exact_bird = Species(
        name_ru="Export exact bird",
        name_latin="Parus major",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.typical,
        photo_urls=["https://example.com/bird.jpg"],
        audio_url="https://example.com/bird.mp3",
    )
    genus_plant = Species(
        name_ru="Export genus plant",
        name_latin="Acer",
        group=SpeciesGroup.plants,
        category=SpeciesCategory.rare,
        conservation_status="Нужна проверка",
        season_info="Май-июнь",
        biotopes="Лесополосы",
        description="Кандидат на уточнение",
        do_dont_rules="Проверить видовой эпитет",
    )
    db.add_all([exact_bird, genus_plant])
    db.commit()
    db.refresh(genus_plant)

    response = client.get(
        "/api/admin/catalog/export?needs_review=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "species-catalog-needs-review.csv" in response.headers[
        "content-disposition"
    ]

    csv_text = response.text.lstrip("\ufeff")
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert rows == [
        {
            "id": str(genus_plant.id),
            "name_ru": "Export genus plant",
            "name_latin": "Acer",
            "group": "plants",
            "category": "rare",
            "conservation_status": "Нужна проверка",
            "season_info": "Май-июнь",
            "biotopes": "Лесополосы",
            "description": "Кандидат на уточнение",
            "do_dont_rules": "Проверить видовой эпитет",
            "is_poisonous": "false",
            "latin_name_quality": "needs_review",
            "latin_name_suspicious_chars": "false",
            "photo_urls": "",
            "audio_url": "",
            "audio_title": "",
            "audio_source": "",
            "audio_license": "",
        }
    ]


def test_admin_catalog_export_returns_quality_gap_csv(client, db, admin_token):
    complete = Species(
        name_ru="Export complete bird",
        name_latin="Parus major",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.typical,
        photo_urls=["https://example.com/bird.jpg"],
        description=(
            "Complete species card with enough editorial detail to pass the "
            "short-description threshold for the admin quality queue. It also "
            "mentions field marks, habitat context, and seasonal behavior."
        ),
        audio_url="https://example.com/bird.mp3",
    )
    missing_photo = Species(
        name_ru="Export missing photo",
        name_latin="Acer platanoides",
        group=SpeciesGroup.plants,
        category=SpeciesCategory.typical,
        description=(
            "Complete species card with enough editorial detail to pass the "
            "short-description threshold for the admin quality queue. It also "
            "mentions field marks, habitat context, and seasonal behavior."
        ),
        audio_url="https://example.com/acer.mp3",
    )
    missing_description = Species(
        name_ru="Export missing description",
        name_latin="Formica rufa",
        group=SpeciesGroup.insects,
        category=SpeciesCategory.typical,
        photo_urls=["https://example.com/formica.jpg"],
        description=" ",
        audio_url="https://example.com/formica.mp3",
    )
    short_description = Species(
        name_ru="Export short description",
        name_latin="Vulpes vulpes",
        group=SpeciesGroup.mammals,
        category=SpeciesCategory.typical,
        photo_urls=["https://example.com/vulpes.jpg"],
        description="Очень коротко.",
        audio_url="https://example.com/vulpes.mp3",
    )
    db.add_all([complete, missing_photo, missing_description, short_description])
    db.commit()
    db.refresh(missing_photo)
    db.refresh(short_description)

    response = client.get(
        "/api/admin/catalog/export?quality_gap=missing_photo",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert "species-catalog-missing-photo.csv" in response.headers[
        "content-disposition"
    ]
    rows = list(csv.DictReader(io.StringIO(response.text.lstrip("\ufeff"))))
    assert [row["id"] for row in rows] == [str(missing_photo.id)]
    assert rows[0]["name_ru"] == "Export missing photo"

    short_response = client.get(
        "/api/admin/catalog/export?quality_gap=short_description",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert short_response.status_code == 200
    assert "species-catalog-short-description.csv" in short_response.headers[
        "content-disposition"
    ]
    short_rows = list(
        csv.DictReader(io.StringIO(short_response.text.lstrip("\ufeff")))
    )
    assert [row["id"] for row in short_rows] == [str(short_description.id)]


def test_admin_catalog_export_rejects_unknown_quality_gap(client, admin_token):
    response = client.get(
        "/api/admin/catalog/export?quality_gap=unknown",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_admin_ops_summary_returns_expected_sections(client, db, admin_token):
    reset_request_metrics()

    author = _create_user(db, external_id="ops-author-001", email="ops-author-001@nlmk.com")
    species = Species(
        name_ru="Ops species",
        name_latin="Parus major",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.typical,
    )
    db.add_all(
        [
            species,
            Species(
                name_ru="Ops genus plant",
                name_latin="Acer",
                group=SpeciesGroup.plants,
                category=SpeciesCategory.typical,
            ),
            Species(
                name_ru="Ops family insect",
                name_latin="Formicidae",
                group=SpeciesGroup.insects,
                category=SpeciesCategory.typical,
            ),
            Species(
                name_ru="Ops suspicious plant",
                name_latin="Еryngium",
                group=SpeciesGroup.plants,
                category=SpeciesCategory.typical,
            ),
        ]
    )
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
    assert payload["catalog"]["latin_name_exact_species"] == 1
    assert payload["catalog"]["latin_name_needs_review"] == 3
    assert payload["catalog"]["latin_name_suspicious_chars"] == 1
    assert payload["catalog"]["latin_name_needs_review_by_group"] == {
        "insects": 1,
        "plants": 2,
    }
    assert payload["catalog"]["content_gap_counts"] == {
        "missing_photo": 4,
        "missing_description": 4,
        "missing_audio": 4,
        "short_description": 0,
    }
    example = payload["catalog"]["latin_name_needs_review_examples"][0]
    assert example["id"] > 0
    assert example == {
        "id": example["id"],
        "name_ru": "Ops genus plant",
        "name_latin": "Acer",
        "group": "plants",
    }
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
