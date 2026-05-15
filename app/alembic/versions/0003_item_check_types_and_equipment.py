"""
Add item check types, measurement/functional/date fields on check_line_items,
compartment location descriptor and parent, and JUMP_BAG/EQUIPMENT location types.

Revision ID: 0003_item_check_types_and_equipment
Revises: 0002_compartments_and_line_items
Create Date: 2026-05-15

## What changed and why

### Items table
Added:
    check_type          — enum: SUPPLY | MEASUREMENT | FUNCTIONAL | DATE_RECORD | DOCUMENT
                          Default: SUPPLY (backward compatible — all existing items are SUPPLY)
    measurement_minimum — float: minimum acceptable reading for MEASUREMENT items
                          e.g. O2 PSI minimum of 500 PSI
    measurement_maximum — float: maximum acceptable reading (optional)
    recurrence_days     — int: max days between events for DATE_RECORD items
                          e.g. AED must be charged every 90 days

Motivation: Real Ambulance 712 inventory forms reveal four fundamentally
different check types that the original SUPPLY-only model cannot handle:
    - O2 tank PSI (on-board, portable, stretcher, jump bag) → MEASUREMENT
    - AED Battery OK, Runs and Starts, Lights & Sirens → FUNCTIONAL
    - AED Date of Last Charge, LUCAS Date of Last Charge → DATE_RECORD
    - PCR forms, Protocol Book, Billing Form → DOCUMENT

### check_line_items table
Added:
    measurement_value  — float: reading recorded for MEASUREMENT items (e.g. PSI = 1800)
    functional_pass    — bool: True/False for FUNCTIONAL items
    date_value         — date: recorded date for DATE_RECORD items

New status values added to LineItemStatus enum (stored as VARCHAR — no ALTER needed):
    LOW     — MEASUREMENT reading below minimum threshold
    FAIL    — FUNCTIONAL check did not pass
    OVERDUE — DATE_RECORD date exceeds recurrence_days

### compartments table
Added:
    location_descriptor    — VARCHAR(150): physical position description
                             e.g. "Exterior, driver side, forward bay"
    parent_compartment_id  — FK → compartments (nullable): supports sub-compartments
                             e.g. "Main Pocket — Flap Left" → parent = "Main Pocket"
    restriction_note       — VARCHAR(100): replaces als_only with flexible text
                             e.g. "ALS crews only", "Approved personnel only"

Note: als_only column is retained for backward compatibility. Will be
deprecated once all API consumers migrate to restriction_note.

### inventory_locations table
Added JUMP_BAG and EQUIPMENT to location_type enum.
Motivation: Ambulance 712 Jump Bag is shared between trucks 710 and 712.
It has its own checklist and compartment structure. Modeling it as a
VEHICLE location tied to one truck is incorrect.
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

    # ── items: add check_type and measurement/recurrence metadata ─────────────
    op.add_column(
        "items",
        sa.Column(
            "check_type",
            sa.String(20),
            nullable=False,
            server_default="SUPPLY",
            comment="SUPPLY | MEASUREMENT | FUNCTIONAL | DATE_RECORD | DOCUMENT",
        ),
    )
    op.add_column(
        "items",
        sa.Column(
            "measurement_minimum",
            sa.Float,
            nullable=True,
            comment="Minimum acceptable reading for MEASUREMENT items (e.g. O2 PSI >= 500)",
        ),
    )
    op.add_column(
        "items",
        sa.Column(
            "measurement_maximum",
            sa.Float,
            nullable=True,
            comment="Maximum acceptable reading for MEASUREMENT items (optional)",
        ),
    )
    op.add_column(
        "items",
        sa.Column(
            "recurrence_days",
            sa.Integer,
            nullable=True,
            comment="Max days between events for DATE_RECORD items (e.g. AED charge every 90 days)",
        ),
    )
    op.create_index("ix_items_check_type", "items", ["check_type"])

    # ── check_line_items: add measurement, functional, and date fields ────────
    op.add_column(
        "check_line_items",
        sa.Column(
            "measurement_value",
            sa.Float,
            nullable=True,
            comment="Numeric reading for MEASUREMENT items (e.g. O2 PSI = 1800.0)",
        ),
    )
    op.add_column(
        "check_line_items",
        sa.Column(
            "functional_pass",
            sa.Boolean,
            nullable=True,
            comment="Pass/fail result for FUNCTIONAL items (True=OK, False=FAIL)",
        ),
    )
    op.add_column(
        "check_line_items",
        sa.Column(
            "date_value",
            sa.Date,
            nullable=True,
            comment="Date recorded for DATE_RECORD items (e.g. AED last charge date)",
        ),
    )
    # Note: LineItemStatus enum is stored as VARCHAR — new values (LOW, FAIL,
    # OVERDUE) do not require an ALTER TYPE in PostgreSQL when native_enum=False.
    # SQLite also handles this transparently.

    # ── compartments: add location descriptor, parent, restriction note ───────
    op.add_column(
        "compartments",
        sa.Column(
            "location_descriptor",
            sa.String(150),
            nullable=True,
            comment="Physical position description shown in UI (e.g. 'Exterior, driver side')",
        ),
    )
    op.add_column(
        "compartments",
        sa.Column(
            "parent_compartment_id",
            sa.Integer,
            sa.ForeignKey("compartments.compartment_id"),
            nullable=True,
            comment="Parent compartment for sub-compartments (e.g. Jump Bag pocket-in-pocket)",
        ),
    )
    op.add_column(
        "compartments",
        sa.Column(
            "restriction_note",
            sa.String(100),
            nullable=True,
            comment="Access restriction shown in UI (e.g. 'ALS crews only')",
        ),
    )
    op.create_index(
        "ix_compartments_parent_compartment_id",
        "compartments",
        ["parent_compartment_id"],
    )

    # ── inventory_locations: add JUMP_BAG and EQUIPMENT to location_type ──────
    # location_type is stored as VARCHAR (native_enum=False) — new values
    # are accepted by the CHECK constraint automatically in SQLite.
    # PostgreSQL with native enums would require ALTER TYPE — not applicable here.


def downgrade() -> None:
    # compartments
    op.drop_index("ix_compartments_parent_compartment_id", table_name="compartments")
    op.drop_column("compartments", "restriction_note")
    op.drop_column("compartments", "parent_compartment_id")
    op.drop_column("compartments", "location_descriptor")

    # check_line_items
    op.drop_column("check_line_items", "date_value")
    op.drop_column("check_line_items", "functional_pass")
    op.drop_column("check_line_items", "measurement_value")

    # items
    op.drop_index("ix_items_check_type", table_name="items")
    op.drop_column("items", "recurrence_days")
    op.drop_column("items", "measurement_maximum")
    op.drop_column("items", "measurement_minimum")
    op.drop_column("items", "check_type")
