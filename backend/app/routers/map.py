import json

from fastapi import APIRouter, Depends, Query, UploadFile, File
from geoalchemy2.functions import ST_AsGeoJSON, ST_X, ST_Y
from sqlalchemy.orm import Session

from app.auth import require_role
from app.database import get_db
from app.models.observation import Observation, ObservationStatus, SensitiveLevel
from app.models.site_zone import SiteZone
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/map", tags=["map"])


@router.get("/observations")
def map_observations(
    group: str | None = None,
    status: ObservationStatus | None = Query(ObservationStatus.confirmed),
    db: Session = Depends(get_db),
):
    """Return observation points for map display, respecting sensitivity."""
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
    if group:
        query = query.filter(Observation.group == group)
    if status:
        query = query.filter(Observation.status == status)

    results = query.all()
    features = []
    for r in results:
        # Respect sensitivity: hide exact coords for sensitive species
        if r.sensitive_level == SensitiveLevel.hidden:
            continue
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
def map_zones(db: Session = Depends(get_db)):
    """Return site zones as GeoJSON for map overlay."""
    zones = db.query(
        SiteZone.id,
        SiteZone.name,
        SiteZone.group,
        ST_AsGeoJSON(SiteZone.geom).label("geojson"),
    ).all()
    features = []
    for z in zones:
        features.append({
            "type": "Feature",
            "geometry": json.loads(z.geojson),
            "properties": {"id": z.id, "name": z.name, "group": z.group},
        })
    return {"type": "FeatureCollection", "features": features}


@router.get("/zone-by-point")
def zone_by_point(
    lat: float = Query(...),
    lon: float = Query(...),
    db: Session = Depends(get_db),
):
    """Determine which zone contains the given point."""
    from app.services.geo import detect_zones
    zones = detect_zones(db, lat, lon)
    return {"zones": zones}
