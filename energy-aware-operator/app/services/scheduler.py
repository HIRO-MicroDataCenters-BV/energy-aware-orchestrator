"""
Simple Scheduler Service for EnergyAwareOrchestration.

This scheduler implements the core scheduling logic using the EnergyAPIClient
to fetch and process energy availability data.

Scheduling Logic by Priority:
- Critical: Deploy immediately (always on, 24/7)
- Preferred: If energy insufficient, delay by 6 hours (next slot)
- Optional: Find best available slot in next 24 hours
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from dateutil import parser as date_parser

from app.services.energy_api_client import EnergyAPIClient

logger = logging.getLogger(__name__)


class SimpleSchedulerService:
    """
    Simple scheduler service that implements priority-based scheduling.
    
    Uses EnergyAPIClient to fetch and process energy availability data.
    """

    def __init__(self, energy_api_client: Optional[EnergyAPIClient] = None):
        """
        Initialize the scheduler service.

        Args:
            energy_api_client: Optional EnergyAPIClient instance for fetching energy data
        """
        self.energy_api_client = energy_api_client

        logger.info(
            f"SimpleSchedulerService initialized "
            f"(energy_api_client: {'configured' if energy_api_client else 'not configured'})"
        )

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

        # Critical: Always deploy immediately (no energy checks)
        if priority == "Critical":
            return self._build_critical_result(now, required_energy_watts)

        # Fetch energy forecast for Preferred/Optional
        energy_slots = await self._fetch_energy_forecast(hours_ahead=24)

        # Fallback to mock scheduling if API unavailable
        if energy_slots is None:
            logger.warning("Energy API unavailable, falling back to time-based scheduling")
            if priority == "Preferred":
                return self._build_preferred_result(now, required_energy_watts)
            elif priority == "Optional":
                return self._build_optional_result(now, required_energy_watts)

        # Map API slots to scheduler slots
        mapped_slots = self._map_api_slots_to_scheduler_slots(energy_slots)

        # Preferred/Optional: Find first sufficient slot
        if priority == "Preferred":
            return self._build_preferred_result_with_energy(now, required_energy_watts, mapped_slots)
        elif priority == "Optional":
            return self._build_optional_result_with_energy(now, required_energy_watts, mapped_slots)

        # Default fallback
        logger.warning(f"Unknown priority '{priority}', treating as Preferred")
        return self._build_preferred_result(now, required_energy_watts)

    async def _fetch_energy_forecast(self, hours_ahead: int = 24) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch energy forecast using the EnergyAPIClient.

        Args:
            hours_ahead: Number of hours ahead to fetch forecast for

        Returns:
            List of energy slots or None if client not configured or API unavailable
        """
        if not self.energy_api_client:
            logger.debug("No energy API client configured")
            return None

        return await self.energy_api_client.fetch_energy_forecast(hours_ahead=hours_ahead)

    def _map_api_slots_to_scheduler_slots(
        self,
        api_slots: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Map API slots to 6-hour scheduler slots using the EnergyAPIClient.

        Args:
            api_slots: List of energy slots from API

        Returns:
            List of enriched scheduler slots
        """
        if not self.energy_api_client:
            logger.warning("No energy API client configured for slot mapping")
            return []

        return self.energy_api_client.map_api_slots_to_scheduler_slots(
            api_slots,
            slot_number_calculator=self._get_current_slot_number,
            slot_boundary_calculator=self._get_slot_boundaries,
        )

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

    def _build_preferred_result_with_energy(
        self,
        now: datetime,
        required_energy_watts: float,
        energy_slots: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build Preferred result using real energy data."""

        # Get current slot data
        current_slot_num = self._get_current_slot_number(now)
        current_date = now.date().isoformat()

        current_slot_data = next(
            (slot for slot in energy_slots
             if slot["slotNumber"] == current_slot_num and slot["date"] == current_date),
            None
        )

        current_available = current_slot_data["availableEnergyWatts"] if current_slot_data else None
        is_sufficient = current_available is not None and current_available >= required_energy_watts

        # If current slot has sufficient energy, deploy immediately
        if is_sufficient:
            return {
                "phase": "Scheduled",
                "decision": {
                    "action": "DeployImmediately",
                    "reason": f"Preferred priority - current slot has sufficient energy ({current_available:.0f}W >= {required_energy_watts:.0f}W)",
                },
                "energyMetrics": {
                    "currentSlotAvailableWatts": current_available,
                    "currentSlotConsumedWatts": None,
                    "requiredWatts": required_energy_watts,
                    "sufficient": True,
                },
                "lastUpdated": now.isoformat(),
            }

        # Find first future slot with sufficient energy
        for slot in energy_slots:
            slot_start = date_parser.isoparse(slot["slotStart"])
            if slot_start > now and slot["availableEnergyWatts"] >= required_energy_watts:
                return {
                    "phase": "Scheduled",
                    "decision": {
                        "action": "Scheduled",
                        "reason": f"Preferred priority - scheduled for first sufficient energy slot ({slot['availableEnergyWatts']:.0f}W >= {required_energy_watts:.0f}W)",
                        "scheduledSlot": {
                            "slotNumber": slot["slotNumber"],
                            "slotStart": slot["slotStart"],
                            "slotEnd": slot["slotEnd"],
                            "availableEnergyWatts": slot["availableEnergyWatts"],
                            "requiredEnergyWatts": required_energy_watts,
                            "confidencePercentage": slot.get("confidencePercentage"),
                        },
                        "nextEvaluationTime": slot["slotStart"],
                    },
                    "energyMetrics": {
                        "currentSlotAvailableWatts": current_available,
                        "currentSlotConsumedWatts": None,
                        "requiredWatts": required_energy_watts,
                        "sufficient": False,
                    },
                    "lastUpdated": now.isoformat(),
                }

        # No sufficient slot found - fall back to time-based scheduling
        logger.warning(f"No slots with sufficient energy found, falling back to time-based scheduling")
        return self._build_preferred_result(now, required_energy_watts)

    def _build_optional_result_with_energy(
        self,
        now: datetime,
        required_energy_watts: float,
        energy_slots: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build Optional result using real energy data."""

        current_slot_num = self._get_current_slot_number(now)
        current_date = now.date().isoformat()

        current_slot_data = next(
            (slot for slot in energy_slots
             if slot["slotNumber"] == current_slot_num and slot["date"] == current_date),
            None
        )

        current_available = current_slot_data["availableEnergyWatts"] if current_slot_data else None
        is_sufficient = current_available is not None and current_available >= required_energy_watts

        # If the current slot already has sufficient energy, deploy immediately.
        # (Previously the current slot was always skipped, so Optional workloads
        # could never reach DeployImmediately even when energy was available now.)
        if is_sufficient:
            return {
                "phase": "Scheduled",
                "decision": {
                    "action": "DeployImmediately",
                    "reason": f"Optional priority - current slot has sufficient energy ({current_available:.0f}W >= {required_energy_watts:.0f}W)",
                },
                "energyMetrics": {
                    "currentSlotAvailableWatts": current_available,
                    "currentSlotConsumedWatts": None,
                    "requiredWatts": required_energy_watts,
                    "sufficient": True,
                },
                "lastUpdated": now.isoformat(),
            }

        # Find first future slot with sufficient energy (skip current slot for Optional)
        for slot in energy_slots:
            slot_start = date_parser.isoparse(slot["slotStart"])
            if slot_start > now and slot["availableEnergyWatts"] >= required_energy_watts:
                return {
                    "phase": "Scheduled",
                    "decision": {
                        "action": "Scheduled",
                        "reason": f"Optional priority - scheduled for optimal energy slot ({slot['availableEnergyWatts']:.0f}W >= {required_energy_watts:.0f}W)",
                        "scheduledSlot": {
                            "slotNumber": slot["slotNumber"],
                            "slotStart": slot["slotStart"],
                            "slotEnd": slot["slotEnd"],
                            "availableEnergyWatts": slot["availableEnergyWatts"],
                            "requiredEnergyWatts": required_energy_watts,
                            "confidencePercentage": slot.get("confidencePercentage"),
                        },
                        "nextEvaluationTime": slot["slotStart"],
                    },
                    "energyMetrics": {
                        "currentSlotAvailableWatts": current_available,
                        "currentSlotConsumedWatts": None,
                        "requiredWatts": required_energy_watts,
                        "sufficient": False,
                    },
                    "lastUpdated": now.isoformat(),
                }

        # No sufficient slot found - fall back to time-based scheduling
        logger.warning(f"No slots with sufficient energy found, falling back to time-based scheduling")
        return self._build_optional_result(now, required_energy_watts)

    def forecast_demand_slots(
        self,
        required_energy_watts: float,
        schedule_result: Dict[str, Any],
        now: Optional[datetime] = None,
        slots_ahead: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Project this CR's demand across the next `slots_ahead` predefined
        6-hour slots (default 4 = 1 day), so a consumer like a grid
        operator gets a forecast to plan capacity against instead of a
        single current/next data point.

        A workload only draws power once it's actually running: every slot
        counts for DeployImmediately (already running), but for a Scheduled
        decision only the slots from its own scheduledSlot start onward do -
        earlier slots report 0W/not-running so a consumer can see exactly
        when the draw begins, not just that it eventually will.

        Returns [] if the decision has nothing concrete to report yet
        (mirrors the Delayed/Waiting/unknown check the caller used to do
        inline).
        """
        if now is None:
            now = datetime.now(timezone.utc)

        decision = schedule_result.get("decision", {}) or {}
        action = decision.get("action")

        if action == "DeployImmediately":
            start_slot_start = None
        elif action == "Scheduled" and (decision.get("scheduledSlot") or {}).get("slotStart"):
            start_slot_start = date_parser.isoparse(decision["scheduledSlot"]["slotStart"])
        else:
            return []

        current_slot_num = self._get_current_slot_number(now)
        window_start, _ = self._get_slot_boundaries(now, current_slot_num)

        slots = []
        for i in range(slots_ahead):
            slot_start = window_start + timedelta(hours=6 * i)
            slot_end = slot_start + timedelta(hours=6)
            running = start_slot_start is None or slot_start >= start_slot_start
            slots.append({
                "slot_start": slot_start,
                "slot_end": slot_end,
                "watts": required_energy_watts if running else 0.0,
                "running": running,
            })
        return slots

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

        # Handle hour 24 as hour 0 of next day
        if end_hour == 24:
            end_time = datetime.combine(date, datetime.min.time()).replace(
                hour=0, tzinfo=timezone.utc
            ) + timedelta(days=1)
        else:
            end_time = datetime.combine(date, datetime.min.time()).replace(
                hour=end_hour, tzinfo=timezone.utc
            )

        return start_time, end_time

