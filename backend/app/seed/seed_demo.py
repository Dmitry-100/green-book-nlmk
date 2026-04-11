"""Seed demo data: users, observations, points, achievements, discoveries.
Usage: docker compose exec backend python -m app.seed.seed_demo
Run AFTER run_seed.py and seed_achievements.py.
"""
from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.observation import Observation, ObsMedia, ObservationStatus
from app.models.species import Species
from app.models.gamification import (
    Achievement, UserAchievement, UserPoints, SpeciesFirstDiscovery,
)


DEMO_USERS = [
    {"external_id": "dev-employee-employee", "display_name": "Сотников Д.С.", "email": "employee@nlmk.com", "role": "employee"},
    {"external_id": "dev-ecologist-ecologist", "display_name": "Эколог Тестовый", "email": "ecologist@nlmk.com", "role": "ecologist"},
]

DEMO_OBSERVATIONS = [
    {
        "species_latin": "Alces alces",
        "group": "mammals",
        "observed_at": "2026-04-05T08:30:00",
        "lat": 52.59, "lon": 39.60,
        "comment": "Видел лося у пруда, шёл спокойно",
        "media_key": "species-pdf/page29_img02.png",
    },
    {
        "species_latin": "Papilio machaon",
        "group": "insects",
        "observed_at": "2026-04-06T06:15:00",
        "lat": 52.591, "lon": 39.602,
        "comment": "Бабочка махаон на территории ЛПЦ-2, раннее утро",
        "media_key": "species-pdf/page20_img04.png",
    },
    {
        "species_latin": "Amanita",
        "group": "fungi",
        "observed_at": "2026-04-04T22:45:00",
        "lat": 52.588, "lon": 39.598,
        "comment": "Мухомор у забора, ночная смена",
        "media_key": "species-pdf/page12_img11.png",
    },
]

DEMO_ACHIEVEMENTS = ["first_steps", "discoverer", "rare_find", "early_bird", "night_watch"]

DEMO_POINTS = [
    {"obs_index": 0, "points": 3, "reason": "Лось, первое наблюдение вида x3 (1x3=3)"},
    {"obs_index": None, "points": 10, "reason": "Достижение «Первые шаги»"},
    {"obs_index": None, "points": 100, "reason": "Достижение «Первооткрыватель»"},
    {"obs_index": 1, "points": 30, "reason": "Махаон, первое наблюдение вида x3 (10x3=30)"},
    {"obs_index": None, "points": 50, "reason": "Достижение «Редкая находка»"},
    {"obs_index": None, "points": 20, "reason": "Достижение «Ранняя пташка»"},
    {"obs_index": 2, "points": 3, "reason": "Мухомор красный, первое наблюдение вида x3 (1x3=3)"},
    {"obs_index": None, "points": 20, "reason": "Достижение «Ночной дозор»"},
]


def seed_demo():
    db = SessionLocal()
    try:
        # Check if demo data already exists
        if db.query(User).count() > 0:
            print("Users already exist. Skipping demo seed.")
            return

        # 1. Create users
        users = []
        for u in DEMO_USERS:
            user = User(
                external_id=u["external_id"],
                display_name=u["display_name"],
                email=u["email"],
                role=UserRole(u["role"]),
            )
            db.add(user)
            users.append(user)
        db.flush()
        employee = users[0]
        print(f"  Created {len(users)} users (employee id={employee.id})")

        # 2. Create observations
        obs_list = []
        for o in DEMO_OBSERVATIONS:
            species = db.query(Species).filter(Species.name_latin == o["species_latin"]).first()
            obs = Observation(
                author_id=employee.id,
                species_id=species.id if species else None,
                group=o["group"],
                observed_at=datetime.fromisoformat(o["observed_at"]),
                location_point=WKTElement(f"POINT({o['lon']} {o['lat']})", srid=4326),
                status=ObservationStatus.confirmed,
                comment=o["comment"],
                is_incident=False,
                safety_checked=True,
                reviewer_id=users[1].id,  # ecologist
                reviewed_at=datetime.now(timezone.utc),
            )
            db.add(obs)
            obs_list.append(obs)
        db.flush()
        print(f"  Created {len(obs_list)} observations")

        # 3. Attach media
        for i, o in enumerate(DEMO_OBSERVATIONS):
            db.add(ObsMedia(
                observation_id=obs_list[i].id,
                s3_key=o["media_key"],
                mime_type="image/png",
            ))
        print(f"  Attached {len(obs_list)} photos")

        # 4. Points
        for p in DEMO_POINTS:
            db.add(UserPoints(
                user_id=employee.id,
                observation_id=obs_list[p["obs_index"]].id if p["obs_index"] is not None else None,
                points=p["points"],
                reason=p["reason"],
            ))
        print(f"  Added {len(DEMO_POINTS)} point records (236 total)")

        # 5. Achievements
        for code in DEMO_ACHIEVEMENTS:
            ach = db.query(Achievement).filter(Achievement.code == code).first()
            if ach:
                db.add(UserAchievement(user_id=employee.id, achievement_id=ach.id))
        print(f"  Awarded {len(DEMO_ACHIEVEMENTS)} achievements")

        # 6. First discoveries
        for i, obs in enumerate(obs_list):
            if obs.species_id:
                db.add(SpeciesFirstDiscovery(
                    species_id=obs.species_id,
                    user_id=employee.id,
                    observation_id=obs.id,
                ))
        print(f"  Recorded {len(obs_list)} first discoveries")

        db.commit()
        print("Demo data seeded successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
