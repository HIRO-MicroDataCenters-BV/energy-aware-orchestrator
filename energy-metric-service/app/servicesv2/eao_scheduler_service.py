"""
EnergyAwareOrchestration Scheduler Service

This service implements the scheduling logic for EAO resources based on:
- Workload priority (Critical, NonCritical, Optional)
- Energy availability in time slots
- 6-hour time windows

Time Slot Windows (daily):
- Slot 1: 00:00 - 06:00 (midnight to 6am)
- Slot 2: 06:00 - 12:00 (6am to noon)
- Slot 3: 12:00 - 18:00 (noon to 6pm)
- Slot 4: 18:00 - 24:00 (6pm to midnight)

Scheduling Logic by Priority:
- Critical: Deploy immediately (always on, 24/7)
- NonCritical: If energy insufficient, delay by 6 hours (next slot)
- Optional: Find best available slot in next 24 hours based on energy availability
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.energy_availability import EnergyAvailabilityRepository
from app.servicesv2.energy_availability_service import EnergyAvailabilityService

logger = logging.getLogger(__name__)


# Time slot boundaries (hour of day)
SLOT_BOUNDARIES = [
    (0, 6),    # Slot 1: 00:00 - 06:00
    (6, 12),   # Slot 2: 06:00 - 12:00
    (12, 18),  # Slot 3: 12:00 - 18:00
    (18, 24),  # Slot 4: 18:00 - 24:00
]

SLOT_DURATION_HOURS = 6


class Priority(str, Enum):
    """Priority levels for workload scheduling."""
    CRITICAL = "Critical"
    NON_CRITICAL = "NonCritical"
    OPTIONAL = "Optional"


class Action(str, Enum):
    """Action recommended by the scheduler."""
    DEPLOY_IMMEDIATELY = "DeployImmediately"
    SCHEDULED = "Scheduled"
    DELAYED = "Delayed"
    WAITING = "Waiting"


@dataclass
class TimeSlotInfo:
    """Information about a time slot."""
    slot_number: int  # 1-4
    start_time: datetime
    end_time: datetime
    available_energy_watts: Optional[float] = None
    confidence_percentage: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "slotNumber": self.slot_number,
            "slotStart": self.start_time.isoformat(),
            "slotEnd": self.end_time.isoformat(),
            "availableEnergyWatts": self.available_energy_watts,
            "confidencePercentage": self.confidence_percentage,
        }


@dataclass
class ScheduleDecision:
    """Decision made by the scheduler."""
    action: Action
    reason: str
    scheduled_slot: Optional[TimeSlotInfo] = None
    next_evaluation_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "action": self.action.value,
            "reason": self.reason,
        }
        if self.scheduled_slot:
            result["scheduledSlot"] = self.scheduled_slot.to_dict()
        if self.next_evaluation_time:
            result["nextEvaluationTime"] = self.next_evaluation_time.isoformat()
        return result


@dataclass
class EnergyMetrics:
    """Energy metrics at the time of scheduling."""
    current_slot_available_watts: Optional[float]
    current_slot_consumed_watts: Optional[float]
    required_watts: float
    sufficient: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "currentSlotAvailableWatts": self.current_slot_available_watts,
            "currentSlotConsumedWatts": self.current_slot_consumed_watts,
            "requiredWatts": self.required_watts,
            "sufficient": self.sufficient,
        }


@dataclass
class ScheduleResult:
    """Complete result from the scheduler."""
    phase: str
    decision: ScheduleDecision
    energy_metrics: EnergyMetrics
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "decision": self.decision.to_dict(),
            "energyMetrics": self.energy_metrics.to_dict(),
            "lastUpdated": self.timestamp.isoformat(),
        }


class EAOSchedulerService:
    """
    Service for calculating execution schedules for EnergyAwareOrchestration resources.
    
    This service implements the core scheduling logic that determines when
    workloads should run based on their priority and energy availability.
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize the scheduler service.
        
        Args:
            db_session: Optional database session for energy availability queries.
        """
        self.db_session = db_session
        self._energy_service: Optional[EnergyAvailabilityService] = None
    
    @property
    def energy_service(self) -> EnergyAvailabilityService:
        """Get or create the energy availability service."""
        if self._energy_service is None:
            self._energy_service = EnergyAvailabilityService(self.db_session)
        return self._energy_service
    
    def get_current_slot_number(self, now: Optional[datetime] = None) -> int:
        """
        Get the current time slot number (1-4).
        
        Args:
            now: Current time (defaults to UTC now)
            
        Returns:
            Slot number (1-4)
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        hour = now.hour
        for i, (start, end) in enumerate(SLOT_BOUNDARIES, 1):
            if start <= hour < end:
                return i
        return 4  # Default to last slot
    
    def get_slot_times(self, slot_number: int, date: datetime) -> tuple[datetime, datetime]:
        """
        Get the start and end times for a specific slot on a given date.
        
        Args:
            slot_number: Slot number (1-4)
            date: The date for which to get slot times
            
        Returns:
            Tuple of (start_time, end_time)
        """
        start_hour, end_hour = SLOT_BOUNDARIES[slot_number - 1]
        
        start_time = date.replace(
            hour=start_hour, minute=0, second=0, microsecond=0,
            tzinfo=timezone.utc
        )
        
        if end_hour == 24:
            # End time is midnight of the next day
            end_time = (date + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0,
                tzinfo=timezone.utc
            )
        else:
            end_time = date.replace(
                hour=end_hour, minute=0, second=0, microsecond=0,
                tzinfo=timezone.utc
            )
        
        return start_time, end_time
    
    def get_next_24h_slots(self, now: Optional[datetime] = None) -> List[TimeSlotInfo]:
        """
        Get all time slots in the next 24 hours.
        
        Args:
            now: Current time (defaults to UTC now)
            
        Returns:
            List of TimeSlotInfo objects for the next 24 hours
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        slots = []
        current_slot = self.get_current_slot_number(now)
        current_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Start from current slot
        for i in range(4):  # 4 slots = 24 hours
            slot_num = ((current_slot - 1 + i) % 4) + 1
            
            # Determine the date for this slot
            if current_slot + i <= 4:
                slot_date = current_date
            else:
                slot_date = current_date + timedelta(days=1)
            
            start_time, end_time = self.get_slot_times(slot_num, slot_date)
            
            # Skip slots that have already passed
            if end_time <= now:
                continue
            
            slots.append(TimeSlotInfo(
                slot_number=slot_num,
                start_time=start_time,
                end_time=end_time
            ))
        
        return slots
    
    def get_next_slot(self, now: Optional[datetime] = None) -> TimeSlotInfo:
        """
        Get the next time slot (6 hours from now).
        
        Args:
            now: Current time (defaults to UTC now)
            
        Returns:
            TimeSlotInfo for the next slot
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        current_slot = self.get_current_slot_number(now)
        next_slot_num = (current_slot % 4) + 1
        
        # Determine date
        current_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if next_slot_num <= current_slot:
            # Next slot is tomorrow
            slot_date = current_date + timedelta(days=1)
        else:
            slot_date = current_date
        
        start_time, end_time = self.get_slot_times(next_slot_num, slot_date)
        
        return TimeSlotInfo(
            slot_number=next_slot_num,
            start_time=start_time,
            end_time=end_time
        )
    
    async def get_energy_for_slot(
        self,
        slot: TimeSlotInfo,
        db_session: Optional[AsyncSession] = None
    ) -> TimeSlotInfo:
        """
        Enrich a slot with energy availability data.
        
        Args:
            slot: The time slot to enrich
            db_session: Database session for queries
            
        Returns:
            TimeSlotInfo with energy data populated
        """
        session = db_session or self.db_session
        if not session:
            logger.warning("No database session available for energy query")
            return slot
        
        try:
            repository = EnergyAvailabilityRepository(session)
            
            # Get energy availability for this time slot
            availability = await repository.get_all(
                start_time=slot.start_time,
                end_time=slot.end_time,
                is_active=True,
                limit=1,
                order_by="available_watts",
                order_direction="desc"
            )
            
            if availability:
                slot.available_energy_watts = float(availability[0].available_watts)
                slot.confidence_percentage = float(availability[0].confidence_percentage or 0)
            else:
                # No energy data - set to 0
                slot.available_energy_watts = 0.0
                slot.confidence_percentage = 0.0
                
        except Exception as e:
            logger.error(f"Error getting energy for slot {slot.slot_number}: {e}")
            slot.available_energy_watts = None
            slot.confidence_percentage = None
        
        return slot
    
    async def calculate_schedule(
        self,
        priority: str,
        required_energy_watts: float,
        db_session: Optional[AsyncSession] = None
    ) -> ScheduleResult:
        """
        Calculate the execution schedule for a workload.
        
        This is the main scheduling method that implements the logic:
        - Critical: Deploy immediately
        - NonCritical: Check current energy, delay 6h if insufficient
        - Optional: Find best slot in next 24 hours
        
        Args:
            priority: Workload priority (Critical, NonCritical, Optional)
            required_energy_watts: Energy required by the workload in Watts
            db_session: Database session for energy queries
            
        Returns:
            ScheduleResult with decision and energy metrics
        """
        now = datetime.now(timezone.utc)
        session = db_session or self.db_session
        
        # Get current energy availability
        current_energy = await self._get_current_energy(session)
        
        available_watts = current_energy.get("available_watts")
        # Handle None values - treat as 0 for comparison
        available_for_comparison = available_watts if available_watts is not None else 0.0
        
        energy_metrics = EnergyMetrics(
            current_slot_available_watts=available_watts,
            current_slot_consumed_watts=current_energy.get("consumed_watts"),
            required_watts=required_energy_watts,
            sufficient=available_for_comparison >= required_energy_watts
        )
        
        # Priority-based scheduling
        if priority == Priority.CRITICAL.value:
            return self._schedule_critical(now, energy_metrics)
        
        elif priority == Priority.NON_CRITICAL.value:
            return await self._schedule_non_critical(now, energy_metrics, session)
        
        elif priority == Priority.OPTIONAL.value:
            return await self._schedule_optional(now, energy_metrics, required_energy_watts, session)
        
        else:
            # Unknown priority - treat as NonCritical
            logger.warning(f"Unknown priority '{priority}', treating as NonCritical")
            return await self._schedule_non_critical(now, energy_metrics, session)
    
    async def _get_current_energy(self, db_session: Optional[AsyncSession]) -> Dict[str, Any]:
        """Get current energy availability."""
        if not db_session:
            return {"available_watts": None, "consumed_watts": None}
        
        try:
            energy_service = EnergyAvailabilityService(db_session)
            result = await energy_service.calculate_available_energy(db_session=db_session)
            
            return {
                "available_watts": result.get("total_available_watts", 0),
                "consumed_watts": result.get("current_consumption_watts", 0),
            }
        except Exception as e:
            logger.error(f"Error getting current energy: {e}")
            return {"available_watts": None, "consumed_watts": None}
    
    def _schedule_critical(
        self,
        now: datetime,
        energy_metrics: EnergyMetrics
    ) -> ScheduleResult:
        """
        Schedule a Critical priority workload.
        
        Critical workloads are deployed immediately, regardless of energy availability.
        They run 24/7.
        """
        logger.info("Scheduling Critical workload: DEPLOY_IMMEDIATELY")
        
        current_slot_num = self.get_current_slot_number(now)
        start_time, end_time = self.get_slot_times(
            current_slot_num,
            now.replace(hour=0, minute=0, second=0, microsecond=0)
        )
        
        current_slot = TimeSlotInfo(
            slot_number=current_slot_num,
            start_time=start_time,
            end_time=end_time,
            available_energy_watts=energy_metrics.current_slot_available_watts,
        )
        
        decision = ScheduleDecision(
            action=Action.DEPLOY_IMMEDIATELY,
            reason="Critical priority workload - deploy immediately (24/7 operation)",
            scheduled_slot=current_slot,
        )
        
        return ScheduleResult(
            phase="Scheduled",
            decision=decision,
            energy_metrics=energy_metrics,
            timestamp=now
        )
    
    async def _schedule_non_critical(
        self,
        now: datetime,
        energy_metrics: EnergyMetrics,
        db_session: Optional[AsyncSession]
    ) -> ScheduleResult:
        """
        Schedule a NonCritical priority workload.
        
        If energy is sufficient: deploy now
        If energy is insufficient: delay by 6 hours (next slot)
        """
        if energy_metrics.sufficient:
            logger.info("Scheduling NonCritical workload: energy sufficient, deploy now")
            
            current_slot_num = self.get_current_slot_number(now)
            start_time, end_time = self.get_slot_times(
                current_slot_num,
                now.replace(hour=0, minute=0, second=0, microsecond=0)
            )
            
            current_slot = TimeSlotInfo(
                slot_number=current_slot_num,
                start_time=start_time,
                end_time=end_time,
                available_energy_watts=energy_metrics.current_slot_available_watts,
            )
            
            decision = ScheduleDecision(
                action=Action.SCHEDULED,
                reason=f"NonCritical workload - energy sufficient ({energy_metrics.current_slot_available_watts:.0f}W available, {energy_metrics.required_watts:.0f}W required)",
                scheduled_slot=current_slot,
            )
            
            return ScheduleResult(
                phase="Scheduled",
                decision=decision,
                energy_metrics=energy_metrics,
                timestamp=now
            )
        else:
            # Delay by 6 hours
            logger.info("Scheduling NonCritical workload: energy insufficient, delaying 6 hours")
            
            next_slot = self.get_next_slot(now)
            next_slot = await self.get_energy_for_slot(next_slot, db_session)
            next_slot.requiredEnergyWatts = energy_metrics.required_watts
            
            decision = ScheduleDecision(
                action=Action.DELAYED,
                reason=f"NonCritical workload - insufficient energy ({energy_metrics.current_slot_available_watts or 0:.0f}W available, {energy_metrics.required_watts:.0f}W required). Delayed to next slot.",
                scheduled_slot=next_slot,
                next_evaluation_time=next_slot.start_time,
            )
            
            return ScheduleResult(
                phase="Scheduled",
                decision=decision,
                energy_metrics=energy_metrics,
                timestamp=now
            )
    
    async def _schedule_optional(
        self,
        now: datetime,
        energy_metrics: EnergyMetrics,
        required_energy_watts: float,
        db_session: Optional[AsyncSession]
    ) -> ScheduleResult:
        """
        Schedule an Optional priority workload.
        
        Find the best available slot in the next 24 hours based on energy availability.
        """
        logger.info("Scheduling Optional workload: finding best slot in next 24 hours")
        
        # Get all slots in next 24 hours
        slots = self.get_next_24h_slots(now)
        
        # Enrich with energy data
        enriched_slots = []
        for slot in slots:
            enriched_slot = await self.get_energy_for_slot(slot, db_session)
            enriched_slots.append(enriched_slot)
        
        # Find the best slot (most available energy that meets requirement)
        best_slot: Optional[TimeSlotInfo] = None
        best_available_energy = -1.0
        
        # First, try to find a slot with sufficient energy
        for slot in enriched_slots:
            available = slot.available_energy_watts or 0
            if available >= required_energy_watts and available > best_available_energy:
                best_slot = slot
                best_available_energy = available
        
        # If no slot has sufficient energy, pick the one with most energy
        if best_slot is None:
            for slot in enriched_slots:
                available = slot.available_energy_watts or 0
                if available > best_available_energy:
                    best_slot = slot
                    best_available_energy = available
        
        # If still no slot found, use the first available slot
        if best_slot is None and enriched_slots:
            best_slot = enriched_slots[0]
            best_available_energy = best_slot.available_energy_watts or 0
        
        if best_slot is None:
            # No slots available at all
            decision = ScheduleDecision(
                action=Action.WAITING,
                reason="Optional workload - no time slots available in next 24 hours",
                next_evaluation_time=now + timedelta(hours=6),
            )
            
            return ScheduleResult(
                phase="Pending",
                decision=decision,
                energy_metrics=energy_metrics,
                timestamp=now
            )
        
        # Check if the best slot has sufficient energy
        if best_available_energy >= required_energy_watts:
            decision = ScheduleDecision(
                action=Action.SCHEDULED,
                reason=f"Optional workload - best slot found with sufficient energy ({best_available_energy:.0f}W available, {required_energy_watts:.0f}W required)",
                scheduled_slot=best_slot,
            )
        else:
            decision = ScheduleDecision(
                action=Action.SCHEDULED,
                reason=f"Optional workload - scheduled in best available slot ({best_available_energy:.0f}W available, {required_energy_watts:.0f}W required - may need partial execution)",
                scheduled_slot=best_slot,
                next_evaluation_time=best_slot.start_time,
            )
        
        return ScheduleResult(
            phase="Scheduled",
            decision=decision,
            energy_metrics=energy_metrics,
            timestamp=now
        )


# Singleton instance for use in operator
_scheduler_instance: Optional[EAOSchedulerService] = None


def get_scheduler_service(db_session: Optional[AsyncSession] = None) -> EAOSchedulerService:
    """
    Get the scheduler service instance.
    
    Args:
        db_session: Database session for energy queries
        
    Returns:
        EAOSchedulerService instance
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = EAOSchedulerService(db_session)
    elif db_session is not None:
        _scheduler_instance.db_session = db_session
    return _scheduler_instance

