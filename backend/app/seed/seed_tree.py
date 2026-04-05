"""Seed decision tree. Usage: docker compose exec backend python -m app.seed.seed_tree"""
from app.database import SessionLocal
from app.models.decision_tree import DecisionTreeNode
from app.models.species import Species
from app.seed.decision_tree_data import DECISION_TREE


def resolve_species_ids(db, latin_names: list[str]) -> list[int]:
    ids = []
    for name in latin_names:
        sp = db.query(Species).filter(Species.name_latin == name).first()
        if sp:
            ids.append(sp.id)
    return ids


def insert_node(db, node: dict, parent_id: int | None, group: str, sort_order: int):
    species_names = node.get("species", [])
    species_ids = resolve_species_ids(db, species_names) if species_names else None

    db_node = DecisionTreeNode(
        parent_id=parent_id,
        question_text=node["question_text"],
        group=group,
        suggested_species_ids=species_ids if species_ids else None,
        sort_order=sort_order,
    )
    db.add(db_node)
    db.flush()

    for i, child in enumerate(node.get("children", [])):
        insert_node(db, child, db_node.id, group, i)


def seed_tree():
    db = SessionLocal()
    try:
        existing = db.query(DecisionTreeNode).count()
        if existing > 0:
            print(f"Decision tree already has {existing} nodes. Skipping.")
            return

        for i, root in enumerate(DECISION_TREE):
            group = root["group"]
            insert_node(db, root, None, group, i)

        db.commit()
        total = db.query(DecisionTreeNode).count()
        print(f"Seeded {total} decision tree nodes.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_tree()
