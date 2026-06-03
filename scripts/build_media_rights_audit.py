#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.seed.content_review_20260417 import (  # noqa: E402
    AUDIO_UPDATES,
    CANONICAL_DUPLICATES,
    CATALOG_UPSERTS,
    LATIN_NAME_UPDATES,
    LOCAL_AUDIO_FILES,
    PHOTO_OVERRIDES,
    PHOTO_UPDATES,
    REMOVED_SPECIES_NAMES,
    XENO_AUDIO_SOURCE_OVERRIDES,
)
from app.seed.species_data import SPECIES_DATA  # noqa: E402

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
USER_AGENT = "green-book-nlmk-media-rights-audit/1.0 (content audit)"

AUDIT_CSV = ROOT / "docs" / "content-rights" / "media-audit.csv"
GENERATED_SEED = BACKEND_DIR / "app" / "seed" / "media_rights_safe_20260603.py"
GENERATED_FRONTEND_MEDIA = ROOT / "frontend" / "src" / "data" / "mediaRightsGenerated.ts"
SPECIES_MEDIA_DIR = BACKEND_DIR / "media" / "species"
FRONTEND_IMG_DIR = ROOT / "frontend" / "public" / "img"
GROUP_COVER_DIR = FRONTEND_IMG_DIR / "group-covers"
CACHE_DIR = ROOT / ".cache" / "media-rights"
DOWNLOAD_MEDIA = "--download" in sys.argv
NO_COMMONS_LOOKUP = "--no-commons" in sys.argv
REQUEST_DELAY_SECONDS = 1.25

ALLOWED_LICENSE_PREFIXES = (
    "cc by ",
    "cc by-",
    "cc-by ",
    "cc-by-",
    "cc0",
    "public domain",
    "gfdl",
)
BLOCKED_LICENSE_MARKERS = (
    "noncommercial",
    "non-commercial",
    "no derivatives",
    "noderivs",
    "no derivative",
    "cc by-nc",
    "cc-by-nc",
    "cc by-nd",
    "cc-by-nd",
    " nc",
    "-nc",
    " nd",
    "-nd",
)

GROUP_COVER_QUERIES = {
    "plants": ("plants", "Растения", "Artemisia vulgaris"),
    "fungi": ("fungi", "Грибы", "Amanita muscaria"),
    "insects": ("insects", "Насекомые", "Papilio machaon"),
    "herpetofauna": ("herpetofauna", "Герпетофауна", "Lacerta agilis"),
    "birds": ("birds", "Птицы", "Cygnus olor"),
    "mammals": ("mammals", "Млекопитающие", "Vulpes vulpes"),
}

# Several legacy catalog rows contain only a genus/family in name_latin even when
# the Russian name identifies a concrete species. These aliases are deliberately
# conservative: when the taxon is not unambiguous, the original name_latin is
# left as-is and the audit will mark the image as representative/manual.
PHOTO_SEARCH_ALIASES = {
    "Белянка (капустница)": "Pieris brassicae",
    "Берёзовый шелкопряд": "Endromis versicolora",
    "Богомол": "Mantis religiosa",
    "Большая ежемуха": "Tachina grossa",
    "Большое коромысло": "Aeshna grandis",
    "Большой рогохвост": "Urocerus gigas",
    "Брандушка разноцветная": "Bulbocodium versicolor",
    "Бронзовка гладкая": "Protaetia aeruginosa",
    "Брусника": "Vaccinium vitis-idaea",
    "Ветреница лесная": "Anemone sylvestris",
    "Вольвариелла шелковистая": "Volvariella bombycina",
    "Вольфия бескорневая": "Wolffia arrhiza",
    "Вьюнковый бражник": "Agrius convolvuli",
    "Вяз приземистый": "Ulmus pumila",
    "Галатея": "Melanargia galathea",
    "Гвоздика песчаная": "Dianthus arenarius",
    "Грушанка зеленоцветковая": "Pyrola chlorantha",
    "Дневной павлиний глаз": "Aglais io",
    "Дозорщик император": "Anax imperator",
    "Дровосек кожевенник": "Prionus coriarius",
    "Дуб": "Quercus robur",
    "Жук-носорог": "Oryctes nasicornis",
    "Ива лопарская": "Salix lapponum",
    "Каштановый гриб": "Gyroporus castaneus",
    "Клавария цоллинегра": "Clavaria zollingeri",
    "Клен": "Acer platanoides",
    "Клоп солдат": "Pyrrhocoris apterus",
    "Колокольчик широколистный": "Campanula latifolia",
    "Красотка-девушка": "Calopteryx virgo",
    "Кувшинка снежно-белая": "Nymphaea candida",
    "Липа": "Tilia cordata",
    "Любка двулистная": "Platanthera bifolia",
    "Малиновая ленточница": "Catocala sponsa",
    "Медведица гера": "Euplagia quadripunctaria",
    "Можжевельник обыкновенный": "Juniperus communis",
    "Молодило русское": "Sempervivum ruthenicum",
    "Мраморный хрущ": "Polyphylla fullo",
    "Мухомор красный": "Amanita muscaria",
    "Неполнокрыл большой": "Necydalis major",
    "Обыкновенный языкан": "Macroglossum stellatarum",
    "Опенок ложный": "Hypholoma fasciculare",
    "Падуболистный коконопряд": "Gastropacha quercifolia",
    "Пахучий красотел": "Calosoma sycophanta",
    "Перевязанная стрекоза": "Sympetrum pedemontanum",
    "Пецица сочная": "Peziza succosa",
    "Плаун сплюснутый": "Diphasiastrum complanatum",
    "Подбел обыкновенный": "Andromeda polifolia",
    "Прозерпина": "Proserpinus proserpina",
    "Рдест длиннейший": "Potamogeton praelongus",
    "Рябчик русский": "Fritillaria ruthenica",
    "Саркодон черепитчатый": "Sarcodon imbricatus",
    "Серый рофитоидес": "Rophitoides canus",
    "Синеголовник плосколистный": "Eryngium planum",
    "Сиреневый бражник": "Sphinx ligustri",
    "Скабиозовая шмелевидка": "Hemaris tityus",
    "Сколия гигант": "Megascolia maculata",
    "Средний винный бражник": "Deilephila porcellus",
    "Степная дыбка": "Saga pedo",
    "Строчок гигантский": "Gyromitra gigas",
    "Толстянка обыкновенная": "Crassula aquatica",
    "Тополевый ленточник": "Limenitis populi",
    "Тюльпан лесной": "Tulipa sylvestris",
    "Усач мускусный": "Aromia moschata",
    "Фиолетовая жужелица": "Carabus violaceus",
    "Черная долгоножка": "Tanyptera atrata",
    "Чёрная медведица": "Epatolmis luctifera",
    "Энтолома серо-стальная": "Entoloma bloxamii",
    "Ясень обыкновенный": "Fraxinus excelsior",
}


@dataclass
class SpeciesCandidate:
    name_ru: str
    name_latin: str
    group: str
    original_photo_urls: list[str]


@dataclass
class CommonsImage:
    file_title: str
    source_url: str
    original_url: str
    source_page: str
    author: str
    license: str
    license_url: str
    mime: str


_LAST_REQUEST_AT = 0.0


def _cache_path(namespace: str, key: str) -> Path:
    safe_key = re.sub(r"[^a-zA-Z0-9_.-]+", "_", key)[:180]
    return CACHE_DIR / namespace / f"{safe_key}.json"


def _read_cache(namespace: str, key: str) -> Any | None:
    path = _cache_path(namespace, key)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _write_cache(namespace: str, key: str, payload: Any) -> None:
    path = _cache_path(namespace, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _respect_rate_limit() -> None:
    global _LAST_REQUEST_AT
    elapsed = time.monotonic() - _LAST_REQUEST_AT
    if elapsed < REQUEST_DELAY_SECONDS:
        time.sleep(REQUEST_DELAY_SECONDS - elapsed)
    _LAST_REQUEST_AT = time.monotonic()


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", value)
    cleaned = html.unescape(cleaned)
    return " ".join(cleaned.split())


def _slug(value: str) -> str:
    value = value.lower().replace("ё", "e")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "asset"


def _api_get(params: dict[str, Any], retries: int = 3) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(params)
    cached = _read_cache("commons-api", encoded)
    if cached is not None:
        return cached
    request = urllib.request.Request(
        f"{COMMONS_API}?{encoded}",
        headers={"User-Agent": USER_AGENT},
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            _respect_rate_limit()
            with urllib.request.urlopen(request, timeout=25) as response:
                payload = json.loads(response.read().decode("utf-8"))
                _write_cache("commons-api", encoded, payload)
                return payload
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")
                delay = int(retry_after) if retry_after and retry_after.isdigit() else 8 + attempt * 10
                print(f"Commons throttled request; sleeping {delay}s", flush=True)
                time.sleep(delay)
            else:
                time.sleep(1.5 + attempt * 2)
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(1.5 + attempt * 2)
    raise RuntimeError(f"Commons API request failed: {last_error}")


def _wikidata_sparql(query: str, retries: int = 3) -> dict[str, Any]:
    cached = _read_cache("wikidata", query)
    if cached is not None:
        return cached
    encoded = urllib.parse.urlencode({"query": query, "format": "json"})
    request = urllib.request.Request(
        f"{WIKIDATA_SPARQL}?{encoded}",
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": USER_AGENT,
        },
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            _respect_rate_limit()
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
                _write_cache("wikidata", query, payload)
                return payload
        except urllib.error.HTTPError as exc:
            last_error = exc
            delay = 10 + attempt * 15 if exc.code == 429 else 2 + attempt * 3
            print(f"Wikidata request failed with {exc.code}; sleeping {delay}s", flush=True)
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(2 + attempt * 3)
    raise RuntimeError(f"Wikidata SPARQL request failed: {last_error}")


def _download(url: str, retries: int = 8) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            _respect_rate_limit()
            with urllib.request.urlopen(request, timeout=35) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")
                server_delay = (
                    int(retry_after)
                    if retry_after and retry_after.isdigit()
                    else 8 + attempt * 10
                )
                if server_delay > 30:
                    raise RuntimeError(
                        f"download throttled with Retry-After={server_delay}s"
                    ) from exc
                delay = max(6, server_delay)
                print(f"Download throttled; sleeping {delay}s", flush=True)
                time.sleep(delay)
            else:
                time.sleep(1.5 + attempt * 2)
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(1.5 + attempt * 2)
    raise RuntimeError(f"Download failed for {url}: {last_error}")


def _license_is_allowed(license_name: str) -> bool:
    normalized = license_name.lower().replace("_", " ").replace("/", " ")
    if any(marker in normalized for marker in BLOCKED_LICENSE_MARKERS):
        return False
    return normalized.startswith(ALLOWED_LICENSE_PREFIXES) or any(
        normalized == prefix.strip() for prefix in ALLOWED_LICENSE_PREFIXES
    )


def _latin_binomial(name_latin: str) -> tuple[str, str] | None:
    normalized = re.sub(r"\s+", " ", name_latin.strip())
    parts = normalized.split(" ")
    if len(parts) < 2:
        return None
    genus, species = parts[0], parts[1]
    if not re.fullmatch(r"[A-Z][A-Za-z-]+", genus):
        return None
    if not re.fullmatch(r"[a-z][a-z-]+", species):
        return None
    if species in {"sp", "spp"}:
        return None
    return genus, species


def _title_matches_binomial(title: str, binomial: tuple[str, str]) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", title.lower())
    genus, species = binomial
    return genus.lower() in normalized.split() and species.lower() in normalized.split()


def _commons_search(query: str, expected_binomial: tuple[str, str] | None) -> CommonsImage | None:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrsearch": query,
        "gsrlimit": "30",
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": "960",
    }
    data = _api_get(params)
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None

    for page in sorted(pages.values(), key=lambda item: item.get("index", 9999)):
        title = page.get("title", "")
        imageinfo = (page.get("imageinfo") or [{}])[0]
        mime = imageinfo.get("mime", "")
        if not mime.startswith("image/"):
            continue
        if expected_binomial and not _title_matches_binomial(title, expected_binomial):
            continue

        metadata = imageinfo.get("extmetadata") or {}
        license_name = _strip_html(metadata.get("LicenseShortName", {}).get("value"))
        if not _license_is_allowed(license_name):
            continue

        source_url = imageinfo.get("thumburl") or imageinfo.get("url")
        source_page = imageinfo.get("descriptionurl") or ""
        if not source_url or not source_page:
            continue

        author = _strip_html(metadata.get("Artist", {}).get("value"))
        if not author:
            author = _strip_html(metadata.get("Credit", {}).get("value"))
        license_url = _strip_html(metadata.get("LicenseUrl", {}).get("value"))

        return CommonsImage(
            file_title=title,
            source_url=source_url,
            original_url=imageinfo.get("url", source_url),
            source_page=source_page,
            author=author or "Wikimedia Commons contributor",
            license=license_name,
            license_url=license_url,
            mime=mime,
        )

    return None


def _commons_image_from_page(page: dict[str, Any]) -> CommonsImage | None:
    title = page.get("title", "")
    imageinfo = (page.get("imageinfo") or [{}])[0]
    mime = imageinfo.get("mime", "")
    if not mime.startswith("image/"):
        return None

    metadata = imageinfo.get("extmetadata") or {}
    license_name = _strip_html(metadata.get("LicenseShortName", {}).get("value"))
    if not _license_is_allowed(license_name):
        return None

    source_url = imageinfo.get("thumburl") or imageinfo.get("url")
    source_page = imageinfo.get("descriptionurl") or ""
    if not source_url or not source_page:
        return None

    author = _strip_html(metadata.get("Artist", {}).get("value"))
    if not author:
        author = _strip_html(metadata.get("Credit", {}).get("value"))
    license_url = _strip_html(metadata.get("LicenseUrl", {}).get("value"))

    return CommonsImage(
        file_title=title,
        source_url=source_url,
        original_url=imageinfo.get("url", source_url),
        source_page=source_page,
        author=author or "Wikimedia Commons contributor",
        license=license_name,
        license_url=license_url,
        mime=mime,
    )


def _commons_images_for_titles(titles: list[str]) -> dict[str, CommonsImage]:
    result: dict[str, CommonsImage] = {}
    unique_titles = sorted({title for title in titles if title.startswith("File:")})
    for start in range(0, len(unique_titles), 40):
        chunk = unique_titles[start : start + 40]
        data = _api_get(
            {
                "action": "query",
                "format": "json",
                "titles": "|".join(chunk),
                "prop": "imageinfo",
                "iiprop": "url|mime|extmetadata",
                "iiurlwidth": "960",
            }
        )
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            image = _commons_image_from_page(page)
            if image is not None:
                result[page.get("title", "")] = image
    return result


def _file_title_from_commons_file_path(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    filename = urllib.parse.unquote(Path(parsed.path).name)
    if not filename:
        return None
    return f"File:{filename}"


def _search_taxon_name(species: SpeciesCandidate) -> tuple[str, bool]:
    alias = PHOTO_SEARCH_ALIASES.get(species.name_ru)
    if alias:
        return alias, True
    binomial = _latin_binomial(species.name_latin)
    if binomial:
        return f"{binomial[0]} {binomial[1]}", True
    return species.name_latin.strip() or species.name_ru, False


def _wikidata_images_for_taxa(taxon_names: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {taxon_name: [] for taxon_name in taxon_names}
    unique_names = sorted({name for name in taxon_names if name})
    for start in range(0, len(unique_names), 80):
        chunk = unique_names[start : start + 80]
        values = " ".join(json.dumps(name, ensure_ascii=False) for name in chunk)
        query = f"""
SELECT ?taxonName ?image WHERE {{
  VALUES ?taxonName {{ {values} }}
  ?item wdt:P225 ?taxonName;
        wdt:P18 ?image.
}}
"""
        data = _wikidata_sparql(query)
        for binding in data.get("results", {}).get("bindings", []):
            taxon_name = binding.get("taxonName", {}).get("value", "")
            image_url = binding.get("image", {}).get("value", "")
            file_title = _file_title_from_commons_file_path(image_url)
            if taxon_name and file_title:
                result.setdefault(taxon_name, []).append(file_title)
    return result


def _save_as_clean_jpeg(image: CommonsImage, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 0:
        return
    try:
        raw = _download(image.source_url, retries=2)
    except RuntimeError:
        if image.original_url and image.original_url != image.source_url:
            raw = _download(image.original_url, retries=6)
        else:
            raise
    with Image.open(BytesIO(raw)) as opened:
        normalized = ImageOps.exif_transpose(opened)
        if normalized.mode not in ("RGB", "L"):
            background = Image.new("RGB", normalized.size, "white")
            if normalized.mode == "RGBA":
                background.paste(normalized, mask=normalized.getchannel("A"))
            else:
                background.paste(normalized.convert("RGB"))
            normalized = background
        else:
            normalized = normalized.convert("RGB")

        normalized.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        normalized.save(destination, format="JPEG", quality=86, optimize=True, progressive=True)


def _catalog_candidates() -> list[SpeciesCandidate]:
    species_by_name: dict[str, dict[str, Any]] = {
        item["name_ru"]: dict(item) for item in SPECIES_DATA
    }

    for item in CATALOG_UPSERTS:
        existing = species_by_name.get(item["name_ru"], {})
        existing.update(item)
        species_by_name[item["name_ru"]] = existing

    for canonical_name, duplicate_name in CANONICAL_DUPLICATES:
        if canonical_name in species_by_name and duplicate_name in species_by_name:
            species_by_name.pop(duplicate_name, None)
        elif duplicate_name in species_by_name:
            duplicate = species_by_name.pop(duplicate_name)
            duplicate["name_ru"] = canonical_name
            species_by_name[canonical_name] = duplicate

    for name_ru, photo_urls in PHOTO_OVERRIDES.items():
        if name_ru in species_by_name:
            species_by_name[name_ru]["photo_urls"] = photo_urls

    for name_ru, name_latin in LATIN_NAME_UPDATES.items():
        if name_ru in species_by_name:
            species_by_name[name_ru]["name_latin"] = name_latin

    for name_ru, photo_urls in PHOTO_UPDATES.items():
        if name_ru in species_by_name and not species_by_name[name_ru].get("photo_urls"):
            species_by_name[name_ru]["photo_urls"] = photo_urls

    for name_ru in REMOVED_SPECIES_NAMES:
        species_by_name.pop(name_ru, None)

    result: list[SpeciesCandidate] = []
    for item in species_by_name.values():
        photos = item.get("photo_urls") or []
        if isinstance(photos, str):
            photos = [photos]
        result.append(
            SpeciesCandidate(
                name_ru=item["name_ru"],
                name_latin=item.get("name_latin", ""),
                group=item.get("group", ""),
                original_photo_urls=list(photos),
            )
        )
    return sorted(result, key=lambda item: (item.group, item.name_ru))


def _audit_row(
    *,
    asset_id: str,
    asset_type: str,
    section: str,
    name_ru: str = "",
    name_latin: str = "",
    local_path: str = "",
    source_url: str = "",
    source_page: str = "",
    author: str = "",
    license_name: str = "",
    license_url: str = "",
    status: str,
    risk: str,
    decision: str,
    permission_candidate: str = "no",
    notes: str = "",
) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "type": asset_type,
        "section": section,
        "name_ru": name_ru,
        "name_latin": name_latin,
        "local_path": local_path,
        "source_url": source_url,
        "source_page": source_page,
        "author": author,
        "license": license_name,
        "license_url": license_url,
        "attribution_required": "yes" if license_name.startswith(("CC BY", "GFDL")) else "no",
        "status": status,
        "risk": risk,
        "decision": decision,
        "permission_candidate": permission_candidate,
        "notes": notes,
    }


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _build_species_images(rows: list[dict[str, str]]) -> dict[str, str | None]:
    mapping: dict[str, str | None] = {}
    used_slugs: set[str] = set()
    SPECIES_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    candidates = _catalog_candidates()
    search_by_name = {species.name_ru: _search_taxon_name(species) for species in candidates}
    wikidata_titles_by_taxon: dict[str, list[str]] = {}
    wikidata_images_by_title: dict[str, CommonsImage] = {}
    if not NO_COMMONS_LOOKUP:
        taxon_names = [taxon_name for taxon_name, _is_exact in search_by_name.values() if taxon_name]
        print(f"Querying Wikidata P18 for {len(set(taxon_names))} taxa", flush=True)
        wikidata_titles_by_taxon = _wikidata_images_for_taxa(taxon_names)
        all_titles = [
            title
            for titles in wikidata_titles_by_taxon.values()
            for title in titles
        ]
        print(f"Checking Commons licenses for {len(set(all_titles))} Wikidata images", flush=True)
        wikidata_images_by_title = _commons_images_for_titles(all_titles)

    for index, species in enumerate(candidates, start=1):
        search_name, exact_taxon = search_by_name[species.name_ru]
        binomial = _latin_binomial(search_name)
        image = None
        source_method = ""
        if NO_COMMONS_LOOKUP:
            print(f"[{index:03d}] {species.name_ru}: Commons lookup disabled", flush=True)
        else:
            for title in wikidata_titles_by_taxon.get(search_name, []):
                image = wikidata_images_by_title.get(title)
                if image is not None:
                    source_method = "Wikidata P18"
                    break
            if image is None:
                expected_binomial = binomial if exact_taxon and binomial else None
                print(f"[{index:03d}] {species.name_ru}: Commons search {search_name}", flush=True)
                image = _commons_search(search_name, expected_binomial)
                if image is not None:
                    source_method = "Commons search"

        if image:
            base_slug = _slug(search_name)
            slug = base_slug
            counter = 2
            while slug in used_slugs:
                slug = f"{base_slug}-{counter}"
                counter += 1
            used_slugs.add(slug)
            destination = SPECIES_MEDIA_DIR / f"{slug}.jpg"
            local_path = ""
            download_error = ""
            if DOWNLOAD_MEDIA:
                try:
                    _save_as_clean_jpeg(image, destination)
                    local_path = _relative(destination)
                    mapping[species.name_ru] = f"/api/media/species/{destination.name}"
                except Exception as exc:
                    download_error = str(exc)
                    print(f"  download failed, leaving species without portal photo: {exc}", flush=True)
                    mapping[species.name_ru] = None
            else:
                mapping[species.name_ru] = image.source_url
            if DOWNLOAD_MEDIA and download_error:
                rows.append(
                    _audit_row(
                        asset_id=f"species-image:{species.name_ru}",
                        asset_type="species_image",
                        section="species catalog",
                        name_ru=species.name_ru,
                        name_latin=species.name_latin,
                        source_url=image.source_url,
                        source_page=image.source_page,
                        author=image.author,
                        license_name=image.license,
                        license_url=image.license_url,
                        status="verified_source_download_failed",
                        risk="medium",
                        decision="retry_download_or_manual",
                        permission_candidate="no",
                        notes=(
                            f"{source_method}; Wikimedia Commons file {image.file_title}; "
                            f"license is acceptable, but local download failed: {download_error}"
                        ),
                    )
                )
                continue
            taxon_note = (
                "exact taxon match"
                if exact_taxon
                else "representative image for non-binomial catalog taxon"
            )

            rows.append(
                _audit_row(
                    asset_id=f"species-image:{species.name_ru}",
                    asset_type="species_image",
                    section="species catalog",
                    name_ru=species.name_ru,
                    name_latin=species.name_latin,
                    local_path=local_path,
                    source_url=image.source_url,
                    source_page=image.source_page,
                    author=image.author,
                    license_name=image.license,
                    license_url=image.license_url,
                    status="verified",
                    risk="low" if exact_taxon else "medium",
                    decision="use",
                    notes=(
                        f"{source_method}; Wikimedia Commons file {image.file_title}; {taxon_note}; "
                        + (
                            "normalized to local JPEG without EXIF."
                            if local_path
                            else "referenced by verified Commons URL; local vendoring is intentionally skipped to avoid bulk-download throttling."
                        )
                    ),
                )
            )
        else:
            mapping[species.name_ru] = None
            originals = species.original_photo_urls or [""]
            notes = (
                "Commons lookup was disabled for strict corporate media lockdown; "
                "legacy image is not used until written permission or a manually verified licensed replacement is added."
                if NO_COMMONS_LOOKUP
                else f"No conservative licensed replacement found automatically for search taxon {search_name!r}; get written permission or pick a licensed replacement manually."
            )
            for original in originals:
                rows.append(
                    _audit_row(
                        asset_id=f"species-image:{species.name_ru}",
                        asset_type="species_image",
                        section="species catalog",
                        name_ru=species.name_ru,
                        name_latin=species.name_latin,
                        local_path=original,
                        status="needs_permission",
                        risk="high",
                        decision="remove_until_permission",
                        permission_candidate="yes",
                        notes=notes,
                    )
                )

    return mapping


def _append_supplied_hero_row(rows: list[dict[str, str]]) -> str:
    rows.append(
        _audit_row(
            asset_id="frontend-hero:swan",
            asset_type="frontend_image",
            section="home hero",
            name_ru="Лебедь-шипун",
            name_latin="Cygnus olor",
            local_path="frontend/public/img/swan-hero.png",
            source_url="generated by product owner",
            author="product owner",
            license_name="owner-generated project asset",
            status="verified",
            risk="low",
            decision="use",
            notes="Hero image generated by product owner and provided on 2026-06-03 for the title page header.",
        )
    )
    return "/img/swan-hero.png"


def _build_hero_and_group_covers(rows: list[dict[str, str]]) -> tuple[str, dict[str, str]]:
    hero_url = ""
    group_urls: dict[str, str] = {}
    supplied_hero = FRONTEND_IMG_DIR / "swan-hero.png"
    if NO_COMMONS_LOOKUP:
        if supplied_hero.exists():
            hero_url = _append_supplied_hero_row(rows)
        else:
            hero_url = "/img/swan-hero.svg"
            rows.append(
                _audit_row(
                    asset_id="frontend-hero:swan",
                    asset_type="frontend_image",
                    section="home hero",
                    name_ru="Лебедь",
                    local_path="frontend/public/img/swan-hero.svg",
                    source_url="project-generated vector",
                    author="Green Book project",
                    license_name="internal project asset",
                    status="verified",
                    risk="low",
                    decision="use",
                    notes="Vector fallback used when no owner-supplied hero image is present.",
                )
            )
        for group, label, _latin in GROUP_COVER_QUERIES.values():
            group_urls[group] = f"/img/group-covers/{group}.svg"
            rows.append(
                _audit_row(
                    asset_id=f"group-cover:{group}",
                    asset_type="frontend_image",
                    section="group cover",
                    name_ru=label,
                    local_path=f"frontend/public/img/group-covers/{group}.svg",
                    source_url="project-generated vector",
                    author="Green Book project",
                    license_name="internal project asset",
                    status="verified",
                    risk="low",
                    decision="use",
                    notes="Vector cover replaces legacy species-pdf preview image.",
                )
            )
        rows.append(
            _audit_row(
                asset_id="exhibition-placeholder",
                asset_type="frontend_image",
                section="photo exhibition",
                local_path="frontend/public/img/exhibition-rights-pending.svg",
                source_url="project-generated vector",
                author="Green Book project",
                license_name="internal project asset",
                status="verified",
                risk="low",
                decision="use_until_written_permission",
                notes="Placeholder shown while exhibition photo permissions are pending.",
            )
        )
        return hero_url, group_urls

    hero = None if supplied_hero.exists() else _commons_search("Cygnus olor", ("Cygnus", "olor"))
    if supplied_hero.exists():
        hero_url = _append_supplied_hero_row(rows)
    elif hero:
        local_path = ""
        if DOWNLOAD_MEDIA:
            destination = FRONTEND_IMG_DIR / "swan-hero.jpg"
            _save_as_clean_jpeg(hero, destination)
            local_path = _relative(destination)
            hero_url = "/img/swan-hero.jpg"
        else:
            hero_url = hero.source_url
        rows.append(
            _audit_row(
                asset_id="frontend-hero:swan",
                asset_type="frontend_image",
                section="home hero",
                name_ru="Лебедь-шипун",
                name_latin="Cygnus olor",
                local_path=local_path,
                source_url=hero.source_url,
                source_page=hero.source_page,
                author=hero.author,
                license_name=hero.license,
                license_url=hero.license_url,
                status="verified",
                risk="low",
                decision="use",
                notes=f"Replaces unverified frontend/public/img/swan-hero.png; Commons file {hero.file_title}.",
            )
        )
    else:
        rows.append(
            _audit_row(
                asset_id="frontend-hero:swan",
                asset_type="frontend_image",
                section="home hero",
                local_path="frontend/public/img/swan-hero.png",
                status="needs_permission",
                risk="high",
                decision="remove_until_permission",
                permission_candidate="yes",
                notes="No safe automated replacement found for hero.",
            )
        )

    if DOWNLOAD_MEDIA:
        GROUP_COVER_DIR.mkdir(parents=True, exist_ok=True)
    for group, label, latin in GROUP_COVER_QUERIES.values():
        binomial = _latin_binomial(latin)
        image = _commons_search(latin, binomial)
        if not image:
            rows.append(
                _audit_row(
                    asset_id=f"group-cover:{group}",
                    asset_type="frontend_image",
                    section="group cover",
                    name_ru=label,
                    name_latin=latin,
                    status="needs_replacement",
                    risk="medium",
                    decision="show_fallback",
                    notes="No safe automated group cover found.",
                )
            )
            continue
        local_path = ""
        if DOWNLOAD_MEDIA:
            destination = GROUP_COVER_DIR / f"{group}.jpg"
            _save_as_clean_jpeg(image, destination)
            local_path = _relative(destination)
            group_urls[group] = f"/img/group-covers/{group}.jpg"
        else:
            group_urls[group] = image.source_url
        rows.append(
            _audit_row(
                asset_id=f"group-cover:{group}",
                asset_type="frontend_image",
                section="group cover",
                name_ru=label,
                name_latin=latin,
                local_path=local_path,
                source_url=image.source_url,
                source_page=image.source_page,
                author=image.author,
                license_name=image.license,
                license_url=image.license_url,
                status="verified",
                risk="low",
                decision="use",
                notes=(
                    f"Wikimedia Commons file {image.file_title}; "
                    + (
                        "normalized to local JPEG without EXIF."
                        if local_path
                        else "referenced by verified Commons URL; local vendoring is intentionally skipped to avoid bulk-download throttling."
                    )
                ),
            )
        )
        time.sleep(0.15)
    return hero_url, group_urls


def _build_audio_rows(rows: list[dict[str, str]]) -> list[str]:
    unsafe = sorted(XENO_AUDIO_SOURCE_OVERRIDES)
    unsafe_set = set(unsafe)
    for name_ru, values in sorted(AUDIO_UPDATES.items()):
        audio_url = values.get("audio_url", "")
        license_name = values.get("audio_license", "")
        source = values.get("audio_source", "")
        filename = audio_url.removeprefix("/api/media/species-audio/") if audio_url.startswith("/api/media/") else audio_url
        is_unsafe = name_ru in unsafe_set or not _license_is_allowed(license_name)
        if name_ru in unsafe_set:
            xc_id, recordist, xeno_license = XENO_AUDIO_SOURCE_OVERRIDES[name_ru]
            filename = LOCAL_AUDIO_FILES.get(name_ru, filename)
            source = f"https://xeno-canto.org/{xc_id}"
            license_name = xeno_license
            author = f"Xeno-canto / {recordist}"
        else:
            author = source
        rows.append(
            _audit_row(
                asset_id=f"species-audio:{name_ru}",
                asset_type="species_audio",
                section="species catalog",
                name_ru=name_ru,
                local_path=(
                    f"backend/media/species-audio/{filename}"
                    if name_ru in unsafe_set or audio_url.startswith("/api/media/")
                    else audio_url
                ),
                source_url=source,
                author=author,
                license_name=license_name,
                status="needs_permission" if is_unsafe else "verified",
                risk="high" if is_unsafe else "low",
                decision="exclude_until_permission" if is_unsafe else "use",
                permission_candidate="yes" if is_unsafe else "no",
                notes=(
                    "NC/ND or otherwise incompatible audio is disabled for corporate deploy."
                    if is_unsafe
                    else "Audio may be used with required attribution/license compliance."
                ),
            )
        )
    return unsafe


def _build_exhibition_rows(rows: list[dict[str, str]]) -> None:
    try:
        text = (ROOT / "frontend" / "src" / "data" / "exhibitionBirds2025.ts").read_text(encoding="utf-8")
    except FileNotFoundError:
        return

    pattern = (
        r"photoNumber:\s*(\d+).*?"
        r"(?:originalImage|image):\s*`\$\{imageBase\}/(photo-\d+\.jpg)`.*?"
        r"author:\s*'([^']+)'"
    )
    for match in re.finditer(pattern, text, re.S):
        number, filename, author = match.groups()
        rows.append(
            _audit_row(
                asset_id=f"exhibition:photo-{number}",
                asset_type="exhibition_image",
                section="photo exhibition",
                local_path=f"frontend/public/img/exhibition/birds-2025/{filename}",
                source_url="Фото птицы НЛМК 2025",
                author=author,
                license_name="permission required",
                status="needs_permission",
                risk="high",
                decision="hide_until_written_permission",
                permission_candidate="yes",
                notes="Specific exhibition photo; no analog should replace it without changing the exhibit meaning.",
            )
        )


def _write_audit(rows: list[dict[str, str]]) -> None:
    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "asset_id",
        "type",
        "section",
        "name_ru",
        "name_latin",
        "local_path",
        "source_url",
        "source_page",
        "author",
        "license",
        "license_url",
        "attribution_required",
        "status",
        "risk",
        "decision",
        "permission_candidate",
        "notes",
    ]
    with AUDIT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_generated_seed(species_mapping: dict[str, str | None], unsafe_audio: list[str]) -> None:
    lines = [
        '"""Apply media rights decisions from docs/content-rights/media-audit.csv.',
        "",
        "Generated by scripts/build_media_rights_audit.py. Do not edit mapping by hand;",
        "regenerate the audit when media rights decisions change.",
        '"""',
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "",
        "from sqlalchemy import or_",
        "from sqlalchemy.orm import Session",
        "",
        "from app.models.observation import Observation, ObsMedia",
        "from app.models.species import Species",
        "",
        "SPECIES_PHOTO_URLS: dict[str, list[str] | None] = {",
    ]
    for name_ru, url in sorted(species_mapping.items()):
        if url is None:
            lines.append(f"    {name_ru!r}: None,")
        else:
            lines.append(f"    {name_ru!r}: [{url!r}],")
    lines += [
        "}",
        "",
        "UNSAFE_AUDIO_SPECIES: set[str] = {",
    ]
    for name_ru in sorted(unsafe_audio):
        lines.append(f"    {name_ru!r},")
    lines += [
        "}",
        "",
        "",
        "def _assign_if_changed(species: Species, values: dict[str, Any]) -> bool:",
        "    changed = False",
        "    for key, value in values.items():",
        "        if getattr(species, key) != value:",
        "            setattr(species, key, value)",
        "            changed = True",
        "    return changed",
        "",
        "",
        "def apply_media_rights_safe(db: Session) -> dict[str, int]:",
        "    summary = {",
        "        'photo_updated': 0,",
        "        'audio_disabled': 0,",
        "        'legacy_observation_media_deleted': 0,",
        "        'unconsented_observation_media_deleted': 0,",
        "        'missing_species': 0,",
        "    }",
        "    for name_ru, photo_urls in SPECIES_PHOTO_URLS.items():",
        "        species = db.query(Species).filter(Species.name_ru == name_ru).first()",
        "        if species is None:",
        "            summary['missing_species'] += 1",
        "            continue",
        "        if species.photo_urls != photo_urls:",
        "            species.photo_urls = photo_urls",
        "            summary['photo_updated'] += 1",
        "",
        "    for name_ru in UNSAFE_AUDIO_SPECIES:",
        "        species = db.query(Species).filter(Species.name_ru == name_ru).first()",
        "        if species is None:",
        "            summary['missing_species'] += 1",
        "            continue",
        "        if _assign_if_changed(",
        "            species,",
        "            {",
        "                'audio_url': None,",
        "                'audio_title': None,",
        "                'audio_source': None,",
        "                'audio_license': None,",
        "            },",
        "        ):",
        "            summary['audio_disabled'] += 1",
        "",
        "    summary['legacy_observation_media_deleted'] = (",
        "        db.query(ObsMedia)",
        "        .filter(",
        "            or_(",
        "                ObsMedia.s3_key.like('species-pdf/%'),",
        "                ObsMedia.thumbnail_key.like('species-pdf/%'),",
        "            )",
        "        )",
        "        .delete(synchronize_session=False)",
        "    )",
        "    summary['unconsented_observation_media_deleted'] = (",
        "        db.query(ObsMedia)",
        "        .filter(",
        "            ObsMedia.observation_id.in_(",
        "                db.query(Observation.id).filter(",
        "                    Observation.content_notice_accepted_at.is_(None)",
        "                )",
        "            )",
        "        )",
        "        .delete(synchronize_session=False)",
        "    )",
        "",
        "    db.flush()",
        "    return summary",
        "",
    ]
    GENERATED_SEED.write_text("\n".join(lines), encoding="utf-8")


def _write_generated_frontend_media(hero_url: str, group_urls: dict[str, str]) -> None:
    GENERATED_FRONTEND_MEDIA.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "// Generated by scripts/build_media_rights_audit.py.",
        "// Safe media URLs are sourced from docs/content-rights/media-audit.csv.",
        f"export const mediaRightsHeroImage = {hero_url!r}",
        "",
        "export const mediaRightsGroupCovers: Record<string, string> = {",
    ]
    for group, url in sorted(group_urls.items()):
        lines.append(f"  {group!r}: {url!r},")
    lines += [
        "}",
        "",
    ]
    GENERATED_FRONTEND_MEDIA.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    rows: list[dict[str, str]] = []
    species_mapping = _build_species_images(rows)
    hero_url, group_urls = _build_hero_and_group_covers(rows)
    unsafe_audio = _build_audio_rows(rows)
    _build_exhibition_rows(rows)
    _write_audit(rows)
    _write_generated_seed(species_mapping, unsafe_audio)
    _write_generated_frontend_media(hero_url, group_urls)
    verified_species = sum(1 for value in species_mapping.values() if value)
    missing_species = sum(1 for value in species_mapping.values() if not value)
    print(f"Media audit written to {AUDIT_CSV}")
    print(f"Generated seed written to {GENERATED_SEED}")
    print(f"Generated frontend media written to {GENERATED_FRONTEND_MEDIA}")
    print(f"Species images: {verified_species} verified, {missing_species} disabled pending permission")
    print(f"Unsafe audio disabled: {len(unsafe_audio)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
