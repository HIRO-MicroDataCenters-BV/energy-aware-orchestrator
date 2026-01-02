"""
Scheduler handler for EnergyAwareOrchestration operator.

This module provides async scheduling functionality for the operator,
wrapping the EAOSchedulerService to avoid event loop conflicts.
"""

import logging
from typing import Optional

from app.servicesv2.eao_scheduler_service import EAOSchedulerService, ScheduleResult

logger = logging.getLogger(__name__)


class SchedulerHandler:
    """
    Handler for calculating execution schedules in the operator context.

    This handler wraps the EAOSchedulerService and provides an async interface
    that works with Kopf's event loop without creating database sessions
    (which would cause event loop conflicts).
    """

    def __init__(self):
        """Initialize the scheduler handler."""
        self._scheduler: Optional[EAOSchedulerService] = None

    @property
    def scheduler(self) -> EAOSchedulerService:
        """Get or create the scheduler service instance."""
        if self._scheduler is None:
            # Create scheduler without database to avoid event loop conflicts
            # The scheduling logic still works based on priority
            self._scheduler = EAOSchedulerService()
        return self._scheduler

    async def calculate_schedule(
        self,
        priority: str,
        energy_consumption: int,
    ) -> Optional[ScheduleResult]:
        """
        Calculate schedule using the scheduler service.

        This function is async and designed to be called from Kopf's async handlers.
        Since Kopf manages its own event loop, we don't create database sessions here
        to avoid event loop conflicts. The scheduler will work without energy data.

        Args:
            priority: Workload priority (Critical, Preferred, Optional)
            energy_consumption: Required energy in Watts

        Returns:
            ScheduleResult or None if scheduling failed
        """
        try:
            # Use scheduler without database to avoid event loop conflicts
            # The scheduling logic still works based on priority
            result = await self.scheduler.calculate_schedule(
                priority=priority,
                required_energy_watts=float(energy_consumption),
            )

            logger.info(
                f"Schedule calculated: {result.decision.action.value} "
                f"for priority={priority}, energy={energy_consumption}W"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating schedule: {e}", exc_info=True)
            return None

    def reset(self) -> None:
        """
        Reset the scheduler instance.

        Useful for testing or when you need to reinitialize the scheduler.
        """
        self._scheduler = None
        logger.debug("Scheduler handler reset")


# Singleton instance for use across the operator
_scheduler_handler: Optional[SchedulerHandler] = None


def get_scheduler_handler() -> SchedulerHandler:
    """
    Get the global scheduler handler instance.

    Returns:
        SchedulerHandler singleton instance
    """
    global _scheduler_handler
    if _scheduler_handler is None:
        _scheduler_handler = SchedulerHandler()
    return _scheduler_handler
