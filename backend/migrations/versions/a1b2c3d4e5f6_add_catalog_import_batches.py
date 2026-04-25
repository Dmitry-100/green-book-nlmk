"""add catalog import batches

Revision ID: a1b2c3d4e5f6
Revises: f9a1b2c3d4e5
Create Date: 2026-04-25 18:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f9a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE catalogimportbatchstatus AS ENUM ('applied', 'rolled_back');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        """
    )
    catalog_import_batch_status = postgresql.ENUM(
        "applied",
        "rolled_back",
        name="catalogimportbatchstatus",
        create_type=False,
    )

    op.create_table(
        "catalog_import_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("status", catalog_import_batch_status, nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("rolled_back_by_user_id", sa.Integer(), nullable=True),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("changed_rows", sa.Integer(), nullable=False),
        sa.Column("unchanged_rows", sa.Integer(), nullable=False),
        sa.Column("error_rows", sa.Integer(), nullable=False),
        sa.Column("applied_rows", sa.Integer(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("rolled_back_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["rolled_back_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_catalog_import_batches_actor_user_id"),
        "catalog_import_batches",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_catalog_import_batches_created_at"),
        "catalog_import_batches",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_catalog_import_batches_status"),
        "catalog_import_batches",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_catalog_import_batches_status_created_at",
        "catalog_import_batches",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_catalog_import_batches_status_created_at",
        table_name="catalog_import_batches",
    )
    op.drop_index(
        op.f("ix_catalog_import_batches_status"),
        table_name="catalog_import_batches",
    )
    op.drop_index(
        op.f("ix_catalog_import_batches_created_at"),
        table_name="catalog_import_batches",
    )
    op.drop_index(
        op.f("ix_catalog_import_batches_actor_user_id"),
        table_name="catalog_import_batches",
    )
    op.drop_table("catalog_import_batches")
    sa.Enum(name="catalogimportbatchstatus").drop(op.get_bind(), checkfirst=True)
