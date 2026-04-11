from app.models.species import Species, SpeciesCategory, SpeciesGroup


def test_identifier_tree_rejects_unknown_group(client):
    response = client.get("/api/identifier/tree?group=unknown")
    assert response.status_code == 422


def test_identifier_tree_accepts_valid_group(client):
    response = client.get("/api/identifier/tree?group=birds")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_identifier_suggest_rejects_empty_species_ids(client):
    response = client.post("/api/identifier/suggest", json={"species_ids": []})
    assert response.status_code == 422


def test_identifier_suggest_rejects_duplicate_species_ids(client):
    response = client.post("/api/identifier/suggest", json={"species_ids": [1, 1]})
    assert response.status_code == 422


def test_identifier_suggest_accepts_valid_species_ids(client, db):
    species = Species(
        name_ru="Query validation species",
        name_latin="Query validation species latin",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.typical,
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    response = client.post(
        "/api/identifier/suggest",
        json={"species_ids": [species.id]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == species.id


def test_export_observations_rejects_unknown_group(client, ecologist_token):
    response = client.get(
        "/api/export/observations?group=unknown",
        headers={"Authorization": f"Bearer {ecologist_token}"},
    )
    assert response.status_code == 422


def test_export_observations_accepts_valid_group(client, ecologist_token):
    response = client.get(
        "/api/export/observations?group=birds",
        headers={"Authorization": f"Bearer {ecologist_token}"},
    )
    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in (
        response.headers.get("content-type", "")
    )
