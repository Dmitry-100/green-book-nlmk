"""Update species with photo URLs. Usage: docker compose exec backend python -m app.seed.update_photos"""
from app.database import SessionLocal
from app.models.species import Species
from app.seed.species_data import SPECIES_DATA


def update_photos():
    db = SessionLocal()
    try:
        for item in SPECIES_DATA:
            photos = item.get("photo_urls", [])
            if not photos:
                continue
            sp = db.query(Species).filter(Species.name_latin == item["name_latin"]).first()
            if sp:
                sp.photo_urls = photos
        db.commit()
        updated = db.query(Species).filter(Species.photo_urls.is_not(None)).count()
        print(f"Updated {updated} species with photos.")
    finally:
        db.close()


if __name__ == "__main__":
    update_photos()
