"""Seed species data. Usage: docker compose exec backend python -m app.seed.run_seed"""
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
                photo_urls=item.get("photo_urls", []),
            )
            db.add(species)
        db.commit()
        print(f"Seeded {len(SPECIES_DATA)} species.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_species()
