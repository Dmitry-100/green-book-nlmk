from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import require_role
from app.config import settings
from app.database import get_db
from app.models.species import Species, SpeciesGroup, SpeciesCategory
from app.models.user import User, UserRole
from app.schemas.species import (
    SpeciesCreate,
    SpeciesListResponse,
    SpeciesResponse,
    SpeciesUpdate,
)
from app.services.audit import audit_event
from app.services.cache import KeyedTTLCache, RedisKeyedTTLCache

router = APIRouter(prefix="/api/species", tags=["species"])
_SPECIES_LIST_CACHE = KeyedTTLCache[
    tuple[str | None, str | None, str | None, int, int, bool],
    dict,
](
    settings.species_list_cache_ttl_seconds,
    max_entries=256,
)
_SPECIES_LIST_REDIS_CACHE = RedisKeyedTTLCache[
    tuple[str | None, str | None, str | None, int, int, bool],
    dict,
](
    redis_url=settings.redis_url,
    key_prefix="cache:species:list",
    ttl_seconds=settings.species_list_cache_ttl_seconds,
    fallback_cache=_SPECIES_LIST_CACHE,
    enabled=settings.redis_cache_enabled,
    namespace=settings.redis_cache_namespace,
)


def invalidate_species_list_cache() -> None:
    _SPECIES_LIST_REDIS_CACHE.invalidate()


def _build_species_list_payload(
    *,
    db: Session,
    group: SpeciesGroup | None,
    category: SpeciesCategory | None,
    normalized_search: str | None,
    skip: int,
    limit: int,
    include_total: bool,
) -> dict:
    query = db.query(Species)
    if group:
        query = query.filter(Species.group == group)
    if category:
        query = query.filter(Species.category == category)
    if normalized_search:
        search_term = f"%{normalized_search}%"
        query = query.filter(
            (func.lower(Species.name_ru).like(search_term))
            | (func.lower(Species.name_latin).like(search_term))
        )
    total = query.count() if include_total else None
    items = query.order_by(Species.name_ru).offset(skip).limit(limit).all()
    return {
        "items": [
            SpeciesResponse.model_validate(item).model_dump(mode="json")
            for item in items
        ],
        "total": total,
    }


@router.get("", response_model=SpeciesListResponse)
def list_species(
    group: SpeciesGroup | None = None,
    category: SpeciesCategory | None = None,
    search: str | None = Query(None, min_length=2, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_total: bool = Query(True),
    db: Session = Depends(get_db),
):
    normalized_search = search.strip().lower() if search else None

    if settings.species_list_cache_ttl_seconds > 0:
        cache_key = (
            group.value if group else None,
            category.value if category else None,
            normalized_search,
            skip,
            limit,
            include_total,
        )
        return _SPECIES_LIST_REDIS_CACHE.get_or_set(
            cache_key,
            lambda: _build_species_list_payload(
                db=db,
                group=group,
                category=category,
                normalized_search=normalized_search,
                skip=skip,
                limit=limit,
                include_total=include_total,
            ),
        )

    return _build_species_list_payload(
        db=db,
        group=group,
        category=category,
        normalized_search=normalized_search,
        skip=skip,
        limit=limit,
        include_total=include_total,
    )


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
    invalidate_species_list_cache()
    audit_event(
        action="species.create",
        actor=user,
        target_type="species",
        target_id=species.id,
        details={
            "name_ru": species.name_ru,
            "name_latin": species.name_latin,
            "group": species.group.value if species.group else None,
            "category": species.category.value if species.category else None,
        },
        db=db,
    )
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
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(species, key, value)
    db.commit()
    db.refresh(species)
    invalidate_species_list_cache()
    audit_event(
        action="species.update",
        actor=user,
        target_type="species",
        target_id=species.id,
        details={"updated_fields": sorted(updates.keys())},
        db=db,
    )
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
    species_meta = {
        "name_ru": species.name_ru,
        "name_latin": species.name_latin,
    }
    db.delete(species)
    db.commit()
    invalidate_species_list_cache()
    audit_event(
        action="species.delete",
        actor=user,
        target_type="species",
        target_id=species_id,
        details=species_meta,
        db=db,
    )
