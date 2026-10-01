"""
Grid Polling Scheduler
Periodically polls one or more configured grid sources (HTTP, Modbus, ...)
for live capacity data and stores it as supply rows in energy_availability.
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from app.db.database import AsyncSessionLocal
from app.repositories.energy_availability import EnergyAvailabilityRepository
from app.services.grid_clients.base import GridSourceClient

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER_NAME = "grid"


class GridPollingScheduler:
    """
    Background scheduler that polls every configured grid source for
    capacity data, once per interval.

    Takes an already-built list of GridSourceClient - HTTP, Modbus, or any
    future kind - rather than constructing one itself, so the choice of
    which sources are active lives entirely in config (see app/main.py).

    Failures (a source unreachable, a bad response, a single bad slot) are
    caught and logged per source - one bad source never stops the others
    from being polled, and the loop always sleeps and tries again next
    interval rather than stopping.
    """

    def __init__(self, clients: List[GridSourceClient], interval_seconds: int = 300):
        self.clients = clients
        self.interval_seconds = interval_seconds
        self._task = None
        self._running = False

    async def _run(self):
        self._running = True
        logger.info(
            f"GridPollingScheduler started, {len(self.clients)} source(s), "
            f"interval: {self.interval_seconds} seconds"
        )

        while self._running:
            for client in self.clients:
                try:
                    slots = await client.fetch_grid_capacity()

                    if not slots:
                        logger.debug(f"GridPollingScheduler: No capacity data from {client}, skipping")
                    else:
                        stored_count = await self._store_slots(slots)
                        logger.info(f"GridPollingScheduler: Stored {stored_count}/{len(slots)} capacity slot(s) from {client}")

                except Exception as e:
                    logger.exception(f"Error polling {client} in GridPollingScheduler: {e}")

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

    async def close_clients(self):
        for client in self.clients:
            try:
                await client.close()
            except Exception as e:
                logger.warning(f"GridPollingScheduler: error closing {client}: {e}")
