import json

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from geoalchemy2.elements import WKTElement
from shapely.geometry import shape
from sqlalchemy.orm import Session

from app.auth import require_role
from app.database import get_db
from app.models.site_zone import SiteZone
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/zones/import")
async def import_zones(
    file: UploadFile = File(...),
    user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Import site zones from a GeoJSON file."""
    if not file.filename.endswith(".geojson") and not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only GeoJSON files are supported")

    content = await file.read()
    try:
        geojson = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    features = geojson.get("features", [])
    if not features:
        raise HTTPException(status_code=400, detail="No features found in GeoJSON")

    imported = 0
    for feature in features:
        geom = feature.get("geometry")
        props = feature.get("properties", {})
        if not geom:
            continue
        # Convert to WKT via Shapely
        shapely_geom = shape(geom)
        wkt = WKTElement(shapely_geom.wkt, srid=4326)
        zone = SiteZone(
            name=props.get("name", f"Zone {imported + 1}"),
            group=props.get("group"),
            geom=wkt,
            source=file.filename,
        )
        db.add(zone)
        imported += 1

    db.commit()
    return {"imported": imported, "filename": file.filename}
