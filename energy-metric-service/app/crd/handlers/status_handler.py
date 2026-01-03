"""
Status handler for EnergyAwareOrchestration operator.

This module handles building and applying status patches to custom resources.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import kopf

from app.servicesv2.eao_scheduler_service import ScheduleResult

logger = logging.getLogger(__name__)


class StatusHandler:
    """
    Handler for managing CR status updates.

    This handler builds status patches from schedule results and applies
    them to the custom resource via Kopf's patch mechanism.
    """

    @staticmethod
    def build_status_from_schedule(schedule_result: ScheduleResult) -> Dict[str, Any]:
        """
        Build a status patch from the schedule result.

        Args:
            schedule_result: Result from the scheduler

        Returns:
            Dictionary to patch into CR status
        """
        return schedule_result.to_dict()

    @staticmethod
    def build_failure_status(
        reason: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build a status patch for a failed scheduling operation.

        Args:
            reason: Reason for failure
            error: Optional error message

        Returns:
            Dictionary to patch into CR status
        """
        status = {
            "phase": "Failed",
            "decision": {
                "action": "Waiting",
                "reason": reason,
            },
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        }

        if error:
            status["error"] = error

        return status

    @staticmethod
    def build_validation_failure_status(field: str, message: str) -> Dict[str, Any]:
        """
        Build a status patch for validation failure.

        Args:
            field: Field that failed validation
            message: Validation error message

        Returns:
            Dictionary to patch into CR status
        """
        return {
            "phase": "Failed",
            "decision": {
                "action": "Waiting",
                "reason": f"Validation failed: {message}",
            },
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "validationError": {
                "field": field,
                "message": message,
            },
        }

    def apply_status_patch(
        self,
        patch: kopf.Patch,
        status_update: Dict[str, Any]
    ) -> None:
        """
        Apply a status update to the CR patch.

        Args:
            patch: Kopf patch object
            status_update: Status dictionary to apply
        """
        for key, value in status_update.items():
            patch.status[key] = value

        logger.debug(f"Applied status patch with keys: {list(status_update.keys())}")

    def log_schedule_decision(
        self,
        name: str,
        schedule_result: ScheduleResult
    ) -> None:
        """
        Log the scheduling decision for observability.

        Args:
            name: Name of the CR
            schedule_result: Schedule result to log
        """
        decision = schedule_result.decision

        logger.info(
            f"Schedule decision for '{name}': {decision.action.value} - {decision.reason}"
        )

        if decision.scheduled_slot:
            slot = decision.scheduled_slot
            logger.info(
                f"  Scheduled slot: {slot.slot_number} "
                f"({slot.start_time} - {slot.end_time})"
            )
            if slot.available_energy_watts is not None:
                logger.info(f"  Available energy: {slot.available_energy_watts}W")

        if decision.next_evaluation_time:
            logger.info(
                f"  Next evaluation: {decision.next_evaluation_time}"
            )


# Singleton instance
_status_handler: Optional[StatusHandler] = None


def get_status_handler() -> StatusHandler:
    """
    Get the global status handler instance.

    Returns:
        StatusHandler singleton instance
    """
    global _status_handler
    if _status_handler is None:
        _status_handler = StatusHandler()
    return _status_handler
