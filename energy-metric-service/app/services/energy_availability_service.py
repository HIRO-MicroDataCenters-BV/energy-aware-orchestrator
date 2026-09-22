"""
Energy Availability Service
Provides business logic for calculating available energy based on time slots
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.energy_availability import EnergyAvailabilityRepository
from app.services.prometheus_metrics_service_v2 import PrometheusMetricsServiceV2

logger = logging.getLogger(__name__)


class EnergyAvailabilityService:
    """Service to calculate and manage energy availability"""

    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize the service.

        Args:
            db_session: Optional database session. If not provided, methods requiring DB will need it passed in.
        """
        self.db_session = db_session
        self.metrics_service = PrometheusMetricsServiceV2()

    async def get_current_time_slot_energy(
        self,
        db_session: Optional[AsyncSession] = None,
        provider_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get energy availability for the current time slot.

        Args:
            db_session: Database session to use (required if not set in constructor)
            provider_name: Optional filter by energy provider name

        Returns:
            Dictionary with current slot energy information:
            {
                "slot_found": bool,
                "slot_start_time": datetime,
                "slot_end_time": datetime,
                "available_watts": float,
                "guaranteed_minimum_watts": float,
                "potential_maximum_watts": float,
                "confidence_percentage": float,
                "provider_name": str,
                "energy_source_type": str
            }
        """
        try:
            session = db_session or self.db_session
            if not session:
                raise ValueError("Database session is required")

            repository = EnergyAvailabilityRepository(session)

            # Get current availability (slots that include current time)
            current_slots = await repository.get_current_availability(
                provider_name=provider_name,
                limit=1  # We only need the best available slot
            )

            if not current_slots:
                logger.warning("No energy availability slot found for current time")
                return {
                    "slot_found": False,
                    "available_watts": 0.0,
                    "guaranteed_minimum_watts": 0.0,
                    "potential_maximum_watts": 0.0,
                    "confidence_percentage": 0.0,
                    "reason": "No energy availability data for current time slot"
                }

            # Use the first (highest available_watts due to ordering in repository)
            slot = current_slots[0]

            return {
                "slot_found": True,
                "slot_start_time": slot.slot_start_time,
                "slot_end_time": slot.slot_end_time,
                "available_watts": float(slot.available_watts) if slot.available_watts else 0.0,
                "guaranteed_minimum_watts": float(slot.guaranteed_minimum_watts) if slot.guaranteed_minimum_watts else 0.0,
                "potential_maximum_watts": float(slot.potential_maximum_watts) if slot.potential_maximum_watts else 0.0,
                "confidence_percentage": float(slot.confidence_percentage) if slot.confidence_percentage else 0.0,
                "provider_name": slot.provider_name,
                "energy_source_type": slot.energy_source_type,
                "location": slot.location
            }

        except Exception as e:
            logger.error(f"Error getting current time slot energy: {e}")
            return {
                "slot_found": False,
                "available_watts": 0.0,
                "reason": f"Error: {str(e)}"
            }

    async def calculate_available_energy(
        self,
        db_session: Optional[AsyncSession] = None,
        provider_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate actual available energy by subtracting current K8s consumption
        from available energy in the current time slot.

        Args:
            db_session: Database session to use
            provider_name: Optional filter by energy provider name

        Returns:
            Dictionary with available energy calculation:
            {
                "total_available_watts": float (slot energy - current consumption),
                "slot_energy_watts": float (from energy availability),
                "current_consumption_watts": float (from K8s metrics),
                "slot_info": dict (time slot details),
                "node_consumption": dict (per-node energy consumption)
            }
        """
        try:
            # Get current time slot energy availability
            slot_info = await self.get_current_time_slot_energy(
                db_session=db_session,
                provider_name=provider_name
            )

            if not slot_info["slot_found"]:
                return {
                    "total_available_watts": 0.0,
                    "slot_energy_watts": 0.0,
                    "current_consumption_watts": 0.0,
                    "slot_info": slot_info,
                    "node_consumption": {},
                    "reason": slot_info.get("reason", "No energy slot available")
                }

            slot_energy = slot_info["available_watts"]

            # Get current K8s container energy consumption
            try:
                current_metrics = await self.metrics_service.scrape_and_transform_range(hours_back=1)
            except Exception as metrics_error:
                logger.warning(f"Failed to get metrics from Prometheus: {metrics_error}")
                current_metrics = []

            # Calculate total current consumption across all nodes
            total_consumption = 0.0
            node_consumption = {}

            if current_metrics:
                for metric in current_metrics:
                    if metric.energy_watts is not None:
                        total_consumption += metric.energy_watts
                        node_consumption[metric.node_name] = metric.energy_watts

            # Calculate available energy (slot energy - current consumption)
            available_energy = max(0.0, slot_energy - total_consumption)

            return {
                "total_available_watts": round(available_energy, 2),
                "slot_energy_watts": round(slot_energy, 2),
                "current_consumption_watts": round(total_consumption, 2),
                "slot_info": slot_info,
                "node_consumption": node_consumption,
                "confidence_percentage": slot_info.get("confidence_percentage", 0.0)
            }

        except Exception as e:
            logger.error(f"Error calculating available energy: {e}")
            return {
                "total_available_watts": 0.0,
                "slot_energy_watts": 0.0,
                "current_consumption_watts": 0.0,
                "reason": f"Error: {str(e)}"
            }

    async def check_energy_sufficient_for_deployment(
        self,
        required_energy_watts: float,
        db_session: Optional[AsyncSession] = None,
        provider_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if there is sufficient energy available for a deployment.

        Args:
            required_energy_watts: Required energy for the deployment
            db_session: Database session to use
            provider_name: Optional filter by energy provider name

        Returns:
            Dictionary with energy check result:
            {
                "sufficient": bool,
                "total_available_watts": float,
                "required_watts": float,
                "slot_energy_watts": float,
                "current_consumption_watts": float,
                "reason": str
            }
        """
        try:
            # Get available energy calculation
            energy_calc = await self.calculate_available_energy(
                db_session=db_session,
                provider_name=provider_name
            )

            available = energy_calc["total_available_watts"]
            sufficient = available >= required_energy_watts

            return {
                "sufficient": sufficient,
                "total_available_watts": available,
                "required_watts": required_energy_watts,
                "slot_energy_watts": energy_calc["slot_energy_watts"],
                "current_consumption_watts": energy_calc["current_consumption_watts"],
                "slot_info": energy_calc.get("slot_info", {}),
                "node_consumption": energy_calc.get("node_consumption", {}),
                "confidence_percentage": energy_calc.get("confidence_percentage", 0.0),
                "reason": (
                    f"Sufficient energy available: {available:.2f}W available, {required_energy_watts:.2f}W required"
                    if sufficient
                    else f"Insufficient energy: {available:.2f}W available, {required_energy_watts:.2f}W required (shortfall: {required_energy_watts - available:.2f}W)"
                )
            }

        except Exception as e:
            logger.error(f"Error checking energy sufficiency: {e}")
            return {
                "sufficient": False,
                "reason": f"Error checking energy: {str(e)}"
            }
