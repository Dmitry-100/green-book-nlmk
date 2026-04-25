import re
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models.species import Species

LATIN_SPECIES_RE = re.compile(r"^[A-Z][a-z]+ [a-z][a-z-]+(?:$| .+)")
SHORT_DESCRIPTION_MIN_CHARS = 120


def _group_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _has_text(value: Any) -> bool:
    if value is None:
        return False
    return bool(str(value).strip())


def _has_any_text(values: Any) -> bool:
    if not values:
        return False
    return any(_has_text(value) for value in values)


def is_short_description(value: str | None) -> bool:
    if not _has_text(value):
        return False
    return len(value.strip()) < SHORT_DESCRIPTION_MIN_CHARS


def is_latin_species_name(value: str | None) -> bool:
    if not value:
        return False
    return bool(LATIN_SPECIES_RE.match(value.strip()))


def has_suspicious_latin_chars(value: str | None) -> bool:
    if not value:
        return False
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return True
    return False


def catalog_quality_snapshot(
    db: Session,
    *,
    examples_limit: int = 10,
) -> dict[str, Any]:
    rows = (
        db.query(
            Species.id,
            Species.name_ru,
            Species.name_latin,
            Species.group,
            Species.photo_urls,
            Species.description,
            Species.audio_url,
        )
        .order_by(Species.id.asc())
        .all()
    )

    needs_review_by_group: Counter[str] = Counter()
    content_gap_counts: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    exact_species_count = 0
    suspicious_chars_count = 0

    for (
        species_id,
        name_ru,
        name_latin,
        group,
        photo_urls,
        description,
        audio_url,
    ) in rows:
        group_value = _group_value(group)

        if is_latin_species_name(name_latin):
            exact_species_count += 1
        else:
            needs_review_by_group[group_value] += 1
            if len(examples) < examples_limit:
                examples.append(
                    {
                        "id": species_id,
                        "name_ru": name_ru,
                        "name_latin": name_latin,
                        "group": group_value,
                    }
                )

        if has_suspicious_latin_chars(name_latin):
            suspicious_chars_count += 1

        if not _has_any_text(photo_urls):
            content_gap_counts["missing_photo"] += 1
        if not _has_text(description):
            content_gap_counts["missing_description"] += 1
        elif is_short_description(description):
            content_gap_counts["short_description"] += 1
        if not _has_text(audio_url):
            content_gap_counts["missing_audio"] += 1

    species_total = len(rows)
    needs_review_count = species_total - exact_species_count

    return {
        "species_total": species_total,
        "latin_name_exact_species": exact_species_count,
        "latin_name_needs_review": needs_review_count,
        "latin_name_suspicious_chars": suspicious_chars_count,
        "latin_name_needs_review_by_group": dict(sorted(needs_review_by_group.items())),
        "latin_name_needs_review_examples": examples,
        "content_gap_counts": {
            "missing_photo": content_gap_counts["missing_photo"],
            "missing_description": content_gap_counts["missing_description"],
            "short_description": content_gap_counts["short_description"],
            "missing_audio": content_gap_counts["missing_audio"],
        },
    }
