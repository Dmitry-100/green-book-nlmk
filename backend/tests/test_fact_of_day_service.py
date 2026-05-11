from datetime import date

from app.models.species import Species, SpeciesCategory, SpeciesGroup
from app.services.fact_of_day import build_fact_of_day


def _add_species(
    db,
    *,
    suffix: str,
    description: str | None = None,
    interesting_facts: list[str] | None = None,
) -> Species:
    species = Species(
        name_ru=f"Вид {suffix}",
        name_latin=f"Species {suffix}",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.typical,
        description=description,
        photo_urls=[f"/api/media/species/{suffix}.jpg"],
        interesting_facts=interesting_facts,
    )
    db.add(species)
    db.commit()
    db.refresh(species)
    return species


def test_fact_of_day_uses_interesting_facts_and_is_stable_for_date(db):
    first = _add_species(
        db,
        suffix="First",
        description="Описание первого вида не должно попадать в факт, если есть facts.",
        interesting_facts=["Первый факт первого вида.", "Второй факт первого вида."],
    )
    second = _add_species(
        db,
        suffix="Second",
        description="Описание второго вида тоже не должно подменять fact_text.",
        interesting_facts=["Первый факт второго вида."],
    )

    result_a = build_fact_of_day(db, for_date=date(2026, 5, 11))
    result_b = build_fact_of_day(db, for_date=date(2026, 5, 11))

    assert result_a == result_b
    assert result_a is not None
    assert result_a["species_id"] in {first.id, second.id}
    assert result_a["fact_text"] in {
        "Первый факт первого вида.",
        "Второй факт первого вида.",
        "Первый факт второго вида.",
    }
    assert result_a["description"] == result_a["fact_text"]


def test_fact_of_day_falls_back_to_description_when_no_facts_exist(db):
    species = _add_species(
        db,
        suffix="Fallback",
        description="Описание используется только как fallback для старых данных.",
    )

    result = build_fact_of_day(db, for_date=date(2026, 5, 11))

    assert result is not None
    assert result["species_id"] == species.id
    assert result["fact_text"] == "Описание используется только как fallback для старых данных."
    assert result["description"] == result["fact_text"]

