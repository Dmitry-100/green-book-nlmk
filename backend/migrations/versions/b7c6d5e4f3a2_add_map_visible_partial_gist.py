"""add partial gist index for map visible observations

Revision ID: b7c6d5e4f3a2
Revises: a9b8c7d6e5f4
Create Date: 2026-04-11 04:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b7c6d5e4f3a2"
down_revision: Union[str, None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_observations_map_visible_location_gist",
        "observations",
        ["location_point"],
        unique=False,
        postgresql_using="gist",
        postgresql_where=sa.text(
            "status = 'confirmed' AND sensitive_level IN ('open', 'blurred')"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_observations_map_visible_location_gist",
        table_name="observations",
        postgresql_using="gist",
    )
