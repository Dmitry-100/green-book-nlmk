import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CatalogImportBatchStatus(str, enum.Enum):
    applied = "applied"
    rolled_back = "rolled_back"


class CatalogImportBatch(Base):
    __tablename__ = "catalog_import_batches"
    __table_args__ = (
        Index("ix_catalog_import_batches_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CatalogImportBatchStatus] = mapped_column(
        Enum(CatalogImportBatchStatus),
        default=CatalogImportBatchStatus.applied,
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    rolled_back_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    changed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unchanged_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    applied_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    changes: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
