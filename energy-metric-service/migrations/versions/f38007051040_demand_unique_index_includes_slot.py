"""demand unique index includes slot for multi-slot forecast reporting

Revision ID: f38007051040
Revises: 4f7cd0a3ac61
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f38007051040'
down_revision: Union[str, Sequence[str], None] = '4f7cd0a3ac61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_OLD_INDEX_NAME = "ix_energy_availability_demand_provider_name"
_NEW_INDEX_NAME = "ix_energy_availability_demand_provider_slot"


def upgrade() -> None:
    """A CR now reports demand for several future slots at once (see
    SimpleSchedulerService.forecast_demand_slots in energy-aware-operator),
    not just its single current decision - so the demand table needs one
    row per (provider_name, slot_start_time, slot_end_time), the same shape
    supply already uses, instead of one row per provider_name alone.
    """
    op.drop_index(_OLD_INDEX_NAME, table_name="energy_availability")
    op.create_index(
        _NEW_INDEX_NAME,
        "energy_availability",
        ["provider_name", "slot_start_time", "slot_end_time"],
        unique=True,
        postgresql_where=sa.text("record_type = 'demand'"),
    )


def downgrade() -> None:
    op.drop_index(_NEW_INDEX_NAME, table_name="energy_availability")
    op.create_index(
        _OLD_INDEX_NAME,
        "energy_availability",
        ["provider_name"],
        unique=True,
        postgresql_where=sa.text("record_type = 'demand'"),
    )
