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

# Grid capacity polling. Off unless both the toggle is on and a URL is set -
# without a real grid endpoint there is nothing to poll, so it stays dormant
# rather than logging a connection error every interval.
grid_polling_scheduler = None
if os.environ.get("ENABLE_GRID_POLLING", "true").lower() == "true":
    _grid_api_url = os.environ.get("GRID_API_URL")
    if _grid_api_url:
        grid_polling_scheduler = GridPollingScheduler(
            api_url=_grid_api_url,
            interval_seconds=int(os.environ.get("GRID_POLL_INTERVAL_SECONDS", "300")),
        )
    else:
        logging.info("Grid polling enabled but GRID_API_URL is not set - poller not started")

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
        await grid_polling_scheduler.grid_client.close()
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
