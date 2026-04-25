import csv
import io
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.catalog_import import CatalogImportBatch, CatalogImportBatchStatus
from app.models.species import Species, SpeciesCategory, SpeciesGroup

CATALOG_IMPORT_EDITABLE_FIELDS = [
    "name_ru",
    "name_latin",
    "group",
    "category",
    "conservation_status",
    "season_info",
    "biotopes",
    "description",
    "do_dont_rules",
    "is_poisonous",
    "photo_urls",
    "audio_url",
    "audio_title",
    "audio_source",
    "audio_license",
]

_TEXT_LIMITS = {
    "name_ru": 255,
    "name_latin": 255,
    "conservation_status": 255,
    "season_info": 500,
    "biotopes": 5000,
    "description": 10000,
    "do_dont_rules": 10000,
    "audio_url": 500,
    "audio_title": 255,
    "audio_source": 255,
    "audio_license": 255,
}


class CatalogImportError(ValueError):
    pass


class CatalogImportConflict(ValueError):
    pass


def _current_value(species: Species, field: str) -> Any:
    value = getattr(species, field)
    if hasattr(value, "value"):
        return value.value
    return value


def _normalize_optional_text(value: str, field: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    max_length = _TEXT_LIMITS[field]
    if len(value) > max_length:
        raise ValueError(f"{field} must be at most {max_length} chars")
    return value


def _normalize_required_text(value: str, field: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field} must not be blank")
    max_length = _TEXT_LIMITS[field]
    if len(value) > max_length:
        raise ValueError(f"{field} must be at most {max_length} chars")
    return value


def _normalize_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "да"}:
        return True
    if normalized in {"false", "0", "no", "n", "нет", ""}:
        return False
    raise ValueError(f"Invalid boolean: {value}")


def _normalize_group(value: str) -> str:
    normalized = value.strip()
    try:
        return SpeciesGroup(normalized).value
    except ValueError:
        raise ValueError(f"Invalid group: {normalized}")


def _normalize_category(value: str) -> str:
    normalized = value.strip()
    try:
        return SpeciesCategory(normalized).value
    except ValueError:
        raise ValueError(f"Invalid category: {normalized}")


def _normalize_photo_urls(value: str) -> list[str] | None:
    value = value.strip()
    if not value:
        return None
    urls = [item.strip() for item in value.split(";")]
    if any(not item for item in urls):
        raise ValueError("photo_urls must not contain empty values")
    if len(urls) > 20:
        raise ValueError("photo_urls must contain at most 20 values")
    for url in urls:
        if len(url) > 500:
            raise ValueError("photo_urls items must be at most 500 chars")
    return urls


def _normalize_audio_url(value: str) -> str | None:
    normalized = _normalize_optional_text(value, "audio_url")
    if normalized is None:
        return None
    if not (normalized.startswith("https://") or normalized.startswith("/api/media/")):
        raise ValueError("audio_url must be https:// or /api/media/")
    return normalized


def _normalize_field(field: str, value: str) -> Any:
    if field in {"name_ru", "name_latin"}:
        return _normalize_required_text(value, field)
    if field in {
        "conservation_status",
        "season_info",
        "biotopes",
        "description",
        "do_dont_rules",
        "audio_title",
        "audio_source",
        "audio_license",
    }:
        return _normalize_optional_text(value, field)
    if field == "group":
        return _normalize_group(value)
    if field == "category":
        return _normalize_category(value)
    if field == "is_poisonous":
        return _normalize_bool(value)
    if field == "photo_urls":
        return _normalize_photo_urls(value)
    if field == "audio_url":
        return _normalize_audio_url(value)
    raise ValueError(f"Unsupported field: {field}")


def _model_value(field: str, value: Any) -> Any:
    if field == "group" and value is not None:
        return SpeciesGroup(value)
    if field == "category" and value is not None:
        return SpeciesCategory(value)
    return value


def _row_id(row: dict[str, str], row_number: int) -> tuple[int | None, str | None, list[str]]:
    raw_id = (row.get("id") or "").strip()
    if not raw_id:
        return None, raw_id, ["id must not be blank"]
    try:
        species_id = int(raw_id)
    except ValueError:
        return None, raw_id, [f"Invalid id at row {row_number}: {raw_id}"]
    if species_id <= 0:
        return None, raw_id, [f"Invalid id at row {row_number}: {raw_id}"]
    return species_id, raw_id, []


def preview_species_catalog_import(
    *,
    db: Session,
    csv_text: str,
    filename: str,
) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise CatalogImportError("CSV must contain a header row")
    if "id" not in reader.fieldnames:
        raise CatalogImportError("CSV must contain id column")

    changes: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    unchanged_rows = 0
    total_rows = 0

    import_fields = [
        field
        for field in CATALOG_IMPORT_EDITABLE_FIELDS
        if field in reader.fieldnames
    ]

    for row_number, row in enumerate(reader, start=2):
        total_rows += 1
        species_id, raw_id, row_errors = _row_id(row, row_number)
        species = db.get(Species, species_id) if species_id is not None else None
        if species_id is not None and species is None:
            row_errors.append("Species not found")

        normalized: dict[str, Any] = {}
        if not row_errors:
            for field in import_fields:
                try:
                    normalized[field] = _normalize_field(field, row.get(field) or "")
                except ValueError as exc:
                    row_errors.append(str(exc))

        if row_errors:
            errors.append({"row": row_number, "id": raw_id or "", "errors": row_errors})
            continue

        before: dict[str, Any] = {}
        after: dict[str, Any] = {}
        changed_fields: list[str] = []
        assert species is not None
        for field, value in normalized.items():
            current = _current_value(species, field)
            if current != value:
                changed_fields.append(field)
                before[field] = current
                after[field] = value

        if changed_fields:
            changes.append(
                {
                    "row": row_number,
                    "id": species.id,
                    "name_ru": species.name_ru,
                    "changed_fields": changed_fields,
                    "before": before,
                    "after": after,
                }
            )
        else:
            unchanged_rows += 1

    return {
        "filename": filename,
        "dry_run": True,
        "total_rows": total_rows,
        "changed_rows": len(changes),
        "unchanged_rows": unchanged_rows,
        "error_rows": len(errors),
        "changes": changes,
        "errors": errors,
    }


def apply_species_catalog_import(
    *,
    db: Session,
    csv_text: str,
    filename: str,
) -> dict[str, Any]:
    result = preview_species_catalog_import(
        db=db,
        csv_text=csv_text,
        filename=filename,
    )
    if result["error_rows"] > 0:
        raise CatalogImportError("CSV contains row errors")

    applied_rows = 0
    for change in result["changes"]:
        species = db.get(Species, change["id"])
        if species is None:
            raise CatalogImportError("Species not found")
        for field, value in change["after"].items():
            setattr(species, field, _model_value(field, value))
        applied_rows += 1

    result["dry_run"] = False
    result["applied_rows"] = applied_rows
    return result


def rollback_catalog_import_batch(
    *,
    db: Session,
    batch: CatalogImportBatch,
    user_id: int | None,
) -> dict[str, Any]:
    if batch.status != CatalogImportBatchStatus.applied:
        raise CatalogImportConflict("Batch is not applied")

    for change in batch.changes:
        species = db.get(Species, change["id"])
        if species is None:
            raise CatalogImportConflict(f"Species not found: {change['id']}")
        for field, expected_value in change["after"].items():
            if _current_value(species, field) != expected_value:
                raise CatalogImportConflict(
                    f"Species {change['id']} has conflicting field: {field}"
                )

    rolled_back_rows = 0
    for change in reversed(batch.changes):
        species = db.get(Species, change["id"])
        assert species is not None
        for field, value in change["before"].items():
            setattr(species, field, _model_value(field, value))
        rolled_back_rows += 1

    batch.status = CatalogImportBatchStatus.rolled_back
    batch.rolled_back_by_user_id = user_id
    batch.rolled_back_at = datetime.now(timezone.utc)

    return {
        "id": batch.id,
        "status": batch.status.value,
        "rolled_back_rows": rolled_back_rows,
    }
