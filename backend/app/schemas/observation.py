from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from app.models.observation import (
    ObservationStatus,
    IncidentType,
    IncidentSeverity,
    IncidentStatus,
    SensitiveLevel,
    MediaProcessingStatus,
)
from app.models.species import SpeciesGroup


class ObservationCreate(BaseModel):
    group: SpeciesGroup
    observed_at: datetime
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    species_id: int | None = Field(default=None, gt=0)
    comment: str | None = Field(default=None, max_length=2000)
    is_incident: bool = False
    incident_type: IncidentType | None = None
    incident_severity: IncidentSeverity | None = None
    safety_checked: bool = False

    @model_validator(mode="after")
    def validate_incident_fields(self):
        if self.is_incident:
            if self.incident_type is None or self.incident_severity is None:
                raise ValueError(
                    "incident_type and incident_severity are required for incidents"
                )
        return self


class MediaAttach(BaseModel):
    s3_key: str = Field(min_length=1, max_length=500)
    mime_type: str = Field(min_length=3, max_length=100)
    thumbnail_key: str | None = Field(default=None, max_length=500)


class ObservationUpdate(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)
    species_id: int | None = Field(default=None, gt=0)


class MediaInfo(BaseModel):
    id: int
    s3_key: str
    thumbnail_key: str | None
    mime_type: str
    processing_status: MediaProcessingStatus
    processing_attempts: int
    processing_error: str | None
    processed_at: datetime | None
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
    lat: float | None = None
    lon: float | None = None
    media: list[MediaInfo] = []
    model_config = {"from_attributes": True}


class ObservationListResponse(BaseModel):
    items: list[ObservationResponse]
    total: int | None = None


class UploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=100)
    file_size: int | None = Field(default=None, gt=0, le=100 * 1024 * 1024)


class UploadUrlResponse(BaseModel):
    upload_url: str
    s3_key: str
    content_type: str
