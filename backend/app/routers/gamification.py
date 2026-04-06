from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.gamification import (
    Achievement, UserAchievement, UserPoints, SpeciesFirstDiscovery,
    ObservationComment, ObservationLike,
)
from app.models.observation import Observation, ObservationStatus
from app.models.species import Species
from app.models.user import User

router = APIRouter(prefix="/api/gamification", tags=["gamification"])


@router.get("/leaderboard")
def leaderboard(
    period: str = Query("all", pattern="^(all|month|quarter|year)$"),
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


@router.get("/profile")
def my_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Current user's gamification profile."""
    total_points = db.query(func.sum(UserPoints.points)).filter(
        UserPoints.user_id == user.id
    ).scalar() or 0

    obs_count = db.query(Observation).filter(
        Observation.author_id == user.id,
        Observation.status == ObservationStatus.confirmed,
    ).count()

    achievements = db.query(Achievement).join(UserAchievement).filter(
        UserAchievement.user_id == user.id
    ).all()

    discoveries = db.query(SpeciesFirstDiscovery).filter(
        SpeciesFirstDiscovery.user_id == user.id
    ).count()

    # Species collection: unique confirmed species
    species_ids = db.query(Observation.species_id).filter(
        Observation.author_id == user.id,
        Observation.status == ObservationStatus.confirmed,
        Observation.species_id != None,
    ).distinct().all()

    return {
        "user_id": user.id,
        "display_name": user.display_name,
        "total_points": total_points,
        "confirmed_observations": obs_count,
        "first_discoveries": discoveries,
        "species_collected": len(species_ids),
        "achievements": [
            {"code": a.code, "name": a.name, "icon": a.icon, "description": a.description}
            for a in achievements
        ],
    }


@router.get("/species/{species_id}/discoverer")
def species_discoverer(species_id: int, db: Session = Depends(get_db)):
    """Who first discovered this species."""
    discovery = db.query(SpeciesFirstDiscovery).filter(
        SpeciesFirstDiscovery.species_id == species_id
    ).first()
    if not discovery:
        return {"discoverer": None}
    user = db.query(User).filter(User.id == discovery.user_id).first()
    return {
        "discoverer": {
            "display_name": user.display_name if user else "Unknown",
            "discovered_at": discovery.discovered_at.isoformat(),
        }
    }


@router.get("/stats")
def biodiversity_stats(db: Session = Depends(get_db)):
    """Ecological passport stats with Shannon index and seasonal dynamics."""
    import math

    total_species = db.query(Species).count()
    confirmed_species = db.query(Observation.species_id).filter(
        Observation.status == ObservationStatus.confirmed,
        Observation.species_id != None,
    ).distinct().count()

    by_group = db.query(
        Species.group, func.count(Species.id)
    ).group_by(Species.group).all()

    total_obs = db.query(Observation).filter(
        Observation.status == ObservationStatus.confirmed
    ).count()

    # Shannon Diversity Index
    shannon_index = 0.0
    if total_obs > 0:
        species_counts = db.query(
            Observation.species_id, func.count(Observation.id)
        ).filter(
            Observation.status == ObservationStatus.confirmed,
            Observation.species_id != None,
        ).group_by(Observation.species_id).all()

        for _, count in species_counts:
            pi = count / total_obs
            if pi > 0:
                shannon_index -= pi * math.log(pi)

    # Seasonal dynamics: distinct species per month
    from sqlalchemy import extract
    seasonal = db.query(
        extract("month", Observation.observed_at).label("month"),
        func.count(func.distinct(Observation.species_id)).label("species_count"),
    ).filter(
        Observation.status == ObservationStatus.confirmed,
        Observation.species_id != None,
    ).group_by("month").order_by("month").all()

    seasonal_data = [{"month": int(m), "species_count": c} for m, c in seasonal]

    # Heatmap data: lat/lon of confirmed observations
    from geoalchemy2.functions import ST_X, ST_Y
    heatmap_rows = db.query(
        ST_Y(Observation.location_point).label("lat"),
        ST_X(Observation.location_point).label("lon"),
        Observation.group,
    ).filter(
        Observation.status == ObservationStatus.confirmed,
    ).all()

    heatmap = [{"lat": float(r.lat), "lon": float(r.lon), "group": r.group} for r in heatmap_rows]

    return {
        "total_species_in_catalog": total_species,
        "confirmed_species": confirmed_species,
        "total_confirmed_observations": total_obs,
        "species_by_group": {g: c for g, c in by_group},
        "biodiversity_coverage": round(confirmed_species / total_species * 100, 1) if total_species else 0,
        "shannon_index": round(shannon_index, 3),
        "seasonal_dynamics": seasonal_data,
        "heatmap": heatmap,
    }


@router.get("/fact-of-day")
def fact_of_day(db: Session = Depends(get_db)):
    """Random interesting species fact."""
    species = db.query(Species).filter(
        Species.description != None, Species.description != ""
    ).order_by(func.random()).first()
    if not species:
        return {"fact": None}
    return {
        "species_id": species.id,
        "name_ru": species.name_ru,
        "name_latin": species.name_latin,
        "description": species.description,
        "photo_url": species.photo_urls[0] if species.photo_urls else None,
        "is_poisonous": species.is_poisonous,
        "conservation_status": species.conservation_status,
    }


@router.get("/quiz")
def quiz_question(db: Session = Depends(get_db)):
    """Generate a quiz question: show a photo, guess the species name."""
    # Pick a random species that has a photo
    correct = db.query(Species).filter(
        Species.photo_urls != None,
        func.array_length(Species.photo_urls, 1) > 0,
    ).order_by(func.random()).first()

    if not correct:
        return {"question": None}

    # Pick 3 wrong answers from same group
    wrong = db.query(Species).filter(
        Species.id != correct.id,
        Species.group == correct.group,
    ).order_by(func.random()).limit(3).all()

    # If not enough from same group, fill from others
    if len(wrong) < 3:
        extra = db.query(Species).filter(
            Species.id != correct.id,
            Species.id.not_in([w.id for w in wrong]),
        ).order_by(func.random()).limit(3 - len(wrong)).all()
        wrong.extend(extra)

    import random
    options = [{"id": correct.id, "name_ru": correct.name_ru, "name_latin": correct.name_latin}]
    for w in wrong:
        options.append({"id": w.id, "name_ru": w.name_ru, "name_latin": w.name_latin})
    random.shuffle(options)

    return {
        "photo_url": correct.photo_urls[0] if correct.photo_urls else None,
        "correct_id": correct.id,
        "group": correct.group,
        "options": options,
    }
