from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.decision_tree import DecisionTreeNode
from app.models.species import Species

router = APIRouter(prefix="/api/identifier", tags=["identifier"])


@router.get("/tree")
def get_tree(
    group: str = Query(...),
    parent_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(DecisionTreeNode).filter(DecisionTreeNode.group == group)
    if parent_id is None:
        query = query.filter(DecisionTreeNode.parent_id == None)
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
    species_ids: list[int],
    db: Session = Depends(get_db),
):
    species = db.query(Species).filter(Species.id.in_(species_ids)).all()
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
