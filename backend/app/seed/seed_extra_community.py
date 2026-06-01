"""Seed additional community: 10 users + 20 observations + points.
Idempotent (checks external_id prefix `seed-community-`).
Run AFTER seed_demo.py.
Usage: docker compose exec backend python -m app.seed.seed_extra_community
"""
import random
from datetime import datetime, timezone, timedelta

from geoalchemy2.elements import WKTElement

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.observation import Observation, ObsMedia, ObservationStatus
from app.models.species import Species
from app.models.gamification import UserPoints


EXTRA_USERS = [
    ("seed-community-1",  "Анна Петровна Кузнецова",      "kuznecova@nlmk.example"),
    ("seed-community-2",  "Михаил Александрович Новиков", "novikov@nlmk.example"),
    ("seed-community-3",  "Елена Сергеевна Морозова",     "morozova@nlmk.example"),
    ("seed-community-4",  "Алексей Викторович Зайцев",    "zaytsev@nlmk.example"),
    ("seed-community-5",  "Ольга Дмитриевна Соколова",    "sokolova@nlmk.example"),
    ("seed-community-6",  "Иван Иванович Романов",        "romanov@nlmk.example"),
    ("seed-community-7",  "Татьяна Александровна Лебедева","lebedeva@nlmk.example"),
    ("seed-community-8",  "Сергей Михайлович Орлов",      "orlov@nlmk.example"),
    ("seed-community-9",  "Мария Алексеевна Журавлёва",   "zhuravleva@nlmk.example"),
    ("seed-community-10", "Павел Николаевич Соловьёв",    "solovyev@nlmk.example"),
]

# Each tuple: (user_index_0to9, comment, group_hint, day_offset)
# Distributed so leaders accumulate different point totals.
EXTRA_OBSERVATIONS = [
    (0,  "Стайка на берегу пруда, кормились",       "birds",   -2),
    (0,  "Заметила редкое растение у дороги",        "plants",  -5),
    (0,  "Сидел на ветке у мартена",                 "birds",  -10),
    (1,  "Пробежал у северного периметра",           "mammals", -1),
    (1,  "Тёмные ягоды на кустах у пожарной части",  "plants",  -7),
    (2,  "Громко куковала из дальней лесопосадки",   "birds",   -3),
    (2,  "Колония муравьёв у южных ворот",           "insects", -4),
    (3,  "Семья с детёнышами у автостоянки",         "mammals", -2),
    (3,  "Ужи в дренажной канаве, осторожно",        "herpetofauna", -8),
    (4,  "Цветёт на пустыре между цехами",           "plants",  -1),
    (4,  "Дятел стучал по сухой сосне",              "birds",   -6),
    (5,  "Бабочка села на лист крапивы",             "insects", -2),
    (5,  "Ёж переходил тропинку вечером",            "mammals", -9),
    (6,  "Лебедь с птенцами на отстойнике",          "birds",   -1),
    (6,  "Грибы целой семейкой после дождя",         "fungi",   -3),
    (7,  "Сокол кружил над трубой ДП-6",             "birds",  -11),
    (8,  "Махаон на репейнике, удалось снять",       "insects", -2),
    (8,  "Журавли клином уходили на юг",             "birds",  -14),
    (9,  "Цапля стояла в дренажной воде",            "birds",   -5),
    (9,  "Косуля выскочила к лесопосадке",           "mammals",-12),
]

POINTS_PER_OBS = 8  # standard award per confirmed observation


def _pick_species(db, group: str):
    q = db.query(Species).filter(Species.group == group).all()
    return random.choice(q) if q else db.query(Species).first()


def _pick_media_key(species) -> str | None:
    urls = species.photo_urls or []
    if not urls:
        return None
    url = random.choice(urls)
    return url.replace("/api/media/", "")


def seed_extra_community():
    db = SessionLocal()
    random.seed(42)
    try:
        existing = db.query(User).filter(User.external_id.like("seed-community-%")).count()
        if existing >= len(EXTRA_USERS):
            print(f"Extra community users already exist ({existing}). Skipping.")
            return

        # 1. Users
        users = []
        for ext_id, name, email in EXTRA_USERS:
            user = db.query(User).filter(User.external_id == ext_id).first()
            if not user:
                user = User(
                    external_id=ext_id,
                    display_name=name,
                    email=email,
                    role=UserRole.employee,
                )
                db.add(user)
            users.append(user)
        db.flush()
        print(f"  Ensured {len(users)} community users")

        # 2. Reviewer (try to find existing ecologist; fallback to first user)
        reviewer = db.query(User).filter(User.role == UserRole.ecologist).first()
        if not reviewer:
            reviewer = users[0]

        # 3. Observations + media
        created = 0
        now = datetime.now(timezone.utc)
        for user_idx, comment, group, day_offset in EXTRA_OBSERVATIONS:
            author = users[user_idx]
            species = _pick_species(db, group)
            if not species:
                continue
            observed_at = now + timedelta(days=day_offset, hours=random.randint(5, 21))
            obs = Observation(
                author_id=author.id,
                species_id=species.id,
                group=group,
                observed_at=observed_at,
                location_point=WKTElement(
                    f"POINT({39.55 + random.random() * 0.1} {52.55 + random.random() * 0.08})",
                    srid=4326,
                ),
                status=ObservationStatus.confirmed,
                comment=comment,
                is_incident=False,
                safety_checked=True,
                reviewer_id=reviewer.id,
                reviewed_at=now,
            )
            db.add(obs)
            db.flush()
            media_key = _pick_media_key(species)
            if media_key:
                db.add(ObsMedia(
                    observation_id=obs.id,
                    s3_key=media_key,
                    mime_type="image/png",
                ))
            # Variable points (5-25) so leaderboard has range
            pts = POINTS_PER_OBS + random.randint(-3, 17)
            db.add(UserPoints(
                user_id=author.id,
                observation_id=obs.id,
                points=pts,
                reason=f"Подтверждённое наблюдение: {species.name_ru}",
            ))
            created += 1
        print(f"  Created {created} observations with media + points")

        db.commit()
        print("Extra community seeded successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_extra_community()
