# Gamification Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up the gamification trigger logic so that confirming an observation awards points, checks achievements, and records first discoveries — then surface this data in the frontend.

**Architecture:** A new `services/gamification.py` module with a single entry point `award_gamification()` is called from `validation.py` after observation confirmation. The leaderboard endpoint gets period filtering. The species detail page calls the existing discoverer endpoint.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Vue 3, TypeScript

---

## File Structure

| Action | File | Responsibility |
|---|---|---|
| Create | `backend/app/services/gamification.py` | Points calculation, first discovery, achievement checking |
| Modify | `backend/app/routers/validation.py:47-73` | Call `award_gamification()` after confirm |
| Modify | `backend/app/routers/gamification.py:18-39` | Add period filtering to leaderboard |
| Modify | `frontend/src/views/SpeciesDetailView.vue` | Show first discoverer block |
| Modify | `frontend/src/views/ProfileView.vue` | Add period tabs to leaderboard |

---

### Task 1: Gamification service — points calculation

**Files:**
- Create: `backend/app/services/gamification.py`

- [ ] **Step 1: Create the gamification service with points logic**

```python
"""Gamification trigger logic. Called when an observation is confirmed."""
from datetime import datetime

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.models.gamification import (
    Achievement, UserAchievement, UserPoints, SpeciesFirstDiscovery,
)
from app.models.observation import Observation, ObservationStatus, ObsMedia
from app.models.species import Species, SpeciesCategory


def _calc_season(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def _calc_points(obs: Observation, species: Species | None, is_first_discovery: bool) -> tuple[int, str]:
    """Calculate points and reason string for this observation."""
    if species is None:
        return 1, "Наблюдение без привязки к виду"

    base = 1
    if species.category == SpeciesCategory.rare:
        base = 5
    elif species.category == SpeciesCategory.red_book:
        base = 10

    multiplier = 1
    reason_parts = [f"{species.name_ru}"]

    if is_first_discovery:
        multiplier = 3
        reason_parts.append("первое наблюдение вида x3")
    elif species.season_info and obs.observed_at:
        month = obs.observed_at.month
        season_info_lower = species.season_info.lower()
        month_names = {
            1: "январ", 2: "феврал", 3: "март", 4: "апрел",
            5: "ма", 6: "июн", 7: "июл", 8: "август",
            9: "сентябр", 10: "октябр", 11: "ноябр", 12: "декабр",
        }
        if month_names.get(month, "") and month_names[month] in season_info_lower:
            multiplier = 2
            reason_parts.append("сезонный бонус x2")

    total = base * multiplier
    reason = ", ".join(reason_parts) + f" ({base}×{multiplier}={total})"
    return total, reason


def _record_first_discovery(obs: Observation, db: Session) -> bool:
    """Record first discovery if this species hasn't been observed before. Returns True if new."""
    if not obs.species_id:
        return False
    existing = db.query(SpeciesFirstDiscovery).filter(
        SpeciesFirstDiscovery.species_id == obs.species_id
    ).first()
    if existing:
        return False
    db.add(SpeciesFirstDiscovery(
        species_id=obs.species_id,
        user_id=obs.author_id,
        observation_id=obs.id,
    ))
    return True


def _check_achievements(user_id: int, obs: Observation, db: Session) -> list[str]:
    """Check all unearned achievements and award any that are now satisfied. Returns list of earned codes."""
    earned_ids = {
        row[0] for row in
        db.query(UserAchievement.achievement_id).filter(UserAchievement.user_id == user_id).all()
    }
    all_achievements = db.query(Achievement).all()
    newly_earned = []

    for ach in all_achievements:
        if ach.id in earned_ids:
            continue

        satisfied = False
        ct = ach.condition_type
        cv = ach.condition_value

        if ct == "obs_count":
            count = db.query(Observation).filter(
                Observation.author_id == user_id,
                Observation.status == ObservationStatus.confirmed,
            ).count()
            satisfied = count >= cv

        elif ct == "group_count":
            groups = db.query(Observation.group).filter(
                Observation.author_id == user_id,
                Observation.status == ObservationStatus.confirmed,
            ).distinct().count()
            satisfied = groups >= cv

        elif ct == "rare_find":
            count = db.query(Observation).join(Species).filter(
                Observation.author_id == user_id,
                Observation.status == ObservationStatus.confirmed,
                Species.category == SpeciesCategory.red_book,
            ).count()
            satisfied = count >= cv

        elif ct == "early_bird":
            if obs.observed_at and obs.observed_at.hour < 7:
                satisfied = True

        elif ct == "night_watch":
            if obs.observed_at and obs.observed_at.hour >= 22:
                satisfied = True

        elif ct == "seasons":
            rows = db.query(extract("month", Observation.observed_at)).filter(
                Observation.author_id == user_id,
                Observation.status == ObservationStatus.confirmed,
            ).distinct().all()
            seasons = {_calc_season(int(r[0])) for r in rows if r[0]}
            satisfied = len(seasons) >= cv

        elif ct == "photo_count":
            count = db.query(Observation).join(ObsMedia).filter(
                Observation.author_id == user_id,
                Observation.status == ObservationStatus.confirmed,
            ).distinct().count()
            satisfied = count >= cv

        elif ct == "incident":
            if obs.is_incident:
                satisfied = True

        elif ct == "first_discovery":
            count = db.query(SpeciesFirstDiscovery).filter(
                SpeciesFirstDiscovery.user_id == user_id
            ).count()
            satisfied = count >= cv

        if satisfied:
            db.add(UserAchievement(user_id=user_id, achievement_id=ach.id))
            # Bonus points for achievement
            if ach.points_reward > 0:
                db.add(UserPoints(
                    user_id=user_id,
                    points=ach.points_reward,
                    reason=f"Достижение «{ach.name}»",
                ))
            newly_earned.append(ach.code)

    return newly_earned


def award_gamification(observation_id: int, db: Session) -> dict:
    """Main entry point. Call after observation is confirmed.

    Returns dict with points, is_first_discovery, new_achievements for logging/notification.
    """
    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        return {}

    species = db.query(Species).filter(Species.id == obs.species_id).first() if obs.species_id else None

    # 1. First discovery
    is_first = _record_first_discovery(obs, db)

    # 2. Points
    points, reason = _calc_points(obs, species, is_first)
    db.add(UserPoints(
        user_id=obs.author_id,
        observation_id=obs.id,
        points=points,
        reason=reason,
    ))

    # 3. Achievements
    new_achievements = _check_achievements(obs.author_id, obs, db)

    db.commit()

    return {
        "points": points,
        "reason": reason,
        "is_first_discovery": is_first,
        "new_achievements": new_achievements,
    }
```

- [ ] **Step 2: Verify the file is importable**

Run: `docker compose exec backend python -c "from app.services.gamification import award_gamification; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/gamification.py
git commit -m "feat: gamification service — points, first discovery, achievements"
```

---

### Task 2: Integrate trigger into validation

**Files:**
- Modify: `backend/app/routers/validation.py:71-73`

- [ ] **Step 1: Add gamification call after confirm**

In `backend/app/routers/validation.py`, replace lines 71-73:

```python
    db.commit()
    db.refresh(obs)
    return obs
```

with:

```python
    db.commit()

    # Award gamification (points, achievements, first discovery)
    from app.services.gamification import award_gamification
    award_gamification(obs.id, db)

    db.refresh(obs)
    return obs
```

- [ ] **Step 2: Verify the endpoint still works**

Run: `docker compose exec backend python -c "from app.routers.validation import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/validation.py
git commit -m "feat: trigger gamification on observation confirmation"
```

---

### Task 3: Leaderboard period filter

**Files:**
- Modify: `backend/app/routers/gamification.py:18-39`

- [ ] **Step 1: Update the leaderboard endpoint with period filtering**

Replace the entire `leaderboard` function in `backend/app/routers/gamification.py` (lines 18-39) with:

```python
@router.get("/leaderboard")
def leaderboard(
    period: str = Query("all", regex="^(all|month|quarter|year)$"),
    db: Session = Depends(get_db),
):
    """Top observers by points, optionally filtered by period."""
    from datetime import datetime, timedelta

    query = db.query(
        UserPoints.user_id,
        func.sum(UserPoints.points).label("total_points"),
    )

    if period == "month":
        cutoff = datetime.utcnow() - timedelta(days=30)
        query = query.filter(UserPoints.created_at >= cutoff)
    elif period == "quarter":
        cutoff = datetime.utcnow() - timedelta(days=90)
        query = query.filter(UserPoints.created_at >= cutoff)
    elif period == "year":
        cutoff = datetime.utcnow() - timedelta(days=365)
        query = query.filter(UserPoints.created_at >= cutoff)

    query = query.group_by(UserPoints.user_id).order_by(
        func.sum(UserPoints.points).desc()
    ).limit(20)

    results = query.all()
    leaders = []
    for user_id, total in results:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            leaders.append({
                "user_id": user_id,
                "display_name": user.display_name,
                "total_points": total,
            })
    return {"leaders": leaders, "period": period}
```

- [ ] **Step 2: Verify**

Run: `docker compose exec backend python -c "from app.routers.gamification import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/gamification.py
git commit -m "feat: leaderboard period filter (month/quarter/year/all)"
```

---

### Task 4: First discoverer on species detail page

**Files:**
- Modify: `frontend/src/views/SpeciesDetailView.vue`

- [ ] **Step 1: Add discoverer data fetching and display**

In `frontend/src/views/SpeciesDetailView.vue`, replace the `<script setup>` section (lines 34-52) with:

```typescript
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/client'

const route = useRoute()
const species = ref<any>(null)
const discoverer = ref<any>(null)

const GROUP_ICONS: Record<string, string> = { plants: '🌿', fungi: '🍄', insects: '🐛', herpetofauna: '🐍', birds: '🐦', mammals: '🦔' }
const GROUP_LABELS: Record<string, string> = { plants: 'Растения', fungi: 'Грибы', insects: 'Насекомые', herpetofauna: 'Герпетофауна', birds: 'Птицы', mammals: 'Млекопитающие' }
const CATEGORY_LABELS: Record<string, string> = { ruderal: 'Рудеральный', typical: 'Типичный', rare: 'Редкий', red_book: 'Красная книга', synanthropic: 'Синантроп' }

const groupIcon = computed(() => GROUP_ICONS[species.value?.group] || '🌱')
const groupLabel = computed(() => GROUP_LABELS[species.value?.group] || '')
const categoryLabel = computed(() => CATEGORY_LABELS[species.value?.category] || '')
const imgStyle = computed(() => species.value?.photo_urls?.length ? { backgroundImage: `url(${species.value.photo_urls[0]})` } : {})

function formatDate(iso: string): string {
  const d = new Date(iso)
  const months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`
}

onMounted(async () => {
  const { data } = await api.get(`/species/${route.params.id}`)
  species.value = data
  try {
    const res = await api.get(`/gamification/species/${route.params.id}/discoverer`)
    if (res.data.discoverer) {
      discoverer.value = res.data.discoverer
    }
  } catch {}
})
```

- [ ] **Step 2: Add the discoverer block to the template**

In the template, after the `detail-rules` div (line 26) and before `detail-actions` (line 27), add:

```html
        <div v-if="discoverer" class="discoverer-block">
          <span class="discoverer-icon">🏅</span>
          <span>Первое наблюдение: <strong>{{ discoverer.display_name }}</strong>, {{ formatDate(discoverer.discovered_at) }}</span>
        </div>
```

- [ ] **Step 3: Add the CSS**

In the `<style scoped>` section, before the `@media` line (line 80), add:

```css
.discoverer-block { display: flex; align-items: center; gap: 10px; margin-top: 20px; padding: 14px 16px; background: rgba(42,122,110,0.06); border-radius: 8px; border-left: 3px solid #2A7A6E; font-size: 14px; color: #1B4D4F; }
.discoverer-icon { font-size: 22px; flex-shrink: 0; }
```

- [ ] **Step 4: Verify frontend compiles**

Run: `docker compose exec frontend npm run build 2>&1 | tail -5`
Expected: Build succeeds without errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/SpeciesDetailView.vue
git commit -m "feat: show first discoverer on species detail page"
```

---

### Task 5: Leaderboard period tabs in ProfileView

**Files:**
- Modify: `frontend/src/views/ProfileView.vue`

- [ ] **Step 1: Add period state and fetch function**

In `frontend/src/views/ProfileView.vue`, replace the `<script setup>` section (lines 69-89) with:

```typescript
import { ref, onMounted } from 'vue'
import api from '../api/client'

const profile = ref<any>(null)
const leaders = ref<any[]>([])
const fact = ref<any>(null)
const leaderboardPeriod = ref('all')

async function fetchLeaderboard(period: string) {
  leaderboardPeriod.value = period
  try {
    const { data } = await api.get(`/gamification/leaderboard?period=${period}`)
    leaders.value = data.leaders || []
  } catch {}
}

onMounted(async () => {
  try {
    const [p, l, f] = await Promise.all([
      api.get('/gamification/profile'),
      api.get('/gamification/leaderboard'),
      api.get('/gamification/fact-of-day'),
    ])
    profile.value = p.data
    leaders.value = l.data.leaders || []
    fact.value = f.data.fact !== null ? f.data : null
  } catch {}
})
```

- [ ] **Step 2: Add period tabs to the template**

Replace the leaderboard section header (lines 41-43) with:

```html
      <div class="section-header">
        <h2 class="section-title">Лидерборд</h2>
        <div class="period-tabs">
          <button v-for="p in [{key:'month',label:'Месяц'},{key:'quarter',label:'Квартал'},{key:'year',label:'Год'},{key:'all',label:'Все время'}]"
                  :key="p.key"
                  class="period-tab"
                  :class="{ active: leaderboardPeriod === p.key }"
                  @click="fetchLeaderboard(p.key)">
            {{ p.label }}
          </button>
        </div>
      </div>
```

- [ ] **Step 3: Add CSS for period tabs**

In the `<style scoped>` section, after `.section-title` styles (line 106), add:

```css
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.section-header .section-title { margin-bottom: 0; }
.period-tabs { display: flex; gap: 4px; background: var(--slate-wash, #E8EEF0); border-radius: 8px; padding: 3px; }
.period-tab { padding: 6px 14px; border: none; background: transparent; border-radius: 6px; font-size: 12px; font-weight: 600; color: var(--slate-mid, #8FA5AB); cursor: pointer; transition: all 0.2s; }
.period-tab:hover { color: var(--teal, #2A7A6E); }
.period-tab.active { background: white; color: var(--teal, #2A7A6E); box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
```

- [ ] **Step 4: Verify frontend compiles**

Run: `docker compose exec frontend npm run build 2>&1 | tail -5`
Expected: Build succeeds without errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/ProfileView.vue
git commit -m "feat: leaderboard period tabs (month/quarter/year/all)"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Feature 1 (trigger logic): Task 1 + Task 2
- ✅ Feature 2 (first discoverer on species detail): Task 4
- ✅ Feature 3 (leaderboard period filter): Task 3 + Task 5

**Placeholder scan:** No TBD/TODO. All code blocks contain complete implementation.

**Type consistency:**
- `award_gamification(observation_id: int, db: Session)` — consistent across Task 1 (definition) and Task 2 (call site)
- `period` parameter: `month|quarter|year|all` — consistent between backend (Task 3) and frontend (Task 5)
- `discoverer.display_name` and `discoverer.discovered_at` — match backend response format in `gamification.py:96-99`
