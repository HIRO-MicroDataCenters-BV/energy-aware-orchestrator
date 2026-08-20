import asyncio
from app.servicesv2.prometheus_metrics_service import PrometheusMetricsService
from app.servicesv2.prometheus_container_metrics_service import PrometheusContainerMetricsService
import logging


class MetricCollectorScheduler:
    def __init__(self, interval_seconds: int = 10):
        self.interval_seconds = interval_seconds
        self.prometheus_service = PrometheusMetricsService()
        self.container_metrics_service = PrometheusContainerMetricsService()
        self._task = None
        self._running = False

    async def _run(self):
        self._running = True
        logging.info(f"MetricCollectorScheduler started, interval: {self.interval_seconds} seconds")
        while self._running:
            try:
                logging.info("MetricCollectorScheduler: Starting Prometheus metrics collection cycle...")

                # Collect node-level metrics (node_metrics table)
                prometheus_count = await self.prometheus_service.collect_and_store_metrics()
                if isinstance(prometheus_count, Exception):
                    logging.error(f"Failed to collect Prometheus metrics: {prometheus_count}")
                    prometheus_count = 0
                logging.info(f"MetricCollectorScheduler: Stored {prometheus_count} node metrics with energy data from Prometheus")
            except Exception as e:
                logging.exception(f"Error in MetricCollectorScheduler (node metrics): {e}")

            try:
                # Collect per-container metrics (container_power_metrics table) -
                # isolated in its own try/except so a failure here never blocks
                # node-level collection above, or vice versa.
                container_count = await self.container_metrics_service.collect_and_store_metrics()
                logging.info(f"MetricCollectorScheduler: Stored {container_count} container metrics with energy/utilization data from Prometheus")
            except Exception as e:
                logging.exception(f"Error in MetricCollectorScheduler (container metrics): {e}")

            await asyncio.sleep(self.interval_seconds)

    def start(self):
        if not self._task:
            logging.info("MetricCollectorScheduler: Starting background task.")
            self._task = asyncio.create_task(self._run())

    def stop(self):
        logging.info("MetricCollectorScheduler: Stopping background task.")
        self._running = False
