"""
Handlers for EnergyAwareOrchestration Operator.

This package contains modular handlers for:
- Validation logic
- Event posting
- Status updates
- Scheduler operations (stub - integrates with external service)
"""

from app.handlers.event import EventHandler, get_event_handler
from app.handlers.status import StatusHandler, get_status_handler
from app.handlers.validation import (
    ValidationError,
    ValidationHandler,
    get_validation_handler,
)

__all__ = [
    "EventHandler",
    "StatusHandler",
    "ValidationError",
    "ValidationHandler",
    "get_event_handler",
    "get_status_handler",
    "get_validation_handler",
]

