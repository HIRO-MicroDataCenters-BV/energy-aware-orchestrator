"""partial unique index on energy_availability slot for supply rows

Revision ID: cd56cb4e4ec9
Revises: e9ee8fc79da5
Create Date: 2026-08-18 17:01:55.850223

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd56cb4e4ec9'
down_revision: Union[str, Sequence[str], None] = 'e9ee8fc79da5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEX_NAME = "ix_energy_availability_supply_provider_slot"


def upgrade() -> None:
    """One supply row per (provider_name, slot_start_time, slot_end_time).
    Lets grid polling upsert a slot in place (INSERT ... ON CONFLICT) instead
    of accumulating a duplicate row every time the same slot is re-polled.
    Scoped to record_type='supply' only, so it doesn't interact with the
    existing provider_name-only unique index for demand rows.
    """
    op.create_index(
        _INDEX_NAME,
        "energy_availability",
        ["provider_name", "slot_start_time", "slot_end_time"],
        unique=True,
        postgresql_where=sa.text("record_type = 'supply'"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="energy_availability")
