"""add observed_at and species ordering indexes

Revision ID: f1e2d3c4b5a6
Revises: c2b5f4a88d31
Create Date: 2026-04-11 03:25:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1e2d3c4b5a6"
down_revision: Union[str, None] = "c2b5f4a88d31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_observations_status_observed_at",
        "observations",
        ["status", "observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_observations_group_status_observed_at",
        "observations",
        ["group", "status", "observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_observations_species_status_observed_at",
        "observations",
        ["species_id", "status", "observed_at"],
        unique=False,
    )
    op.create_index(
        "ix_species_updated_at_id",
        "species",
        ["updated_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_species_updated_at_id", table_name="species")
    op.drop_index(
        "ix_observations_species_status_observed_at",
        table_name="observations",
    )
    op.drop_index(
        "ix_observations_group_status_observed_at",
        table_name="observations",
    )
    op.drop_index(
        "ix_observations_status_observed_at",
        table_name="observations",
    )
