"""
Status handler for EnergyAwareOrchestration operator.

This module handles building and applying status patches to custom resources.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import kopf

logger = logging.getLogger(__name__)


class StatusHandler:
    """
    Handler for managing CR status updates.

    This handler builds status patches from schedule results and applies
    them to the custom resource via Kopf's patch mechanism.
    """

    @staticmethod
    def build_status_from_schedule(schedule_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a status patch from the schedule result.

        Args:
            schedule_result: Result from the scheduler (dict format)

        Returns:
            Dictionary to patch into CR status
        """
        return schedule_result

    @staticmethod
    def build_failure_status(reason: str, error: Optional[str] = None) -> Dict[str, Any]:
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

    def apply_status_patch(self, patch: kopf.Patch, status_update: Dict[str, Any]) -> None:
        """
        Apply a status update to the CR patch.

        Args:
            patch: Kopf patch object
            status_update: Status dictionary to apply
        """
        for key, value in status_update.items():
            patch.status[key] = value

        logger.debug(f"Applied status patch with keys: {list(status_update.keys())}")

    def log_schedule_decision(self, name: str, schedule_result: Dict[str, Any]) -> None:
        """
        Log the scheduling decision for observability.

        Args:
            name: Name of the CR
            schedule_result: Schedule result to log
        """
        decision = schedule_result.get("decision", {})
        action = decision.get("action", "Unknown")
        reason = decision.get("reason", "No reason provided")

        logger.info(f"Schedule decision for '{name}': {action} - {reason}")

        scheduled_slot = decision.get("scheduledSlot")
        if scheduled_slot:
            slot_number = scheduled_slot.get("slotNumber")
            slot_start = scheduled_slot.get("slotStart")
            slot_end = scheduled_slot.get("slotEnd")
            logger.info(f"  Scheduled slot: {slot_number} ({slot_start} - {slot_end})")

            available_energy = scheduled_slot.get("availableEnergyWatts")
            if available_energy is not None:
                logger.info(f"  Available energy: {available_energy}W")

        next_eval = decision.get("nextEvaluationTime")
        if next_eval:
            logger.info(f"  Next evaluation: {next_eval}")


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

