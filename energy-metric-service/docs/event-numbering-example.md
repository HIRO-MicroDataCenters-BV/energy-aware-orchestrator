# Event Numbering in Kubernetes

## Overview

The operator now automatically numbers all Kubernetes events to make it easier to track the sequence of operations.

## How It Works

**Event Counter:**
- Resets to 0 at the start of each reconciliation
- Increments with each event posted
- Events are numbered [Event 1], [Event 2], etc.

**Example Reconciliation:**

```
[Event 1] Calculating schedule for 'ml-training-job' (Priority: Preferred, Energy: 500W)
[Event 2] Scheduled: Preferred workload - energy sufficient (800W available, 500W required)
```

## Viewing Events

### Using kubectl describe

```bash
kubectl describe eao ml-training-job
```

**Output:**
```yaml
Events:
  Type    Reason      Age   From                Message
  ----    ------      ----  ----                -------
  Normal  Scheduling  2m    kopf                [Event 1] Calculating schedule for 'ml-training-job' (Priority: Preferred, Energy: 500W)
  Normal  Scheduled   2m    kopf                [Event 2] Scheduled: Preferred workload - energy sufficient (800W available, 500W required)
```

### Using kubectl get events

```bash
kubectl get events --sort-by='.lastTimestamp' | grep energyawareorchestrations
```

**Output:**
```
2m    Normal  Scheduling     energyawareorchestrations/ml-training-job   [Event 1] Calculating schedule for 'ml-training-job' (Priority: Preferred, Energy: 500W)
2m    Normal  Scheduled      energyawareorchestrations/ml-training-job   [Event 2] Scheduled: Preferred workload - energy sufficient (800W available, 500W required)
```

## Event Sequence for Different Scenarios

### Successful Reconciliation

```
[Event 1] Calculating schedule for 'batch-job' (Priority: Optional, Energy: 200W)
[Event 2] Scheduled: Optional workload - best slot found with sufficient energy
```

### Validation Failure

```
[Event 1] Calculating schedule for 'invalid-job' (Priority: Preferred, Energy: 100W)
[Event 2] ValidationFailed: applicationRef.name is required
```

### Scheduling Failure

```
[Event 1] Calculating schedule for 'heavy-job' (Priority: Optional, Energy: 5000W)
[Event 2] SchedulingFailed: Failed to calculate schedule
```

### Exception During Reconciliation

```
[Event 1] Calculating schedule for 'problematic-job' (Priority: Preferred, Energy: 1000W)
[Event 2] Error: Scheduling error: Invalid energy value
```

### Deletion

```
[Event 1] EnergyAwareOrchestration 'ml-training-job' is being deleted
```

### Periodic Re-evaluation

```
[Event 1] Periodic re-evaluation for 'ml-training-job'
```

## Complete Event Flow Example

For a CR going through its full lifecycle:

```yaml
# Initial creation
[Event 1] Calculating schedule for 'ml-training-job' (Priority: Preferred, Energy: 500W)
[Event 2] Scheduled: Preferred workload - energy sufficient

# User updates energyConsumption
[Event 1] Calculating schedule for 'ml-training-job' (Priority: Preferred, Energy: 800W)
[Event 2] Delayed: Preferred workload - insufficient energy. Delayed to next slot.

# Periodic re-evaluation (1 hour later)
[Event 1] Periodic re-evaluation for 'ml-training-job'

# User deletes the CR
[Event 1] EnergyAwareOrchestration 'ml-training-job' is being deleted
```

**Note:** Event numbers reset with each reconciliation cycle!

## Benefits

1. **Easy sequence tracking** - Know the exact order of events
2. **Debugging** - Quickly identify missing or duplicate events
3. **Audit trail** - Clear timeline of operations
4. **Multi-CR clarity** - When viewing all events, numbers help separate different reconciliations

## Filtering Events by Number

### First event of each reconciliation
```bash
kubectl get events -o json | jq '.items[] | select(.message | contains("[Event 1]"))'
```

### All scheduling events
```bash
kubectl get events --field-selector reason=Scheduling
```

### Events for specific CR
```bash
kubectl get events --field-selector involvedObject.name=ml-training-job
```

## Disabling Event Numbering

If you want to disable event numbering, you can pass `include_number=False`:

```python
event_handler.post_event_safe(
    body,
    event_type="Normal",
    reason="CustomEvent",
    message="My message",
    include_number=False  # No event number
)
```

But by default, all events include numbering for better traceability.
