from pydantic import BaseModel
from app.models.species import SpeciesGroup, SpeciesCategory


class SpeciesBase(BaseModel):
    name_ru: str
    name_latin: str
    group: SpeciesGroup
    category: SpeciesCategory
    conservation_status: str | None = None
    is_poisonous: bool = False
    season_info: str | None = None
    biotopes: str | None = None
    description: str | None = None
    do_dont_rules: str | None = None
    qr_url: str | None = None
    photo_urls: list[str] | None = None


class SpeciesCreate(SpeciesBase):
    pass


class SpeciesUpdate(BaseModel):
    name_ru: str | None = None
    name_latin: str | None = None
    group: SpeciesGroup | None = None
    category: SpeciesCategory | None = None
    conservation_status: str | None = None
    is_poisonous: bool | None = None
    season_info: str | None = None
    biotopes: str | None = None
    description: str | None = None
    do_dont_rules: str | None = None
    qr_url: str | None = None
    photo_urls: list[str] | None = None


class SpeciesResponse(SpeciesBase):
    id: int
    model_config = {"from_attributes": True}


class SpeciesListResponse(BaseModel):
    items: list[SpeciesResponse]
    total: int
