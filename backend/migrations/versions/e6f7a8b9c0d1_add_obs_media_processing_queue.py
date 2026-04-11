"""add obs_media processing queue columns

Revision ID: e6f7a8b9c0d1
Revises: d3e4f5a6b7c8
Create Date: 2026-04-11 14:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    media_processing_status = sa.Enum(
        "pending",
        "processing",
        "ready",
        "failed",
        name="mediaprocessingstatus",
    )
    media_processing_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "obs_media",
        sa.Column(
            "processing_status",
            media_processing_status,
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "obs_media",
        sa.Column(
            "processing_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "obs_media",
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "obs_media",
        sa.Column("processing_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "obs_media",
        sa.Column("processed_at", sa.DateTime(), nullable=True),
    )

    op.create_index(
        op.f("ix_obs_media_processing_status"),
        "obs_media",
        ["processing_status"],
        unique=False,
    )
    op.create_index(
        "ix_obs_media_processing_status_next_retry",
        "obs_media",
        ["processing_status", "next_retry_at"],
        unique=False,
    )

    # Existing rows were attached before async pipeline; treat them as already processed.
    op.execute(
        "UPDATE obs_media "
        "SET processing_status = 'ready', processing_attempts = 0, processed_at = created_at"
    )
    op.alter_column("obs_media", "processing_status", server_default=None)
    op.alter_column("obs_media", "processing_attempts", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_obs_media_processing_status_next_retry", table_name="obs_media")
    op.drop_index(op.f("ix_obs_media_processing_status"), table_name="obs_media")

    op.drop_column("obs_media", "processed_at")
    op.drop_column("obs_media", "processing_error")
    op.drop_column("obs_media", "next_retry_at")
    op.drop_column("obs_media", "processing_attempts")
    op.drop_column("obs_media", "processing_status")

    media_processing_status = sa.Enum(
        "pending",
        "processing",
        "ready",
        "failed",
        name="mediaprocessingstatus",
    )
    media_processing_status.drop(op.get_bind(), checkfirst=True)
