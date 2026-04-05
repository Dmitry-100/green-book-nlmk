"""Seed achievement definitions. Usage: docker compose exec backend python -m app.seed.seed_achievements"""
from app.database import SessionLocal
from app.models.gamification import Achievement

ACHIEVEMENTS = [
    {"code": "first_steps", "name": "Первые шаги", "description": "Первое подтверждённое наблюдение", "icon": "🌱", "points_reward": 10, "condition_type": "obs_count", "condition_value": 1},
    {"code": "naturalist", "name": "Натуралист", "description": "10 подтверждённых наблюдений", "icon": "🔬", "points_reward": 50, "condition_type": "obs_count", "condition_value": 10},
    {"code": "expert", "name": "Эксперт", "description": "50 подтверждённых наблюдений", "icon": "🏆", "points_reward": 200, "condition_type": "obs_count", "condition_value": 50},
    {"code": "all_groups", "name": "Все группы", "description": "Наблюдение из каждой из 6 групп", "icon": "🌈", "points_reward": 100, "condition_type": "group_count", "condition_value": 6},
    {"code": "rare_find", "name": "Редкая находка", "description": "Наблюдение вида из Красной книги", "icon": "💎", "points_reward": 50, "condition_type": "rare_find", "condition_value": 1},
    {"code": "early_bird", "name": "Ранняя пташка", "description": "Наблюдение до 7:00 утра", "icon": "🌅", "points_reward": 20, "condition_type": "early_bird", "condition_value": 1},
    {"code": "night_watch", "name": "Ночной дозор", "description": "Наблюдение после 22:00", "icon": "🌙", "points_reward": 20, "condition_type": "night_watch", "condition_value": 1},
    {"code": "four_seasons", "name": "Сезонный охотник", "description": "Наблюдения в 4 разных сезона", "icon": "🍂", "points_reward": 100, "condition_type": "seasons", "condition_value": 4},
    {"code": "photographer", "name": "Фотограф", "description": "5 наблюдений с фото", "icon": "📸", "points_reward": 30, "condition_type": "photo_count", "condition_value": 5},
    {"code": "rescuer", "name": "Спасатель", "description": "Сообщение об инциденте", "icon": "🚨", "points_reward": 30, "condition_type": "incident", "condition_value": 1},
    {"code": "discoverer", "name": "Первооткрыватель", "description": "Первое наблюдение нового вида на площадке", "icon": "🏅", "points_reward": 100, "condition_type": "first_discovery", "condition_value": 1},
]


def seed_achievements():
    db = SessionLocal()
    try:
        existing = db.query(Achievement).count()
        if existing > 0:
            print(f"Achievements already seeded ({existing}). Skipping.")
            return
        for a in ACHIEVEMENTS:
            db.add(Achievement(**a))
        db.commit()
        print(f"Seeded {len(ACHIEVEMENTS)} achievements.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_achievements()
