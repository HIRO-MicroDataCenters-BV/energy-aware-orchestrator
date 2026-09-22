import asyncio
import logging
import time
from datetime import datetime, timedelta

from app.db.database import get_async_db
from app.repositories.node_metrics_repository import NodeMetricsRepository
from app.repositories.container_power_metrics import ContainerPowerMetricsRepository


class MetricsRetentionScheduler:
    """
    Periodically deletes rows older than retention_days from node_metrics
    and container_power_metrics.

    Both tables accumulate a fresh row every MetricCollectorScheduler cycle
    (30s default) with no upsert - nothing else ever removes a row.
    Confirmed live: container_power_metrics alone reaches ~141K rows/day at
    default settings. Without this, the DB grows unbounded.
    """

    def __init__(self, retention_days: int = 7, interval_seconds: int = 3600):
        self.retention_days = retention_days
        self.interval_seconds = interval_seconds
        self._task = None
        self._running = False

    async def _run(self):
        self._running = True
        logging.info(
            f"MetricsRetentionScheduler started, retention: {self.retention_days} day(s), "
            f"interval: {self.interval_seconds} seconds"
        )
        while self._running:
            try:
                await self._cleanup_once()
            except Exception as e:
                logging.exception(f"Error in MetricsRetentionScheduler: {e}")
            await asyncio.sleep(self.interval_seconds)

    async def _cleanup_once(self):
        async for db in get_async_db():
            node_cutoff = int(time.time()) - self.retention_days * 86400
            node_deleted = await NodeMetricsRepository(db).delete_older_than(node_cutoff)

            container_cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
            container_deleted = await ContainerPowerMetricsRepository(db).delete_older_than(container_cutoff)

            logging.info(
                f"MetricsRetentionScheduler: deleted {node_deleted} node_metrics row(s), "
                f"{container_deleted} container_power_metrics row(s) older than {self.retention_days} day(s)"
            )
            break

    def start(self):
        if not self._task:
            logging.info("MetricsRetentionScheduler: Starting background task.")
            self._task = asyncio.create_task(self._run())

    def stop(self):
        logging.info("MetricsRetentionScheduler: Stopping background task.")
        self._running = False
