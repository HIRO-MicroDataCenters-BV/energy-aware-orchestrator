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

    async def report_demand_batch(
        self,
        identifier: str,
        slots: List[Dict[str, Any]],
    ) -> Optional[List[float]]:
        """
        Report a CR's demand forecast across multiple slots in one HTTP call.

        Best-effort like fetch_energy_forecast(): failures are logged and
        return None rather than raising, so a demand-reporting problem
        never blocks the CR's own scheduling decision from being persisted.

        Args:
            identifier: '<namespace>/<name>' of the EAO CR
            slots: list of dicts, each with slot_start_time/slot_end_time
                (ISO 8601 strings), required_watts, and application_name
                (may be None to force required_watts verbatim for that
                slot - e.g. a not-yet-running future slot, where live
                measurement/prediction would reflect 'now', not that slot).

        Returns:
            Resolved watts per slot, same order as input (may differ from
            required_watts - see resolve_demand_watts() server-side), or
            None if the whole batch failed.
        """
        if not self.api_url:
            logger.debug("No API URL configured, skipping demand batch report")
            return None

        url = f"{self.api_url}/api/energy-availability/demand/batch"
        payload = {"identifier": identifier, "slots": slots}

        try:
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            resolved = [float(record["available_watts"]) for record in response.json()["demand"]]
            logger.info(f"Reported demand batch for '{identifier}': {len(resolved)} slot(s), current={resolved[0] if resolved else None}W resolved")
            return resolved

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"Energy API unavailable, could not report demand batch for '{identifier}': {e.__class__.__name__}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Energy API error reporting demand batch for '{identifier}': {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error reporting demand batch for '{identifier}': {e}")
            return None

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
        slot_number_calculator: callable,
        slot_boundary_calculator: callable,
    ) -> List[Dict[str, Any]]:
        """
        Map API slots to 6-hour scheduler slots, aggregating energy by time period.

        Args:
            api_slots: List of energy slots from API
            slot_number_calculator: Function to calculate slot number from datetime
            slot_boundary_calculator: Function to calculate (start, end) for a
                (datetime, slot_number) pair - shares SimpleSchedulerService's
                own boundary math instead of a separate copy of it here.

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

                # Track confidence - key presence alone isn't enough, the
                # field is present but null on every real/predicted supply
                # row today since nothing populates it yet.
                if api_slot.get("confidence_percentage") is not None:
                    aggregated[key]["confidence_sum"] += api_slot["confidence_percentage"]
                    aggregated[key]["confidence_count"] += 1

            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping invalid API slot: {e}")
                continue

        # Convert to scheduler slot format
        scheduler_slots = []
        for (date, slot_num), agg_data in sorted(aggregated.items()):
            # slot_boundary_calculator takes a datetime (it only reads
            # .date() off it), so wrap the bare aggregation-key date first.
            slot_start, slot_end = slot_boundary_calculator(
                datetime.combine(date, datetime.min.time(), tzinfo=timezone.utc),
                slot_num,
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
