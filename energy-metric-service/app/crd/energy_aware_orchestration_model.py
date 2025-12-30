"""
Pydantic models for EnergyAwareOrchestration CRD.

This module defines all the data models used in the EnergyAwareOrchestration
custom resource definition.

Time Slot Windows:
- Slot 1: 00:00 - 06:00 (midnight to 6am)
- Slot 2: 06:00 - 12:00 (6am to noon)
- Slot 3: 12:00 - 18:00 (noon to 6pm)
- Slot 4: 18:00 - 24:00 (6pm to midnight)
"""
from typing import Optional, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class Priority(str, Enum):
    """
    Priority levels for workload scheduling.

    - CRITICAL: Run immediately, always on (24/7)
    - PREFERRED: If energy insufficient, delay by 6 hours
    - OPTIONAL: Find best available slot in next 24 hours
    """
    CRITICAL = "Critical"
    PREFERRED = "Preferred"
    OPTIONAL = "Optional"


class Phase(str, Enum):
    """Phase of the EnergyAwareOrchestration lifecycle."""
    PENDING = "Pending"           # Waiting for scheduling
    SCHEDULED = "Scheduled"       # Schedule calculated, waiting for execution
    RUNNING = "Running"           # Workload is currently running
    COMPLETED = "Completed"       # Workload finished successfully
    FAILED = "Failed"             # Scheduling or execution failed


class Action(str, Enum):
    """Action recommended by the scheduler."""
    DEPLOY_IMMEDIATELY = "DeployImmediately"  # For Critical priority
    SCHEDULED = "Scheduled"                    # Scheduled for a specific slot
    DELAYED = "Delayed"                        # Delayed due to insufficient energy
    WAITING = "Waiting"                        # Waiting for energy availability


class ApplicationRef(BaseModel):
    """Reference to the application."""
    name: str = Field(..., description="Name of the application")
    namespace: Optional[str] = Field(None, description="Target namespace for the application")


class EnergyAwareOrchestrationSpec(BaseModel):
    """Spec for EnergyAwareOrchestration resource."""
    energyConsumption: int = Field(
        ...,
        ge=0,
        description="Estimated energy consumption in Watts"
    )
    forecastWindowDays: int = Field(
        ...,
        ge=1,
        le=30,
        description="Number of days to forecast the execution schedule for."
    )
    priority: Priority = Field(
        default=Priority.PREFERRED,
        description="Business priority of the workload. Used for scheduling and cost/energy optimisation."
    )
    applicationRef: ApplicationRef = Field(
        ...,
        description="Reference to the application"
    )


class ScheduledSlot(BaseModel):
    """
    A scheduled time slot for execution.
    
    Time slots are 6-hour windows:
    - Slot 1: 00:00 - 06:00
    - Slot 2: 06:00 - 12:00
    - Slot 3: 12:00 - 18:00
    - Slot 4: 18:00 - 24:00
    """
    slotNumber: int = Field(..., ge=1, le=4, description="Slot number (1-4)")
    slotStart: str = Field(..., description="Start time in ISO 8601 format")
    slotEnd: str = Field(..., description="End time in ISO 8601 format")
    availableEnergyWatts: Optional[float] = Field(None, description="Available energy in this slot (Watts)")
    requiredEnergyWatts: Optional[float] = Field(None, description="Required energy for workload (Watts)")
    confidencePercentage: Optional[float] = Field(None, description="Confidence level of energy forecast (0-100)")


class ScheduleDecision(BaseModel):
    """Decision made by the scheduler."""
    action: Action = Field(..., description="Recommended action")
    reason: str = Field(..., description="Human-readable explanation for the decision")
    scheduledSlot: Optional[ScheduledSlot] = Field(None, description="The scheduled time slot (if applicable)")
    nextEvaluationTime: Optional[str] = Field(None, description="When to re-evaluate the schedule (ISO 8601)")


class EnergyMetrics(BaseModel):
    """Energy metrics at the time of scheduling."""
    currentSlotAvailableWatts: Optional[float] = Field(None, description="Energy available in current slot")
    currentSlotConsumedWatts: Optional[float] = Field(None, description="Energy currently being consumed")
    requiredWatts: float = Field(..., description="Energy required by the workload")
    sufficient: bool = Field(..., description="Whether current energy is sufficient")


# Legacy models for backward compatibility
class TimeSlot(BaseModel):
    """Time slot for execution (legacy format)."""
    start: str = Field(..., description="Start time in HH:MM:SS format")
    stop: str = Field(..., description="Stop time in HH:MM:SS format")
    cost: float = Field(..., description="Energy cost for this time slot")


class DailySchedule(BaseModel):
    """Daily schedule entry (legacy format)."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    times: List[TimeSlot] = Field(..., description="List of time slots for this date")


class ExecutionSchedule(BaseModel):
    """Execution schedule with timestamp (legacy format)."""
    updated: Optional[datetime] = Field(None, description="UTC timestamp of the last schedule computation")
    schedule: Optional[List[DailySchedule]] = Field(None, description="List of per-day schedules")


class EnergyAwareOrchestrationStatus(BaseModel):
    """Status for EnergyAwareOrchestration resource."""
    phase: Phase = Field(
        default=Phase.PENDING,
        description="Current phase of the workload lifecycle"
    )
    decision: Optional[ScheduleDecision] = Field(
        None,
        description="Scheduling decision made by the operator"
    )
    energyMetrics: Optional[EnergyMetrics] = Field(
        None,
        description="Energy metrics at the time of scheduling"
    )
    lastUpdated: Optional[str] = Field(
        None,
        description="Timestamp of last status update (ISO 8601)"
    )
    # Legacy field for backward compatibility
    executionSchedule: Optional[ExecutionSchedule] = Field(
        None,
        description="Computed execution schedule (legacy format)"
    )
