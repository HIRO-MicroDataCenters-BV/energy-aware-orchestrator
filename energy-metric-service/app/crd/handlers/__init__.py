"""
Operator handlers for EnergyAwareOrchestration custom resources.

This package contains modular handlers for:
- Scheduler operations
- Validation logic
- Status updates
- Event posting
"""

from .scheduler_handler import SchedulerHandler, get_scheduler_handler
from .validation_handler import ValidationHandler, ValidationError, get_validation_handler
from .status_handler import StatusHandler, get_status_handler
from .event_handler import EventHandler, get_event_handler

__all__ = [
    "SchedulerHandler",
    "ValidationHandler",
    "ValidationError",
    "StatusHandler",
    "EventHandler",
    "get_scheduler_handler",
    "get_validation_handler",
    "get_status_handler",
    "get_event_handler",
]
