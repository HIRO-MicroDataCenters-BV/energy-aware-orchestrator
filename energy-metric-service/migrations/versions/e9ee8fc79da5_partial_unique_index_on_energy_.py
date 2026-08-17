"""partial unique index on energy_availability provider_name for demand rows

Revision ID: e9ee8fc79da5
Revises: 6df62fb22abe
Create Date: 2026-08-17 11:57:18.581053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9ee8fc79da5'
down_revision: Union[str, Sequence[str], None] = '6df62fb22abe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEX_NAME = "ix_energy_availability_demand_provider_name"


def upgrade() -> None:
    """One demand row per identifier (provider_name holds '<namespace>/<name>'
    of the EAO CR for demand rows). Lets the write path use a real upsert
    (INSERT ... ON CONFLICT) instead of delete-then-insert, and matches how
    the operator actually produces this data - one current decision per CR,
    not an accumulating history. Scoped to record_type='demand' only, so it
    has no effect on supply rows, which legitimately have many rows sharing
    a provider_name (one per time slot).
    """
    op.create_index(
        _INDEX_NAME,
        "energy_availability",
        ["provider_name"],
        unique=True,
        postgresql_where=sa.text("record_type = 'demand'"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="energy_availability")
