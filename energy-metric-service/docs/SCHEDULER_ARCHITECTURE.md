# Energy-Aware Orchestration Scheduler Architecture

> ⚠️ **Outdated.** This document describes an earlier architecture where the
> Kopf operator and scheduling logic lived inside `energy-metric-service`
> itself (`app/crd/operator.py`, `app/servicesv2/eao_scheduler_service.py`
> below). Both have since moved to their own repo, `energy-aware-operator`
> (see its README) - `eao_scheduler_service.py` no longer exists in this
> repo. Kept here for historical context, not as a guide to the current
> system.

## Overview

The Energy-Aware Orchestration (EAO) system provides intelligent workload scheduling based on energy availability and workload priority. 
It follows the **Kubernetes Operator Pattern** with a separate **Scheduler Service** for business logic.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EnergyAwareOrchestration System                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐                      ┌──────────────────────────┐     │
│   │  User/Admin     │                      │   Energy Availability    │     │
│   │                 │                      │   Database (PostgreSQL)  │     │
│   └────────┬────────┘                      └────────────┬─────────────┘     │
│            │                                            │                   │
│            │ kubectl apply                              │ Energy Data       │
│            ▼                                            ▼                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     Kubernetes Cluster                              │   │
│   │  ┌──────────────────────────────────────────────────────────────┐   │   │
│   │  │              EnergyAwareOrchestration CRD                    │   │   │
│   │  │  - spec.priority (Critical/Preferred/Optional)               │   │   │
│   │  │  - spec.energyConsumption (Watts)                            │   │   │
│   │  │  - spec.applicationRef                                       │   │   │
│   │  │  - status.phase                                              │   │   │
│   │  │  - status.decision                                           │   │   │
│   │  │  - status.energyMetrics                                      │   │   │
│   │  └──────────────────────────────────────────────────────────────┘   │   │
│   │                              │                                      │   │
│   │                              │ Watch Events                         │   │
│   │                              ▼                                      │   │
│   │  ┌──────────────────────────────────────────────────────────────┐   │   │
│   │  │                    Kopf Operator                             │   │   │
│   │  │                  (app/crd/operator.py)                       │   │   │
│   │  │                                                              │   │   │
│   │  │  • on.create / on.update → Reconcile CR                      │   │   │
│   │  │  • timer (1hr) → Re-evaluate schedules                       │   │   │
│   │  │  • on.delete → Cleanup                                       │   │   │
│   │  │  • Posts Kubernetes Events                                   │   │   │
│   │  └──────────────────────────────────────────────────────────────┘   │   │
│   │                              │                                      │   │
│   │                              │ Calculate Schedule                   │   │
│   │                              ▼                                      │   │
│   │  ┌──────────────────────────────────────────────────────────────┐   │   │
│   │  │              EAO Scheduler Service                           │   │   │
│   │  │       (app/servicesv2/eao_scheduler_service.py)              │   │   │
│   │  │                                                              │   │   │
│   │  │  Priority-Based Scheduling:                                  │   │   │
│   │  │  ┌─────────────┬────────────────────────────────────────┐    │   │   │
│   │  │  │ Critical    │ DeployImmediately (24/7 operation)     │    │   │   │
│   │  │  │ Preferred   │ Delay 6h if energy insufficient        │    │   │   │
│   │  │  │ Optional    │ Best slot in next 24h                  │    │   │   │
│   │  │  └─────────────┴────────────────────────────────────────┘    │   │   │
│   │  └──────────────────────────────────────────────────────────────┘   │   │
│   │                              │                                      │   │
│   │                              │ Update Status                        │   │
│   │                              ▼                                      │   │
│   │  ┌──────────────────────────────────────────────────────────────┐   │   │
│   │  │                   CR Status Updated                          │   │   │
│   │  │  status:                                                     │   │   │
│   │  │    phase: Scheduled                                          │   │   │
│   │  │    decision:                                                 │   │   │
│   │  │      action: DeployImmediately | Scheduled | Delayed         │   │   │
│   │  │      scheduledSlot: { slotNumber, slotStart, slotEnd }       │   │   │
│   │  │    energyMetrics: { requiredWatts, sufficient }              │   │   │
│   │  └──────────────────────────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```


## Time Slot System

The day is divided into **4 time slots** of **6 hours each**:

```
┌────────────────────────────────────────────────────────────────────┐
│                          24-Hour Day                               │
├────────────┬────────────┬────────────┬────────────────────────────┤
│   Slot 1   │   Slot 2   │   Slot 3   │          Slot 4            │
│ 00:00-06:00│ 06:00-12:00│ 12:00-18:00│       18:00-24:00          │
│  Midnight  │  Morning   │ Afternoon  │         Evening            │
│   to 6am   │  to Noon   │  to 6pm    │       to Midnight          │
└────────────┴────────────┴────────────┴────────────────────────────┘
```

## Scheduling Logic by Priority

### Critical Priority

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CRITICAL WORKLOADS                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Decision: DeployImmediately                                        │
│  Behavior: Run 24/7, regardless of energy availability              │
│                                                                     │
│  Example Use Cases [e.g of workload type]:                          │
│  • Production APIs                                                  │
│  • Real-time data processing                                        │
│  • Security services                                                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  CR Created → Operator → Scheduler                          │    │
│  │                            │                                │    │
│  │                            ▼                                │    │
│  │                  if priority == Critical:                   │    │
│  │                      return DeployImmediately               │    │
│  │                                                             │    │
│  │  Status: phase=Scheduled, action=DeployImmediately          │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Preferred Priority

```
┌─────────────────────────────────────────────────────────────────────┐
│                   PREFERRED WORKLOADS                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Decision: Scheduled (now) OR Delayed (6 hours)                     │
│  Behavior: If energy insufficient → delay to next slot              │
│                                                                     │
│  Example Use Cases:                                                 │
│  • Batch processing jobs                                            │
│  • Data synchronization                                             │
│  • Report generation                                                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  CR Created → Operator → Scheduler                          │    │
│  │                            │                                │    │
│  │                            ▼                                │    │
│  │         ┌─────────────────────────────────────┐             │    │
│  │         │ Is energy_available >= required?    │             │    │
│  │         └──────────────┬──────────────────────┘             │    │
│  │                        │                                    │    │
│  │              ┌─────────┴─────────┐                          │    │
│  │              │                   │                          │    │
│  │            Yes                  No                          │    │
│  │              │                   │                          │    │
│  │              ▼                   ▼                          │    │
│  │         Scheduled           Delayed                         │    │
│  │        (current slot)     (next slot +6h)                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Optional Priority

```
┌─────────────────────────────────────────────────────────────────────┐
│                     OPTIONAL WORKLOADS                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Decision: Scheduled (best slot in 24h)                             │
│  Behavior: Find slot with most available energy in next 24 hours    │
│                                                                     │
│  Example Use Cases:                                                 │
│  • ML model training                                                │
│  • Analytics jobs                                                   │
│  • Backup operations                                                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  CR Created → Operator → Scheduler                          │    │
│  │                            │                                │    │
│  │                            ▼                                │    │
│  │       ┌────────────────────────────────────────────┐        │    │
│  │       │ Get all slots in next 24 hours             │        │    │
│  │       │ [Slot N, Slot N+1, Slot N+2, Slot N+3]     │        │    │
│  │       └────────────────────┬───────────────────────┘        │    │
│  │                            │                                │    │
│  │                            ▼                                │    │
│  │       ┌────────────────────────────────────────────┐        │    │
│  │       │ For each slot:                             │        │    │
│  │       │   - Query energy availability              │        │    │
│  │       │   - Check if sufficient for workload       │        │    │
│  │       └────────────────────┬───────────────────────┘        │    │
│  │                            │                                │    │
│  │                            ▼                                │    │
│  │       ┌────────────────────────────────────────────┐        │    │
│  │       │ Select best slot:                          │        │    │
│  │       │   1. First with sufficient energy          │        │    │
│  │       │   2. Or slot with most available energy    │        │    │
│  │       └────────────────────┬───────────────────────┘        │    │
│  │                            │                                │    │
│  │                            ▼                                │    │
│  │                   Status: Scheduled                         │    │
│  │                   scheduledSlot: { best slot }              │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Custom Resource Definition (CRD)

**File:** `app/crd/energy_aware_orchestration_model.py`

```yaml
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: my-workload
spec:
  applicationRef:
    name: my-app
    namespace: default
  energyConsumption: 200      # Watts required
  forecastWindowDays: 7       # Days to forecast
  priority: Optional          # Critical | Preferred | Optional
status:
  phase: Scheduled            # Pending | Scheduled | Running | Completed | Failed
  decision:
    action: Scheduled         # DeployImmediately | Scheduled | Delayed | Waiting
    reason: "Human-readable explanation"
    scheduledSlot:
      slotNumber: 2           # 1-4
      slotStart: "2025-12-09T06:00:00+00:00"
      slotEnd: "2025-12-09T12:00:00+00:00"
      availableEnergyWatts: 500.0
    nextEvaluationTime: "2025-12-09T06:00:00+00:00"
  energyMetrics:
    currentSlotAvailableWatts: 300.0
    currentSlotConsumedWatts: 150.0
    requiredWatts: 200.0
    sufficient: true
  lastUpdated: "2025-12-09T07:16:26+00:00"
```

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Scheduling Flow                                 │
└──────────────────────────────────────────────────────────────────────────┘

1. USER CREATES CR
   │
   │  kubectl apply -f my-eao.yaml
   │
   ▼
2. KOPF OPERATOR RECEIVES EVENT
   │
   │  @kopf.on.create triggers reconcile_handler
   │
   ▼
3. EXTRACT SPEC
   │
   │  priority = spec.priority
   │  energy_consumption = spec.energyConsumption
   │  application_ref = spec.applicationRef
   │
   ▼
4. CALL SCHEDULER SERVICE
   │
   │  scheduler.calculate_schedule(priority, energy_consumption)
   │
   ▼
5. SCHEDULER EVALUATES
   │
   │  ┌─────────────────────────────────────────────┐
   │  │  if Critical:                               │
   │  │      return DeployImmediately               │
   │  │  if Preferred:                              │
   │  │      if energy_sufficient:                  │
   │  │          return Scheduled (current slot)    │
   │  │      else:                                  │
   │  │          return Delayed (next slot)         │
   │  │  if Optional:                               │
   │  │      return Scheduled (best slot in 24h)    │
   │  └─────────────────────────────────────────────┘
   │
   ▼
6. UPDATE CR STATUS
   │
   │  patch.status["phase"] = "Scheduled"
   │  patch.status["decision"] = { action, reason, scheduledSlot }
   │  patch.status["energyMetrics"] = { ... }
   │
   ▼
7. POST KUBERNETES EVENT
   │
   │  kopf.event(body, type="Normal", reason="Scheduled", message="...")
   │
   ▼
8. PERIODIC RE-EVALUATION (every hour)
   │
   │  @kopf.timer re-runs scheduler to update if conditions change
   │
   ▼
9. DONE
```

---

## Integration with Energy Data

The scheduler integrates with the existing energy availability system:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Energy Data Integration                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────┐      ┌───────────────────────────────┐   │
│  │ EnergyAvailability   │      │  EnergyAvailabilityService    │   │
│  │ (PostgreSQL Table)   │◄────▶│  - get_current_time_slot()    │   │
│  │                      │      │  - calculate_available_energy()│   │
│  │  - slot_start_time   │      │  - check_energy_sufficient()  │   │
│  │  - slot_end_time     │      └───────────────────────────────┘   │
│  │  - available_watts   │                    ▲                     │
│  │  - provider_name     │                    │                     │
│  │  - confidence_%      │                    │                     │
│  └──────────────────────┘                    │                     │
│                                              │                     │
│  ┌───────────────────────────────────────────┴───────────────────┐ │
│  │                   EAO Scheduler Service                       │ │
│  │                                                               │ │
│  │  async def get_energy_for_slot(slot):                         │ │
│  │      repository = EnergyAvailabilityRepository(session)       │ │
│  │      availability = await repository.get_all(                 │ │
│  │          start_time=slot.start_time,                          │ │
│  │          end_time=slot.end_time                               │ │
│  │      )                                                        │ │
│  │      slot.available_energy_watts = availability.available_watts │ │
│  │      return slot                                              │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---
---

## Usage Examples

### Deploy a Critical Workload

```yaml
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: production-api
spec:
  applicationRef:
    name: api-server
    namespace: production
  energyConsumption: 100
  forecastWindowDays: 7
  priority: Critical
```

**Result:**
```
status:
  phase: Scheduled
  decision:
    action: DeployImmediately
    reason: "Critical priority workload - deploy immediately (24/7 operation)"
```

### Deploy an Optional Workload

```yaml
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: ml-training
spec:
  applicationRef:
    name: training-job
    namespace: ml
  energyConsumption: 500
  forecastWindowDays: 3
  priority: Optional
```

**Result:**
```
status:
  phase: Scheduled
  decision:
    action: Scheduled
    reason: "Optional workload - best slot found with sufficient energy"
    scheduledSlot:
      slotNumber: 3
      slotStart: "2025-12-09T12:00:00+00:00"
      slotEnd: "2025-12-09T18:00:00+00:00"
```

---

## Future Enhancements

1. **Deployment Trigger** - Actually deploy workloads at scheduled times
2. **Energy Forecasting** - Predict future energy availability using ML
3. **Cost Optimization** - Consider energy cost in addition to availability
4. **Multi-Cluster** - Schedule across multiple clusters
5. **Preemption** - Allow Critical workloads to preempt Optional ones


