"""
Services for EnergyAwareOrchestration Operator.

This package contains service layer logic including:
- Scheduler service (scheduling logic)
- Energy API client (optional, for integration)
"""

from app.services.scheduler import SimpleSchedulerService

__all__ = ["SimpleSchedulerService"]

