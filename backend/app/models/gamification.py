from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Index,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Achievement(Base):
    """Achievement/badge definition."""
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(10))  # emoji
    points_reward: Mapped[int] = mapped_column(Integer, default=0)
    condition_type: Mapped[str] = mapped_column(String(50))  # obs_count, group_count, rare_find, etc
    condition_value: Mapped[int] = mapped_column(Integer, default=1)


class UserAchievement(Base):
    """Earned achievements for a user."""
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id"))
    earned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "achievement_id"),)


class UserPoints(Base):
    """Points log for a user."""
    __tablename__ = "user_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    observation_id: Mapped[int | None] = mapped_column(ForeignKey("observations.id"))
    points: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("ix_user_points_created_at_user_id", "created_at", "user_id"),)


class SpeciesFirstDiscovery(Base):
    """First confirmed observation of a species."""
    __tablename__ = "species_first_discoveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    observation_id: Mapped[int] = mapped_column(ForeignKey("observations.id"))
    discovered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ObservationComment(Base):
    """Comments on observations."""
    __tablename__ = "observation_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    observation_id: Mapped[int] = mapped_column(ForeignKey("observations.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (
        Index(
            "ix_observation_comments_observation_created_at",
            "observation_id",
            "created_at",
        ),
    )


class ObservationLike(Base):
    """Likes on observations."""
    __tablename__ = "observation_likes"

    id: Mapped[int] = mapped_column(primary_key=True)
    observation_id: Mapped[int] = mapped_column(ForeignKey("observations.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("observation_id", "user_id"),)
