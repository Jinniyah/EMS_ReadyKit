"""
Add AI identification fields to items table.

Revision ID: 0009_item_ai_fields
Revises: 0008_station_members
Create Date: 2026-05-29

Changes (AI Foundation):
  Alter table: items
    ai_tags            VARCHAR(500) nullable
      Comma-separated keywords an AI classifier might return.
      e.g. "tourniquet,CAT tourniquet,hemostatic"
      Used for fuzzy matching when the AI returns a label.

    alternate_names    VARCHAR(500) nullable
      Other names crews use for this item.
      e.g. "cric kit,surgical airway,bougie"
      Helps the AI match colloquial or regional names.

    reference_image_url  VARCHAR(500) nullable
      URL of a reference photo of this item stored in Azure Blob Storage.
      Used by the AI pipeline to verify a visual match.

    barcode            VARCHAR(100) nullable, unique
      UPC or GS1 barcode for scanner-based identification.
      The AI image pipeline can also attempt to read barcodes from photos.

Design notes:
  - All four columns are nullable — zero impact on existing items or behavior.
  - They sit quietly in the schema until the AI module is built.
  - barcode has a unique index; two items cannot share the same barcode.
  - No application-layer changes are required for existing workflows.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0009_item_ai_fields"
down_revision: Union[str, None] = "0008_station_members"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        op.add_column("items", sa.Column("ai_tags",             sa.String(500), nullable=True))
        op.add_column("items", sa.Column("alternate_names",     sa.String(500), nullable=True))
        op.add_column("items", sa.Column("reference_image_url", sa.String(500), nullable=True))
        op.add_column("items", sa.Column("barcode",             sa.String(100), nullable=True))
        op.create_index("ix_items_barcode", "items", ["barcode"], unique=True)
    else:
        # PostgreSQL — idempotent IF NOT EXISTS guards
        for col, coltype in [
            ("ai_tags",             "VARCHAR(500)"),
            ("alternate_names",     "VARCHAR(500)"),
            ("reference_image_url", "VARCHAR(500)"),
            ("barcode",             "VARCHAR(100)"),
        ]:
            bind.execute(sa.text(
                f"ALTER TABLE items ADD COLUMN IF NOT EXISTS {col} {coltype}"
            ))
        bind.execute(sa.text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_items_barcode
            ON items (barcode) WHERE barcode IS NOT NULL
        """))


def downgrade() -> None:
    op.drop_index("ix_items_barcode", table_name="items")
    op.drop_column("items", "barcode")
    op.drop_column("items", "reference_image_url")
    op.drop_column("items", "alternate_names")
    op.drop_column("items", "ai_tags")
