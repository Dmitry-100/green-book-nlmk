from fastapi import APIRouter, Depends, HTTPException, Query
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
