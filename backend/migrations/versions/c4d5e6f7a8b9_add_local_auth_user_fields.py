"""add local auth user fields

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-06-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

approval_status_enum = sa.Enum(
    "pending",
    "approved",
    "rejected",
    name="userapprovalstatus",
)


def upgrade() -> None:
    approval_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("login", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "approval_status",
            approval_status_enum,
            server_default="approved",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column("users", sa.Column("approved_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("approved_by_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)
    op.create_index(op.f("ix_users_login"), "users", ["login"], unique=True)
    op.create_foreign_key(
        "fk_users_approved_by_id_users",
        "users",
        "users",
        ["approved_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_approved_by_id_users", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_login"), table_name="users")
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "approved_by_id")
    op.drop_column("users", "approved_at")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "is_active")
    op.drop_column("users", "approval_status")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "login")
    approval_status_enum.drop(op.get_bind(), checkfirst=True)
