# Operator Architecture

## Overview

The EnergyAwareOrchestration operator has been modularized into separate, focused handler modules for better maintainability, testability, and separation of concerns.

## Architecture

```
app/crd/
├── operator.py                  # Main operator with Kopf handlers
└── handlers/                    # Modular handler components
    ├── __init__.py
    ├── scheduler_handler.py     # Scheduling logic wrapper
    ├── validation_handler.py    # CR validation
    ├── status_handler.py        # Status patch building
    └── event_handler.py         # Kubernetes event posting
```

## Handler Modules

### 1. SchedulerHandler (`scheduler_handler.py`)

**Purpose**: Wraps the `EAOSchedulerService` for use in the operator context.

**Key Features**:
- Async interface compatible with Kopf's event loop
- Avoids database session conflicts
- Singleton pattern for resource efficiency

**Usage**:
```python
from app.crd.handlers import get_scheduler_handler

scheduler = get_scheduler_handler()
result = await scheduler.calculate_schedule(priority="Critical", energy_consumption=100)
```

**Methods**:
- `calculate_schedule(priority, energy_consumption)` → Returns `ScheduleResult` or `None`
- `reset()` → Resets the scheduler instance

### 2. ValidationHandler (`validation_handler.py`)

**Purpose**: Validates and extracts fields from CR specifications.

**Key Features**:
- Centralized validation logic
- Custom `ValidationError` exception
- Type coercion and defaults
- Field extraction utilities

**Usage**:
```python
from app.crd.handlers import get_validation_handler, ValidationError

validator = get_validation_handler()

try:
    spec_data = validator.validate_and_extract_spec(spec, namespace)
    # Returns: {energy_consumption, priority, app_name, app_namespace, ...}
except ValidationError as e:
    # Handle validation failure
    print(f"Field '{e.field}' failed: {e.message}")
```

**Methods**:
- `validate_and_extract_spec(spec, namespace)` → Validates and returns extracted fields
- `validate_spec_quick(spec)` → Quick validation check
- `extract_spec_field(spec, field, default)` → Safe field extraction

**Validations**:
- ✓ `applicationRef.name` is required
- ✓ `energyConsumption` is non-negative
- ✓ `priority` is one of: Critical, Preferred, Optional
- ✓ `forecastWindowDays` is between 1-30

### 3. StatusHandler (`status_handler.py`)

**Purpose**: Builds status patches and applies them to CRs.

**Key Features**:
- Status patch builders for different scenarios
- Logging of scheduling decisions
- Clean separation of status logic

**Usage**:
```python
from app.crd.handlers import get_status_handler

status = get_status_handler()

# Build from schedule result
status_patch = status.build_status_from_schedule(schedule_result)

# Apply to CR
status.apply_status_patch(patch, status_patch)

# Log decision
status.log_schedule_decision(name, schedule_result)
```

**Methods**:
- `build_status_from_schedule(schedule_result)` → Build from successful scheduling
- `build_failure_status(reason, error)` → Build for scheduling failures
- `build_validation_failure_status(field, message)` → Build for validation errors
- `apply_status_patch(patch, status_update)` → Apply status to CR
- `log_schedule_decision(name, schedule_result)` → Log decision for observability

### 4. EventHandler (`event_handler.py`)

**Purpose**: Posts Kubernetes events for observability.

**Key Features**:
- Safe event posting with error handling
- Predefined event types for common scenarios
- Consistent event formatting

**Usage**:
```python
from app.crd.handlers import get_event_handler

events = get_event_handler()

# Post scheduling started
events.post_scheduling_started(body, name, priority, energy_consumption)

# Post completion
events.post_scheduling_completed(body, schedule_result)

# Post error
events.post_error(body, error_message)
```

**Methods**:
- `post_event_safe(body, type, reason, message)` → Generic event posting
- `post_scheduling_started(...)` → "Scheduling" event
- `post_scheduling_completed(...)` → "Scheduled" event
- `post_scheduling_failed(...)` → "SchedulingFailed" event
- `post_validation_failed(...)` → "ValidationFailed" event
- `post_error(...)` → "Error" event
- `post_deletion(...)` → "Deleting" event
- `post_periodic_reevaluation(...)` → "Reevaluating" event

## Operator Flow

### Main Reconciliation (`reconcile_handler`)

```python
1. Get handler instances (singleton)
   ├── ValidationHandler
   ├── SchedulerHandler
   ├── StatusHandler
   └── EventHandler

2. Validate CR spec
   ├── Extract fields
   ├── Validate constraints
   └── Handle ValidationError → Post event, update status, raise PermanentError

3. Post "Scheduling" event

4. Calculate schedule
   ├── Call scheduler.calculate_schedule()
   └── Handle result:
       ├── Success → Build status, apply patch, log, post event
       └── Failure → Build failure status, post error event

5. Handle exceptions
   └── TemporaryError with 60s retry delay
```

### Deletion Handler (`deletion_handler`)

```python
1. Get EventHandler
2. Post "Deleting" event
3. Perform cleanup (if needed)
```

### Periodic Reconciliation (`periodic_reconcile`)

```python
1. Check if phase is "Completed" → skip
2. Get handler instances
3. Extract spec fields (no validation needed)
4. Post "Reevaluating" event
5. Calculate schedule
6. Update status if decision changed
```

## Benefits of Modularization

### 1. **Separation of Concerns**
- Each handler has a single, well-defined responsibility
- Easier to understand and reason about

### 2. **Testability**
- Each handler can be unit tested independently
- Mock handlers for operator testing

### 3. **Maintainability**
- Changes to validation logic → only touch `validation_handler.py`
- Changes to event formatting → only touch `event_handler.py`
- Reduced file size and complexity

### 4. **Reusability**
- Handlers can be used in other contexts (CLI tools, tests, etc.)
- Singleton pattern ensures consistent behavior

### 5. **Type Safety**
- Clear interfaces and return types
- Better IDE support and autocomplete

## Testing the Modularized Operator

### Unit Testing Individual Handlers

```python
# Test scheduler handler
from app.crd.handlers import SchedulerHandler

async def test_scheduler():
    handler = SchedulerHandler()
    result = await handler.calculate_schedule("Critical", 100)
    assert result is not None
    assert result.decision.action.value == "DeployImmediately"

# Test validation handler
from app.crd.handlers import ValidationHandler, ValidationError
import pytest

def test_validation():
    validator = ValidationHandler()

    # Valid spec
    spec = {
        "energyConsumption": 100,
        "priority": "Critical",
        "applicationRef": {"name": "test-app"}
    }
    result = validator.validate_and_extract_spec(spec, "default")
    assert result["app_name"] == "test-app"

    # Invalid spec
    invalid_spec = {"applicationRef": {}}  # Missing name
    with pytest.raises(ValidationError) as exc:
        validator.validate_and_extract_spec(invalid_spec, "default")
    assert "name is required" in str(exc.value)

# Test status handler
from app.crd.handlers import StatusHandler

def test_status_builder():
    status = StatusHandler()

    # Build failure status
    failure = status.build_failure_status("Test failure")
    assert failure["phase"] == "Failed"
    assert "Test failure" in failure["decision"]["reason"]

# Test event handler
from app.crd.handlers import EventHandler

def test_event_posting():
    events = EventHandler()

    # Mock body
    body = {"metadata": {"name": "test", "namespace": "default"}}

    # This will attempt to post - in tests, mock kopf.event
    # success = events.post_scheduling_started(body, "test", "Critical", 100)
```

### Integration Testing

```bash
# Run operator locally
kopf run app/crd/operator.py --verbose

# Apply test CR
kubectl apply -f sample_deployments/sample-cr-eao.yaml

# Watch for events
kubectl get events -w --field-selector involvedObject.kind=EnergyAwareOrchestration

# Check CR status
kubectl get eao ml-training-job -o yaml
```

## Migration Guide

### Before (Monolithic)

```python
# All logic in operator.py
def _calculate_schedule_async(...):
    # 30 lines of scheduling logic
    pass

def _extract_spec_field(...):
    # Field extraction
    pass

def _build_status_patch(...):
    # Status building
    pass

@kopf.on.create(...)
async def reconcile_handler(...):
    # 100+ lines mixing validation, scheduling, status, events
    pass
```

### After (Modularized)

```python
# operator.py - Clean and focused
from app.crd.handlers import (
    get_scheduler_handler,
    get_validation_handler,
    get_status_handler,
    get_event_handler,
)

@kopf.on.create(...)
async def reconcile_handler(...):
    # Get handlers
    validator = get_validation_handler()
    scheduler = get_scheduler_handler()
    status = get_status_handler()
    events = get_event_handler()

    # Clear workflow
    validated = validator.validate_and_extract_spec(spec, namespace)
    events.post_scheduling_started(...)
    result = await scheduler.calculate_schedule(...)
    status.apply_status_patch(...)
    events.post_scheduling_completed(...)
```

## File Size Comparison

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| operator.py | 329 lines | 264 lines | **20% smaller** |
| **Total** | 329 lines | 543 lines* | Better organized |

*Includes 4 new handler modules with comprehensive documentation

## Future Enhancements

1. **Add handler tests**: Create `tests/handlers/` with unit tests
2. **Metrics handler**: Separate module for collecting operator metrics
3. **Deployment handler**: Module to actually deploy/scale workloads
4. **Configuration handler**: Centralized operator configuration
5. **Webhook handler**: Admission webhook for CR validation

## Summary

The modularized architecture provides:
- ✅ Clean separation of concerns
- ✅ Easy to test and maintain
- ✅ Reusable components
- ✅ Better error handling
- ✅ Improved observability
- ✅ Simpler operator.py (20% reduction)

Each handler is a focused, single-purpose module that can be independently tested, modified, and reused.
