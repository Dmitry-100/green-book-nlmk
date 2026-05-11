from app.models.species import Species, SpeciesCategory, SpeciesGroup
from app.seed.species_enrichment_20260511 import apply_species_enrichment


def test_species_enrichment_extends_short_descriptions_and_adds_facts(db):
    species = Species(
        name_ru="Тестовая синица",
        name_latin="Parus testus",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.typical,
        description="Небольшая птица.",
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    summary = apply_species_enrichment(db)

    db.refresh(species)
    assert summary["updated"] == 1
    assert species.description is not None
    assert len(species.description) >= 350
    assert species.interesting_facts is not None
    assert len(species.interesting_facts) >= 3
    assert all(0 < len(fact) <= 500 for fact in species.interesting_facts)


def test_species_enrichment_keeps_existing_rich_editorial_content(db):
    rich_description = " ".join(["Экспертное описание вида."] * 30)
    facts = ["Проверенный факт 1.", "Проверенный факт 2.", "Проверенный факт 3."]
    species = Species(
        name_ru="Экспертный вид",
        name_latin="Expertus species",
        group=SpeciesGroup.plants,
        category=SpeciesCategory.rare,
        description=rich_description,
        interesting_facts=facts,
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    summary = apply_species_enrichment(db)

    db.refresh(species)
    assert summary["updated"] == 0
    assert species.description == rich_description
    assert species.interesting_facts == facts


def test_species_enrichment_replaces_generic_facts_for_known_species(db):
    generic_bird_facts = [
        "Голос птицы часто помогает подтвердить вид даже тогда, когда птицу трудно сфотографировать.",
        "Для птиц ценны повторные наблюдения: они показывают гнездование, миграцию или регулярное кормление.",
        "Лучшее наблюдение птицы фиксирует не только внешний вид, но и поведение: пение, кормление, полет или тревогу.",
    ]
    species = Species(
        name_ru="Грач",
        name_latin="Corvus frugilegus",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.typical,
        description="Крупная чёрная птица семейства врановых.",
        interesting_facts=generic_bird_facts,
    )
    db.add(species)
    db.commit()
    db.refresh(species)

    summary = apply_species_enrichment(db)

    db.refresh(species)
    facts_text = " ".join(species.interesting_facts or []).lower()
    assert summary["updated"] == 1
    assert summary["facts"] == 1
    assert species.interesting_facts != generic_bird_facts
    assert "грач" in facts_text or "corvus frugilegus" in facts_text
    assert "голос птицы часто помогает" not in facts_text
