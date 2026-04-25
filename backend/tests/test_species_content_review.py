from pathlib import Path

from app.models.species import Species, SpeciesCategory, SpeciesGroup
from app.seed.content_review_20260417 import AUDIO_UPDATES, apply_content_review


MEDIA_ROOT = Path(__file__).resolve().parents[1] / "media"


def _add_species(
    db,
    *,
    name_ru: str,
    name_latin: str,
    group: SpeciesGroup,
    category: SpeciesCategory,
    conservation_status: str | None = None,
    is_poisonous: bool = False,
    photo_urls: list[str] | None = None,
) -> Species:
    species = Species(
        name_ru=name_ru,
        name_latin=name_latin,
        group=group,
        category=category,
        conservation_status=conservation_status,
        is_poisonous=is_poisonous,
        photo_urls=photo_urls,
    )
    db.add(species)
    db.flush()
    return species


def _by_name(db, name_ru: str) -> Species | None:
    return db.query(Species).filter(Species.name_ru == name_ru).first()


def test_content_review_applies_expert_catalog_delta(db):
    _add_species(
        db,
        name_ru="Полынь горькая",
        name_latin="Artemisia absinthium",
        group=SpeciesGroup.plants,
        category=SpeciesCategory.ruderal,
    )
    _add_species(
        db,
        name_ru="Ковыль перистый",
        name_latin="Stipa pennata",
        group=SpeciesGroup.plants,
        category=SpeciesCategory.rare,
        conservation_status="Красная книга Липецкой области",
        photo_urls=["/api/media/species-pdf/page11_img00.png"],
    )
    _add_species(
        db,
        name_ru="Гадюка Никольского",
        name_latin="Vipera nikolskii",
        group=SpeciesGroup.herpetofauna,
        category=SpeciesCategory.red_book,
        conservation_status="Красная книга Липецкой области",
        is_poisonous=True,
        photo_urls=["/api/media/species-pdf/page21_img01.png"],
    )
    _add_species(
        db,
        name_ru="Большая синица",
        name_latin="Parus major",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.synanthropic,
    )
    _add_species(
        db,
        name_ru="Синица",
        name_latin="Parus",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.synanthropic,
    )
    _add_species(
        db,
        name_ru="Сорока",
        name_latin="Pica pica",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.synanthropic,
    )
    _add_species(
        db,
        name_ru="Сорока обыкновенная",
        name_latin="Pica",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.synanthropic,
    )
    _add_species(
        db,
        name_ru="Крапчатый суслик",
        name_latin="Spermophilus suslicus",
        group=SpeciesGroup.mammals,
        category=SpeciesCategory.red_book,
        conservation_status="Красная книга Липецкой области",
    )
    _add_species(
        db,
        name_ru="Малиновая ленточница",
        name_latin="Catocala",
        group=SpeciesGroup.insects,
        category=SpeciesCategory.red_book,
        conservation_status="Красная книга Липецкой области",
        photo_urls=["/api/media/species-pdf/page20_img06.png"],
    )
    _add_species(
        db,
        name_ru="Обыкновенный уж",
        name_latin="Natrix natrix",
        group=SpeciesGroup.herpetofauna,
        category=SpeciesCategory.typical,
        photo_urls=["/api/media/species-pdf/page21_img00.png"],
    )
    _add_species(
        db,
        name_ru="Заяц-беляк",
        name_latin="Lepus timidus",
        group=SpeciesGroup.mammals,
        category=SpeciesCategory.red_book,
        conservation_status="Красная книга Липецкой области",
        photo_urls=[],
    )
    _add_species(
        db,
        name_ru="Серая неясыть",
        name_latin="Strix aluco",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.red_book,
    )
    _add_species(
        db,
        name_ru="Озёрная лягушка",
        name_latin="Pelophylax ridibundus",
        group=SpeciesGroup.herpetofauna,
        category=SpeciesCategory.typical,
    )
    _add_species(
        db,
        name_ru="Домовый воробей",
        name_latin="Passer domesticus",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.synanthropic,
    )
    _add_species(
        db,
        name_ru="Обыкновенная кукушка",
        name_latin="Cuculus canorus",
        group=SpeciesGroup.birds,
        category=SpeciesCategory.typical,
    )
    for name_ru, name_latin, group, category in (
        ("Балобан", "Falco", SpeciesGroup.birds, SpeciesCategory.red_book),
        (
            "Белоспинный дятел",
            "Dendrocopos",
            SpeciesGroup.birds,
            SpeciesCategory.red_book,
        ),
        ("Беркут", "Aquila chrysaetos", SpeciesGroup.birds, SpeciesCategory.red_book),
        (
            "Большая белая цапля",
            "Ardea alba",
            SpeciesGroup.birds,
            SpeciesCategory.typical,
        ),
        (
            "Волчек (малая выпь)",
            "Ixobrychus minutus",
            SpeciesGroup.birds,
            SpeciesCategory.red_book,
        ),
        (
            "Козодой",
            "Caprimulgus europaeus",
            SpeciesGroup.birds,
            SpeciesCategory.red_book,
        ),
        (
            "Травяная лягушка",
            "Rana temporaria",
            SpeciesGroup.herpetofauna,
            SpeciesCategory.typical,
        ),
        (
            "Сокол сапсан",
            "Falco peregrinus",
            SpeciesGroup.birds,
            SpeciesCategory.red_book,
        ),
        ("Серая жаба", "Bufo", SpeciesGroup.herpetofauna, SpeciesCategory.typical),
        ("Барсук", "Meles meles", SpeciesGroup.mammals, SpeciesCategory.typical),
        ("Косуля", "Capreоlus", SpeciesGroup.mammals, SpeciesCategory.typical),
        (
            "Синеголовник плосколистный",
            "Еryngium",
            SpeciesGroup.plants,
            SpeciesCategory.typical,
        ),
        (
            "Гвоздика песчаная",
            "Diānthus",
            SpeciesGroup.plants,
            SpeciesCategory.red_book,
        ),
        (
            "Грушанка зеленоцветковая",
            "Pýrola",
            SpeciesGroup.plants,
            SpeciesCategory.red_book,
        ),
        (
            "Большое коромысло",
            "Aesсhna",
            SpeciesGroup.insects,
            SpeciesCategory.typical,
        ),
        (
            "Хейлозия Кузнецовой",
            "Сheilosia",
            SpeciesGroup.insects,
            SpeciesCategory.red_book,
        ),
        (
            "Лисица обыкновенная",
            "Vulpes vulpes",
            SpeciesGroup.mammals,
            SpeciesCategory.typical,
        ),
    ):
        _add_species(
            db,
            name_ru=name_ru,
            name_latin=name_latin,
            group=group,
            category=category,
        )
    db.commit()

    summary = apply_content_review(db)
    db.commit()

    assert summary["created"] >= 20
    assert _by_name(db, "Полынь горькая") is None
    assert _by_name(db, "Крапчатый суслик") is None
    assert _by_name(db, "Синица") is None
    assert _by_name(db, "Сорока обыкновенная") is None

    kovyl = _by_name(db, "Ковыль перистый")
    assert kovyl is not None
    assert kovyl.category == SpeciesCategory.red_book
    assert kovyl.photo_urls == ["/api/media/species-pdf/page11_img00.png"]

    viper = _by_name(db, "Гадюка Никольского")
    assert viper is not None
    assert viper.category == SpeciesCategory.typical
    assert viper.conservation_status is None
    assert viper.is_poisonous is True
    assert viper.photo_urls == ["/api/media/species-pdf/page21_img01.png"]

    assert _by_name(db, "Тополь черный") is not None
    assert _by_name(db, "Тополь черный").photo_urls
    assert _by_name(db, "Рдест остролистный").category == SpeciesCategory.red_book
    assert _by_name(db, "Рдест остролистный").photo_urls
    assert _by_name(db, "Бабочка лимонница").category == SpeciesCategory.typical
    assert _by_name(db, "Бабочка лимонница").photo_urls
    assert _by_name(db, "Медведица госпожа").category == SpeciesCategory.red_book
    assert _by_name(db, "Медведица госпожа").photo_urls
    assert _by_name(db, "Грач").category == SpeciesCategory.synanthropic
    assert _by_name(db, "Грач").photo_urls
    assert _by_name(db, "Заяц-беляк").category == SpeciesCategory.red_book
    assert _by_name(db, "Заяц-беляк").photo_urls

    raspberry_underwing = _by_name(db, "Малиновая ленточница")
    assert raspberry_underwing is not None
    assert raspberry_underwing.photo_urls[0].endswith("Catocala_sponsa.jpg")

    blue_underwing = _by_name(db, "Голубая ленточница")
    assert blue_underwing is not None
    assert blue_underwing.photo_urls == ["/api/media/species-pdf/page20_img06.png"]

    grass_snake = _by_name(db, "Обыкновенный уж")
    assert grass_snake is not None
    assert "Natrix_natrix" in grass_snake.photo_urls[0]

    great_tit = _by_name(db, "Большая синица")
    assert great_tit is not None
    assert great_tit.audio_url == "/api/media/species-audio/parus-major.ogg"
    assert great_tit.audio_title == "Песня большой синицы"
    assert great_tit.audio_source == "Wikimedia Commons / Oona Raisanen"
    assert great_tit.audio_license == "Public domain"

    tawny_owl = _by_name(db, "Серая неясыть")
    assert tawny_owl is not None
    assert tawny_owl.audio_url == "/api/media/species-audio/strix-aluco.ogg"

    marsh_frog = _by_name(db, "Озёрная лягушка")
    assert marsh_frog is not None
    assert marsh_frog.audio_url == "/api/media/species-audio/pelophylax-ridibundus.ogg"

    rook = _by_name(db, "Грач")
    assert rook is not None
    assert rook.audio_url == "/api/media/species-audio/corvus-frugilegus.ogg"

    magpie = _by_name(db, "Сорока")
    assert magpie is not None
    assert magpie.audio_url == "/api/media/species-audio/pica-pica.ogg"

    sparrow = _by_name(db, "Домовый воробей")
    assert sparrow is not None
    assert sparrow.audio_license == "CC0"

    cuckoo = _by_name(db, "Обыкновенная кукушка")
    assert cuckoo is not None
    assert cuckoo.audio_url == "/api/media/species-audio/cuculus-canorus.mp3"

    hedgehog = _by_name(db, "Ёж обыкновенный")
    assert hedgehog is not None
    assert hedgehog.audio_url == "/api/media/species-audio/erinaceus-europaeus.ogg"

    expected_new_audio = {
        "Беркут": "aquila-chrysaetos.ogg",
        "Белоспинный дятел": "dendrocopos-leucotos.ogg",
        "Большая белая цапля": "ardea-alba.ogg",
        "Волчек (малая выпь)": "ixobrychus-minutus.mp3",
        "Козодой": "caprimulgus-europaeus.mp3",
        "Сокол сапсан": "falco-peregrinus.ogg",
        "Травяная лягушка": "rana-temporaria.ogg",
        "Барсук": "meles-meles.ogg",
        "Лисица обыкновенная": "vulpes-vulpes.ogg",
    }
    for name_ru, filename in expected_new_audio.items():
        species = _by_name(db, name_ru)
        assert species is not None
        assert species.audio_url == f"/api/media/species-audio/{filename}"

    golden_eagle = _by_name(db, "Беркут")
    assert golden_eagle is not None
    assert golden_eagle.audio_source == "Xeno-canto XC1045328 / Lars Edenius"
    assert (
        golden_eagle.audio_license
        == "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"
    )

    expected_latin_names = {
        "Балобан": "Falco cherrug",
        "Белоспинный дятел": "Dendrocopos leucotos",
        "Беркут": "Aquila chrysaetos",
        "Большая белая цапля": "Ardea alba",
        "Волчек (малая выпь)": "Ixobrychus minutus",
        "Козодой": "Caprimulgus europaeus",
        "Сокол сапсан": "Falco peregrinus",
        "Серая жаба": "Bufo bufo",
        "Травяная лягушка": "Rana temporaria",
        "Барсук": "Meles meles",
        "Косуля": "Capreolus capreolus",
        "Синеголовник плосколистный": "Eryngium",
        "Гвоздика песчаная": "Dianthus",
        "Грушанка зеленоцветковая": "Pyrola",
        "Большое коромысло": "Aeshna",
        "Хейлозия Кузнецовой": "Cheilosia",
    }
    for name_ru, name_latin in expected_latin_names.items():
        species = _by_name(db, name_ru)
        assert species is not None
        assert species.name_latin == name_latin


def test_content_review_audio_assets_are_local_and_versioned():
    assert AUDIO_UPDATES
    for name_ru, values in AUDIO_UPDATES.items():
        audio_url = values["audio_url"]
        assert audio_url.startswith("/api/media/species-audio/"), name_ru
        audio_path = MEDIA_ROOT / audio_url.removeprefix("/api/media/")
        assert audio_path.is_file(), name_ru
        assert audio_path.stat().st_size > 0, name_ru
