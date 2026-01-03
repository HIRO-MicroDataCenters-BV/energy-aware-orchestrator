# Operator Logs Example

This document shows example logs from the modularized operator with structured logging.

## Successful Reconciliation

```
================================================================================
🔄 RECONCILIATION STARTED: 'ml-training-job' (namespace: default)
================================================================================

📋 STEP 1: Validating CR Specification
--------------------------------------------------------------------------------
✓ Validation successful
   Priority: Preferred
   Energy Required: 500W
   Application: ml-training-deployment (namespace: default)
--------------------------------------------------------------------------------

📣 STEP 2: Posting Kubernetes Event
--------------------------------------------------------------------------------
✓ Event posted: Scheduling started
--------------------------------------------------------------------------------

⚡ STEP 3: Calculating Schedule
--------------------------------------------------------------------------------
✓ Schedule calculation successful
--------------------------------------------------------------------------------

📝 STEP 4: Updating CR Status
--------------------------------------------------------------------------------
✓ Status patch applied
--------------------------------------------------------------------------------

📊 STEP 5: Schedule Decision
--------------------------------------------------------------------------------
Schedule decision for 'ml-training-job': Scheduled - Preferred workload - energy sufficient (800W available, 500W required)
  Scheduled slot: 3 (2026-01-02T12:00:00+00:00 - 2026-01-02T18:00:00+00:00)
  Available energy: 800.0W
--------------------------------------------------------------------------------

📣 STEP 6: Posting Completion Event
--------------------------------------------------------------------------------
✓ Event posted: Scheduled
--------------------------------------------------------------------------------

================================================================================
✅ RECONCILIATION COMPLETED: 'ml-training-job'
   Action: Scheduled
================================================================================

```

## Validation Failure

```
================================================================================
🔄 RECONCILIATION STARTED: 'invalid-job' (namespace: default)
================================================================================

📋 STEP 1: Validating CR Specification
--------------------------------------------------------------------------------

❌ VALIDATION FAILED
   Field: applicationRef.name
   Error: applicationRef.name is required
--------------------------------------------------------------------------------
```

## Scheduling Error (with Exception)

```
================================================================================
🔄 RECONCILIATION STARTED: 'problematic-job' (namespace: default)
================================================================================

📋 STEP 1: Validating CR Specification
--------------------------------------------------------------------------------
✓ Validation successful
   Priority: Optional
   Energy Required: 1000W
   Application: heavy-workload (namespace: default)
--------------------------------------------------------------------------------

📣 STEP 2: Posting Kubernetes Event
--------------------------------------------------------------------------------
✓ Event posted: Scheduling started
--------------------------------------------------------------------------------

⚡ STEP 3: Calculating Schedule
--------------------------------------------------------------------------------

================================================================================
💥 EXCEPTION DURING RECONCILIATION: 'problematic-job'
================================================================================
   Error Type: ValueError
   Error Message: Invalid energy value
--------------------------------------------------------------------------------
Traceback (most recent call last):
  File "app/crd/operator.py", line 162, in reconcile_handler
    schedule_result = await scheduler_handler.calculate_schedule(
  ...
ValueError: Invalid energy value
================================================================================

```

## Deletion Handler

```
================================================================================
🗑️  DELETION TRIGGERED: 'ml-training-job' (namespace: default)
================================================================================

📣 Posting deletion event
--------------------------------------------------------------------------------
✓ Event posted: Deleting
--------------------------------------------------------------------------------

🧹 Performing cleanup
--------------------------------------------------------------------------------
✓ Cleanup completed
--------------------------------------------------------------------------------

================================================================================
✅ DELETION COMPLETED: 'ml-training-job'
================================================================================

```

## Periodic Re-evaluation

```
================================================================================
🔁 PERIODIC RE-EVALUATION: 'ml-training-job' (namespace: default)
   Current Phase: Scheduled
================================================================================

📋 Extracting spec fields
--------------------------------------------------------------------------------
   Priority: Preferred
   Energy Required: 500W
--------------------------------------------------------------------------------

📣 Posting re-evaluation event
--------------------------------------------------------------------------------
✓ Event posted
--------------------------------------------------------------------------------

⚡ Recalculating schedule
--------------------------------------------------------------------------------
✓ Schedule recalculated
--------------------------------------------------------------------------------

📝 Updating status
--------------------------------------------------------------------------------
✓ Status updated
--------------------------------------------------------------------------------

================================================================================
✅ RE-EVALUATION COMPLETED: 'ml-training-job'
   New Action: Scheduled
================================================================================

```

## Periodic Re-evaluation (Skipped)

```
⏭️  Skipping re-evaluation for 'completed-job': phase is Completed
```

## Log Structure

### Separators

- **Double line (`=`)**: Major section boundaries (start/end of operations)
- **Single line (`-`)**: Step boundaries within an operation
- **Newlines (`\n`)**: Before major sections for visual separation

### Icons

- 🔄 **Reconciliation started**
- ✅ **Successful completion**
- ❌ **Failure**
- 💥 **Exception/Error**
- 📋 **Validation/Extraction**
- 📣 **Event posting**
- ⚡ **Scheduling**
- 📝 **Status update**
- 📊 **Decision logging**
- 🗑️ **Deletion**
- 🧹 **Cleanup**
- 🔁 **Re-evaluation**
- ⏭️ **Skip**
- ⚠️ **Warning**

### Log Levels

- **INFO**: Normal operations, steps, completions
- **ERROR**: Validation failures, scheduling failures, exceptions
- **WARNING**: Re-evaluation errors (non-critical)
- **DEBUG**: Skipped operations

## Benefits

1. **Clear visual separation** between different reconciliation runs
2. **Step-by-step visibility** into what the operator is doing
3. **Easy to spot errors** with distinct formatting and icons
4. **Context-rich** - each log includes relevant details
5. **Searchable** - consistent formatting makes log searching easy
6. **Production-ready** - structured enough for log aggregation tools

## Searching Logs

### Find all reconciliations
```bash
kubectl logs <operator-pod> | grep "RECONCILIATION STARTED"
```

### Find all completions
```bash
kubectl logs <operator-pod> | grep "✅"
```

### Find all errors
```bash
kubectl logs <operator-pod> | grep -E "(❌|💥)"
```

### Find specific CR
```bash
kubectl logs <operator-pod> | grep "ml-training-job"
```

### Extract a single reconciliation
```bash
kubectl logs <operator-pod> | sed -n '/RECONCILIATION STARTED.*ml-training/,/RECONCILIATION COMPLETED/p'
```

## Integration with Log Aggregation

The structured format works well with log aggregation tools:

### Elasticsearch/Kibana
- Filter by icon/emoji: `message: "🔄"`
- Filter by CR name: `message: "ml-training-job"`
- Filter by step: `message: "STEP 3"`

### Prometheus/Loki
```promql
{job="operator"} |= "RECONCILIATION COMPLETED"
```

### DataDog
```
source:operator status:info @message:"✅"
```
