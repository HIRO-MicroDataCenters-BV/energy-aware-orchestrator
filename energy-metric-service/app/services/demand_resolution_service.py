"""
Demand Resolution
Resolves the best-known current energy demand for a workload.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.container_power_metrics import ContainerPowerMetricsRepository
from app.services.energy_forecasting_service import EnergyForecastingService

logger = logging.getLogger(__name__)


async def resolve_demand_watts(
    db: AsyncSession,
    application_name: Optional[str],
    namespace: str,
    fallback_watts: float,
) -> float:
    """
    Best-known current demand for a workload, in watts. Tiers, most
    accurate first:

    1. Measured - actual Kepler-measured wattage for the workload's pods.
       Treated as unavailable if it sums to 0 - Kepler attributes
       container power proportionally to CPU usage, so an idle pod
       measures as exactly 0W, which is a true "not currently drawing
       power" reading but a useless signal for a workload that may spike
       or that this row represents a future-scheduled slot for - falling
       through lets prediction/fallback supply a non-degenerate estimate.
    2. Predicted - the ML model's estimate from the workload's live
       CPU/memory utilization, used only when direct measurement is
       momentarily unavailable (e.g. a scrape gap).
    3. Fallback - the operator-provided static estimate
       (spec.energyConsumption), used before deployment (no utilization
       data can exist yet) or when neither of the above has any data.

    Never raises - any failure in tiers 1-2 falls through to the fallback,
    since resolving demand must never block a demand report from being
    stored.
    """
    if not application_name:
        return fallback_watts

    try:
        repository = ContainerPowerMetricsRepository(db)

        measured = await repository.get_latest_measured_watts(application_name, namespace)
        if measured is not None and measured > 0:
            return measured

        utilization = await repository.get_latest_utilization(application_name, namespace)
        if utilization is not None:
            try:
                service = EnergyForecastingService.get_instance()
                prediction = service.predict_single(
                    cpu_utilization=utilization["cpu_utilization_percent"],
                    memory_utilization=utilization["memory_utilization_percent"],
                )
                return float(prediction["predicted_energy_watts"])
            except Exception as e:
                logger.warning(f"ML demand prediction failed for '{application_name}/{namespace}', falling back: {e}")

    except Exception as e:
        logger.warning(f"Demand resolution failed for '{application_name}/{namespace}', falling back: {e}")

    return fallback_watts
