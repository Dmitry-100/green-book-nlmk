from pydantic import BaseModel, Field, field_validator
from app.models.species import SpeciesGroup, SpeciesCategory


class SpeciesBase(BaseModel):
    name_ru: str = Field(min_length=2, max_length=255)
    name_latin: str = Field(min_length=2, max_length=255)
    group: SpeciesGroup
    category: SpeciesCategory
    conservation_status: str | None = Field(default=None, max_length=255)
    is_poisonous: bool = False
    season_info: str | None = Field(default=None, max_length=500)
    biotopes: str | None = Field(default=None, max_length=5000)
    description: str | None = Field(default=None, max_length=10000)
    do_dont_rules: str | None = Field(default=None, max_length=10000)
    qr_url: str | None = Field(default=None, max_length=500)
    photo_urls: list[str] | None = Field(default=None, min_length=1, max_length=20)
    audio_url: str | None = Field(default=None, max_length=500)
    audio_title: str | None = Field(default=None, max_length=255)
    audio_source: str | None = Field(default=None, max_length=255)
    audio_license: str | None = Field(default=None, max_length=255)

    @field_validator("name_ru", "name_latin", mode="before")
    @classmethod
    def _normalize_required_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Field must not be blank")
        return value

    @field_validator(
        "conservation_status",
        "season_info",
        "biotopes",
        "description",
        "do_dont_rules",
        "qr_url",
        "audio_title",
        "audio_source",
        "audio_license",
        mode="before",
    )
    @classmethod
    def _normalize_optional_text(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("photo_urls")
    @classmethod
    def _validate_photo_urls(cls, value: list[str] | None):
        if value is None:
            return None
        normalized: list[str] = []
        for item in value:
            url = item.strip()
            if not url:
                raise ValueError("photo_urls must not contain empty values")
            if len(url) > 500:
                raise ValueError("photo_urls items must be at most 500 chars")
            normalized.append(url)
        return normalized

    @field_validator("audio_url", mode="before")
    @classmethod
    def _normalize_audio_url(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("audio_url")
    @classmethod
    def _validate_audio_url(cls, value: str | None):
        if value is None:
            return None
        if not (value.startswith("https://") or value.startswith("/api/media/")):
            raise ValueError("audio_url must be https:// or /api/media/")
        return value


class SpeciesCreate(SpeciesBase):
    pass


class SpeciesUpdate(BaseModel):
    name_ru: str | None = Field(default=None, min_length=2, max_length=255)
    name_latin: str | None = Field(default=None, min_length=2, max_length=255)
    group: SpeciesGroup | None = None
    category: SpeciesCategory | None = None
    conservation_status: str | None = Field(default=None, max_length=255)
    is_poisonous: bool | None = None
    season_info: str | None = Field(default=None, max_length=500)
    biotopes: str | None = Field(default=None, max_length=5000)
    description: str | None = Field(default=None, max_length=10000)
    do_dont_rules: str | None = Field(default=None, max_length=10000)
    qr_url: str | None = Field(default=None, max_length=500)
    photo_urls: list[str] | None = Field(default=None, min_length=1, max_length=20)
    audio_url: str | None = Field(default=None, max_length=500)
    audio_title: str | None = Field(default=None, max_length=255)
    audio_source: str | None = Field(default=None, max_length=255)
    audio_license: str | None = Field(default=None, max_length=255)

    @field_validator("name_ru", "name_latin", mode="before")
    @classmethod
    def _normalize_required_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Field must not be blank")
        return value

    @field_validator(
        "conservation_status",
        "season_info",
        "biotopes",
        "description",
        "do_dont_rules",
        "qr_url",
        "audio_title",
        "audio_source",
        "audio_license",
        mode="before",
    )
    @classmethod
    def _normalize_optional_text(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("photo_urls")
    @classmethod
    def _validate_photo_urls(cls, value: list[str] | None):
        if value is None:
            return None
        normalized: list[str] = []
        for item in value:
            url = item.strip()
            if not url:
                raise ValueError("photo_urls must not contain empty values")
            if len(url) > 500:
                raise ValueError("photo_urls items must be at most 500 chars")
            normalized.append(url)
        return normalized

    @field_validator("audio_url", mode="before")
    @classmethod
    def _normalize_audio_url(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("audio_url")
    @classmethod
    def _validate_audio_url(cls, value: str | None):
        if value is None:
            return None
        if not (value.startswith("https://") or value.startswith("/api/media/")):
            raise ValueError("audio_url must be https:// or /api/media/")
        return value


class SpeciesResponse(SpeciesBase):
    id: int
    model_config = {"from_attributes": True}


class SpeciesListResponse(BaseModel):
    items: list[SpeciesResponse]
    total: int | None = None
