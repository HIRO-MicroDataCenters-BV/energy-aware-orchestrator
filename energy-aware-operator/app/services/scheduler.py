"""
Simple Scheduler Service for EnergyAwareOrchestration.

This is a standalone scheduler that implements the core scheduling logic
without external dependencies. It can be extended to integrate with
an energy availability service.

Scheduling Logic by Priority:
- Critical: Deploy immediately (always on, 24/7)
- Preferred: If energy insufficient, delay by 6 hours (next slot)
- Optional: Find best available slot in next 24 hours
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SimpleSchedulerService:
    """
    Simple scheduler service that implements priority-based scheduling.
    
    This is a standalone version that works without external dependencies.
    For production use, integrate with an energy availability service.
    """

    def __init__(self, energy_api_url: Optional[str] = None):
        """
        Initialize the scheduler service.
        
        Args:
            energy_api_url: Optional URL for energy API integration
        """
        self.energy_api_url = energy_api_url
        logger.info(f"SimpleSchedulerService initialized (energy_api_url: {energy_api_url})")

    async def calculate_schedule(
        self, priority: str, required_energy_watts: float
    ) -> Dict[str, Any]:
        """
        Calculate schedule based on priority and energy requirements.

        Args:
            priority: Workload priority (Critical, Preferred, Optional)
            required_energy_watts: Required energy in Watts

        Returns:
            Schedule result dictionary with phase, decision, and energyMetrics
        """
        now = datetime.now(timezone.utc)

        logger.info(
            f"Calculating schedule: priority={priority}, "
            f"energy={required_energy_watts}W"
        )

        # Critical: Deploy immediately
        if priority == "Critical":
            return self._build_critical_result(now, required_energy_watts)

        # Preferred: Check current slot, delay if needed
        if priority == "Preferred":
            return self._build_preferred_result(now, required_energy_watts)

        # Optional: Find best slot in next 24 hours
        if priority == "Optional":
            return self._build_optional_result(now, required_energy_watts)

        # Default fallback
        logger.warning(f"Unknown priority '{priority}', treating as Preferred")
        return self._build_preferred_result(now, required_energy_watts)

    def _build_critical_result(
        self, now: datetime, required_energy_watts: float
    ) -> Dict[str, Any]:
        """Build result for Critical priority workloads."""
        return {
            "phase": "Scheduled",
            "decision": {
                "action": "DeployImmediately",
                "reason": "Critical priority workload - deploying immediately for 24/7 operation",
            },
            "energyMetrics": {
                "currentSlotAvailableWatts": None,
                "currentSlotConsumedWatts": None,
                "requiredWatts": required_energy_watts,
                "sufficient": True,  # Always sufficient for critical
            },
            "lastUpdated": now.isoformat(),
        }

    def _build_preferred_result(
        self, now: datetime, required_energy_watts: float
    ) -> Dict[str, Any]:
        """Build result for Preferred priority workloads."""
        # Calculate next slot (6 hours from now)
        next_slot_time = now + timedelta(hours=6)
        slot_number = self._get_current_slot_number(next_slot_time)
        slot_start, slot_end = self._get_slot_boundaries(next_slot_time, slot_number)

        return {
            "phase": "Scheduled",
            "decision": {
                "action": "Scheduled",
                "reason": "Preferred priority - scheduled for next available slot",
                "scheduledSlot": {
                    "slotNumber": slot_number,
                    "slotStart": slot_start.isoformat(),
                    "slotEnd": slot_end.isoformat(),
                    "availableEnergyWatts": None,  # Would come from energy service
                    "requiredEnergyWatts": required_energy_watts,
                    "confidencePercentage": None,
                },
                "nextEvaluationTime": next_slot_time.isoformat(),
            },
            "energyMetrics": {
                "currentSlotAvailableWatts": None,
                "currentSlotConsumedWatts": None,
                "requiredWatts": required_energy_watts,
                "sufficient": False,  # Assume insufficient, hence delayed
            },
            "lastUpdated": now.isoformat(),
        }

    def _build_optional_result(
        self, now: datetime, required_energy_watts: float
    ) -> Dict[str, Any]:
        """Build result for Optional priority workloads."""
        # Find best slot in next 24 hours (for demo, use slot in 12 hours)
        best_slot_time = now + timedelta(hours=12)
        slot_number = self._get_current_slot_number(best_slot_time)
        slot_start, slot_end = self._get_slot_boundaries(best_slot_time, slot_number)

        return {
            "phase": "Scheduled",
            "decision": {
                "action": "Scheduled",
                "reason": "Optional priority - scheduled for optimal energy availability slot",
                "scheduledSlot": {
                    "slotNumber": slot_number,
                    "slotStart": slot_start.isoformat(),
                    "slotEnd": slot_end.isoformat(),
                    "availableEnergyWatts": None,  # Would come from energy service
                    "requiredEnergyWatts": required_energy_watts,
                    "confidencePercentage": None,
                },
                "nextEvaluationTime": best_slot_time.isoformat(),
            },
            "energyMetrics": {
                "currentSlotAvailableWatts": None,
                "currentSlotConsumedWatts": None,
                "requiredWatts": required_energy_watts,
                "sufficient": False,  # Waiting for better slot
            },
            "lastUpdated": now.isoformat(),
        }

    def _get_current_slot_number(self, dt: datetime) -> int:
        """
        Get the current 6-hour slot number (1-4) for a given datetime.

        Time slots:
        - Slot 1: 00:00 - 06:00
        - Slot 2: 06:00 - 12:00
        - Slot 3: 12:00 - 18:00
        - Slot 4: 18:00 - 24:00

        Args:
            dt: Datetime to calculate slot for

        Returns:
            Slot number (1-4)
        """
        hour = dt.hour
        if 0 <= hour < 6:
            return 1
        elif 6 <= hour < 12:
            return 2
        elif 12 <= hour < 18:
            return 3
        else:
            return 4

    def _get_slot_boundaries(
        self, dt: datetime, slot_number: int
    ) -> tuple[datetime, datetime]:
        """
        Get the start and end times for a given slot.

        Args:
            dt: Base datetime
            slot_number: Slot number (1-4)

        Returns:
            Tuple of (start_time, end_time)
        """
        # Get the date part
        date = dt.date()

        # Slot boundaries in hours
        slot_hours = {
            1: (0, 6),
            2: (6, 12),
            3: (12, 18),
            4: (18, 24),
        }

        start_hour, end_hour = slot_hours.get(slot_number, (0, 6))

        start_time = datetime.combine(date, datetime.min.time()).replace(
            hour=start_hour, tzinfo=timezone.utc
        )
        end_time = datetime.combine(date, datetime.min.time()).replace(
            hour=end_hour, tzinfo=timezone.utc
        )

        return start_time, end_time

