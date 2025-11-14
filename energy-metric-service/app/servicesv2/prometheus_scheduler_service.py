"""
Background scheduler service for periodic Prometheus metrics collection.
"""

import asyncio
import logging
from datetime import datetime
from app.servicesv2.prometheus_metrics_service import PrometheusMetricsService

class PrometheusSchedulerService:
    """Service to periodically collect and store Prometheus container metrics."""
    
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self.prometheus_service = PrometheusMetricsService()
        self._running = False
        self._task = None
        
    async def start(self):
        """Start the periodic metrics collection."""
        if self._running:
            logging.warning("PrometheusSchedulerService is already running")
            return
            
        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logging.info(f"PrometheusSchedulerService started - collecting metrics every {self.interval_seconds} seconds")
        
    async def stop(self):
        """Stop the periodic metrics collection."""
        if not self._running:
            logging.warning("PrometheusSchedulerService is not running")
            return
            
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
        logging.info("PrometheusSchedulerService stopped")
        
    async def _run_scheduler(self):
        """Main scheduler loop that runs every interval."""
        while self._running:
            try:
                start_time = datetime.utcnow()
                
                # Collect and store metrics
                stored_count = await self.prometheus_service.collect_and_store_metrics()
                
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                logging.info(f"PrometheusScheduler: Collected and stored {stored_count} metrics in {duration:.2f}s")
                
                # Wait for the next interval
                await asyncio.sleep(self.interval_seconds)
                
            except asyncio.CancelledError:
                # Expected when stopping the service
                break
            except Exception as e:
                logging.error(f"Error in PrometheusScheduler: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(self.interval_seconds)
                
    def is_running(self) -> bool:
        """Check if the scheduler is currently running."""
        return self._running

# Global instance for the scheduler
prometheus_scheduler = PrometheusSchedulerService(interval_seconds=60)