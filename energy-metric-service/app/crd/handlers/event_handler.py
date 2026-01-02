"""
Event handler for EnergyAwareOrchestration operator.

This module handles posting Kubernetes events for observability.
"""

import logging
from typing import Any, Dict, Optional

import kopf

from app.servicesv2.eao_scheduler_service import ScheduleResult

logger = logging.getLogger(__name__)


class EventHandler:
    """
    Handler for posting Kubernetes events.

    This handler provides convenience methods for posting events at different
    stages of the reconciliation process, with proper error handling.
    """

    @staticmethod
    def post_event_safe(
        body: Dict[str, Any],
        event_type: str,
        reason: str,
        message: str
    ) -> bool:
        """
        Post a Kubernetes event with error handling.

        Args:
            body: The CR body
            event_type: Event type ("Normal" or "Warning")
            reason: Event reason (e.g., "Scheduling", "Scheduled")
            message: Event message

        Returns:
            True if event was posted successfully, False otherwise
        """
        try:
            kopf.event(
                body,
                type=event_type,
                reason=reason,
                message=message
            )
            logger.debug(f"Posted {event_type} event: {reason} - {message}")
            return True

        except Exception as e:
            logger.warning(f"Failed to post event '{reason}': {e}")
            return False

    def post_scheduling_started(
        self,
        body: Dict[str, Any],
        name: str,
        priority: str,
        energy_consumption: int
    ) -> bool:
        """
        Post event when scheduling starts.

        Args:
            body: The CR body
            name: CR name
            priority: Workload priority
            energy_consumption: Energy consumption in Watts

        Returns:
            True if successful
        """
        return self.post_event_safe(
            body,
            event_type="Normal",
            reason="Scheduling",
            message=(
                f"Calculating schedule for '{name}' "
                f"(Priority: {priority}, Energy: {energy_consumption}W)"
            )
        )

    def post_scheduling_completed(
        self,
        body: Dict[str, Any],
        schedule_result: ScheduleResult
    ) -> bool:
        """
        Post event when scheduling completes successfully.

        Args:
            body: The CR body
            schedule_result: The schedule result

        Returns:
            True if successful
        """
        decision = schedule_result.decision

        return self.post_event_safe(
            body,
            event_type="Normal",
            reason="Scheduled",
            message=f"{decision.action.value}: {decision.reason}"
        )

    def post_scheduling_failed(
        self,
        body: Dict[str, Any],
        reason: str = "Failed to calculate schedule"
    ) -> bool:
        """
        Post event when scheduling fails.

        Args:
            body: The CR body
            reason: Failure reason

        Returns:
            True if successful
        """
        return self.post_event_safe(
            body,
            event_type="Warning",
            reason="SchedulingFailed",
            message=reason
        )

    def post_validation_failed(
        self,
        body: Dict[str, Any],
        message: str
    ) -> bool:
        """
        Post event when validation fails.

        Args:
            body: The CR body
            message: Validation error message

        Returns:
            True if successful
        """
        return self.post_event_safe(
            body,
            event_type="Warning",
            reason="ValidationFailed",
            message=message
        )

    def post_error(
        self,
        body: Dict[str, Any],
        error: str
    ) -> bool:
        """
        Post event for general errors.

        Args:
            body: The CR body
            error: Error message

        Returns:
            True if successful
        """
        return self.post_event_safe(
            body,
            event_type="Warning",
            reason="Error",
            message=f"Scheduling error: {error}"
        )

    def post_deletion(
        self,
        body: Dict[str, Any],
        name: str
    ) -> bool:
        """
        Post event when CR is being deleted.

        Args:
            body: The CR body
            name: CR name

        Returns:
            True if successful
        """
        return self.post_event_safe(
            body,
            event_type="Normal",
            reason="Deleting",
            message=f"EnergyAwareOrchestration '{name}' is being deleted"
        )

    def post_periodic_reevaluation(
        self,
        body: Dict[str, Any],
        name: str
    ) -> bool:
        """
        Post event when periodic re-evaluation occurs.

        Args:
            body: The CR body
            name: CR name

        Returns:
            True if successful
        """
        return self.post_event_safe(
            body,
            event_type="Normal",
            reason="Reevaluating",
            message=f"Periodic re-evaluation for '{name}'"
        )


# Singleton instance
_event_handler: Optional[EventHandler] = None


def get_event_handler() -> EventHandler:
    """
    Get the global event handler instance.

    Returns:
        EventHandler singleton instance
    """
    global _event_handler
    if _event_handler is None:
        _event_handler = EventHandler()
    return _event_handler
