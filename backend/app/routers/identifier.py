from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.decision_tree import DecisionTreeNode
from app.models.species import Species, SpeciesGroup

router = APIRouter(prefix="/api/identifier", tags=["identifier"])


class SuggestRequest(BaseModel):
    species_ids: list[Annotated[int, Field(gt=0)]] = Field(
        min_length=1,
        max_length=100,
    )

    @field_validator("species_ids")
    @classmethod
    def _ensure_unique_ids(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("species_ids must not contain duplicates")
        return value


@router.get("/tree")
def get_tree(
    group: SpeciesGroup = Query(...),
    parent_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(DecisionTreeNode).filter(DecisionTreeNode.group == group.value)
    if parent_id is None:
        query = query.filter(DecisionTreeNode.parent_id.is_(None))
    else:
        query = query.filter(DecisionTreeNode.parent_id == parent_id)
    nodes = query.order_by(DecisionTreeNode.sort_order).all()
    return [
        {
            "id": n.id,
            "question_text": n.question_text,
            "has_children": db.query(DecisionTreeNode).filter(DecisionTreeNode.parent_id == n.id).count() > 0,
            "suggested_species_ids": n.suggested_species_ids,
        }
        for n in nodes
    ]


@router.post("/suggest")
def suggest_species(
    data: SuggestRequest,
    db: Session = Depends(get_db),
):
    species = db.query(Species).filter(Species.id.in_(data.species_ids)).all()
    return [
        {
            "id": s.id,
            "name_ru": s.name_ru,
            "name_latin": s.name_latin,
            "group": s.group.value,
            "category": s.category.value,
            "is_poisonous": s.is_poisonous,
        }
        for s in species
    ]
