"""
Energy API Client for fetching and processing energy availability data.

This client handles all HTTP communication with the energy availability API
and provides methods to fetch and transform energy forecast data.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class EnergyAPIClient:
    """
    Client for interacting with the Energy Availability API.

    This client manages HTTP connections and provides methods to fetch
    and process energy forecast data from the external API.
    """

    def __init__(self, api_url: Optional[str] = None):
        """
        Initialize the Energy API client.

        Args:
            api_url: Base URL for the energy API (e.g., "http://0.0.0.0:8086")
        """
        self.api_url = api_url

        # Initialize HTTP client for API calls
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_connections=10),
            follow_redirects=True
        )

        logger.info(f"EnergyAPIClient initialized (api_url: {api_url})")

    async def close(self):
        """Close HTTP client connections."""
        if hasattr(self, 'http_client'):
            await self.http_client.aclose()
            logger.debug("HTTP client closed")

    async def fetch_energy_forecast(self, hours_ahead: int = 24) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch energy forecast from API.

        Args:
            hours_ahead: Number of hours ahead to fetch forecast for

        Returns:
            List of energy slots or None if API unavailable
        """
        if not self.api_url:
            logger.debug("No API URL configured, skipping energy forecast fetch")
            return None

        url = f"{self.api_url}/api/energy-availability/future/forecast"
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

    async def report_demand(
        self,
        identifier: str,
        slot_start_time: str,
        slot_end_time: str,
        required_watts: float,
    ) -> bool:
        """
        Report a CR's current demand to energy-metric-service.

        Best-effort like fetch_energy_forecast(): failures are logged and
        return False rather than raising, so a demand-reporting problem
        never blocks the CR's own scheduling decision from being persisted.

        Args:
            identifier: '<namespace>/<name>' of the EAO CR
            slot_start_time: ISO 8601 start of the currently decided slot
            slot_end_time: ISO 8601 end of the currently decided slot
            required_watts: spec.energyConsumption, verbatim

        Returns:
            True if the report was accepted, False otherwise
        """
        if not self.api_url:
            logger.debug("No API URL configured, skipping demand report")
            return False

        url = f"{self.api_url}/api/energy-availability/demand"
        payload = {
            "identifier": identifier,
            "slot_start_time": slot_start_time,
            "slot_end_time": slot_end_time,
            "required_watts": required_watts,
        }

        try:
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"Reported demand for '{identifier}': {required_watts}W ({slot_start_time} - {slot_end_time})")
            return True

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"Energy API unavailable, could not report demand for '{identifier}': {e.__class__.__name__}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"Energy API error reporting demand for '{identifier}': {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error reporting demand for '{identifier}': {e}")
            return False

    async def delete_demand(self, identifier: str) -> bool:
        """
        Deactivate a CR's demand record (called on CR deletion).

        Best-effort, same as report_demand() - a failure here is logged and
        does not block the rest of CR deletion cleanup. A 404 (nothing to
        delete) counts as success, since the end state - no active demand
        record for this identifier - is what we wanted either way.

        Args:
            identifier: '<namespace>/<name>' of the EAO CR

        Returns:
            True if the record was deleted or already absent, False on error
        """
        if not self.api_url:
            logger.debug("No API URL configured, skipping demand deletion")
            return False

        url = f"{self.api_url}/api/energy-availability/demand/{identifier}"

        try:
            response = await self.http_client.delete(url)
            if response.status_code == 404:
                logger.debug(f"No demand record to delete for '{identifier}'")
                return True
            response.raise_for_status()
            logger.info(f"Deleted demand record for '{identifier}'")
            return True

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"Energy API unavailable, could not delete demand for '{identifier}': {e.__class__.__name__}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"Energy API error deleting demand for '{identifier}': {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting demand for '{identifier}': {e}")
            return False

    def map_api_slots_to_scheduler_slots(
        self,
        api_slots: List[Dict[str, Any]],
        slot_number_calculator: callable
    ) -> List[Dict[str, Any]]:
        """
        Map API slots to 6-hour scheduler slots, aggregating energy by time period.

        Args:
            api_slots: List of energy slots from API
            slot_number_calculator: Function to calculate slot number from datetime

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
                slot_num = slot_number_calculator(start)
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
            # Calculate slot boundaries
            slot_start, slot_end = self._calculate_slot_boundaries(date, slot_num)

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

    def _calculate_slot_boundaries(self, date, slot_number: int) -> tuple:
        """
        Calculate start and end times for a scheduler slot.

        Args:
            date: Date for the slot
            slot_number: Slot number (1-4)

        Returns:
            Tuple of (start_time, end_time)
        """
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
