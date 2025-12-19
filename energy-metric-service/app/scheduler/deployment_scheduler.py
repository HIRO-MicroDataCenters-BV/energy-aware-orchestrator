"""
Deployment Scheduler
Runs every 1 minute to process pending deployment requests based on energy availability
"""

import asyncio
import logging

from app.servicesv2.deployment.deployment_scheduler_service import DeploymentSchedulerService


logger = logging.getLogger(__name__)


class DeploymentScheduler:
    """
    Background scheduler that processes pending deployment requests.
    Runs every 1 minute to check for pending deployments and deploy them
    when sufficient energy is available.
    """

    def __init__(self, interval_seconds: int = 10):
        """
        Initialize the deployment scheduler.

        Args:
            interval_seconds: Interval between scheduler runs (default: 60 seconds = 1 minute)
        """
        self.interval_seconds = interval_seconds
        self.deployment_service = DeploymentSchedulerService()
        self._task = None
        self._running = False

    async def _run(self):
        """Main scheduler loop"""
        self._running = True
        logger.info(f"DeploymentScheduler started, interval: {self.interval_seconds} seconds")

        while self._running:
            try:
                logger.info("DeploymentScheduler: Starting deployment processing cycle...")

                # Process pending deployments
                processed_count = await self.deployment_service.process_pending_deployments()

                if processed_count > 0:
                    logger.info(f"DeploymentScheduler: Processed {processed_count} deployment(s)")
                else:
                    logger.debug("DeploymentScheduler: No pending deployments to process")

            except Exception as e:
                logger.exception(f"Error in DeploymentScheduler: {e}")

            # Wait for next cycle
            await asyncio.sleep(self.interval_seconds)

    def start(self):
        """Start the background scheduler task"""
        if not self._task:
            logger.info("DeploymentScheduler: Starting background task")
            self._task = asyncio.create_task(self._run())
        else:
            logger.warning("DeploymentScheduler: Task already running")

    def stop(self):
        """Stop the background scheduler task"""
        logger.info("DeploymentScheduler: Stopping background task")
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
