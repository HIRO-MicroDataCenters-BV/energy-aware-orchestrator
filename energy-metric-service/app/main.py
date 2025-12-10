"""
FastAPI application entry point.
"""

import asyncio
import logging
import os
import threading
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

# Kopf operator thread
operator_thread = None
operator_stop_flag = threading.Event()


def run_kopf_operator(stop_flag: threading.Event):
    """
    Run the Kopf operator in a separate thread.
    
    This function imports and runs the operator module which registers
    handlers for EnergyAwareOrchestration CRD events.
    
    Note: Kopf manages its own event loop internally, so we don't create one here.
    """
    import kopf
    
    # Import the operator module to register handlers
    from app.crd import operator  # noqa: F401
    
    logging.info("Starting Kopf operator for EnergyAwareOrchestration CRD...")
    
    try:
        # Run kopf operator - it manages its own event loop
        kopf.run(
            clusterwide=True,
            standalone=True,
            stop_flag=stop_flag,
        )
    except Exception as e:
        logging.error(f"Kopf operator error: {e}")
    finally:
        logging.info("Kopf operator stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global operator_thread
    
    # Initialize services on startup
    if metrics_scheduler:
        metrics_scheduler.start()

    if deployment_scheduler:
        deployment_scheduler.start()
        logging.info("Deployment scheduler started - will check pending deployments every 1 minute")

    # Start Kopf operator in background thread
    if os.environ.get("ENABLE_OPERATOR", "true").lower() == "true":
        operator_thread = threading.Thread(
            target=run_kopf_operator,
            args=(operator_stop_flag,),
            daemon=True,
            name="kopf-operator"
        )
        operator_thread.start()
        logging.info("Kopf operator thread started")

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
    
    # Stop Kopf operator
    if operator_thread and operator_thread.is_alive():
        logging.info("Stopping Kopf operator...")
        operator_stop_flag.set()
        operator_thread.join(timeout=5)
        logging.info("Kopf operator thread stopped")


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
