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
from typing import Any, Dict, List, Optional

import httpx
from dateutil import parser as date_parser

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

        # Initialize HTTP client for energy API calls
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_connections=10),
            follow_redirects=True
        )

        logger.info(f"SimpleSchedulerService initialized (energy_api_url: {energy_api_url})")

    async def close(self):
        """Close HTTP client connections."""
        if hasattr(self, 'http_client'):
            await self.http_client.aclose()

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
        mapped_slots = self._map_api_slots_to_scheduler_slots(energy_slots, now)

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
        Fetch energy forecast from API.

        Args:
            hours_ahead: Number of hours ahead to fetch forecast for

        Returns:
            List of energy slots or None if API unavailable
        """
        if not self.energy_api_url:
            return None

        url = f"{self.energy_api_url}/api/energy-availability/future/forecast"
        params = {"hours_ahead": hours_ahead, "limit": 100}

        try:
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            availability = data.get("availability", [])

            if not isinstance(availability, list):
                logger.error("Invalid response: 'availability' is not a list")
                return None

            logger.info(f"Fetched {len(availability)} energy slots from API")
            return availability

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"Energy API unavailable: {e.__class__.__name__}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Energy API error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching energy data: {e}")
            return None

    def _map_api_slots_to_scheduler_slots(
        self,
        api_slots: List[Dict[str, Any]],
        now: datetime
    ) -> List[Dict[str, Any]]:
        """
        Map API slots to 6-hour scheduler slots, aggregating energy by time period.

        Args:
            api_slots: List of energy slots from API
            now: Current datetime

        Returns:
            List of enriched scheduler slots
        """
        from collections import defaultdict

        aggregated = defaultdict(lambda: {
            "total_watts": 0,
            "confidence_sum": 0,
            "confidence_count": 0,
        })

        for api_slot in api_slots:
            try:
                start = date_parser.isoparse(api_slot["slot_start_time"])
                end = date_parser.isoparse(api_slot["slot_end_time"])
                watts = float(api_slot["available_watts"])

                # Ensure UTC timezone
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)

                # Determine which scheduler slot this overlaps
                date = start.date()
                slot_num = self._get_current_slot_number(start)
                key = (date, slot_num)

                # Aggregate energy
                aggregated[key]["total_watts"] += watts

                # Track confidence
                if "confidence_percentage" in api_slot:
                    aggregated[key]["confidence_sum"] += api_slot["confidence_percentage"]
                    aggregated[key]["confidence_count"] += 1

            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping invalid API slot: {e}")
                continue

        # Convert to scheduler slot format
        scheduler_slots = []
        for (date, slot_num), agg_data in sorted(aggregated.items()):
            slot_start, slot_end = self._get_slot_boundaries(
                datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc),
                slot_num
            )

            avg_confidence = None
            if agg_data["confidence_count"] > 0:
                avg_confidence = agg_data["confidence_sum"] / agg_data["confidence_count"]

            scheduler_slots.append({
                "slotNumber": slot_num,
                "slotStart": slot_start.isoformat(),
                "slotEnd": slot_end.isoformat(),
                "availableEnergyWatts": agg_data["total_watts"],
                "confidencePercentage": avg_confidence,
                "date": date.isoformat(),
            })

        logger.debug(f"Mapped {len(api_slots)} API slots to {len(scheduler_slots)} scheduler slots")
        return scheduler_slots

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

