"""add EXPIRY_DATE check type for AED pads

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-10

ItemCheckType is stored as VARCHAR (native_enum=False), so no schema change
is required — only existing rows are updated.

AED Pads Adult and AED Pads Pediatric previously used DATE_RECORD with
recurrence_days=730 (OVERDUE after 2 years). They now use EXPIRY_DATE:
the date_value IS the printed expiry date on the package. Status is EXPIRED
when today > date_value.
"""

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE items SET check_type = 'EXPIRY_DATE', recurrence_days = NULL "
        "WHERE name IN ('AED Pads Adult', 'AED Pads Pediatric')"
    )


def downgrade():
    op.execute(
        "UPDATE items SET check_type = 'DATE_RECORD', recurrence_days = 730 "
        "WHERE name IN ('AED Pads Adult', 'AED Pads Pediatric')"
    )
