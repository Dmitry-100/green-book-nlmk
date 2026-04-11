"""add performance indexes

Revision ID: c2b5f4a88d31
Revises: 6a815ba011de
Create Date: 2026-04-11 02:15:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2b5f4a88d31"
down_revision: Union[str, None] = "6a815ba011de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_observations_status_created_at",
        "observations",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_observations_author_status_created_at",
        "observations",
        ["author_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_observations_group_status_created_at",
        "observations",
        ["group", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_user_is_read_created_at",
        "notifications",
        ["user_id", "is_read", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_observation_comments_observation_created_at",
        "observation_comments",
        ["observation_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_points_created_at_user_id",
        "user_points",
        ["created_at", "user_id"],
        unique=False,
    )
    op.create_index(
        "ix_obs_media_s3_key",
        "obs_media",
        ["s3_key"],
        unique=False,
    )
    op.create_index(
        "ix_obs_media_thumbnail_key",
        "obs_media",
        ["thumbnail_key"],
        unique=False,
    )

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_species_name_ru_trgm "
        "ON species USING gin (lower(name_ru) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_species_name_latin_trgm "
        "ON species USING gin (lower(name_latin) gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_species_name_latin_trgm")
    op.execute("DROP INDEX IF EXISTS ix_species_name_ru_trgm")

    op.drop_index("ix_obs_media_thumbnail_key", table_name="obs_media")
    op.drop_index("ix_obs_media_s3_key", table_name="obs_media")
    op.drop_index("ix_user_points_created_at_user_id", table_name="user_points")
    op.drop_index(
        "ix_observation_comments_observation_created_at",
        table_name="observation_comments",
    )
    op.drop_index(
        "ix_notifications_user_is_read_created_at",
        table_name="notifications",
    )
    op.drop_index(
        "ix_observations_group_status_created_at",
        table_name="observations",
    )
    op.drop_index(
        "ix_observations_author_status_created_at",
        table_name="observations",
    )
    op.drop_index(
        "ix_observations_status_created_at",
        table_name="observations",
    )
