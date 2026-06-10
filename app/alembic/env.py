"""
alembic/env.py
Alembic migration environment.
Reads the database URL from the application config (not alembic.ini)
so that secrets are never stored in version-controlled config files.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

import ems_readykit.models  # noqa: F401 — registers all ORM models with Base.metadata
from alembic import context

# ── Import application config and all models ──────────────────────────────────
# Models must be imported before Base.metadata is passed to Alembic,
# otherwise the autogenerate will produce empty migrations.
from ems_readykit.core.config import get_settings, resolve_database_url
from ems_readykit.core.database import Base

# ── Alembic Config object (provides .ini file values) ─────────────────────────
config = context.config

# Apply Python logging config from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resolve the database URL from application settings — never from alembic.ini.
# This is the single source of truth for both offline and online runners so
# the same code path is used regardless of how alembic is invoked.
settings = get_settings()
db_url = resolve_database_url(settings)

target_metadata = Base.metadata


# ── Offline migration (generates SQL without connecting) ───────────────────────
def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online migration (connects to the database) ────────────────────────────────
def run_migrations_online() -> None:
    # Build the engine directly from the resolved URL rather than delegating
    # to engine_from_config, which reads sqlalchemy.url from alembic.ini.
    # alembic.ini intentionally leaves that key blank (secrets stay out of VCS),
    # so engine_from_config would silently use an empty string without this fix.
    connectable = create_engine(db_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
