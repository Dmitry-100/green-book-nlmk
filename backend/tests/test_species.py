from app.models.audit_log import AuditLog
from app.models.species import Species, SpeciesGroup, SpeciesCategory


def test_list_species_empty(client):
    response = client.get("/api/species")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_species_with_group_filter(client, db):
    db.add(Species(name_ru="Полынь", name_latin="Artemisia vulgaris", group=SpeciesGroup.plants, category=SpeciesCategory.ruderal))
    db.add(Species(name_ru="Сорока", name_latin="Pica pica", group=SpeciesGroup.birds, category=SpeciesCategory.synanthropic))
    db.commit()

    response = client.get("/api/species?group=plants")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name_latin"] == "Artemisia vulgaris"


def test_list_species_with_audio_filter(client, db):
    db.add(
        Species(
            name_ru="Большая синица",
            name_latin="Parus major",
            group=SpeciesGroup.birds,
            category=SpeciesCategory.synanthropic,
            audio_url="/api/media/species-audio/parus-major.ogg",
        )
    )
    db.add(
        Species(
            name_ru="Полынь",
            name_latin="Artemisia vulgaris",
            group=SpeciesGroup.plants,
            category=SpeciesCategory.ruderal,
        )
    )
    db.commit()

    response = client.get("/api/species?has_audio=true")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name_latin"] == "Parus major"


def test_list_species_with_quality_gap_filters(client, db):
    db.add(
        Species(
            name_ru="Большая синица",
            name_latin="Parus major",
            group=SpeciesGroup.birds,
            category=SpeciesCategory.typical,
            photo_urls=["https://example.com/parus.jpg"],
            description=(
                "Подробное описание вида для редакционной карточки, "
                "которое заметно длиннее минимального порога и помогает "
                "пользователю понять признаки, местообитания и сезонность."
            ),
            audio_url="/api/media/species-audio/parus-major.ogg",
        )
    )
    db.add(
        Species(
            name_ru="Без фото",
            name_latin="Missing photo",
            group=SpeciesGroup.plants,
            category=SpeciesCategory.typical,
            description=(
                "Подробное описание вида для редакционной карточки, "
                "которое заметно длиннее минимального порога и помогает "
                "пользователю понять признаки, местообитания и сезонность."
            ),
            audio_url="/api/media/species-audio/example.ogg",
        )
    )
    db.add(
        Species(
            name_ru="Без описания",
            name_latin="Missing description",
            group=SpeciesGroup.fungi,
            category=SpeciesCategory.typical,
            photo_urls=["https://example.com/fungi.jpg"],
            audio_url="/api/media/species-audio/example.ogg",
        )
    )
    db.add(
        Species(
            name_ru="Без аудио",
            name_latin="Missing audio",
            group=SpeciesGroup.mammals,
            category=SpeciesCategory.typical,
            photo_urls=["https://example.com/mammal.jpg"],
            description=(
                "Подробное описание вида для редакционной карточки, "
                "которое заметно длиннее минимального порога и помогает "
                "пользователю понять признаки, местообитания и сезонность."
            ),
        )
    )
    db.add(
        Species(
            name_ru="Короткое описание",
            name_latin="Short description",
            group=SpeciesGroup.birds,
            category=SpeciesCategory.typical,
            photo_urls=["https://example.com/short.jpg"],
            description="Слишком кратко.",
            audio_url="/api/media/species-audio/short.ogg",
        )
    )
    db.add(
        Species(
            name_ru="Полное описание",
            name_latin="Complete description",
            group=SpeciesGroup.birds,
            category=SpeciesCategory.typical,
            photo_urls=["https://example.com/full.jpg"],
            description=(
                "Подробное описание вида для редакционной карточки, "
                "которое заметно длиннее минимального порога и помогает "
                "пользователю понять признаки, местообитания и сезонность."
            ),
            audio_url="/api/media/species-audio/full.ogg",
        )
    )
    db.commit()

    missing_photo = client.get("/api/species?quality_gap=missing_photo&limit=200")
    missing_description = client.get(
        "/api/species?quality_gap=missing_description&limit=200"
    )
    missing_audio = client.get("/api/species?quality_gap=missing_audio&limit=200")
    short_description = client.get(
        "/api/species?quality_gap=short_description&limit=200"
    )

    assert missing_photo.status_code == 200
    assert [item["name_latin"] for item in missing_photo.json()["items"]] == [
        "Missing photo"
    ]
    assert [item["name_latin"] for item in missing_description.json()["items"]] == [
        "Missing description"
    ]
    assert [item["name_latin"] for item in missing_audio.json()["items"]] == [
        "Missing audio"
    ]
    assert [item["name_latin"] for item in short_description.json()["items"]] == [
        "Short description"
    ]


def test_species_quality_gap_rejects_unknown_value(client):
    response = client.get("/api/species?quality_gap=unknown")
    assert response.status_code == 422


def test_search_species(client, db):
    db.add(Species(name_ru="Лебедь-шипун", name_latin="Cygnus olor", group=SpeciesGroup.birds, category=SpeciesCategory.rare))
    db.commit()

    response = client.get("/api/species?search=лебедь")
    assert response.json()["total"] == 1

    response = client.get("/api/species?search=Cygnus")
    assert response.json()["total"] == 1

    response = client.get("/api/species?search=%20%20CYGNUS%20%20")
    assert response.json()["total"] == 1


def test_get_species_detail(client, db):
    sp = Species(name_ru="Ёж", name_latin="Erinaceus europaeus", group=SpeciesGroup.mammals, category=SpeciesCategory.typical)
    db.add(sp)
    db.commit()
    db.refresh(sp)

    response = client.get(f"/api/species/{sp.id}")
    assert response.status_code == 200
    assert response.json()["name_ru"] == "Ёж"


def test_get_species_not_found(client):
    response = client.get("/api/species/9999")
    assert response.status_code == 404


def test_create_species_requires_admin(client, employee_token):
    response = client.post(
        "/api/species",
        json={"name_ru": "Test", "name_latin": "Test", "group": "plants", "category": "typical"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


def test_create_species_rejects_blank_name(client, admin_token):
    response = client.post(
        "/api/species",
        json={
            "name_ru": "   ",
            "name_latin": "Erinaceus europaeus",
            "group": "mammals",
            "category": "typical",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_species_rejects_invalid_photo_urls(client, admin_token):
    response = client.post(
        "/api/species",
        json={
            "name_ru": "Ёж",
            "name_latin": "Erinaceus europaeus",
            "group": "mammals",
            "category": "typical",
            "photo_urls": ["https://cdn.example.org/photo.jpg", "   "],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_create_species_accepts_audio_metadata(client, admin_token):
    response = client.post(
        "/api/species",
        json={
            "name_ru": "Большая синица",
            "name_latin": "Parus major",
            "group": "birds",
            "category": "synanthropic",
            "audio_url": "https://upload.wikimedia.org/wikipedia/commons/d/df/Parus_major.ogg",
            "audio_title": "Песня большой синицы",
            "audio_source": "Wikimedia Commons / Oona Raisanen",
            "audio_license": "Public domain",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["audio_url"].endswith("/Parus_major.ogg")
    assert data["audio_title"] == "Песня большой синицы"
    assert data["audio_source"] == "Wikimedia Commons / Oona Raisanen"
    assert data["audio_license"] == "Public domain"


def test_create_species_accepts_full_editorial_card(client, admin_token):
    response = client.post(
        "/api/species",
        json={
            "name_ru": "Большая синица",
            "name_latin": "Parus major",
            "group": "birds",
            "category": "synanthropic",
            "conservation_status": "Обычный вид",
            "is_poisonous": False,
            "season_info": "Апрель-июнь",
            "biotopes": "Парки и лесополосы",
            "description": "Обычная птица промплощадки.",
            "do_dont_rules": "Не тревожить гнездо.",
            "photo_urls": ["https://example.com/parus.jpg"],
            "audio_url": "/api/media/species-audio/parus-major.ogg",
            "audio_title": "Голос большой синицы",
            "audio_source": "Wikimedia Commons",
            "audio_license": "CC BY",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name_ru"] == "Большая синица"
    assert data["conservation_status"] == "Обычный вид"
    assert data["season_info"] == "Апрель-июнь"
    assert data["biotopes"] == "Парки и лесополосы"
    assert data["description"] == "Обычная птица промплощадки."
    assert data["do_dont_rules"] == "Не тревожить гнездо."
    assert data["photo_urls"] == ["https://example.com/parus.jpg"]
    assert data["audio_url"] == "/api/media/species-audio/parus-major.ogg"


def test_create_species_rejects_invalid_audio_url(client, admin_token):
    response = client.post(
        "/api/species",
        json={
            "name_ru": "Серая неясыть",
            "name_latin": "Strix aluco",
            "group": "birds",
            "category": "red_book",
            "audio_url": "ftp://example.org/owl.ogg",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 422


def test_update_species_accepts_editorial_fields(client, db, admin_token):
    species = Species(
        name_ru="Синица",
        name_latin="Parus",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.synanthropic,
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    response = client.put(
        f"/api/species/{species.id}",
        json={
            "name_ru": "Большая синица",
            "name_latin": "Parus major",
            "season_info": "Апрель-июнь",
            "biotopes": "Парки и лесополосы",
            "description": "Обычный синантропный вид.",
            "do_dont_rules": "Не тревожить гнездо.",
            "photo_urls": ["https://example.com/parus.jpg"],
            "audio_url": "/api/media/species-audio/parus-major.ogg",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name_ru"] == "Большая синица"
    assert data["name_latin"] == "Parus major"
    assert data["season_info"] == "Апрель-июнь"
    assert data["biotopes"] == "Парки и лесополосы"
    assert data["description"] == "Обычный синантропный вид."
    assert data["do_dont_rules"] == "Не тревожить гнездо."
    assert data["photo_urls"] == ["https://example.com/parus.jpg"]
    assert data["audio_url"] == "/api/media/species-audio/parus-major.ogg"

    audit_log = (
        db.query(AuditLog)
        .filter(AuditLog.action == "species.update")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit_log is not None
    assert audit_log.target_id == species.id
    assert audit_log.details["updated_fields"] == [
        "audio_url",
        "biotopes",
        "description",
        "do_dont_rules",
        "name_latin",
        "name_ru",
        "photo_urls",
        "season_info",
    ]


def test_species_search_rejects_too_long_query(client):
    response = client.get(f"/api/species?search={'a' * 101}")
    assert response.status_code == 422


def test_species_list_cache_invalidates_after_create(client, admin_token):
    first_list = client.get("/api/species?limit=200")
    assert first_list.status_code == 200
    assert first_list.json()["total"] == 0

    create_response = client.post(
        "/api/species",
        json={
            "name_ru": "Аист",
            "name_latin": "Ciconia ciconia",
            "group": "birds",
            "category": "typical",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201

    second_list = client.get("/api/species?limit=200")
    assert second_list.status_code == 200
    assert second_list.json()["total"] == 1


def test_species_list_include_total_false_uses_separate_cache_key(client, db):
    db.add(
        Species(
            name_ru="Лисица",
            name_latin="Vulpes vulpes",
            group=SpeciesGroup.mammals,
            category=SpeciesCategory.typical,
        )
    )
    db.commit()

    without_total = client.get("/api/species?group=mammals&limit=200&include_total=false")
    assert without_total.status_code == 200
    without_total_data = without_total.json()
    assert len(without_total_data["items"]) == 1
    assert without_total_data["total"] is None

    with_total = client.get("/api/species?group=mammals&limit=200")
    assert with_total.status_code == 200
    with_total_data = with_total.json()
    assert len(with_total_data["items"]) == 1
    assert with_total_data["total"] == 1
