"""
Add item check types, measurement/functional/date fields on check_line_items,
compartment location descriptor and parent, and JUMP_BAG/EQUIPMENT location types.

Revision ID: 0003_item_check_types_and_equipment
Revises: 0002_compartments_and_line_items
Create Date: 2026-05-15

SQLite note:
  All ALTER TABLE operations on existing tables use Alembic batch mode
  (copy-and-move strategy) because SQLite does not support ALTER TABLE
  ADD COLUMN with constraints, ADD CONSTRAINT, or DROP COLUMN natively.

PostgreSQL note:
  PostgreSQL supports these operations natively and must NOT use batch mode
  because it enforces FK constraints during table drop/recreate. Dialect is
  checked at runtime so the same migration file works for both databases.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_item_check_types_and_equipment"
down_revision: Union[str, None] = "0002_compartments_and_line_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name

    # ── items: add check_type and measurement/recurrence metadata ─────────────
    if dialect == "sqlite":
        with op.batch_alter_table("items", schema=None) as batch_op:
            batch_op.add_column(sa.Column(
                "check_type",
                sa.String(20),
                nullable=False,
                server_default="SUPPLY",
            ))
            batch_op.add_column(sa.Column(
                "measurement_minimum",
                sa.Float,
                nullable=True,
            ))
            batch_op.add_column(sa.Column(
                "measurement_maximum",
                sa.Float,
                nullable=True,
            ))
            batch_op.add_column(sa.Column(
                "recurrence_days",
                sa.Integer,
                nullable=True,
            ))
            batch_op.create_index("ix_items_check_type", ["check_type"])
    else:
        op.add_column("items", sa.Column(
            "check_type", sa.String(20), nullable=False, server_default="SUPPLY",
        ))
        op.add_column("items", sa.Column("measurement_minimum", sa.Float, nullable=True))
        op.add_column("items", sa.Column("measurement_maximum", sa.Float, nullable=True))
        op.add_column("items", sa.Column("recurrence_days", sa.Integer, nullable=True))
        op.create_index("ix_items_check_type", "items", ["check_type"])

    # ── check_line_items: add measurement, functional, and date fields ────────
    if dialect == "sqlite":
        with op.batch_alter_table("check_line_items", schema=None) as batch_op:
            batch_op.add_column(sa.Column("measurement_value", sa.Float, nullable=True))
            batch_op.add_column(sa.Column("functional_pass", sa.Boolean, nullable=True))
            batch_op.add_column(sa.Column("date_value", sa.Date, nullable=True))
    else:
        op.add_column("check_line_items", sa.Column("measurement_value", sa.Float, nullable=True))
        op.add_column("check_line_items", sa.Column("functional_pass", sa.Boolean, nullable=True))
        op.add_column("check_line_items", sa.Column("date_value", sa.Date, nullable=True))

    # ── compartments: add location descriptor, parent, restriction note ───────
    if dialect == "sqlite":
        with op.batch_alter_table("compartments", schema=None) as batch_op:
            batch_op.add_column(sa.Column(
                "location_descriptor", sa.String(150), nullable=True,
            ))
            batch_op.add_column(sa.Column(
                "parent_compartment_id", sa.Integer, nullable=True,
            ))
            batch_op.add_column(sa.Column(
                "restriction_note", sa.String(100), nullable=True,
            ))
            batch_op.create_index(
                "ix_compartments_parent_compartment_id",
                ["parent_compartment_id"],
            )
    else:
        op.add_column("compartments", sa.Column(
            "location_descriptor", sa.String(150), nullable=True,
        ))
        op.add_column("compartments", sa.Column(
            "parent_compartment_id", sa.Integer, nullable=True,
        ))
        op.add_column("compartments", sa.Column(
            "restriction_note", sa.String(100), nullable=True,
        ))
        op.create_index(
            "ix_compartments_parent_compartment_id",
            "compartments",
            ["parent_compartment_id"],
        )

    # ── inventory_locations: JUMP_BAG and EQUIPMENT are VARCHAR values ────────
    # location_type is stored as VARCHAR (native_enum=False).
    # New enum values require no DDL change — accepted automatically.


def downgrade() -> None:
    dialect = op.get_bind().dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("compartments", schema=None) as batch_op:
            batch_op.drop_index("ix_compartments_parent_compartment_id")
            batch_op.drop_column("restriction_note")
            batch_op.drop_column("parent_compartment_id")
            batch_op.drop_column("location_descriptor")

        with op.batch_alter_table("check_line_items", schema=None) as batch_op:
            batch_op.drop_column("date_value")
            batch_op.drop_column("functional_pass")
            batch_op.drop_column("measurement_value")

        with op.batch_alter_table("items", schema=None) as batch_op:
            batch_op.drop_index("ix_items_check_type")
            batch_op.drop_column("recurrence_days")
            batch_op.drop_column("measurement_maximum")
            batch_op.drop_column("measurement_minimum")
            batch_op.drop_column("check_type")
    else:
        op.drop_index("ix_compartments_parent_compartment_id", table_name="compartments")
        op.drop_column("compartments", "restriction_note")
        op.drop_column("compartments", "parent_compartment_id")
        op.drop_column("compartments", "location_descriptor")

        op.drop_column("check_line_items", "date_value")
        op.drop_column("check_line_items", "functional_pass")
        op.drop_column("check_line_items", "measurement_value")

        op.drop_index("ix_items_check_type", table_name="items")
        op.drop_column("items", "recurrence_days")
        op.drop_column("items", "measurement_maximum")
        op.drop_column("items", "measurement_minimum")
        op.drop_column("items", "check_type")
