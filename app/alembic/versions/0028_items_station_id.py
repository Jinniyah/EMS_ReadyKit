"""
Add station_id to items; replace global unique on name with per-station unique.

Revision ID: 0028
Revises: 0027
Create Date: 2026-06-20

Changes:
  - Adds items.station_id (Integer, NOT NULL, FK → stations.station_id)
  - Removes the old global UNIQUE on items.name
  - Adds UniqueConstraint(station_id, name) named uq_items_station_name

DB wiped and reseeded before this runs — no live data to migrate (Jennifer, 2026-06-20).

SQLite path — raw SQL, not Alembic batch mode:
  Migration 0001 created items.name with unique=True (inline UNIQUE in DDL).
  Alembic batch_alter_table recreates the table by reading its CREATE TABLE SQL
  from sqlite_master and carries the inline UNIQUE over on every recreation
  (migrations 0003 and 0017 each batch-altered this table). SQLAlchemy's inspector
  filters out sqlite_autoindex_* names so we can't find and drop the constraint via
  the ORM layer.  Raw SQL gives us full control over the new table schema.

PostgreSQL path — native ALTER TABLE:
  PostgreSQL supports real ALTER TABLE; batch mode is not needed.
  The old inline UNIQUE is auto-named by PostgreSQL as items_name_key.
"""

import sqlalchemy as sa

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        # Raw SQL: create replacement table, copy data, swap.
        # barcode unique index is recreated separately (was a named index from 0009).
        bind.execute(sa.text("""
            CREATE TABLE _items_new (
                item_id              INTEGER  NOT NULL PRIMARY KEY AUTOINCREMENT,
                station_id           INTEGER  NOT NULL REFERENCES stations (station_id),
                name                 VARCHAR(150) NOT NULL,
                category             VARCHAR(20)  NOT NULL,
                controlled_substance BOOLEAN NOT NULL DEFAULT 0,
                unit_of_measure      VARCHAR(30)  NOT NULL,
                active               BOOLEAN NOT NULL DEFAULT 1,
                created_at           DATETIME NOT NULL,
                updated_at           DATETIME NOT NULL,
                check_type           VARCHAR(20) NOT NULL DEFAULT 'SUPPLY',
                measurement_minimum  FLOAT,
                measurement_maximum  FLOAT,
                recurrence_days      INTEGER,
                ai_tags              VARCHAR(500),
                alternate_names      VARCHAR(500),
                reference_image_url  VARCHAR(500),
                barcode              VARCHAR(100),
                station_supply       BOOLEAN NOT NULL DEFAULT 1,
                UNIQUE (station_id, name)
            )
        """))

        bind.execute(sa.text("""
            INSERT INTO _items_new (
                item_id, station_id, name, category, controlled_substance,
                unit_of_measure, active, created_at, updated_at,
                check_type, measurement_minimum, measurement_maximum, recurrence_days,
                ai_tags, alternate_names, reference_image_url, barcode, station_supply
            )
            SELECT
                item_id, 0, name, category, controlled_substance,
                unit_of_measure, active, created_at, updated_at,
                check_type, measurement_minimum, measurement_maximum, recurrence_days,
                ai_tags, alternate_names, reference_image_url, barcode, station_supply
            FROM items
        """))

        op.drop_table("items")
        bind.execute(sa.text("ALTER TABLE _items_new RENAME TO items"))

        # Restore the named barcode unique index (originally created in migration 0009).
        op.create_index("ix_items_barcode", "items", ["barcode"], unique=True)

    else:
        # PostgreSQL: native ALTER TABLE — no batch mode needed.
        # No data exists so NOT NULL column can be added without a default,
        # but we use server_default="0" defensively and drop it immediately.
        op.add_column(
            "items",
            sa.Column(
                "station_id",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )
        op.execute(sa.text("ALTER TABLE items ALTER COLUMN station_id DROP DEFAULT"))

        op.create_foreign_key(
            "fk_items_station_id", "items", "stations", ["station_id"], ["station_id"]
        )

        # Drop the old global unique on name.
        # PostgreSQL auto-names an inline UNIQUE as <table>_<column>_key.
        op.execute(
            sa.text("ALTER TABLE items DROP CONSTRAINT IF EXISTS items_name_key")
        )
        # Also try the SQLAlchemy auto-name in case a naming convention was active.
        op.execute(
            sa.text("ALTER TABLE items DROP CONSTRAINT IF EXISTS uq_items_name")
        )

        op.create_unique_constraint(
            "uq_items_station_name", "items", ["station_id", "name"]
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        op.drop_index("ix_items_barcode", table_name="items")

        bind.execute(sa.text("""
            CREATE TABLE _items_old (
                item_id              INTEGER  NOT NULL PRIMARY KEY AUTOINCREMENT,
                name                 VARCHAR(150) NOT NULL UNIQUE,
                category             VARCHAR(20)  NOT NULL,
                controlled_substance BOOLEAN NOT NULL DEFAULT 0,
                unit_of_measure      VARCHAR(30)  NOT NULL,
                active               BOOLEAN NOT NULL DEFAULT 1,
                created_at           DATETIME NOT NULL,
                updated_at           DATETIME NOT NULL,
                check_type           VARCHAR(20) NOT NULL DEFAULT 'SUPPLY',
                measurement_minimum  FLOAT,
                measurement_maximum  FLOAT,
                recurrence_days      INTEGER,
                ai_tags              VARCHAR(500),
                alternate_names      VARCHAR(500),
                reference_image_url  VARCHAR(500),
                barcode              VARCHAR(100),
                station_supply       BOOLEAN NOT NULL DEFAULT 1
            )
        """))

        bind.execute(sa.text("""
            INSERT INTO _items_old (
                item_id, name, category, controlled_substance,
                unit_of_measure, active, created_at, updated_at,
                check_type, measurement_minimum, measurement_maximum, recurrence_days,
                ai_tags, alternate_names, reference_image_url, barcode, station_supply
            )
            SELECT
                item_id, name, category, controlled_substance,
                unit_of_measure, active, created_at, updated_at,
                check_type, measurement_minimum, measurement_maximum, recurrence_days,
                ai_tags, alternate_names, reference_image_url, barcode, station_supply
            FROM items
        """))

        op.drop_table("items")
        bind.execute(sa.text("ALTER TABLE _items_old RENAME TO items"))
        op.create_index("ix_items_barcode", "items", ["barcode"], unique=True)

    else:
        op.drop_constraint("uq_items_station_name", "items", type_="unique")
        op.drop_constraint("fk_items_station_id", "items", type_="foreignkey")
        op.drop_column("items", "station_id")
        op.create_unique_constraint("items_name_key", "items", ["name"])
