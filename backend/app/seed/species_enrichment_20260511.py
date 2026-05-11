"""Enrich species cards with longer descriptions and fact-of-day facts.

The module is intentionally deterministic and idempotent: it fills editorial
gaps without overwriting already rich expert content.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.species import Species
from app.seed.species_fact_overrides_20260511 import SPECIES_FACT_OVERRIDES


MIN_DESCRIPTION_CHARS = 350
MIN_FACTS = 3
MAX_FACTS = 8
MAX_FACT_CHARS = 500

GROUP_LABELS = {
    "plants": "растений",
    "fungi": "грибов",
    "insects": "насекомых",
    "herpetofauna": "герпетофауны",
    "birds": "птиц",
    "mammals": "млекопитающих",
}

GROUP_CONTEXT = {
    "plants": (
        "На промплощадке такие растения помогают быстро закрывать нарушенные "
        "почвы, удерживать пыль и создавать укрытия для мелких беспозвоночных."
    ),
    "fungi": (
        "Грибы важны для круговорота органики: они разлагают растительные "
        "остатки и показывают, где сохраняются влажные микроместообитания."
    ),
    "insects": (
        "Насекомые быстро реагируют на состояние травостоя, водоемов и лесополос, "
        "поэтому наблюдения за ними хорошо дополняют мониторинг биоразнообразия."
    ),
    "herpetofauna": (
        "Амфибии и рептилии особенно чувствительны к качеству укрытий, влажности "
        "и состоянию малых водоемов, поэтому их находки ценны для экологов."
    ),
    "birds": (
        "Птицы хорошо заметны в сезонных наблюдениях и помогают понять, какие "
        "участки промплощадки работают как кормовые, гнездовые или транзитные."
    ),
    "mammals": (
        "Млекопитающие чаще оставляют косвенные признаки присутствия, поэтому "
        "для учета важны следы, норы, помет и повторяющиеся маршруты."
    ),
}

GROUP_FACTS = {
    "plants": [
        "Растения на нарушенных почвах часто первыми показывают, где формируются новые устойчивые микросообщества.",
        "Даже обычные рудеральные растения важны как кормовая база для насекомых-опылителей.",
        "Наблюдения за растениями лучше делать с фото листьев, стебля, цветков или плодов.",
    ],
    "fungi": [
        "Плодовое тело гриба - только видимая часть организма, основная грибница скрыта в субстрате.",
        "Для определения грибов особенно важны нижняя сторона шляпки, ножка и место произрастания.",
        "Ядовитость грибов нельзя надежно оценивать по запаху, цвету или повреждениям насекомыми.",
    ],
    "insects": [
        "У многих насекомых разные стадии жизни занимают разные местообитания, поэтому важны дата и точное место наблюдения.",
        "Фото насекомого сбоку и сверху часто дает больше диагностических признаков, чем один крупный план.",
        "Насекомые служат кормом для птиц, амфибий и мелких млекопитающих, связывая разные уровни экосистемы.",
    ],
    "herpetofauna": [
        "Амфибии и рептилии особенно уязвимы к пересыханию укрытий и загрязнению малых водоемов.",
        "Для таких видов важны безопасные переходы между водоемами, влажными низинами и местами зимовки.",
        "При встрече не стоит брать животное в руки: достаточно фото и координат наблюдения.",
    ],
    "birds": [
        "Голос птицы часто помогает подтвердить вид даже тогда, когда птицу трудно сфотографировать.",
        "Для птиц ценны повторные наблюдения: они показывают гнездование, миграцию или регулярное кормление.",
        "Лучшее наблюдение птицы фиксирует не только внешний вид, но и поведение: пение, кормление, полет или тревогу.",
    ],
    "mammals": [
        "Млекопитающих часто надежнее учитывать по следам и другим признакам присутствия, чем по прямой встрече.",
        "Повторные находки на одном маршруте помогают понять постоянные тропы и кормовые участки животных.",
        "Для наблюдения млекопитающих полезны фото следов, нор, погрызов или помета рядом с ориентиром масштаба.",
    ],
}

GENERIC_FACT_MARKERS = (
    "Голос птицы часто помогает",
    "Для птиц ценны повторные наблюдения",
    "Лучшее наблюдение птицы",
    "Растения на нарушенных почвах",
    "Даже обычные рудеральные растения",
    "Наблюдения за растениями лучше делать",
    "Плодовое тело гриба",
    "Для определения грибов особенно важны",
    "Ядовитость грибов нельзя",
    "У многих насекомых разные стадии жизни",
    "Фото насекомого сбоку",
    "Насекомые служат кормом",
    "Амфибии и рептилии особенно уязвимы",
    "Для таких видов важны безопасные переходы",
    "При встрече не стоит брать животное",
    "Млекопитающих часто надежнее учитывать",
    "Повторные находки на одном маршруте",
    "Для наблюдения млекопитающих полезны",
    "Охранный статус:",
    "Синантропные виды показывают",
    "Рудеральные виды часто первыми",
    "Типичные виды важны как экологический фон",
    "Для краснокнижных видов особенно важна",
    "Редкие виды полезно отмечать повторно",
    "Красная книга Липецкой области.",
    "Вид помечен как потенциально опасный",
    "представитель группы",
    "отмеченный в каталоге Зеленой книги",
)

CATEGORY_CONTEXT = {
    "ruderal": "В каталоге вид относится к рудеральным: он хорошо переносит нарушенные или уплотненные участки.",
    "typical": "В каталоге вид отмечен как типичный представитель местной биоты и полезен для регулярных наблюдений.",
    "rare": "В каталоге вид отмечен как редкий, поэтому для него особенно важны аккуратные фото и повторная проверка.",
    "red_book": "Охраняемый статус требует бережного наблюдения без изъятия, пересадки или беспокойства особей.",
    "synanthropic": "Синантропные виды приспособлены жить рядом с человеком и хорошо показывают связь природных и рабочих зон.",
}


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").split())


def _first_sentence(text: str) -> str:
    for delimiter in (". ", "! ", "? "):
        if delimiter in text:
            return text.split(delimiter, 1)[0].strip(" .!?") + "."
    return text.strip(" .!?") + "." if text else ""


def _append_sentence(parts: list[str], text: str | None) -> None:
    normalized = _normalize_text(text)
    if not normalized:
        return
    if not normalized.endswith((".", "!", "?")):
        normalized += "."
    if normalized not in parts:
        parts.append(normalized)


def _species_key(species: Species) -> tuple[str, str]:
    return (_normalize_text(species.name_ru), _normalize_text(species.name_latin))


def _normalize_facts(values: list[str] | None) -> list[str]:
    facts: list[str] = []
    for value in values or []:
        if not isinstance(value, str):
            continue
        normalized = _normalize_text(value)
        if not normalized:
            continue
        if len(normalized) > MAX_FACT_CHARS:
            normalized = normalized[: MAX_FACT_CHARS - 1].rstrip(" .,;") + "."
        if normalized not in facts:
            facts.append(normalized)
    return facts[:MAX_FACTS]


def _has_generic_seed_facts(facts: list[str]) -> bool:
    text = " ".join(facts).lower()
    return any(marker.lower() in text for marker in GENERIC_FACT_MARKERS)


def build_enriched_description(species: Species) -> str:
    group = _enum_value(species.group)
    category = _enum_value(species.category)
    base = _normalize_text(species.description)
    if not base:
        group_label = GROUP_LABELS.get(group, "видов")
        base = (
            f"{species.name_ru} ({species.name_latin}) - представитель группы "
            f"{group_label}, отмеченный в каталоге Зеленой книги НЛМК."
        )

    parts: list[str] = []
    _append_sentence(parts, base)
    _append_sentence(parts, species.biotopes)
    _append_sentence(parts, species.season_info)
    _append_sentence(parts, species.conservation_status)
    _append_sentence(parts, GROUP_CONTEXT.get(group))
    _append_sentence(parts, CATEGORY_CONTEXT.get(category))
    if species.is_poisonous:
        _append_sentence(
            parts,
            "Вид помечен как потенциально опасный, поэтому его не нужно трогать руками или переносить.",
        )
    _append_sentence(
        parts,
        "Для наблюдения достаточно сделать четкое фото, отметить дату, место и кратко описать условия находки.",
    )

    description = " ".join(parts)
    while len(description) < MIN_DESCRIPTION_CHARS:
        _append_sentence(
            parts,
            "Такие записи помогают экологам отличать случайные встречи от устойчивого присутствия вида на территории.",
        )
        description = " ".join(parts)
        break
    return description


def _category_fact(species: Species) -> str:
    category = _enum_value(species.category)
    if species.conservation_status:
        return f"Охранный статус: {species.conservation_status}; такие находки важно фиксировать особенно аккуратно."
    if species.is_poisonous:
        return "Вид отмечен как ядовитый или потенциально опасный, поэтому безопаснее ограничиться фотофиксацией."
    if category == "red_book":
        return "Для краснокнижных видов особенно важна ненарушающая фиксация: фото, дата и место без сбора экземпляров."
    if category == "rare":
        return "Редкие виды полезно отмечать повторно: серия наблюдений лучше показывает устойчивость местной популяции."
    if category == "synanthropic":
        return "Синантропные виды показывают, как животные и растения приспосабливаются к соседству с человеком."
    if category == "ruderal":
        return "Рудеральные виды часто первыми заселяют нарушенные участки и помогают отслеживать восстановление почвенного покрова."
    return "Типичные виды важны как экологический фон: по ним удобно отслеживать сезонные изменения на территории."


def build_interesting_facts(species: Species) -> list[str]:
    existing = _normalize_facts(species.interesting_facts)
    override = _normalize_facts(SPECIES_FACT_OVERRIDES.get(_species_key(species)))
    if override and (len(existing) < MIN_FACTS or _has_generic_seed_facts(existing)):
        return override

    if len(existing) >= MIN_FACTS:
        return existing[:MAX_FACTS]

    group = _enum_value(species.group)
    candidates = [
        _first_sentence(_normalize_text(species.description)),
        _category_fact(species),
        *GROUP_FACTS.get(group, []),
    ]

    facts: list[str] = []
    for fact in [*existing, *candidates]:
        normalized = _normalize_text(fact)
        if not normalized:
            continue
        if len(normalized) > MAX_FACT_CHARS:
            normalized = normalized[: MAX_FACT_CHARS - 1].rstrip(" .,;") + "."
        if normalized not in facts:
            facts.append(normalized)
        if len(facts) >= MIN_FACTS:
            break
    return facts[:MAX_FACTS]


def apply_species_enrichment(db: Session) -> dict[str, int]:
    summary = {"updated": 0, "descriptions": 0, "facts": 0}
    species_rows = db.query(Species).order_by(Species.id.asc()).all()

    for species in species_rows:
        changed = False
        description = _normalize_text(species.description)
        if len(description) < MIN_DESCRIPTION_CHARS:
            species.description = build_enriched_description(species)
            summary["descriptions"] += 1
            changed = True

        current_facts = _normalize_facts(species.interesting_facts)
        facts = build_interesting_facts(species)
        if facts and facts != current_facts:
            species.interesting_facts = facts
            summary["facts"] += 1
            changed = True

        if changed:
            summary["updated"] += 1

    db.flush()
    return summary


def main() -> None:
    db = SessionLocal()
    try:
        summary = apply_species_enrichment(db)
        db.commit()
        print(f"Applied species enrichment 2026-05-11: {summary}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
