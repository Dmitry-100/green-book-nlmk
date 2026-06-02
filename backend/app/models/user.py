import enum
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Enum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    employee = "employee"
    ecologist = "ecologist"
    admin = "admin"


class UserApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    login: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.employee)
    approval_status: Mapped[UserApprovalStatus] = mapped_column(
        Enum(UserApprovalStatus),
        default=UserApprovalStatus.approved,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
