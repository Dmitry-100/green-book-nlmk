from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.species import Species


def _fact_index(for_date: date, total: int) -> int:
    digest = hashlib.sha256(for_date.isoformat().encode("utf-8")).hexdigest()
    return int(digest, 16) % total


def _species_payload(species: Species, fact_text: str) -> dict:
    return {
        "species_id": species.id,
        "name_ru": species.name_ru,
        "name_latin": species.name_latin,
        "fact_text": fact_text,
        "description": fact_text,
        "photo_url": species.photo_urls[0] if species.photo_urls else None,
        "is_poisonous": species.is_poisonous,
        "conservation_status": species.conservation_status,
    }


def build_fact_of_day(
    db: Session,
    *,
    for_date: date | None = None,
) -> dict | None:
    selected_date = for_date or datetime.now(timezone.utc).date()
    species_with_facts = (
        db.query(Species)
        .filter(func.coalesce(func.array_length(Species.interesting_facts, 1), 0) > 0)
        .order_by(Species.id.asc())
        .all()
    )

    facts: list[tuple[Species, str]] = []
    for species in species_with_facts:
        for fact in species.interesting_facts or []:
            fact_text = fact.strip()
            if fact_text:
                facts.append((species, fact_text))

    if facts:
        species, fact_text = facts[_fact_index(selected_date, len(facts))]
        return _species_payload(species, fact_text)

    fallback_species = (
        db.query(Species)
        .filter(
            Species.description.is_not(None),
            func.length(func.btrim(Species.description)) > 0,
        )
        .order_by(Species.id.asc())
        .all()
    )
    if not fallback_species:
        return None

    species = fallback_species[_fact_index(selected_date, len(fallback_species))]
    return _species_payload(species, species.description or "")

