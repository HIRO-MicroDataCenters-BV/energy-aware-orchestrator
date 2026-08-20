"""
Grid Polling Scheduler
Periodically polls the external grid for live capacity data and stores it
as supply rows in energy_availability.
"""

import asyncio
import logging
import os
from datetime import date, datetime

from app.db.database import AsyncSessionLocal
from app.repositories.energy_availability import EnergyAvailabilityRepository
from app.services.grid_api_client import GridAPIClient

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER_NAME = "grid"


class GridPollingScheduler:
    """
    Background scheduler that polls the grid API for capacity data.

    Failures (grid unreachable, bad response, a single bad slot) are caught
    and logged per cycle - the loop always sleeps and tries again on the
    next interval rather than stopping.
    """

    def __init__(self, api_url: str, interval_seconds: int = 300):
        self.interval_seconds = interval_seconds
        self.grid_client = GridAPIClient(api_url=api_url)
        self._task = None
        self._running = False

    async def _run(self):
        self._running = True
        logger.info(f"GridPollingScheduler started, interval: {self.interval_seconds} seconds")

        while self._running:
            try:
                slots = await self.grid_client.fetch_grid_capacity()

                if not slots:
                    logger.debug("GridPollingScheduler: No capacity data this cycle, skipping")
                else:
                    stored_count = await self._store_slots(slots)
                    logger.info(f"GridPollingScheduler: Stored {stored_count}/{len(slots)} capacity slot(s)")

            except Exception as e:
                logger.exception(f"Error in GridPollingScheduler: {e}")

            await asyncio.sleep(self.interval_seconds)

    async def _store_slots(self, slots: list) -> int:
        """Upsert each polled slot. One bad slot is logged and skipped rather
        than discarding the rest of the cycle's data."""
        stored_count = 0
        async with AsyncSessionLocal() as db:
            repository = EnergyAvailabilityRepository(db)
            for slot in slots:
                try:
                    slot_start_time = datetime.fromisoformat(slot["slot_start_time"])
                    slot_end_time = datetime.fromisoformat(slot["slot_end_time"])
                    await repository.upsert_supply(
                        provider_name=slot.get("provider_name") or DEFAULT_PROVIDER_NAME,
                        slot_start_time=slot_start_time,
                        slot_end_time=slot_end_time,
                        available_watts=float(slot["available_watts"]),
                        forecast_date=slot_start_time.date(),
                        location=slot.get("location"),
                        energy_source_type=slot.get("energy_source_type"),
                        confidence_percentage=slot.get("confidence_percentage"),
                    )
                    stored_count += 1
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"GridPollingScheduler: Skipping invalid slot {slot}: {e}")
        return stored_count

    def start(self):
        if not self._task:
            logger.info("GridPollingScheduler: Starting background task.")
            self._task = asyncio.create_task(self._run())
        else:
            logger.warning("GridPollingScheduler: Task already running")

    def stop(self):
        logger.info("GridPollingScheduler: Stopping background task.")
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
