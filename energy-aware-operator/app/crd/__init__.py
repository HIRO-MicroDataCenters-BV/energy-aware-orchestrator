"""
CRD Models and Builder for EnergyAwareOrchestration.

This package contains:
- Pydantic models for the CRD specification and status
- CRD builder that generates Kubernetes CRD YAML
"""

from app.crd.models import (
    Action,
    ApplicationRef,
    EnergyAwareOrchestrationSpec,
    EnergyAwareOrchestrationStatus,
    EnergyMetrics,
    Phase,
    Priority,
    ScheduleDecision,
    ScheduledSlot,
)

__all__ = [
    "Action",
    "ApplicationRef",
    "EnergyAwareOrchestrationSpec",
    "EnergyAwareOrchestrationStatus",
    "EnergyMetrics",
    "Phase",
    "Priority",
    "ScheduleDecision",
    "ScheduledSlot",
]

