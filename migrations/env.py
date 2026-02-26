import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add src to path for model imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from whaleback.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from environment if available
db_url = os.environ.get("WB_DATABASE_URL")
if not db_url:
    # Build URL from individual WB_DB_* env vars (Docker compose sets these)
    host = os.environ.get("WB_DB_HOST")
    if host:
        port = os.environ.get("WB_DB_PORT", "5432")
        name = os.environ.get("WB_DB_NAME", "whaleback")
        user = os.environ.get("WB_DB_USER", "whaleback")
        password = os.environ.get("WB_DB_PASSWORD", "")
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
