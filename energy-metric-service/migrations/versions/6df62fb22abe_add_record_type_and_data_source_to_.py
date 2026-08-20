"""add record_type and data_source to energy_availability

Revision ID: 6df62fb22abe
Revises: 512771aab2f7
Create Date: 2026-08-14 16:08:20.943108

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6df62fb22abe'
down_revision: Union[str, Sequence[str], None] = '512771aab2f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Distinguish supply vs demand, real vs predicted rows in
    energy_availability. server_default backfills every existing row as
    supply/real, matching what the table has only ever held until now.

    Unrelated pre-existing model/DB drift (again surfaced by autogenerate,
    same as in the baseline migration) is left un-actioned here.
    """
    op.add_column('energy_availability', sa.Column('record_type', sa.String(length=10), server_default='supply', nullable=False))
    op.add_column('energy_availability', sa.Column('data_source', sa.String(length=10), server_default='real', nullable=False))


def downgrade() -> None:
    op.drop_column('energy_availability', 'data_source')
    op.drop_column('energy_availability', 'record_type')
