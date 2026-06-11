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
    unlisted_species_name: str | None = Field(default=None, max_length=200)
    comment: str | None = Field(default=None, max_length=2000)
    is_incident: bool = False
    incident_type: IncidentType | None = None
    incident_severity: IncidentSeverity | None = None
    safety_checked: bool = False
    content_notice_accepted: bool = False
    content_notice_version: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_incident_fields(self):
        if self.is_incident:
            if self.incident_type is None or self.incident_severity is None:
                raise ValueError(
                    "incident_type and incident_severity are required for incidents"
                )
        return self

    @model_validator(mode="after")
    def validate_species_claim(self):
        if self.unlisted_species_name is not None:
            self.unlisted_species_name = self.unlisted_species_name.strip() or None
        if self.species_id is not None and self.unlisted_species_name is not None:
            raise ValueError(
                "Укажите либо вид из справочника, либо название нового вида"
            )
        return self


class MediaAttach(BaseModel):
    s3_key: str = Field(min_length=1, max_length=500)
    mime_type: str = Field(min_length=3, max_length=100)
    thumbnail_key: str | None = Field(default=None, max_length=500)


class ObservationUpdate(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)
    species_id: int | None = Field(default=None, gt=0)
    unlisted_species_name: str | None = Field(default=None, max_length=200)


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
    author_id: int | None
    species_id: int | None
    group: str
    observed_at: datetime
    site_zone_id: int | None
    status: ObservationStatus
    comment: str | None
    unlisted_species_name: str | None = None
    is_incident: bool
    incident_type: IncidentType | None
    incident_severity: IncidentSeverity | None
    incident_status: IncidentStatus | None
    sensitive_level: SensitiveLevel
    safety_checked: bool
    created_at: datetime
    lat: float | None = None
    lon: float | None = None
    author_display_name: str | None = None
    author_public_name: str | None = None
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
