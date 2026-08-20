"""
Forecasting Scheduler
Periodically predicts future supply slots from historical real supply data,
giving the scheduler a sensible answer for slots beyond what live grid
polling has reached yet.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.db.database import AsyncSessionLocal
from app.repositories.energy_availability import EnergyAvailabilityRepository
from app.services.prediction_service import PredictionService

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 14
LOOKAHEAD_SLOTS = 8  # 8 * 6h = 2 days
SLOT_HOURS = 6


def _future_slot_boundaries(count: int = LOOKAHEAD_SLOTS) -> list:
    """Next `count` fixed 6-hour slots from the current slot boundary,
    matching the scheduler's own 0/6/12/18 boundaries."""
    now = datetime.now(timezone.utc)
    aligned_hour = (now.hour // SLOT_HOURS) * SLOT_HOURS
    slot_start = now.replace(hour=aligned_hour, minute=0, second=0, microsecond=0)
    slots = []
    for i in range(count):
        start = slot_start + timedelta(hours=SLOT_HOURS * i)
        end = start + timedelta(hours=SLOT_HOURS)
        slots.append((start, end))
    return slots


class ForecastingScheduler:
    """
    Background scheduler that refreshes predicted supply slots.

    Failures (bad history for one provider, a prediction error) are caught
    and logged per provider - one bad provider doesn't stop the rest of the
    cycle, and the loop always sleeps and tries again on the next interval
    rather than stopping.
    """

    def __init__(self, interval_seconds: int = 1800):
        self.interval_seconds = interval_seconds
        self.prediction_service = PredictionService()
        self._task = None
        self._running = False

    async def _run(self):
        self._running = True
        logger.info(f"ForecastingScheduler started, interval: {self.interval_seconds} seconds")

        while self._running:
            try:
                stored_count = await self._refresh_predictions()
                logger.info(f"ForecastingScheduler: Refreshed {stored_count} predicted slot(s)")
            except Exception as e:
                logger.exception(f"Error in ForecastingScheduler: {e}")

            await asyncio.sleep(self.interval_seconds)

    async def _refresh_predictions(self) -> int:
        stored_count = 0
        async with AsyncSessionLocal() as db:
            repository = EnergyAvailabilityRepository(db)
            providers = await repository.get_distinct_real_supply_providers()

            if not providers:
                logger.debug("ForecastingScheduler: No real supply history yet, nothing to predict from")
                return 0

            future_slots = _future_slot_boundaries()

            for provider_name in providers:
                try:
                    history_rows = await repository.get_supply_history(provider_name, lookback_days=LOOKBACK_DAYS)
                    history = [
                        {"slot_start_time": row.slot_start_time, "available_watts": float(row.available_watts)}
                        for row in history_rows
                    ]
                    predictions = self.prediction_service.predict(history, future_slots)

                    for prediction in predictions:
                        await repository.upsert_predicted_supply(
                            provider_name=provider_name,
                            slot_start_time=prediction["slot_start_time"],
                            slot_end_time=prediction["slot_end_time"],
                            available_watts=prediction["available_watts"],
                            forecast_date=prediction["slot_start_time"].date(),
                        )
                        stored_count += 1
                except Exception as e:
                    logger.warning(f"ForecastingScheduler: Skipping provider '{provider_name}' due to an error: {e}")

        return stored_count

    def start(self):
        if not self._task:
            logger.info("ForecastingScheduler: Starting background task.")
            self._task = asyncio.create_task(self._run())
        else:
            logger.warning("ForecastingScheduler: Task already running")

    def stop(self):
        logger.info("ForecastingScheduler: Stopping background task.")
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
