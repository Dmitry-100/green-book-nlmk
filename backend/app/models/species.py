import enum
from datetime import datetime

from sqlalchemy import String, Text, Enum, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SpeciesGroup(str, enum.Enum):
    plants = "plants"
    fungi = "fungi"
    insects = "insects"
    herpetofauna = "herpetofauna"
    birds = "birds"
    mammals = "mammals"


class SpeciesCategory(str, enum.Enum):
    ruderal = "ruderal"
    typical = "typical"
    rare = "rare"
    red_book = "red_book"
    synanthropic = "synanthropic"


class Species(Base):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_ru: Mapped[str] = mapped_column(String(255))
    name_latin: Mapped[str] = mapped_column(String(255))
    group: Mapped[SpeciesGroup] = mapped_column(Enum(SpeciesGroup), index=True)
    category: Mapped[SpeciesCategory] = mapped_column(Enum(SpeciesCategory), index=True)
    conservation_status: Mapped[str | None] = mapped_column(String(255))
    is_poisonous: Mapped[bool] = mapped_column(Boolean, default=False)
    season_info: Mapped[str | None] = mapped_column(String(500))
    biotopes: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    do_dont_rules: Mapped[str | None] = mapped_column(Text)
    qr_url: Mapped[str | None] = mapped_column(String(500))
    photo_urls: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
