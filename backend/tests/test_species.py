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
