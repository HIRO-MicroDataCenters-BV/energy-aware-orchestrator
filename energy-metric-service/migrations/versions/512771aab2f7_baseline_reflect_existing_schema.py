"""baseline - reflect existing schema

Revision ID: 512771aab2f7
Revises: 
Create Date: 2026-08-14 16:01:43.158004

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '512771aab2f7'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Frozen DDL, copied verbatim from charts/postgres/db-init.sql (wrapped in
# IF NOT EXISTS for idempotency) rather than generated from the current
# SQLAlchemy models. This has to be a frozen snapshot of the schema as it
# stood *before* this revision, not a live reflection of Base.metadata -
# pulling from the live models broke on a genuinely empty database, because
# by the time this baseline ran, the models already had the record_type/
# data_source columns that the next migration (6df62fb22abe) also tries to
# add, causing a "column already exists" error. Every future migration
# should describe its own diff explicitly, the same way this one does, not
# reach for the models' current state.
_NODE_METRICS_DDL = """
CREATE TABLE IF NOT EXISTS node_metrics (
    timestamp                  BIGINT NOT NULL,
    node_name                  VARCHAR(255),
    metric_source               VARCHAR(255),
    cpu_utilization_percent    DOUBLE PRECISION,
    total_cpu_assigned         INTEGER,
    machine_cpu_cores          INTEGER,
    memory_utilization_percent DOUBLE PRECISION,
    memory_utilization_bytes   DOUBLE PRECISION,
    memory_assigned_bytes      DOUBLE PRECISION,
    machine_memory_total_bytes DOUBLE PRECISION,
    cpu_core_watts             DOUBLE PRECISION,
    cpu_package_watts          DOUBLE PRECISION,
    memory_power_watts         DOUBLE PRECISION,
    platform_watts             DOUBLE PRECISION,
    energy_watts               DOUBLE PRECISION,
    created_at                 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (timestamp, node_name)
)
"""

_ENERGY_AVAILABILITY_DDL = """
CREATE TABLE IF NOT EXISTS energy_availability (
    id                          SERIAL PRIMARY KEY,
    provider_name               VARCHAR(100)             NOT NULL,
    location                    VARCHAR(255),
    energy_source_type          VARCHAR(50),
    slot_start_time             TIMESTAMP WITH TIME ZONE NOT NULL,
    slot_end_time               TIMESTAMP WITH TIME ZONE NOT NULL,
    available_watts             DECIMAL(15, 4)           NOT NULL,
    guaranteed_minimum_watts    DECIMAL(15, 4),
    potential_maximum_watts     DECIMAL(15, 4),
    confidence_percentage       DECIMAL(5, 2),
    weather_dependency          BOOLEAN                  DEFAULT false,
    forecast_date                DATE                     NOT NULL,
    is_active                   BOOLEAN                  DEFAULT true,
    created_at                  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
"""

_APP_DEFINITIONS_DDL = """
CREATE TABLE IF NOT EXISTS app_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    namespace VARCHAR(255) NOT NULL DEFAULT 'default',
    workload_type VARCHAR(20) NOT NULL DEFAULT 'Optional',
    deployment_type VARCHAR(20) NOT NULL DEFAULT 'kubernetes',
    estimated_energy_required DOUBLE PRECISION,
    description TEXT,
    manifest TEXT NOT NULL,
    CONSTRAINT chk_app_workload_type CHECK (workload_type IN ('Critical', 'Preferred', 'Optional')),
    CONSTRAINT chk_deployment_type CHECK (deployment_type IN ('kubernetes', 'helm', 'custom'))
)
"""

_APP_DEPLOYMENTS_REQUEST_DDL = """
CREATE TABLE IF NOT EXISTS app_deployments_request (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_definition_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    estimated_energy_watts DECIMAL(10, 4),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deployed_at TIMESTAMP WITH TIME ZONE,
    schedule_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_deployment_app FOREIGN KEY (app_definition_id)
        REFERENCES app_definitions(id) ON DELETE CASCADE
)
"""

# No db-init.sql equivalent exists for this one - the ContainerPowerMetrics
# model has never had a backing table anywhere, so its own column
# definitions are the only source of truth there is.
_CONTAINER_POWER_METRICS_DDL = """
CREATE TABLE IF NOT EXISTS container_power_metrics (
    "timestamp" TIMESTAMP NOT NULL,
    container_name VARCHAR(255) NOT NULL,
    pod_name VARCHAR(255) NOT NULL,
    namespace VARCHAR(255),
    node_name VARCHAR(255),
    metric_source VARCHAR(255),
    cpu_core_watts DOUBLE PRECISION,
    cpu_package_watts DOUBLE PRECISION,
    memory_power_watts DOUBLE PRECISION,
    platform_watts DOUBLE PRECISION,
    other_watts DOUBLE PRECISION,
    cpu_utilization_percent DOUBLE PRECISION,
    memory_utilization_percent DOUBLE PRECISION,
    memory_usage_bytes BIGINT,
    network_io_rate_bytes_per_sec DOUBLE PRECISION,
    disk_io_rate_bytes_per_sec DOUBLE PRECISION,
    PRIMARY KEY (timestamp, container_name, pod_name)
)
"""


def upgrade() -> None:
    """Baseline: create any of these tables that doesn't exist yet.

    Idempotent (IF NOT EXISTS) so this works the same way on both an
    already-provisioned database (tables created by
    charts/postgres/db-init.sql, which is still how this repo bootstraps
    Postgres today) and a genuinely empty one.
    """
    op.execute(_NODE_METRICS_DDL)
    op.execute(_ENERGY_AVAILABILITY_DDL)
    op.execute(_APP_DEFINITIONS_DDL)
    op.execute(_APP_DEPLOYMENTS_REQUEST_DDL)
    op.execute(_CONTAINER_POWER_METRICS_DDL)


def downgrade() -> None:
    """No-op - this baseline never drops a table that might have existed
    before Alembic started tracking this database."""
    pass
