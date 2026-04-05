from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base
from app.models import (  # noqa: F401 — ensure models are imported
    User,
    Species,
    Observation,
    ObsMedia,
    SiteZone,
    Notification,
    DecisionTreeNode,
)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Only track our tables, ignore PostGIS/tiger system tables
INCLUDE_TABLES = {t.name for t in Base.metadata.tables.values()}


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in INCLUDE_TABLES
    if type_ == "index" and hasattr(object, "table"):
        return object.table.name in INCLUDE_TABLES
    return True


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, include_object=include_object)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
