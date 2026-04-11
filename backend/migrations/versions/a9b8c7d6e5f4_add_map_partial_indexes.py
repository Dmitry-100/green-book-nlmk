"""add map partial indexes for visible observations

Revision ID: a9b8c7d6e5f4
Revises: f1e2d3c4b5a6
Create Date: 2026-04-11 04:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, None] = "f1e2d3c4b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_observations_map_visible_observed_at",
        "observations",
        ["observed_at"],
        unique=False,
        postgresql_where=sa.text(
            "status = 'confirmed' AND sensitive_level IN ('open', 'blurred')"
        ),
    )
    op.create_index(
        "ix_observations_map_visible_group_observed_at",
        "observations",
        ["group", "observed_at"],
        unique=False,
        postgresql_where=sa.text(
            "status = 'confirmed' AND sensitive_level IN ('open', 'blurred')"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_observations_map_visible_group_observed_at",
        table_name="observations",
    )
    op.drop_index(
        "ix_observations_map_visible_observed_at",
        table_name="observations",
    )
