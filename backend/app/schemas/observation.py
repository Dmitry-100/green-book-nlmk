from datetime import datetime
from pydantic import BaseModel
from app.models.observation import (
    ObservationStatus, IncidentType, IncidentSeverity, IncidentStatus, SensitiveLevel,
)


class ObservationCreate(BaseModel):
    group: str
    observed_at: datetime
    lat: float
    lon: float
    species_id: int | None = None
    comment: str | None = None
    is_incident: bool = False
    incident_type: IncidentType | None = None
    incident_severity: IncidentSeverity | None = None
    safety_checked: bool = False


class MediaAttach(BaseModel):
    s3_key: str
    mime_type: str
    thumbnail_key: str | None = None


class ObservationUpdate(BaseModel):
    comment: str | None = None
    species_id: int | None = None


class MediaInfo(BaseModel):
    id: int
    s3_key: str
    thumbnail_key: str | None
    mime_type: str
    model_config = {"from_attributes": True}


class ObservationResponse(BaseModel):
    id: int
    author_id: int
    species_id: int | None
    group: str
    observed_at: datetime
    site_zone_id: int | None
    status: ObservationStatus
    comment: str | None
    is_incident: bool
    incident_type: IncidentType | None
    incident_severity: IncidentSeverity | None
    incident_status: IncidentStatus | None
    sensitive_level: SensitiveLevel
    safety_checked: bool
    created_at: datetime
    media: list[MediaInfo] = []
    model_config = {"from_attributes": True}


class ObservationListResponse(BaseModel):
    items: list[ObservationResponse]
    total: int


class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str


class UploadUrlResponse(BaseModel):
    upload_url: str
    s3_key: str
