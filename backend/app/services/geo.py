from geoalchemy2.functions import ST_Contains, ST_SetSRID, ST_MakePoint
from sqlalchemy.orm import Session

from app.models.site_zone import SiteZone


def detect_zone(db: Session, lat: float, lon: float) -> int | None:
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    zone = db.query(SiteZone).filter(ST_Contains(SiteZone.geom, point)).first()
    return zone.id if zone else None


def detect_zones(db: Session, lat: float, lon: float) -> list[dict]:
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
    zones = db.query(SiteZone).filter(ST_Contains(SiteZone.geom, point)).all()
    return [{"id": z.id, "name": z.name} for z in zones]
