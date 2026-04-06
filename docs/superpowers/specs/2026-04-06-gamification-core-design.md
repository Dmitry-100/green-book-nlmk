# Gamification Core — Design Spec

## Goal

Оживить геймификацию: при подтверждении наблюдения начислять баллы, выдавать достижения, фиксировать первооткрывателей. Показывать первооткрывателя на карточке вида. Добавить фильтр по периоду в лидерборд.

## Architecture

Вся trigger-логика вынесена в `backend/app/services/gamification.py` — единая функция `award_gamification(observation_id, db)`, вызываемая из `validation.py` при подтверждении. В будущем ИИ-валидатор вызовет ту же функцию.

## Existing Infrastructure

Уже реализовано (не нужно создавать):
- Модели: `Achievement`, `UserAchievement`, `UserPoints`, `SpeciesFirstDiscovery` (в `models/gamification.py`)
- Seed 11 бейджей: `seed/seed_achievements.py`
- Эндпоинты чтения: `GET /api/gamification/leaderboard`, `/profile`, `/species/{id}/discoverer`, `/stats`, `/fact-of-day`
- Фронтенд: `ProfileView.vue` отображает баллы, достижения, лидерборд

---

## Feature 1: Trigger-логика

### Новый файл: `backend/app/services/gamification.py`

Функция `award_gamification(observation_id: int, db: Session)`:

#### 1.1 Начисление баллов

Логика расчёта:
- `base_points`: typical/synanthropic/ruderal → 1, rare → 5, red_book → 10
- `multiplier`: x3 если это первое подтверждённое наблюдение вида (проверка SpeciesFirstDiscovery), x2 если сезон совпадает (месяц `observed_at` входит в `species.season_info`), иначе x1. Множители не складываются — берётся максимальный.
- `total = base_points * multiplier`
- Создаём запись `UserPoints(user_id=obs.author_id, observation_id=obs.id, points=total, reason=описание)`

#### 1.2 First Discovery

- `SELECT` из `SpeciesFirstDiscovery` по `species_id`
- Если записи нет → `INSERT SpeciesFirstDiscovery(species_id, user_id, observation_id)`

#### 1.3 Проверка достижений

Для каждого `Achievement`, которого у пользователя ещё нет (`LEFT JOIN UserAchievement IS NULL`), проверяем условие на основе `condition_type`:

| condition_type | Условие |
|---|---|
| `obs_count=1` (first_steps) | count(confirmed observations by user) >= 1 |
| `obs_count=10` (naturalist) | count >= 10 |
| `obs_count=50` (expert) | count >= 50 |
| `group_count=6` (all_groups) | distinct groups in confirmed obs >= 6 |
| `rare_find=1` | есть confirmed obs вида с category=red_book |
| `early_bird=1` | текущее obs.observed_at.hour < 7 |
| `night_watch=1` | текущее obs.observed_at.hour >= 22 |
| `seasons=4` | distinct seasons (из observed_at) >= 4 |
| `photo_count=5` | confirmed obs с медиа (ObsMedia) >= 5 |
| `incident=1` | текущее obs.is_incident == True |
| `first_discovery=1` | пользователь есть в SpeciesFirstDiscovery |

Сезон определяется по месяцу: 12,1,2 → зима; 3,4,5 → весна; 6,7,8 → лето; 9,10,11 → осень.

При выполнении условия: `INSERT UserAchievement(user_id, achievement_id)`.

### Интеграция в `routers/validation.py`

В функцию `confirm_observation` (после `db.commit()` для статуса) добавить вызов:
```python
from app.services.gamification import award_gamification
award_gamification(observation_id, db)
```

---

## Feature 2: Первооткрыватель на карточке вида

### Изменения: `frontend/src/views/SpeciesDetailView.vue`

- При загрузке вида вызываем `GET /api/gamification/species/{id}/discoverer`
- Если ответ содержит данные — показываем блок под описанием:
  - Текст: «Первое наблюдение: {display_name}, {formatted_date}»
  - Дата форматируется как "12 марта 2026"
- Если данных нет — блок не отображается

Бэкенд не меняется — эндпоинт уже существует и возвращает `{user: {display_name}, observation: {observed_at}}`.

---

## Feature 3: Лидерборд с фильтром по периоду

### Изменения бэкенда: `routers/gamification.py`

Эндпоинт `GET /api/gamification/leaderboard` — добавить реальную фильтрацию по параметру `period`:
- `month` — `UserPoints.created_at >= now() - 30 days`
- `quarter` — `>= now() - 90 days`
- `year` — `>= now() - 365 days`
- `all` (default) — без фильтра

SQL: `SELECT user_id, SUM(points) as total FROM user_points WHERE created_at >= :cutoff GROUP BY user_id ORDER BY total DESC LIMIT 20`.

### Изменения фронтенда: `ProfileView.vue`

- Добавить табы над лидербордом: Месяц | Квартал | Год | Всё время
- Состояние: `leaderboardPeriod = ref('all')`
- При переключении — `GET /api/gamification/leaderboard?period={value}`
- Стилизация: активный таб с подчёркиванием в цвете `#2A7A6E`

---

## File Map

| Действие | Файл |
|---|---|
| Create | `backend/app/services/gamification.py` |
| Modify | `backend/app/routers/validation.py` (добавить вызов award_gamification) |
| Modify | `backend/app/routers/gamification.py` (фильтр по периоду в leaderboard) |
| Modify | `frontend/src/views/SpeciesDetailView.vue` (блок первооткрывателя) |
| Modify | `frontend/src/views/ProfileView.vue` (табы периода в лидерборде) |

## Out of Scope

- Комментарии и лайки (подпроект B)
- Сезонные челленджи (подпроект B)
- Экопаспорт, викторина, маршруты (подпроект C)
- ИИ-валидация (отдельный проект, но интерфейс совместим)
- Командный рейтинг по подразделениям
- Настройка приватности первооткрывателя (ФИО/инициалы)
