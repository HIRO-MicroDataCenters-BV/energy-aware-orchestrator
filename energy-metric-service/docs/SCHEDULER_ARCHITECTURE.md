# Scheduler Architecture

This document describes the background schedulers that run inside
`energy-metric-service`. There is no Kopf operator or CRD reconcile loop in
this repo - that logic lives in the separate `energy-aware-operator` repo
(see its README). This service exposes a REST API and runs five independent
`asyncio` background loops, started from `app/main.py`'s FastAPI `lifespan`
handler and stopped on shutdown.

## Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                         FastAPI app (main.py)                         │
│                                                                       │
│   lifespan(): start() each enabled scheduler on boot, stop() on       │
│   shutdown. Each scheduler is a single asyncio task running its own   │
│   "do work, sleep interval_seconds, repeat" loop - independent of     │
│   the others and of the request-handling event loop.                 │
└───────────────────────────────────────────────────────────────────────┘
        │                │                │                │            │
        ▼                ▼                ▼                ▼            ▼
 MetricCollector   GridPolling      Forecasting  MetricsRetention  Deployment
   Scheduler        Scheduler        Scheduler      Scheduler      Scheduler
                                                                   (unused, see end)
```

| Scheduler | File | Default interval | Enabled by | Default |
|---|---|---|---|---|
| `MetricCollectorScheduler` | `app/scheduler/metric_collector_scheduler.py` | 30s | `ENABLE_METRICS_SCHEDULER` | off |
| `GridPollingScheduler` | `app/scheduler/grid_polling_scheduler.py` | 300s | `ENABLE_GRID_POLLING` + `GRID_API_URL` | on, but dormant without a URL |
| `ForecastingScheduler` | `app/scheduler/forecasting_scheduler.py` | 1800s | `ENABLE_FORECASTING` | on |
| `MetricsRetentionScheduler` | `app/scheduler/metrics_retention_scheduler.py` | 3600s | `ENABLE_METRICS_RETENTION` | on |
| `DeploymentScheduler` (NOT USED - see end of doc) | `app/scheduler/deployment_scheduler.py` | 30s | `ENABLE_DEPLOYMENT_SCHEDULER` | on |

Every loop follows the same shape: try the work, catch and log any
exception, then `asyncio.sleep(interval_seconds)` and repeat. A failure in
one cycle (a bad Prometheus response, an unreachable grid API, one
malformed slot) never stops the loop - it's logged and retried on the next
interval.

---

## 1. MetricCollectorScheduler

Polls Prometheus every cycle and stores two kinds of rows:

- **Node-level metrics** (`node_metrics` table) via `PrometheusMetricsService`
- **Per-container metrics** (`container_power_metrics` table) via `PrometheusContainerMetricsService`

The two collection calls are wrapped in separate `try`/`except` blocks so a
failure collecting one never blocks the other. This is the scheduler that
feeds real energy-consumption data into everything downstream (deployment
energy checks, the demand side of the data-flow diagrams in the root
README).

Off by default (`ENABLE_METRICS_SCHEDULER=false`) - a cluster without Kepler/
cAdvisor wired up yet shouldn't be spending a cycle every 30s hitting
Prometheus.

## 2. GridPollingScheduler

Polls an external grid capacity API (`GRID_API_URL`) via `GridAPIClient` and
upserts each returned slot as a **real supply** row in `energy_availability`
(`app/repositories/energy_availability.py`, `record_type="supply"`).

Stays dormant (constructed as `None`, never started) if `GRID_API_URL` isn't
set - there's nothing to poll without a real endpoint, and logging a
connection error every 5 minutes would be noise. **This is currently backed
by a mock/dev stub** - wiring a real external grid endpoint is open backlog
work (see `energy-aware-operator` demand-reporting integration, US5).

Each slot is upserted independently inside its own `try`/`except`, so one
malformed slot in a batch doesn't discard the rest of that cycle's data.

## 3. ForecastingScheduler

Refreshes **predicted supply** rows so the scheduler has a sensible answer
for slots beyond what live grid polling has reached. Every 30 minutes
(default), for each distinct provider with real supply history:

1. Pull up to 14 days of real supply history for that provider
2. Call `PredictionService.predict(history, future_slots)` for the next 8
   fixed 6-hour slots (aligned to 0/6/12/18 UTC boundaries, i.e. 2 days ahead)
3. Upsert each prediction as a `record_type="supply"` row with `data_source="predicted"`, so it can be picked up by demand resolution

`PredictionService.predict()` is currently a **placeholder**: it buckets
history by hour-of-day/slot and returns the historical average per bucket -
it is not a trained model. Replacing it with a real forecasting model is
open backlog work; the integration point (same input/output contract) is
this call site, so a real model can be swapped in without touching the
scheduler itself.

A provider with no real supply history yet is a no-op cycle, not an error -
there's nothing to forecast from.

## 4. MetricsRetentionScheduler

Deletes rows older than `retention_days` (default 30) from `node_metrics`
and `container_power_metrics` every hour. Both tables get a fresh row every
`MetricCollectorScheduler` cycle with no upsert, so nothing else ever
removes old data - confirmed in practice, `container_power_metrics` alone
reaches roughly 141K rows/day at default 30s collection. This scheduler
exists purely as a hygiene/safety measure and is on by default.

---

## End-to-end data flow

How the five schedulers feed each other, from raw metrics/grid data down to
an actual deployment decision:

```
 GridPollingScheduler          MetricCollectorScheduler
 (every 5 min, if               (every 30s, if enabled)
  GRID_API_URL set)                      │
        │                                ▼
        │                     Prometheus (Kepler + cAdvisor)
        ▼                                │
 energy_availability                     ▼
   record_type=supply          node_metrics /
   data_source=real             container_power_metrics
        │                                │
        │                                │ (last 1h, summed)
        ▼                                │
 ForecastingScheduler                    │
 (every 30 min)                          │
   reads real supply history             │
   writes predicted slots ─┐             │
        │                  │             │
        ▼                  │             │
 energy_availability        │             │
   record_type=supply       │             │
   data_source=predicted    │             │
        │                  │             │
        └──────────┬───────┘             │
                    ▼                    │
      EnergyAvailabilityService          │
      .get_current_time_slot_energy()    │
        real slot preferred over         │
        predicted for the same window    │
                    │                    │
                    ▼                    ▼
          slot_energy_watts  −  current_consumption_watts
                    │
                    ▼
          total_available_watts  ≥  required_energy_watts ?
                    │
                    ▼
         Consumed by whatever actually makes deployment decisions:
           - energy-aware-operator (separate repo) - the real path today
           - DeploymentScheduler (this repo, every 30s) - NOT USED in
             production, see "Unused: DeploymentScheduler" below
                    │
                    ▼
         kubectl/helm/CR apply to the cluster
```

`MetricsRetentionScheduler` runs alongside this independently, deleting rows
from `node_metrics`/`container_power_metrics` older than `retention_days` -
it doesn't sit in the decision path above, it just keeps those two tables
bounded.

---

## Unused: DeploymentScheduler

Runs `DeploymentSchedulerService.process_pending_deployments()` every 30s,
but nothing in production relies on its output: real workload scheduling
lives in the separate `energy-aware-operator` repo (CRD + reconcile loop).
This scheduler, the `ApplicationDeployment`/`ApplicationDefinition` tables
it drives, and the `EnergyAvailabilityService.check_energy_sufficient_
for_deployment()` energy check it alone calls (no API endpoint or other
service touches it) are a leftover in-repo path with no other caller
anywhere in this codebase. Treat it as a removal candidate (see Future
Enhancements), not as documentation of how deployments actually get made.

Briefly, when active: it polls `ApplicationDeployment` rows in
`Created`/`Schedule` status, checks each one's `WorkloadType`
(`Critical` skips the energy check; `Preferred`/`Optional` require the
current slot's available watts, real supply preferred over predicted, to
cover the estimated requirement), then delegates to a `kubernetes` /
`helm` / `custom` deployment service based on `deployment_type`.

---

## Future Enhancements

1. **Real ML forecasting model** - replace `PredictionService.predict()`'s
   historical-average placeholder with an actual trained model
2. **Real external grid endpoint** - `GridPollingScheduler` currently talks
   to a mock/dev stub; wire up a production grid API
3. **Remove the unused DeploymentScheduler path** - `DeploymentScheduler`,
   `DeploymentSchedulerService`, and the energy-resolution code it alone
   calls are dead weight now that `energy-aware-operator` is the real
   scheduling path; delete rather than keep maintaining in parallel
4. **Cost optimization** - factor energy cost, not just availability, into
   deployment decisions (in whichever repo ends up owning scheduling)
