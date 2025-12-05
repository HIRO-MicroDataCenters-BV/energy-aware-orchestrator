"""
Pydantic models for EnergyAwareOrchestration CRD.

This module defines all the data models used in the EnergyAwareOrchestration
custom resource definition.
"""
from typing import Optional, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class Priority(str, Enum):
    """Priority levels for workload scheduling."""
    CRITICAL = "Critical"
    NON_CRITICAL = "NonCritical"
    OPTIONAL = "Optional"


class ApplicationRef(BaseModel):
    """Reference to the application."""
    name: str = Field(..., description="Name of the application")
    namespace: Optional[str] = Field(None, description="Target namespace for the application")


class EnergyAwareOrchestrationSpec(BaseModel):
    """Spec for EnergyAwareOrchestration resource."""
    energyConsumption: int = Field(
        ...,
        ge=0,
        description="Estimated energy consumption (arbitrary units, e.g. kWh)"
    )
    forecastWindowDays: int = Field(
        ...,
        ge=1,
        le=30,
        description="Number of days to forecast the execution schedule for."
    )
    priority: Priority = Field(
        default=Priority.NON_CRITICAL,
        description="Business priority of the workload. Used for scheduling and cost/energy optimisation."
    )
    applicationRef: ApplicationRef = Field(
        ...,
        description="Reference to the application"
    )


class TimeSlot(BaseModel):
    """Time slot for execution."""
    start: str = Field(..., description="Start time in HH:MM:SS format")
    stop: str = Field(..., description="Stop time in HH:MM:SS format")
    cost: float = Field(..., description="Energy cost for this time slot")


class DailySchedule(BaseModel):
    """Daily schedule entry."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    times: List[TimeSlot] = Field(..., description="List of time slots for this date")


class ExecutionSchedule(BaseModel):
    """Execution schedule with timestamp."""
    updated: Optional[datetime] = Field(None, description="UTC timestamp of the last schedule computation")
    schedule: Optional[List[DailySchedule]] = Field(None, description="List of per-day schedules")


class EnergyAwareOrchestrationStatus(BaseModel):
    """Status for EnergyAwareOrchestration resource."""
    executionSchedule: Optional[ExecutionSchedule] = Field(
        None,
        description="Computed execution schedule and last update timestamp"
    )
