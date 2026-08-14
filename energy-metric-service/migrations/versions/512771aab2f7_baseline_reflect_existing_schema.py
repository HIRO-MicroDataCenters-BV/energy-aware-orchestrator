"""baseline - reflect existing schema

Revision ID: 512771aab2f7
Revises: 
Create Date: 2026-08-14 16:01:43.158004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.database import Base
from app import models  # noqa: F401 - registers every model on Base.metadata

# revision identifiers, used by Alembic.
revision: str = '512771aab2f7'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Baseline: create any modeled table that doesn't exist yet.

    Idempotent by design so this works the same way on both an
    already-provisioned database (tables created by
    charts/postgres/db-init.sql, which is still how this repo bootstraps
    Postgres today) and a genuinely empty one - each table is only created
    if it's missing, so nothing that already exists is ever touched here.

    Autogenerate against the live dev DB also surfaced pre-existing drift
    between these models and db-init.sql's actual DDL for tables that DO
    already exist, unrelated to this migration:
      - app_definitions: constraint/index names differ from the model
        (app_definitions_name_key, chk_app_workload_type, chk_deployment_type)
      - app_deployments_request: estimated_energy_watts is NUMERIC(10,4) in
        the DB vs Float() in the model; created_at/updated_at/deployed_at/
        schedule_at are timezone-aware in the DB vs naive DateTime() in the
        model; fk_deployment_app has ON DELETE CASCADE in the DB, not
        reflected in the model
      - node_metrics.created_at is timezone-aware in the DB vs naive in the
        model
    That drift is intentionally left un-actioned here - reconciling it is a
    separate task. energy_availability itself matched cleanly.
    """
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            table.create(bind=bind)


def downgrade() -> None:
    """No-op - this baseline never drops a table that might have existed
    before Alembic started tracking this database."""
    pass
