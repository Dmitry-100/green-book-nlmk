from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import String, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SiteZone(Base):
    __tablename__ = "site_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    group: Mapped[str | None] = mapped_column(String(255))
    geom: Mapped[str] = mapped_column(Geometry("POLYGON", srid=4326))
    source: Mapped[str | None] = mapped_column(String(255))
    polygon_count: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
