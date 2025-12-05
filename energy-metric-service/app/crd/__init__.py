"""
CRD module for EnergyAwareOrchestration.

This module provides Pydantic models for the EnergyAwareOrchestration custom resource.

To generate CRD YAML, use:
    python -m app.crd.builder
    # or
    ./scripts/generate-crd.sh
"""

# Export models
from .energy_aware_orchestration_model import (
    Priority,
    ApplicationRef,
    EnergyAwareOrchestrationSpec,
    TimeSlot,
    DailySchedule,
    ExecutionSchedule,
    EnergyAwareOrchestrationStatus,
)

__all__ = [
    "Priority",
    "ApplicationRef",
    "EnergyAwareOrchestrationSpec",
    "TimeSlot",
    "DailySchedule",
    "ExecutionSchedule",
    "EnergyAwareOrchestrationStatus",
]
