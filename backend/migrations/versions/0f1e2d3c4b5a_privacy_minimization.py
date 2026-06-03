"""Add privacy notices and approve existing pending users.

Revision ID: 0f1e2d3c4b5a
Revises: c4d5e6f7a8b9
Create Date: 2026-06-03 02:10:00.000000
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "0f1e2d3c4b5a"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("privacy_notice_version", sa.String(length=50)))
    op.add_column("users", sa.Column("privacy_notice_accepted_at", sa.DateTime()))
    op.add_column(
        "observations",
        sa.Column("content_notice_version", sa.String(length=50)),
    )
    op.add_column(
        "observations",
        sa.Column("content_notice_accepted_at", sa.DateTime()),
    )
    op.execute(
        """
        UPDATE users
        SET approval_status = 'approved',
            approved_at = COALESCE(approved_at, NOW()),
            approved_by_id = NULL
        WHERE approval_status = 'pending'
        """
    )


def downgrade() -> None:
    op.drop_column("observations", "content_notice_accepted_at")
    op.drop_column("observations", "content_notice_version")
    op.drop_column("users", "privacy_notice_accepted_at")
    op.drop_column("users", "privacy_notice_version")
