# Species Directory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Species directory — backend CRUD API with filtering/search, frontend list and detail pages, seed data from the Green Book PDF.

**Architecture:** FastAPI router with Pydantic schemas for Species CRUD. Vue.js pages for list (grid with cards, filters by group/category, search) and detail view (photo, metadata, rules). Admin endpoints for species management. Seed script to populate initial data from the PDF catalog.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, Vue 3, Vue Router, Element Plus

---

## File Structure

```
backend/
├── app/
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── species.py        # Pydantic request/response schemas
│   ├── routers/
│   │   └── species.py         # GET list, GET detail, POST/PUT/DELETE (admin)
│   └── seed/
│       └── species_data.py    # Initial species data from Green Book PDF
├── tests/
│   └── test_species.py
frontend/
├── src/
│   ├── views/
│   │   ├── SpeciesListView.vue   # Grid + filters + search
│   │   └── SpeciesDetailView.vue # Full species card
│   ├── components/
│   │   └── SpeciesCard.vue       # Reusable card component
│   └── router/
│       └── index.ts              # Add /species and /species/:id routes
```

---

### Task 1: Pydantic Schemas for Species

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/species.py`

- [ ] **Step 1: Create backend/app/schemas/__init__.py**

```python
```

- [ ] **Step 2: Create backend/app/schemas/species.py**

```python
from pydantic import BaseModel
from app.models.species import SpeciesGroup, SpeciesCategory


class SpeciesBase(BaseModel):
    name_ru: str
    name_latin: str
    group: SpeciesGroup
    category: SpeciesCategory
    conservation_status: str | None = None
    is_poisonous: bool = False
    season_info: str | None = None
    biotopes: str | None = None
    description: str | None = None
    do_dont_rules: str | None = None
    qr_url: str | None = None
    photo_urls: list[str] | None = None


class SpeciesCreate(SpeciesBase):
    pass


class SpeciesUpdate(BaseModel):
    name_ru: str | None = None
    name_latin: str | None = None
    group: SpeciesGroup | None = None
    category: SpeciesCategory | None = None
    conservation_status: str | None = None
    is_poisonous: bool | None = None
    season_info: str | None = None
    biotopes: str | None = None
    description: str | None = None
    do_dont_rules: str | None = None
    qr_url: str | None = None
    photo_urls: list[str] | None = None


class SpeciesResponse(SpeciesBase):
    id: int
    model_config = {"from_attributes": True}


class SpeciesListResponse(BaseModel):
    items: list[SpeciesResponse]
    total: int
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: Pydantic schemas for Species CRUD"
```

---

### Task 2: Species API Router

**Files:**
- Create: `backend/app/routers/species.py`
- Modify: `backend/app/main.py` — register species router

- [ ] **Step 1: Create backend/app/routers/species.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.database import get_db
from app.models.species import Species, SpeciesGroup, SpeciesCategory
from app.models.user import User, UserRole
from app.schemas.species import (
    SpeciesCreate,
    SpeciesListResponse,
    SpeciesResponse,
    SpeciesUpdate,
)

router = APIRouter(prefix="/api/species", tags=["species"])


@router.get("", response_model=SpeciesListResponse)
def list_species(
    group: SpeciesGroup | None = None,
    category: SpeciesCategory | None = None,
    search: str | None = Query(None, min_length=2),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Species)
    if group:
        query = query.filter(Species.group == group)
    if category:
        query = query.filter(Species.category == category)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Species.name_ru.ilike(search_term))
            | (Species.name_latin.ilike(search_term))
        )
    total = query.count()
    items = query.order_by(Species.name_ru).offset(skip).limit(limit).all()
    return SpeciesListResponse(items=items, total=total)


@router.get("/{species_id}", response_model=SpeciesResponse)
def get_species(species_id: int, db: Session = Depends(get_db)):
    species = db.query(Species).filter(Species.id == species_id).first()
    if not species:
        raise HTTPException(status_code=404, detail="Species not found")
    return species


@router.post("", response_model=SpeciesResponse, status_code=201)
def create_species(
    data: SpeciesCreate,
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    species = Species(**data.model_dump())
    db.add(species)
    db.commit()
    db.refresh(species)
    return species


@router.put("/{species_id}", response_model=SpeciesResponse)
def update_species(
    species_id: int,
    data: SpeciesUpdate,
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    species = db.query(Species).filter(Species.id == species_id).first()
    if not species:
        raise HTTPException(status_code=404, detail="Species not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(species, key, value)
    db.commit()
    db.refresh(species)
    return species


@router.delete("/{species_id}", status_code=204)
def delete_species(
    species_id: int,
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    species = db.query(Species).filter(Species.id == species_id).first()
    if not species:
        raise HTTPException(status_code=404, detail="Species not found")
    db.delete(species)
    db.commit()
```

- [ ] **Step 2: Register router in main.py**

Add to `backend/app/main.py` after the health router import:

```python
from app.routers import health, species
```

And add:

```python
app.include_router(species.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/species.py backend/app/main.py
git commit -m "feat: Species CRUD API — list with filters, detail, create/update/delete"
```

---

### Task 3: Species API Tests

**Files:**
- Create: `backend/tests/test_species.py`

- [ ] **Step 1: Create backend/tests/test_species.py**

```python
from tests.conftest import make_token


def _create_species(client, token=None):
    """Helper to create a species via API."""
    if token is None:
        token = make_token(external_id="admin-001", name="Admin", email="admin@nlmk.com")
    # First, ensure user exists with admin role
    # (auto-created as employee, need to set admin manually for tests)
    data = {
        "name_ru": "Полынь обыкновенная",
        "name_latin": "Artemisia vulgaris",
        "group": "plants",
        "category": "ruderal",
        "is_poisonous": False,
        "description": "Многолетнее травянистое растение",
    }
    return client.post(
        "/api/species",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )


def test_list_species_empty(client):
    response = client.get("/api/species")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_species_with_filter(client, admin_token, db):
    # Need admin role to create species
    from app.models.user import User, UserRole

    # Create admin user directly in DB
    user = User(
        external_id="admin-001",
        display_name="Admin",
        email="admin@nlmk.com",
        role=UserRole.admin,
    )
    db.add(user)
    db.commit()

    # Create a species
    response = client.post(
        "/api/species",
        json={
            "name_ru": "Полынь обыкновенная",
            "name_latin": "Artemisia vulgaris",
            "group": "plants",
            "category": "ruderal",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201

    # List with group filter
    response = client.get("/api/species?group=plants")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert data["items"][0]["name_latin"] == "Artemisia vulgaris"

    # List with wrong group filter
    response = client.get("/api/species?group=birds")
    data = response.json()
    assert data["total"] == 0


def test_get_species_detail(client, admin_token, db):
    from app.models.user import User, UserRole

    user = User(
        external_id="admin-002",
        display_name="Admin2",
        email="admin2@nlmk.com",
        role=UserRole.admin,
    )
    db.add(user)
    db.commit()

    token = make_token(external_id="admin-002", name="Admin2", email="admin2@nlmk.com")
    response = client.post(
        "/api/species",
        json={
            "name_ru": "Сорока",
            "name_latin": "Pica pica",
            "group": "birds",
            "category": "synanthropic",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    species_id = response.json()["id"]

    response = client.get(f"/api/species/{species_id}")
    assert response.status_code == 200
    assert response.json()["name_ru"] == "Сорока"


def test_get_species_not_found(client):
    response = client.get("/api/species/9999")
    assert response.status_code == 404


def test_search_species(client, db):
    from app.models.species import Species, SpeciesGroup, SpeciesCategory

    db.add(
        Species(
            name_ru="Лебедь-шипун",
            name_latin="Cygnus olor",
            group=SpeciesGroup.birds,
            category=SpeciesCategory.rare,
        )
    )
    db.commit()

    response = client.get("/api/species?search=лебедь")
    assert response.status_code == 200
    assert response.json()["total"] >= 1

    response = client.get("/api/species?search=Cygnus")
    assert response.json()["total"] >= 1


def test_create_species_requires_admin(client, employee_token):
    response = client.post(
        "/api/species",
        json={
            "name_ru": "Test",
            "name_latin": "Test test",
            "group": "plants",
            "category": "typical",
        },
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Commit**

```bash
git add backend/tests/test_species.py
git commit -m "test: Species API tests — list, filter, search, detail, auth"
```

---

### Task 4: Seed Species Data from Green Book

**Files:**
- Create: `backend/app/seed/__init__.py`
- Create: `backend/app/seed/species_data.py`
- Create: `backend/app/seed/run_seed.py`

- [ ] **Step 1: Create backend/app/seed/__init__.py**

Empty file.

- [ ] **Step 2: Create backend/app/seed/species_data.py**

Extract key species from the Green Book PDF. Include representatives from each group with real data:

```python
SPECIES_DATA = [
    # === РАСТЕНИЯ: Сорно-рудеральные ===
    {"name_ru": "Неравноцветник кровельный", "name_latin": "Anisantha tectorum", "group": "plants", "category": "ruderal"},
    {"name_ru": "Полынь обыкновенная", "name_latin": "Artemisia vulgaris", "group": "plants", "category": "ruderal"},
    {"name_ru": "Костёр растопыренный", "name_latin": "Bromus squarrosus", "group": "plants", "category": "ruderal"},
    {"name_ru": "Бассия венечная", "name_latin": "Bassia scoparia", "group": "plants", "category": "ruderal"},
    {"name_ru": "Полынь горькая", "name_latin": "Artemisia absinthium", "group": "plants", "category": "ruderal"},
    {"name_ru": "Лапчатка гусиная", "name_latin": "Argentina anserina", "group": "plants", "category": "ruderal"},
    {"name_ru": "Донник белый", "name_latin": "Melilotus albus", "group": "plants", "category": "ruderal"},
    {"name_ru": "Мятлик однолетний", "name_latin": "Poa annua", "group": "plants", "category": "ruderal"},
    {"name_ru": "Татарник колючий", "name_latin": "Onopordum acanthium", "group": "plants", "category": "ruderal"},
    {"name_ru": "Трёхреберник непахучий", "name_latin": "Tripleurospermum perforatum", "group": "plants", "category": "ruderal"},
    {"name_ru": "Иван-чай узколистный", "name_latin": "Chamaenerion angustifolium", "group": "plants", "category": "ruderal"},
    {"name_ru": "Бодяк полевой", "name_latin": "Cirsium arvense", "group": "plants", "category": "ruderal"},
    {"name_ru": "Подорожник большой", "name_latin": "Plantago major", "group": "plants", "category": "ruderal"},
    {"name_ru": "Пижма обыкновенная", "name_latin": "Tanacetum vulgare", "group": "plants", "category": "ruderal"},
    {"name_ru": "Синяк обыкновенный", "name_latin": "Echium vulgare", "group": "plants", "category": "ruderal"},
    {"name_ru": "Латук компасный", "name_latin": "Lactuca serriola", "group": "plants", "category": "ruderal"},
    {"name_ru": "Льнянка обыкновенная", "name_latin": "Linaria vulgaris", "group": "plants", "category": "ruderal"},
    {"name_ru": "Мать-и-мачеха обыкновенная", "name_latin": "Tussilago farfara", "group": "plants", "category": "ruderal"},
    {"name_ru": "Мышей зелёный", "name_latin": "Setaria viridis", "group": "plants", "category": "ruderal"},
    {"name_ru": "Горошек мышиный", "name_latin": "Vicia cracca", "group": "plants", "category": "ruderal"},
    {"name_ru": "Люцерна хмелевидная", "name_latin": "Medicago lupulina", "group": "plants", "category": "ruderal"},
    {"name_ru": "Клевер ползучий", "name_latin": "Trifolium repens", "group": "plants", "category": "ruderal"},
    {"name_ru": "Робиния псевдоакация", "name_latin": "Robinia pseudoacacia", "group": "plants", "category": "ruderal"},
    # === РАСТЕНИЯ: Типичные ===
    {"name_ru": "Тополь чёрный", "name_latin": "Populus nigra", "group": "plants", "category": "typical"},
    {"name_ru": "Клён ясенелистный", "name_latin": "Acer negundo", "group": "plants", "category": "typical"},
    {"name_ru": "Берёза повислая", "name_latin": "Betula pendula", "group": "plants", "category": "typical"},
    {"name_ru": "Ива белая", "name_latin": "Salix alba", "group": "plants", "category": "typical"},
    # === РАСТЕНИЯ: Редкие ===
    {"name_ru": "Ковыль перистый", "name_latin": "Stipa pennata", "group": "plants", "category": "rare", "conservation_status": "Красная книга Липецкой области"},
    {"name_ru": "Прострел раскрытый", "name_latin": "Pulsatilla patens", "group": "plants", "category": "red_book", "conservation_status": "Красная книга РФ"},
    # === ГРИБЫ ===
    {"name_ru": "Мухомор красный", "name_latin": "Amanita muscaria", "group": "fungi", "category": "typical", "is_poisonous": True, "description": "Ядовитый гриб с красной шляпкой и белыми точками."},
    {"name_ru": "Бледная поганка", "name_latin": "Amanita phalloides", "group": "fungi", "category": "typical", "is_poisonous": True, "description": "Смертельно ядовитый гриб."},
    {"name_ru": "Свинушка тонкая", "name_latin": "Paxillus involutus", "group": "fungi", "category": "typical", "is_poisonous": True},
    {"name_ru": "Подберёзовик", "name_latin": "Leccinum scabrum", "group": "fungi", "category": "typical"},
    {"name_ru": "Сыроежка", "name_latin": "Russula sp.", "group": "fungi", "category": "typical"},
    # === НАСЕКОМЫЕ ===
    {"name_ru": "Жук-плавунец широчайший", "name_latin": "Dytiscus latissimus", "group": "insects", "category": "red_book", "conservation_status": "Красная книга Липецкой области"},
    {"name_ru": "Коромысло зелёное", "name_latin": "Aeshna viridis", "group": "insects", "category": "red_book", "conservation_status": "Красная книга Липецкой области"},
    {"name_ru": "Махаон", "name_latin": "Papilio machaon", "group": "insects", "category": "red_book", "conservation_status": "Красная книга Липецкой области"},
    {"name_ru": "Пчела-плотник", "name_latin": "Xylocopa valga", "group": "insects", "category": "red_book", "conservation_status": "Красная книга РФ"},
    # === ГЕРПЕТОФАУНА ===
    {"name_ru": "Прыткая ящерица", "name_latin": "Lacerta agilis", "group": "herpetofauna", "category": "typical"},
    {"name_ru": "Обыкновенный уж", "name_latin": "Natrix natrix", "group": "herpetofauna", "category": "typical"},
    {"name_ru": "Гадюка Никольского", "name_latin": "Vipera nikolskii", "group": "herpetofauna", "category": "red_book", "conservation_status": "Красная книга Липецкой области", "is_poisonous": True, "do_dont_rules": "Не приближайтесь! Ядовита. При обнаружении сообщите экологу."},
    {"name_ru": "Озёрная лягушка", "name_latin": "Pelophylax ridibundus", "group": "herpetofauna", "category": "typical"},
    # === ПТИЦЫ: Синантропные ===
    {"name_ru": "Сизый голубь", "name_latin": "Columba livia", "group": "birds", "category": "synanthropic"},
    {"name_ru": "Домовый воробей", "name_latin": "Passer domesticus", "group": "birds", "category": "synanthropic"},
    {"name_ru": "Серая ворона", "name_latin": "Corvus cornix", "group": "birds", "category": "synanthropic"},
    {"name_ru": "Сорока", "name_latin": "Pica pica", "group": "birds", "category": "synanthropic"},
    {"name_ru": "Большая синица", "name_latin": "Parus major", "group": "birds", "category": "synanthropic"},
    {"name_ru": "Чёрный стриж", "name_latin": "Apus apus", "group": "birds", "category": "synanthropic"},
    # === ПТИЦЫ: Типичные ===
    {"name_ru": "Обыкновенная кукушка", "name_latin": "Cuculus canorus", "group": "birds", "category": "typical"},
    {"name_ru": "Обыкновенный соловей", "name_latin": "Luscinia luscinia", "group": "birds", "category": "typical"},
    {"name_ru": "Обыкновенный скворец", "name_latin": "Sturnus vulgaris", "group": "birds", "category": "typical"},
    # === ПТИЦЫ: Красная книга ===
    {"name_ru": "Лебедь-шипун", "name_latin": "Cygnus olor", "group": "birds", "category": "red_book", "conservation_status": "Красная книга Липецкой области", "season_info": "Апрель — Октябрь", "description": "Крупная водоплавающая птица семейства утиных. Размах крыльев до 240 см.", "do_dont_rules": "Фотографируйте с расстояния не менее 30 м. Не приближайтесь к гнёздам. Не кормите хлебом."},
    {"name_ru": "Серый журавль", "name_latin": "Grus grus", "group": "birds", "category": "red_book", "conservation_status": "Красная книга Липецкой области"},
    # === МЛЕКОПИТАЮЩИЕ ===
    {"name_ru": "Ёж обыкновенный", "name_latin": "Erinaceus europaeus", "group": "mammals", "category": "typical", "do_dont_rules": "Не берите в руки. Могут переносить бешенство."},
    {"name_ru": "Заяц-русак", "name_latin": "Lepus europaeus", "group": "mammals", "category": "typical"},
    {"name_ru": "Лисица обыкновенная", "name_latin": "Vulpes vulpes", "group": "mammals", "category": "typical", "do_dont_rules": "Не приближайтесь. При агрессивном поведении сообщите экологу."},
    {"name_ru": "Кабан", "name_latin": "Sus scrofa", "group": "mammals", "category": "typical", "do_dont_rules": "Опасен! Не приближайтесь. Сообщите экологу немедленно."},
    {"name_ru": "Лось", "name_latin": "Alces alces", "group": "mammals", "category": "typical", "do_dont_rules": "Не приближайтесь, особенно к самкам с детёнышами."},
    {"name_ru": "Крапчатый суслик", "name_latin": "Spermophilus suslicus", "group": "mammals", "category": "red_book", "conservation_status": "Красная книга Липецкой области"},
]
```

- [ ] **Step 3: Create backend/app/seed/run_seed.py**

```python
"""Seed species data into the database.

Usage: docker compose exec backend python -m app.seed.run_seed
"""
from app.database import SessionLocal
from app.models.species import Species, SpeciesGroup, SpeciesCategory
from app.seed.species_data import SPECIES_DATA


def seed_species():
    db = SessionLocal()
    try:
        existing = db.query(Species).count()
        if existing > 0:
            print(f"Species table already has {existing} records. Skipping seed.")
            return

        for item in SPECIES_DATA:
            species = Species(
                name_ru=item["name_ru"],
                name_latin=item["name_latin"],
                group=SpeciesGroup(item["group"]),
                category=SpeciesCategory(item["category"]),
                conservation_status=item.get("conservation_status"),
                is_poisonous=item.get("is_poisonous", False),
                season_info=item.get("season_info"),
                description=item.get("description"),
                do_dont_rules=item.get("do_dont_rules"),
            )
            db.add(species)

        db.commit()
        print(f"Seeded {len(SPECIES_DATA)} species.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_species()
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/seed/
git commit -m "feat: seed species data — 58 species from Green Book PDF"
```

---

### Task 5: Frontend — SpeciesCard Component

**Files:**
- Create: `frontend/src/components/SpeciesCard.vue`

- [ ] **Step 1: Create the reusable card component**

```vue
<template>
  <div class="species-card" @click="$router.push(`/species/${species.id}`)">
    <div
      class="species-card__img"
      :style="{ backgroundImage: species.photo_urls?.length ? `url(${species.photo_urls[0]})` : 'none' }"
    >
      <div class="species-card__no-photo" v-if="!species.photo_urls?.length">
        {{ groupIcon }}
      </div>
      <div
        class="species-card__status"
        :class="statusClass"
        :title="statusLabel"
      ></div>
      <div v-if="species.is_poisonous" class="species-card__poison" title="Ядовито">&#9888;</div>
    </div>
    <div class="species-card__body">
      <div class="species-card__name-ru">{{ species.name_ru }}</div>
      <div class="species-card__name-lat">{{ species.name_latin }}</div>
      <div class="species-card__tags">
        <span class="tag tag--group">{{ groupLabel }}</span>
        <span v-if="species.category === 'red_book'" class="tag tag--redbook">Красная книга</span>
        <span v-else-if="species.category === 'rare'" class="tag tag--rare">Редкий</span>
        <span v-else class="tag tag--typical">{{ categoryLabel }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Species {
  id: number
  name_ru: string
  name_latin: string
  group: string
  category: string
  is_poisonous: boolean
  photo_urls: string[] | null
  conservation_status: string | null
}

const props = defineProps<{ species: Species }>()

const GROUP_ICONS: Record<string, string> = {
  plants: '🌿', fungi: '🍄', insects: '🐛',
  herpetofauna: '🐍', birds: '🐦', mammals: '🦔',
}
const GROUP_LABELS: Record<string, string> = {
  plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые',
  herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие',
}
const CATEGORY_LABELS: Record<string, string> = {
  ruderal: 'Рудеральный', typical: 'Типичный', rare: 'Редкий',
  red_book: 'Красная книга', synanthropic: 'Синантроп',
}

const groupIcon = computed(() => GROUP_ICONS[props.species.group] || '🌱')
const groupLabel = computed(() => GROUP_LABELS[props.species.group] || props.species.group)
const categoryLabel = computed(() => CATEGORY_LABELS[props.species.category] || props.species.category)

const statusClass = computed(() => {
  if (props.species.category === 'red_book') return 'species-card__status--reference'
  if (props.species.category === 'rare') return 'species-card__status--potential'
  return 'species-card__status--confirmed'
})
const statusLabel = computed(() => {
  if (props.species.category === 'red_book') return 'Красная книга'
  if (props.species.category === 'rare') return 'Редкий вид'
  return 'Подтверждено'
})
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: SpeciesCard component with status badges and group icons"
```

---

### Task 6: Frontend — Species List Page

**Files:**
- Create: `frontend/src/views/SpeciesListView.vue`
- Modify: `frontend/src/router/index.ts` — add route

- [ ] **Step 1: Create SpeciesListView.vue**

This page shows a grid of SpeciesCard components with filter controls (group dropdown, category dropdown, search input). Uses the `/api/species` endpoint.

```vue
<template>
  <div class="species-page">
    <div class="species-page__header">
      <h1>Справочник видов</h1>
      <p>{{ total }} видов в каталоге</p>
    </div>

    <div class="species-page__filters">
      <el-input
        v-model="search"
        placeholder="Поиск по названию..."
        clearable
        @input="debouncedFetch"
        style="max-width: 300px"
      />
      <el-select v-model="groupFilter" placeholder="Группа" clearable @change="fetchSpecies">
        <el-option label="Растения" value="plants" />
        <el-option label="Грибы" value="fungi" />
        <el-option label="Насекомые" value="insects" />
        <el-option label="Герпетофауна" value="herpetofauna" />
        <el-option label="Птицы" value="birds" />
        <el-option label="Млекопитающие" value="mammals" />
      </el-select>
      <el-select v-model="categoryFilter" placeholder="Категория" clearable @change="fetchSpecies">
        <el-option label="Рудеральный" value="ruderal" />
        <el-option label="Типичный" value="typical" />
        <el-option label="Редкий" value="rare" />
        <el-option label="Красная книга" value="red_book" />
        <el-option label="Синантроп" value="synanthropic" />
      </el-select>
    </div>

    <div class="species-grid">
      <SpeciesCard v-for="s in species" :key="s.id" :species="s" />
    </div>

    <div v-if="species.length === 0 && !loading" class="species-page__empty">
      Виды не найдены
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import SpeciesCard from '../components/SpeciesCard.vue'

const species = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')
const groupFilter = ref('')
const categoryFilter = ref('')

let debounceTimer: ReturnType<typeof setTimeout>

async function fetchSpecies() {
  loading.value = true
  const params: any = {}
  if (groupFilter.value) params.group = groupFilter.value
  if (categoryFilter.value) params.category = categoryFilter.value
  if (search.value && search.value.length >= 2) params.search = search.value
  const { data } = await api.get('/species', { params })
  species.value = data.items
  total.value = data.total
  loading.value = false
}

function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchSpecies, 300)
}

onMounted(fetchSpecies)
</script>

<style scoped>
.species-page { max-width: 1200px; margin: 0 auto; padding: 32px; }
.species-page__header { margin-bottom: 24px; }
.species-page__header h1 {
  font-family: 'Cormorant Garamond', serif;
  font-size: 30px; font-weight: 600; color: #1B4D4F;
}
.species-page__header p { font-size: 14px; color: #8FA5AB; margin-top: 4px; }
.species-page__filters { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
.species-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px;
}
.species-page__empty {
  text-align: center; padding: 60px 20px; color: #8FA5AB; font-size: 16px;
}
</style>
```

- [ ] **Step 2: Add route to router/index.ts**

Add to the children array of the main layout route:

```typescript
{
  path: 'species',
  name: 'species-list',
  component: () => import('../views/SpeciesListView.vue'),
},
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/SpeciesListView.vue frontend/src/router/index.ts
git commit -m "feat: Species list page with filters, search, and card grid"
```

---

### Task 7: Frontend — Species Detail Page

**Files:**
- Create: `frontend/src/views/SpeciesDetailView.vue`
- Modify: `frontend/src/router/index.ts` — add route

- [ ] **Step 1: Create SpeciesDetailView.vue**

Full species card page with metadata, description, do/don't rules, similar to the prototype design.

```vue
<template>
  <div class="detail-page" v-if="species">
    <div class="detail-header">
      <div class="detail-gallery">
        <div
          class="detail-gallery__main"
          :style="{ backgroundImage: species.photo_urls?.length ? `url(${species.photo_urls[0]})` : 'none' }"
        >
          <div class="detail-gallery__no-photo" v-if="!species.photo_urls?.length">
            {{ groupIcon }}
          </div>
          <div class="detail-gallery__badges">
            <span class="detail-badge detail-badge--status">{{ groupLabel }}</span>
            <span v-if="species.conservation_status" class="detail-badge detail-badge--redbook">
              {{ species.conservation_status }}
            </span>
            <span v-if="species.is_poisonous" class="detail-badge detail-badge--poison">Ядовито</span>
          </div>
        </div>
      </div>
      <div class="detail-info">
        <h1>{{ species.name_ru }}</h1>
        <div class="latin">{{ species.name_latin }}</div>
        <div class="detail-meta">
          <div class="meta-item">
            <div class="meta-item__label">Группа</div>
            <div class="meta-item__value">{{ groupLabel }}</div>
          </div>
          <div class="meta-item">
            <div class="meta-item__label">Категория</div>
            <div class="meta-item__value">{{ categoryLabel }}</div>
          </div>
          <div class="meta-item" v-if="species.season_info">
            <div class="meta-item__label">Сезонность</div>
            <div class="meta-item__value">{{ species.season_info }}</div>
          </div>
          <div class="meta-item" v-if="species.conservation_status">
            <div class="meta-item__label">Охранный статус</div>
            <div class="meta-item__value">{{ species.conservation_status }}</div>
          </div>
        </div>
        <p v-if="species.description" class="detail-description">{{ species.description }}</p>

        <div v-if="species.do_dont_rules" class="detail-rules">
          <div class="rule-card rule-card--do">
            <span class="rule-card__icon">&#9888;</span>
            <span>{{ species.do_dont_rules }}</span>
          </div>
        </div>

        <div class="detail-actions">
          <router-link to="/species" class="btn btn-outline">&larr; К списку видов</router-link>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="detail-loading">Загрузка...</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/client'

const route = useRoute()
const species = ref<any>(null)

const GROUP_ICONS: Record<string, string> = {
  plants: '🌿', fungi: '🍄', insects: '🐛',
  herpetofauna: '🐍', birds: '🐦', mammals: '🦔',
}
const GROUP_LABELS: Record<string, string> = {
  plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые',
  herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие',
}
const CATEGORY_LABELS: Record<string, string> = {
  ruderal: 'Рудеральный', typical: 'Типичный', rare: 'Редкий',
  red_book: 'Красная книга', synanthropic: 'Синантроп',
}

const groupIcon = computed(() => GROUP_ICONS[species.value?.group] || '🌱')
const groupLabel = computed(() => GROUP_LABELS[species.value?.group] || '')
const categoryLabel = computed(() => CATEGORY_LABELS[species.value?.category] || '')

onMounted(async () => {
  const { data } = await api.get(`/species/${route.params.id}`)
  species.value = data
})
</script>

<style scoped>
.detail-page { max-width: 1200px; margin: 0 auto; padding: 32px; }
.detail-header { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }
.detail-gallery { border-radius: 20px; overflow: hidden; }
.detail-gallery__main {
  width: 100%; height: 380px; background-size: cover; background-position: center;
  position: relative; background-color: #D6E0E3;
}
.detail-gallery__no-photo {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 80px; opacity: 0.3;
}
.detail-gallery__badges { position: absolute; top: 16px; left: 16px; display: flex; gap: 8px; }
.detail-badge {
  padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700;
  backdrop-filter: blur(8px);
}
.detail-badge--status { background: rgba(42,122,110,0.85); color: white; }
.detail-badge--redbook { background: rgba(229,57,53,0.85); color: white; }
.detail-badge--poison { background: rgba(255,152,0,0.85); color: white; }
.detail-info h1 {
  font-family: 'Cormorant Garamond', serif; font-size: 38px; font-weight: 700;
  color: #1B4D4F; line-height: 1.2;
}
.latin { font-family: 'Cormorant Garamond', serif; font-style: italic; font-size: 20px; color: #4A6572; margin: 4px 0 20px; }
.detail-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }
.meta-item { background: #E8EEF0; padding: 14px 16px; border-radius: 6px; }
.meta-item__label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #8FA5AB; margin-bottom: 4px; }
.meta-item__value { font-size: 14px; font-weight: 600; color: #2C3E4A; }
.detail-description { font-size: 15px; color: #4A6572; line-height: 1.8; }
.detail-rules { margin-top: 24px; }
.rule-card { padding: 16px; border-radius: 6px; font-size: 13px; font-weight: 600; display: flex; align-items: flex-start; gap: 10px; background: rgba(255,152,0,0.08); color: #E65100; border-left: 3px solid #FF9800; }
.rule-card__icon { font-size: 18px; flex-shrink: 0; }
.detail-actions { margin-top: 24px; }
.btn { display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; border-radius: 6px; font-size: 14px; font-weight: 600; text-decoration: none; }
.btn-outline { background: transparent; color: #2A7A6E; border: 1.5px solid #2A7A6E; }
.btn-outline:hover { background: #2A7A6E; color: white; }
.detail-loading { text-align: center; padding: 60px; color: #8FA5AB; }
@media (max-width: 768px) { .detail-header { grid-template-columns: 1fr; } }
</style>
```

- [ ] **Step 2: Add route**

Add to children in router/index.ts:

```typescript
{
  path: 'species/:id',
  name: 'species-detail',
  component: () => import('../views/SpeciesDetailView.vue'),
},
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/SpeciesDetailView.vue frontend/src/router/index.ts
git commit -m "feat: Species detail page with metadata, badges, and rules"
```
