import json

import orjson
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from geoalchemy2.functions import ST_AsGeoJSON, ST_MakeEnvelope, ST_X, ST_Y
from sqlalchemy.orm import Session

from app.auth import get_optional_user
from app.config import settings
from app.database import get_db
from app.models.observation import Observation, ObservationStatus, SensitiveLevel
from app.models.site_zone import SiteZone
from app.models.species import SpeciesGroup
from app.models.user import User, UserRole
from app.services.cache import KeyedTTLCache, RedisKeyedTTLCache, TTLCache

router = APIRouter(prefix="/api/map", tags=["map"])
_MAP_ZONES_CACHE = TTLCache[dict](settings.map_zones_cache_ttl_seconds)
_MAP_OBSERVATIONS_MEMORY_CACHE = KeyedTTLCache[tuple[str | None, str | None, int], dict](
    settings.map_observations_cache_ttl_seconds,
    max_entries=128,
)
_MAP_OBSERVATIONS_CACHE = RedisKeyedTTLCache[tuple[str | None, str | None, int], dict](
    redis_url=settings.redis_url,
    key_prefix="cache:map:observations",
    ttl_seconds=settings.map_observations_cache_ttl_seconds,
    fallback_cache=_MAP_OBSERVATIONS_MEMORY_CACHE,
    enabled=settings.redis_cache_enabled,
    namespace=settings.redis_cache_namespace,
)


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    parts = [part.strip() for part in bbox.split(",")]
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="Invalid bbox format")

    try:
        min_lon, min_lat, max_lon, max_lat = (float(part) for part in parts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid bbox format") from exc

    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        raise HTTPException(status_code=400, detail="bbox longitude out of range")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise HTTPException(status_code=400, detail="bbox latitude out of range")
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=400, detail="bbox bounds are invalid")
    return min_lon, min_lat, max_lon, max_lat


@router.get("/observations")
def map_observations(
    group: SpeciesGroup | None = None,
    status: ObservationStatus | None = Query(ObservationStatus.confirmed),
    bbox: str | None = Query(default=None),
    limit: int = Query(default=1200, ge=1, le=5000),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Return observation points for map display, respecting sensitivity."""
    if status != ObservationStatus.confirmed:
        if user is None or user.role not in (UserRole.ecologist, UserRole.admin):
            raise HTTPException(status_code=403, detail="Not enough permissions")

    cacheable = (
        status == ObservationStatus.confirmed
        and settings.map_observations_cache_ttl_seconds > 0
    )
    if cacheable:
        cache_key = (group.value if group else None, bbox, limit)
        payload = _MAP_OBSERVATIONS_CACHE.get_or_set(
            cache_key,
            lambda: _build_map_observations_payload(
                db=db,
                group=group,
                status=status,
                bbox=bbox,
                limit=limit,
            ),
        )
        return Response(
            content=orjson.dumps(payload),
            media_type="application/json",
            headers={
                "Cache-Control": (
                    f"public, max-age={settings.map_observations_cache_ttl_seconds}"
                )
            },
        )

    payload = _build_map_observations_payload(
        db=db,
        group=group,
        status=status,
        bbox=bbox,
        limit=limit,
    )
    return Response(
        content=orjson.dumps(payload),
        media_type="application/json",
        headers={"Cache-Control": "private, no-store"},
    )


def _build_map_observations_payload(
    *,
    db: Session,
    group: SpeciesGroup | None,
    status: ObservationStatus | None,
    bbox: str | None,
    limit: int,
) -> dict:
    query = db.query(
        Observation.id,
        Observation.group,
        Observation.status,
        Observation.is_incident,
        Observation.sensitive_level,
        Observation.species_id,
        Observation.observed_at,
        ST_X(Observation.location_point).label("lon"),
        ST_Y(Observation.location_point).label("lat"),
    )
    query = query.filter(
        Observation.sensitive_level.in_([SensitiveLevel.open, SensitiveLevel.blurred])
    )
    if group:
        query = query.filter(Observation.group == group.value)
    if status:
        query = query.filter(Observation.status == status)
    if bbox:
        min_lon, min_lat, max_lon, max_lat = _parse_bbox(bbox)
        envelope = ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        # location_point is POINT geometry, so bbox intersection is sufficient.
        query = query.filter(
            Observation.location_point.op("&&")(envelope),
        )

    results = query.order_by(Observation.observed_at.desc()).limit(limit).all()
    features = []
    for r in results:
        lat, lon = r.lat, r.lon
        if r.sensitive_level == SensitiveLevel.blurred:
            # Round to ~1km precision
            lat = round(lat, 2)
            lon = round(lon, 2)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "id": r.id,
                "group": r.group,
                "status": r.status.value if r.status else None,
                "is_incident": r.is_incident,
                "observed_at": r.observed_at.isoformat() if r.observed_at else None,
            },
        })
    return {"type": "FeatureCollection", "features": features}


@router.get("/zones")
def map_zones(response: Response, db: Session = Depends(get_db)):
    """Return site zones as GeoJSON for map overlay."""
    response.headers["Cache-Control"] = (
        f"public, max-age={settings.map_zones_cache_ttl_seconds}"
    )

    def _load_zones() -> dict:
        zones = db.query(
            SiteZone.id,
            SiteZone.name,
            SiteZone.group,
            ST_AsGeoJSON(SiteZone.geom).label("geojson"),
        ).all()
        features = []
        for zone in zones:
            features.append({
                "type": "Feature",
                "geometry": json.loads(zone.geojson),
                "properties": {
                    "id": zone.id,
                    "name": zone.name,
                    "group": zone.group,
                },
            })
        return {"type": "FeatureCollection", "features": features}

    return _MAP_ZONES_CACHE.get_or_set(_load_zones)


@router.get("/zone-by-point")
def zone_by_point(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    db: Session = Depends(get_db),
):
    """Determine which zone contains the given point."""
    from app.services.geo import detect_zones
    zones = detect_zones(db, lat, lon)
    return {"zones": zones}
