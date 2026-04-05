from tests.conftest import make_token
from app.models.species import Species, SpeciesGroup, SpeciesCategory
from app.models.user import User, UserRole


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
