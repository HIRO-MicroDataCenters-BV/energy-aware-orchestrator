import asyncio
from app.servicesv2.prometheus_metrics_service import PrometheusMetricsService
import logging


class MetricCollectorScheduler:
    def __init__(self, interval_seconds: int = 10):
        self.interval_seconds = interval_seconds
        self.prometheus_service = PrometheusMetricsService()
        self._task = None
        self._running = False

    async def _run(self):
        self._running = True
        logging.info(f"MetricCollectorScheduler started, interval: {self.interval_seconds} seconds")
        while self._running:
            try:
                logging.info("MetricCollectorScheduler: Starting Prometheus metrics collection cycle...")

                # Collect Prometheus metrics (includes both container and energy metrics)
                prometheus_count = await self.prometheus_service.collect_and_store_metrics()

                # Handle potential exceptions
                if isinstance(prometheus_count, Exception):
                    logging.error(f"Failed to collect Prometheus metrics: {prometheus_count}")
                    prometheus_count = 0

                logging.info(f"MetricCollectorScheduler: Stored {prometheus_count} node metrics with energy data from Prometheus")
            except Exception as e:
                logging.exception(f"Error in MetricCollectorScheduler: {e}")
            await asyncio.sleep(self.interval_seconds)

    def start(self):
        if not self._task:
            logging.info("MetricCollectorScheduler: Starting background task.")
            self._task = asyncio.create_task(self._run())

    def stop(self):
        logging.info("MetricCollectorScheduler: Stopping background task.")
        self._running = False
