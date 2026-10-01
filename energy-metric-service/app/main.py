"""
FastAPI application entry point.
"""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import metrics_api
from app.api import energy_forecast_api
from app.api import kubernetes_api
from app.api import app_deployment_api
from app.api import app_definition_api
from app.api import energy_availability_api
from app.scheduler.metric_collector_scheduler import MetricCollectorScheduler
from app.scheduler.deployment_scheduler import DeploymentScheduler
from app.scheduler.grid_polling_scheduler import GridPollingScheduler
from app.services.grid_clients.http_client import HttpGridClient
from app.services.grid_clients.modbus_client import ModbusGridClient
from app.scheduler.forecasting_scheduler import ForecastingScheduler
from app.scheduler.metrics_retention_scheduler import MetricsRetentionScheduler
from app.services.energy_forecasting_service import EnergyForecastingService

from app.utils.exception_handlers import init_exception_handlers

# Configured before any module-level logging calls below (e.g. the grid
# polling dormant-state notice) - logging.info() before basicConfig() runs
# is silently dropped by Python's default "handler of last resort", which
# only emits WARNING and above.
logging.basicConfig(level=logging.DEBUG)

metrics_scheduler = None
if os.environ.get("ENABLE_METRICS_SCHEDULER", "false").lower() == "true":
    metrics_scheduler = MetricCollectorScheduler(interval_seconds=30)

deployment_scheduler = None
if os.environ.get("ENABLE_DEPLOYMENT_SCHEDULER", "true").lower() == "true":
    deployment_scheduler = DeploymentScheduler(interval_seconds=30)  # Runs every 1 minute

# Grid capacity polling. Off unless the toggle is on and at least one source
# is configured - without a real source there is nothing to poll, so it
# stays dormant rather than logging a connection error every interval. An
# HTTP source and a Modbus PDU source can both be configured at once; each
# is polled independently every cycle.
grid_polling_scheduler = None
if os.environ.get("ENABLE_GRID_POLLING", "true").lower() == "true":
    _grid_interval = int(os.environ.get("GRID_POLL_INTERVAL_SECONDS", "300"))
    _grid_clients = []

    _grid_api_url = os.environ.get("GRID_API_URL")
    if _grid_api_url:
        _grid_clients.append(HttpGridClient(api_url=_grid_api_url))

    _grid_modbus_host = os.environ.get("GRID_MODBUS_HOST")
    if _grid_modbus_host:
        _unit_ids = [
            int(u) for u in os.environ.get("GRID_MODBUS_UNIT_IDS", "1").split(",") if u.strip()
        ]
        _rated_capacity = os.environ.get("GRID_MODBUS_RATED_CAPACITY_WATTS")
        _grid_clients.append(ModbusGridClient(
            host=_grid_modbus_host,
            port=int(os.environ.get("GRID_MODBUS_PORT", "502")),
            unit_ids=_unit_ids,
            mode=os.environ.get("GRID_MODBUS_MODE", "reading"),
            rated_capacity_watts=float(_rated_capacity) if _rated_capacity else None,
            poll_interval_seconds=_grid_interval,
        ))

    if _grid_clients:
        grid_polling_scheduler = GridPollingScheduler(
            clients=_grid_clients,
            interval_seconds=_grid_interval,
        )
    else:
        logging.info("Grid polling enabled but no source is configured (GRID_API_URL / GRID_MODBUS_HOST) - poller not started")

# Supply forecasting. Runs entirely in-process (no external service) - a
# cold start with zero real supply history is a harmless no-op cycle, so
# this defaults on rather than needing a URL like grid polling does.
forecasting_scheduler = None
if os.environ.get("ENABLE_FORECASTING", "true").lower() == "true":
    forecasting_scheduler = ForecastingScheduler(
        interval_seconds=int(os.environ.get("FORECASTING_INTERVAL_SECONDS", "1800")),
    )

# Deletes old rows from node_metrics/container_power_metrics - both grow
# unbounded otherwise, a fresh row every metrics-collection cycle with
# nothing to ever remove one. Defaults on since it's a safety/hygiene
# concern, not an optional feature.
metrics_retention_scheduler = None
if os.environ.get("ENABLE_METRICS_RETENTION", "true").lower() == "true":
    metrics_retention_scheduler = MetricsRetentionScheduler(
        retention_days=int(os.environ.get("METRICS_RETENTION_DAYS", "30")),
        interval_seconds=int(os.environ.get("METRICS_RETENTION_INTERVAL_SECONDS", "3600")),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize services on startup
    if metrics_scheduler:
        metrics_scheduler.start()

    if deployment_scheduler:
        deployment_scheduler.start()
        logging.info("Deployment scheduler started - will check pending deployments every 1 minute")

    if grid_polling_scheduler:
        grid_polling_scheduler.start()
        logging.info("Grid polling scheduler started")

    if forecasting_scheduler:
        forecasting_scheduler.start()
        logging.info("Forecasting scheduler started")

    if metrics_retention_scheduler:
        metrics_retention_scheduler.start()
        logging.info("Metrics retention scheduler started")

    # Singleton consumption-prediction model (CPU/memory -> watts), used as
    # the fallback tier in demand resolution when direct Kepler measurement
    # isn't available. Loading the ~600KB model file blocks briefly, but
    # only once at startup before the app serves any traffic.
    try:
        EnergyForecastingService.get_instance()
        logging.info("Energy forecasting service initialized")
    except Exception as e:
        logging.warning(f"Failed to initialize energy forecasting service: {e}")

    yield

    # Cleanup on shutdown
    if metrics_scheduler:
        metrics_scheduler.stop()

    if deployment_scheduler:
        deployment_scheduler.stop()
        logging.info("Deployment scheduler stopped")

    if grid_polling_scheduler:
        grid_polling_scheduler.stop()
        await grid_polling_scheduler.close_clients()
        logging.info("Grid polling scheduler stopped")

    if forecasting_scheduler:
        forecasting_scheduler.stop()
        logging.info("Forecasting scheduler stopped")

    if metrics_retention_scheduler:
        metrics_retention_scheduler.stop()
        logging.info("Metrics retention scheduler stopped")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics_api.router)
app.include_router(energy_forecast_api.router)
app.include_router(kubernetes_api.router)
app.include_router(app_deployment_api.router)
app.include_router(app_definition_api.router)
app.include_router(energy_availability_api.router)

init_exception_handlers(app)


if __name__ == '__main__':
    uvicorn.run(app, port=8086, host='0.0.0.0')
