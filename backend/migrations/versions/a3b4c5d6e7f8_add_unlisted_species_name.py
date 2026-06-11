"""Add observations.unlisted_species_name

Revision ID: a3b4c5d6e7f8
Revises: 0f1e2d3c4b5a
Create Date: 2026-06-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "0f1e2d3c4b5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "observations",
        sa.Column("unlisted_species_name", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("observations", "unlisted_species_name")
