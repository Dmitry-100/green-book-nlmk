"""add species audio metadata

Revision ID: f9a1b2c3d4e5
Revises: e6f7a8b9c0d1
Create Date: 2026-04-25 13:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f9a1b2c3d4e5"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("species", sa.Column("audio_url", sa.String(length=500), nullable=True))
    op.add_column("species", sa.Column("audio_title", sa.String(length=255), nullable=True))
    op.add_column("species", sa.Column("audio_source", sa.String(length=255), nullable=True))
    op.add_column("species", sa.Column("audio_license", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("species", "audio_license")
    op.drop_column("species", "audio_source")
    op.drop_column("species", "audio_title")
    op.drop_column("species", "audio_url")
