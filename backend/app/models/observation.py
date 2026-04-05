import enum
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    String,
    Text,
    Enum,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ObservationStatus(str, enum.Enum):
    on_review = "on_review"
    needs_data = "needs_data"
    confirmed = "confirmed"
    rejected = "rejected"


class IncidentType(str, enum.Enum):
    injured = "injured"
    dead = "dead"
    mass_death = "mass_death"
    other = "other"


class IncidentSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(str, enum.Enum):
    new = "new"
    in_progress = "in_progress"
    closed = "closed"


class SensitiveLevel(str, enum.Enum):
    open = "open"
    blurred = "blurred"
    hidden = "hidden"


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    species_id: Mapped[int | None] = mapped_column(ForeignKey("species.id"))
    group: Mapped[str] = mapped_column(String(50))
    observed_at: Mapped[datetime] = mapped_column(DateTime)
    location_point: Mapped[str] = mapped_column(Geometry("POINT", srid=4326))
    site_zone_id: Mapped[int | None] = mapped_column(ForeignKey("site_zones.id"))
    status: Mapped[ObservationStatus] = mapped_column(
        Enum(ObservationStatus), default=ObservationStatus.on_review, index=True
    )
    comment: Mapped[str | None] = mapped_column(Text)
    is_incident: Mapped[bool] = mapped_column(Boolean, default=False)
    incident_type: Mapped[IncidentType | None] = mapped_column(Enum(IncidentType))
    incident_severity: Mapped[IncidentSeverity | None] = mapped_column(
        Enum(IncidentSeverity)
    )
    incident_status: Mapped[IncidentStatus | None] = mapped_column(
        Enum(IncidentStatus)
    )
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    reviewer_comment: Mapped[str | None] = mapped_column(Text)
    sensitive_level: Mapped[SensitiveLevel] = mapped_column(
        Enum(SensitiveLevel), default=SensitiveLevel.open
    )
    safety_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    media: Mapped[list["ObsMedia"]] = relationship(back_populates="observation")


class ObsMedia(Base):
    __tablename__ = "obs_media"

    id: Mapped[int] = mapped_column(primary_key=True)
    observation_id: Mapped[int] = mapped_column(
        ForeignKey("observations.id", ondelete="CASCADE"), index=True
    )
    s3_key: Mapped[str] = mapped_column(String(500))
    thumbnail_key: Mapped[str | None] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    observation: Mapped["Observation"] = relationship(back_populates="media")
