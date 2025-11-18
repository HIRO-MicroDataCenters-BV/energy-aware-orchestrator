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
from app.scheduler.metric_collector_scheduler import MetricCollectorScheduler
from app.scheduler.deployment_scheduler import DeploymentScheduler
from app.services.energy_forecasting_service import EnergyForecastingService

from app.utils.exception_handlers import init_exception_handlers

metrics_scheduler = None
if os.environ.get("ENABLE_METRICS_SCHEDULER", "false").lower() == "true":
    metrics_scheduler = MetricCollectorScheduler(interval_seconds=30)

deployment_scheduler = None
if os.environ.get("ENABLE_DEPLOYMENT_SCHEDULER", "true").lower() == "true":
    deployment_scheduler = DeploymentScheduler(interval_seconds=30)  # Runs every 1 minute


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize services on startup
    if metrics_scheduler:
        metrics_scheduler.start()

    if deployment_scheduler:
        deployment_scheduler.start()
        logging.info("Deployment scheduler started - will check pending deployments every 1 minute")

    # Initialize singleton forecasting service
    # Temporarily disable to isolate async issues
    try:
        # EnergyForecastingService.get_instance()
        logging.info("Energy forecasting service initialization skipped temporarily")
    except Exception as e:
        logging.warning(f"Failed to initialize energy forecasting service: {e}")

    yield

    # Cleanup on shutdown
    if metrics_scheduler:
        metrics_scheduler.stop()

    if deployment_scheduler:
        deployment_scheduler.stop()
        logging.info("Deployment scheduler stopped")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.DEBUG)

app.include_router(metrics_api.router)
app.include_router(energy_forecast_api.router)
app.include_router(kubernetes_api.router)
app.include_router(app_deployment_api.router)
app.include_router(app_definition_api.router)

init_exception_handlers(app)


if __name__ == '__main__':
    uvicorn.run(app, port=8086, host='0.0.0.0')
