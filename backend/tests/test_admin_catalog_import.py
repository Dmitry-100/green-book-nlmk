from app.models.audit_log import AuditLog
from app.models.species import Species, SpeciesCategory, SpeciesGroup


def _csv_payload(rows: list[str]) -> str:
    header = (
        "id,name_ru,name_latin,group,category,conservation_status,is_poisonous,"
        "photo_urls,audio_url,audio_title,audio_source,audio_license,"
        "season_info,biotopes,description,do_dont_rules\n"
    )
    return header + "\n".join(rows) + "\n"


def test_admin_catalog_import_preview_requires_admin(client, employee_token):
    response = client.post(
        "/api/admin/catalog/import/preview",
        headers={"Authorization": f"Bearer {employee_token}"},
        files={
            "file": (
                "catalog.csv",
                _csv_payload([]),
                "text/csv",
            )
        },
    )
    assert response.status_code == 403


def test_admin_catalog_import_preview_reports_changes_without_mutating_db(
    client,
    db,
    admin_token,
):
    species = Species(
        name_ru="Preview plant",
        name_latin="Acer",
        group=SpeciesGroup.plants,
        category=SpeciesCategory.rare,
        conservation_status=None,
        is_poisonous=False,
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    response = client.post(
        "/api/admin/catalog/import/preview",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "catalog.csv",
                _csv_payload(
                    [
                        (
                            f"{species.id},Preview plant,Acer platanoides,plants,"
                            "typical,Проверено экспертом,true,"
                            "https://example.com/acer.jpg,,,,"
                        ),
                    ]
                ),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "catalog.csv"
    assert payload["dry_run"] is True
    assert payload["total_rows"] == 1
    assert payload["changed_rows"] == 1
    assert payload["error_rows"] == 0
    assert payload["errors"] == []
    assert payload["changes"] == [
        {
            "row": 2,
            "id": species.id,
            "name_ru": "Preview plant",
            "changed_fields": [
                "name_latin",
                "category",
                "conservation_status",
                "is_poisonous",
                "photo_urls",
            ],
            "before": {
                "name_latin": "Acer",
                "category": "rare",
                "conservation_status": None,
                "is_poisonous": False,
                "photo_urls": None,
            },
            "after": {
                "name_latin": "Acer platanoides",
                "category": "typical",
                "conservation_status": "Проверено экспертом",
                "is_poisonous": True,
                "photo_urls": ["https://example.com/acer.jpg"],
            },
        }
    ]

    db.refresh(species)
    assert species.name_latin == "Acer"
    assert species.category == SpeciesCategory.rare
    assert species.conservation_status is None
    assert species.is_poisonous is False
    assert species.photo_urls is None


def test_admin_catalog_import_preview_reports_row_errors(client, db, admin_token):
    species = Species(
        name_ru="Preview insect",
        name_latin="Pieris",
        group=SpeciesGroup.insects,
        category=SpeciesCategory.typical,
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    response = client.post(
        "/api/admin/catalog/import/preview",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "catalog.csv",
                _csv_payload(
                    [
                        f"{species.id},Preview insect,Pieris brassicae,insects,bad,,,,,,,",
                        "999,Missing species,Parus major,birds,typical,,,,,,,",
                    ]
                ),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 2
    assert payload["changed_rows"] == 0
    assert payload["error_rows"] == 2
    assert payload["changes"] == []
    assert payload["errors"] == [
        {
            "row": 2,
            "id": str(species.id),
            "errors": ["Invalid category: bad"],
        },
        {
            "row": 3,
            "id": "999",
            "errors": ["Species not found"],
        },
    ]


def test_admin_catalog_import_preview_accepts_editorial_fields(client, db, admin_token):
    species = Species(
        name_ru="Editorial bird",
        name_latin="Parus",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.synanthropic,
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    response = client.post(
        "/api/admin/catalog/import/preview",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "catalog.csv",
                _csv_payload(
                    [
                        (
                            f"{species.id},Editorial bird,Parus major,birds,"
                            "synanthropic,,false,,,,,,"
                            "Апрель-август,Парки и опушки,"
                            "Обычная птица промплощадки,Не тревожить гнездо"
                        ),
                    ]
                ),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["error_rows"] == 0
    assert payload["changes"] == [
        {
            "row": 2,
            "id": species.id,
            "name_ru": "Editorial bird",
            "changed_fields": [
                "name_latin",
                "season_info",
                "biotopes",
                "description",
                "do_dont_rules",
            ],
            "before": {
                "name_latin": "Parus",
                "season_info": None,
                "biotopes": None,
                "description": None,
                "do_dont_rules": None,
            },
            "after": {
                "name_latin": "Parus major",
                "season_info": "Апрель-август",
                "biotopes": "Парки и опушки",
                "description": "Обычная птица промплощадки",
                "do_dont_rules": "Не тревожить гнездо",
            },
        }
    ]


def test_admin_catalog_import_apply_updates_species_and_writes_audit(
    client,
    db,
    admin_token,
):
    species = Species(
        name_ru="Apply plant",
        name_latin="Acer",
        group=SpeciesGroup.plants,
        category=SpeciesCategory.rare,
        is_poisonous=False,
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    response = client.post(
        "/api/admin/catalog/import/apply",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "catalog.csv",
                _csv_payload(
                    [
                        (
                            f"{species.id},Apply plant,Acer platanoides,plants,"
                            "typical,Проверено экспертом,true,"
                            "https://example.com/acer.jpg,,,,"
                        ),
                    ]
                ),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run"] is False
    assert payload["batch_id"] > 0
    assert payload["applied_rows"] == 1
    assert payload["changed_rows"] == 1
    assert payload["error_rows"] == 0

    db.refresh(species)
    assert species.name_latin == "Acer platanoides"
    assert species.category == SpeciesCategory.typical
    assert species.conservation_status == "Проверено экспертом"
    assert species.is_poisonous is True
    assert species.photo_urls == ["https://example.com/acer.jpg"]

    audit_log = (
        db.query(AuditLog)
        .filter(AuditLog.action == "admin.catalog_import_apply")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit_log is not None
    assert audit_log.target_type == "species"
    assert audit_log.details["filename"] == "catalog.csv"
    assert audit_log.details["applied_rows"] == 1
    assert audit_log.details["changed_rows"] == 1


def test_admin_catalog_import_batches_require_admin(client, employee_token):
    response = client.get(
        "/api/admin/catalog/import/batches",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


def test_admin_catalog_import_batch_can_be_rolled_back(client, db, admin_token):
    species = Species(
        name_ru="Rollback plant",
        name_latin="Acer",
        group=SpeciesGroup.plants,
        category=SpeciesCategory.rare,
        is_poisonous=False,
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    apply_response = client.post(
        "/api/admin/catalog/import/apply",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "catalog.csv",
                _csv_payload(
                    [
                        (
                            f"{species.id},Rollback plant,Acer platanoides,plants,"
                            "typical,Проверено экспертом,true,"
                            "https://example.com/acer.jpg,,,,"
                        ),
                    ]
                ),
                "text/csv",
            )
        },
    )
    assert apply_response.status_code == 200
    batch_id = apply_response.json()["batch_id"]

    list_response = client.get(
        "/api/admin/catalog/import/batches",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["id"] == batch_id
    assert list_payload["items"][0]["status"] == "applied"
    assert list_payload["items"][0]["filename"] == "catalog.csv"
    assert list_payload["items"][0]["changed_rows"] == 1

    rollback_response = client.post(
        f"/api/admin/catalog/import/batches/{batch_id}/rollback",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert rollback_response.status_code == 200
    assert rollback_response.json()["status"] == "rolled_back"
    assert rollback_response.json()["rolled_back_rows"] == 1

    db.refresh(species)
    assert species.name_latin == "Acer"
    assert species.category == SpeciesCategory.rare
    assert species.conservation_status is None
    assert species.is_poisonous is False
    assert species.photo_urls is None

    second_rollback = client.post(
        f"/api/admin/catalog/import/batches/{batch_id}/rollback",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert second_rollback.status_code == 409
    assert second_rollback.json()["detail"] == "Batch is not applied"


def test_admin_catalog_import_batch_detail_returns_changes(client, db, admin_token):
    species = Species(
        name_ru="Detail plant",
        name_latin="Acer",
        group=SpeciesGroup.plants,
        category=SpeciesCategory.rare,
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    apply_response = client.post(
        "/api/admin/catalog/import/apply",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "catalog.csv",
                _csv_payload(
                    [
                        (
                            f"{species.id},Detail plant,Acer platanoides,plants,"
                            "typical,,false,,,,,"
                        ),
                    ]
                ),
                "text/csv",
            )
        },
    )
    assert apply_response.status_code == 200
    batch_id = apply_response.json()["batch_id"]

    detail_response = client.get(
        f"/api/admin/catalog/import/batches/{batch_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["id"] == batch_id
    assert payload["status"] == "applied"
    assert payload["changes"] == [
        {
            "row": 2,
            "id": species.id,
            "name_ru": "Detail plant",
            "changed_fields": ["name_latin", "category"],
            "before": {
                "name_latin": "Acer",
                "category": "rare",
            },
            "after": {
                "name_latin": "Acer platanoides",
                "category": "typical",
            },
        }
    ]


def test_admin_catalog_import_batches_filter_by_status_and_paginate(
    client,
    db,
    admin_token,
):
    species_a = Species(
        name_ru="Batch filter plant A",
        name_latin="Acer",
        group=SpeciesGroup.plants,
        category=SpeciesCategory.rare,
    )
    species_b = Species(
        name_ru="Batch filter plant B",
        name_latin="Betula",
        group=SpeciesGroup.plants,
        category=SpeciesCategory.rare,
    )
    db.add_all([species_a, species_b])
    db.commit()
    db.refresh(species_a)
    db.refresh(species_b)

    first_apply = client.post(
        "/api/admin/catalog/import/apply",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "first.csv",
                _csv_payload(
                    [
                        (
                            f"{species_a.id},Batch filter plant A,Acer platanoides,"
                            "plants,typical,,false,,,,,"
                        ),
                    ]
                ),
                "text/csv",
            )
        },
    )
    assert first_apply.status_code == 200
    first_batch_id = first_apply.json()["batch_id"]
    rollback = client.post(
        f"/api/admin/catalog/import/batches/{first_batch_id}/rollback",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert rollback.status_code == 200

    second_apply = client.post(
        "/api/admin/catalog/import/apply",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "second.csv",
                _csv_payload(
                    [
                        (
                            f"{species_b.id},Batch filter plant B,Betula pendula,"
                            "plants,typical,,false,,,,,"
                        ),
                    ]
                ),
                "text/csv",
            )
        },
    )
    assert second_apply.status_code == 200
    second_batch_id = second_apply.json()["batch_id"]

    applied_response = client.get(
        "/api/admin/catalog/import/batches?status=applied",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert applied_response.status_code == 200
    assert applied_response.json()["total"] == 1
    assert applied_response.json()["items"][0]["id"] == second_batch_id

    rolled_back_response = client.get(
        "/api/admin/catalog/import/batches?status=rolled_back",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert rolled_back_response.status_code == 200
    assert rolled_back_response.json()["total"] == 1
    assert rolled_back_response.json()["items"][0]["id"] == first_batch_id

    paginated_response = client.get(
        "/api/admin/catalog/import/batches?skip=1&limit=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert paginated_response.status_code == 200
    assert paginated_response.json()["total"] == 2
    assert len(paginated_response.json()["items"]) == 1
    assert paginated_response.json()["items"][0]["id"] == first_batch_id


def test_admin_catalog_import_apply_rejects_csv_with_errors(client, db, admin_token):
    species = Species(
        name_ru="Apply insect",
        name_latin="Pieris",
        group=SpeciesGroup.insects,
        category=SpeciesCategory.typical,
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    response = client.post(
        "/api/admin/catalog/import/apply",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": (
                "catalog.csv",
                _csv_payload(
                    [
                        f"{species.id},Apply insect,Pieris brassicae,insects,bad,,,,,,,",
                    ]
                ),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "CSV contains row errors"
    db.refresh(species)
    assert species.name_latin == "Pieris"
    assert species.category == SpeciesCategory.typical
