"""supply unique index includes data_source for real vs predicted coexistence

Revision ID: 4f7cd0a3ac61
Revises: cd56cb4e4ec9
Create Date: 2026-08-19 16:45:11.747951

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f7cd0a3ac61'
down_revision: Union[str, Sequence[str], None] = 'cd56cb4e4ec9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_OLD_INDEX_NAME = "ix_energy_availability_supply_provider_slot"
_NEW_INDEX_NAME = "ix_energy_availability_supply_provider_slot_source"


def upgrade() -> None:
    """Real and predicted supply data must coexist as independent rows for
    the same slot - real polling should never overwrite a prediction, and a
    prediction refresh should never overwrite real data. The previous index
    (provider_name, slot_start_time, slot_end_time) treated real and
    predicted as the same row, forcing them to collide. Adding data_source
    to the key gives each its own row, each independently upsertable.
    """
    op.drop_index(_OLD_INDEX_NAME, table_name="energy_availability")
    op.create_index(
        _NEW_INDEX_NAME,
        "energy_availability",
        ["provider_name", "slot_start_time", "slot_end_time", "data_source"],
        unique=True,
        postgresql_where=sa.text("record_type = 'supply'"),
    )


def downgrade() -> None:
    op.drop_index(_NEW_INDEX_NAME, table_name="energy_availability")
    op.create_index(
        _OLD_INDEX_NAME,
        "energy_availability",
        ["provider_name", "slot_start_time", "slot_end_time"],
        unique=True,
        postgresql_where=sa.text("record_type = 'supply'"),
    )
