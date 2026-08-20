"""
Grid API Client for polling live capacity data from the external grid.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class GridAPIClient:
    """
    Client for polling the external grid's capacity API.

    Best-effort like the operator's EnergyAPIClient: failures are logged and
    return None rather than raising, so a bad poll cycle never crashes the
    polling loop - it just skips to the next interval.
    """

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_connections=10),
            follow_redirects=True,
        )
        logger.info(f"GridAPIClient initialized (api_url: {api_url})")

    async def close(self):
        if hasattr(self, "http_client"):
            await self.http_client.aclose()
            logger.debug("HTTP client closed")

    async def fetch_grid_capacity(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch current/future capacity slots from the grid.

        Expects the same envelope this service's own
        /api/energy-availability/future/forecast endpoint returns:
        {"availability": [{"slot_start_time", "slot_end_time",
        "available_watts", ...}, ...]}, so a manual stub for testing can
        reuse that exact shape.

        Returns:
            List of capacity slots, or None if the grid API is unavailable
            or returned something we can't use.
        """
        if not self.api_url:
            logger.debug("No grid API URL configured, skipping capacity fetch")
            return None

        try:
            response = await self.http_client.get(self.api_url)
            response.raise_for_status()
            data = response.json()
            availability = data.get("availability", [])

            if not isinstance(availability, list):
                logger.error("Invalid grid response: 'availability' is not a list")
                return None

            logger.info(f"Fetched {len(availability)} capacity slots from grid")
            return availability

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"Grid API unavailable: {e.__class__.__name__}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Grid API error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching grid capacity: {e}")
            return None
