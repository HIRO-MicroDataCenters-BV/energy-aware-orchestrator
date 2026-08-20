# Energy Metric Service

A comprehensive energy monitoring and forecasting service for Kubernetes clusters. Integrates with Prometheus, Kepler, and Kubernetes to provide real-time energy consumption metrics, grid capacity tracking, and supply forecasting. Includes both the FastAPI application and a custom PostgreSQL Helm chart for persistent storage.

---

## 📁 Project Structure

```
energy-metric-service/
├── app/                  # FastAPI application source code
│   ├── api/               # API routers (metrics, k8s, forecasting, energy-availability, etc.)
│   ├── db/                 # Database connection logic
│   ├── models/             # ORM/data models
│   ├── repositories/       # Data access logic
│   ├── scheduler/          # Background schedulers (metrics, deployment, grid polling, forecasting)
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Metrics, prediction, and integration logic (grid client, prediction service)
│   ├── servicesv2/         # Newer service implementations
│   └── utils/               # Utilities and helpers
├── charts/
│   ├── app/                # Helm chart for FastAPI app (incl. dev/test grid stub)
│   └── postgres/           # Helm chart for PostgreSQL
├── migrations/            # Alembic database migrations (see "Database Migrations" below)
│   └── versions/
├── scripts/
│   ├── deploy-all.sh       # Deploys both PostgreSQL and app (recommended)
│   ├── deploy-app.sh       # Deploys only the FastAPI app
│   └── deploy-postgres.sh  # Deploys only PostgreSQL
├── Dockerfile              # Container build for FastAPI app
├── entrypoint.sh           # Runs migrations, then starts the app (container CMD)
├── docker-compose.yaml     # Local dev (optional)
├── README.md               # This file
└── ...
```

---

## 🚀 Features

- **Energy Metrics Collection:** Fetches energy data from Kepler via Prometheus
- **Resource Monitoring:** Tracks CPU and memory utilization
- **Grid Capacity Polling:** Periodically polls an external grid API for live supply data (see [Grid Integration](#-grid-integration))
- **Supply Forecasting:** Predicts future supply for slots beyond what live polling has reached (see [Supply Forecasting](#-supply-forecasting-predictions)) — currently a dummy averaging model, not yet a trained ML model (see [Known Limitations](#-known-limitations--next-steps))
- **Demand Reporting:** Tracks each workload's currently required watts, reported by `energy-aware-operator` (see [Demand Reporting](#-demand-reporting))
- **Automatic Database Migrations:** Alembic migrations run at deploy time and on every container start, with a drift check gating the deploy (see [Database Migrations](#-database-migrations))
- **Kubernetes Integration:** Pod and namespace management APIs
- **Time Series Analysis:** Historical data and trend monitoring
- **Custom PostgreSQL Helm Chart:** Easy, persistent storage setup
- **Demand Resolution:** Resolves each workload's actual current demand — measured (Kepler) > ML-predicted (consumption model) > operator-provided fallback (see [Demand Reporting](#-demand-reporting))

---

## ⚡ Quick Start (Recommended)

### 1. Prerequisites

- Kubernetes cluster (tested with Minikube / kind)
- Helm 3.x
- kubectl configured
- Docker (for building the app image)

### 2. Deploy Everything (App + PostgreSQL)

From the `energy-metric-service/` directory:

```bash
./scripts/deploy-all.sh
```

- This script will:
  - Deploy PostgreSQL using the custom Helm chart
  - Build and deploy the FastAPI application (running Alembic migrations on startup)
  - Wait for all pods to be ready

#### Options

- Deploy only DB: `./scripts/deploy-all.sh --db-only`
- Deploy only App: `./scripts/deploy-all.sh --app-only`
- Skip image build: `./scripts/deploy-all.sh --no-build`
- Specify namespace: `./scripts/deploy-all.sh -n my-namespace`

> For the full multi-component stack (operator, UI, monitoring, etc.), use `deploy-full-stack.sh` at the repo root instead — see the root `README.md` for its `--grid-stub`/`--grid-url` flags.

---

## 🛠️ Manual Installation

### 1. Deploy PostgreSQL Only

```bash
./scripts/deploy-postgres.sh
```

- Custom options:
  - `-n my-namespace` — set namespace
  - `--db mydb` — set database name
  - `--user myuser` — set username
  - `--password mypass` — set password
  - `--storage 20Gi` — set storage size
  - `-f my-values.yaml` — use custom values file

### 2. Deploy FastAPI App Only

```bash
./scripts/deploy-app.sh
```

- Options:
  - `-n my-namespace` — set namespace
  - `--no-build` — skip Docker image build
  - `--grid-stub` — also deploy the dev/test mock grid server and point `GRID_API_URL` at it (see [Grid Integration](#-grid-integration))
  - `--grid-url URL` — point `GRID_API_URL` at a real grid endpoint instead

---

## 📦 Helm Installation (Advanced)

### Deploy PostgreSQL Chart Directly

```bash
cd charts
helm install postgres ./postgres
```

- With custom values:
  ```bash
  helm install postgres ./postgres \
    --set postgres.credentials.database=mydb \
    --set postgres.credentials.username=myuser \
    --set postgres.credentials.password=mypass \
    --set postgres.persistence.size=20Gi
  ```
- Or with a values file:
  ```bash
  helm install postgres ./postgres -f my-values.yaml
  ```

### Deploy App Chart Directly

```bash
cd charts
helm install energy-metric-service ./app
```

- Set image/tag or environment variables as needed (see [Configuration & Customization](#%EF%B8%8F-configuration--customization) below).

---

## ⚙️ Configuration & Customization

### PostgreSQL Chart (`charts/postgres/values.yaml`)

```yaml
postgres:
  name: eao-postgres
  image:
    repository: postgres
    tag: "14"
  credentials:
    username: postgres
    password: postgres
    database: orchestration_db
  persistence:
    enabled: true
    size: 8Gi
  service:
    type: ClusterIP
    port: 5432
```

- **Override any value** via `--set` or a custom values file.
- **Init scripts:** Edit `charts/postgres/templates/postgres-configmap.yaml` to add custom SQL.

### App Chart (`charts/app/values.yaml`)

Environment variables under `app.env`:

| Variable | Default | Purpose |
|---|---|---|
| `ENABLE_METRICS_SCHEDULER` | `false` | Periodic Prometheus/Kepler metrics collection |
| `ENABLE_DEPLOYMENT_SCHEDULER` | `true` | Legacy deployment-request processor (largely superseded by `energy-aware-operator`) |
| `ENABLE_GRID_POLLING` | `true` | Whether `GridPollingScheduler` runs at all |
| `GRID_API_URL` | `""` | Where to poll for grid capacity. Empty = poller stays dormant, unless `gridStub.enabled=true` auto-points it at the dev stub |
| `GRID_POLL_INTERVAL_SECONDS` | `300` | Grid polling interval |
| `ENABLE_FORECASTING` | `true` | Whether `ForecastingScheduler` runs at all (in-process, no URL needed) |
| `FORECASTING_INTERVAL_SECONDS` | `1800` | Supply prediction refresh interval |
| `LOG_LEVEL` | `INFO` | App log level |
| `KUBERNETES_NAMESPACE` | *(release namespace)* | Namespace the app operates against |
| `USE_KUBECTL_PROXY` | `false` | Use `kubectl proxy` instead of in-cluster ServiceAccount auth |

Top-level chart values:

| Value | Default | Purpose |
|---|---|---|
| `gridStub.enabled` | `false` | Deploy the dev/test mock grid server (see [Grid Integration](#-grid-integration)) |

---

## 🔄 Database Migrations

Schema changes are managed with **Alembic** (`migrations/`), applied at two points:

1. **Deploy time** — `scripts/deploy-app.sh` opens a temporary port-forward to Postgres, runs `alembic upgrade head`, then `alembic check` (drift detection — see below), and **aborts the deploy** if either fails. This means a broken migration or a model that's drifted from the DB fails loudly on the host before a pod ever rolls, instead of surfacing later as a `CrashLoopBackOff`. `deploy-all.sh`/`deploy-full-stack.sh` inherit this for free since they call `deploy-app.sh`.
2. **Pod start** — `entrypoint.sh` also runs `alembic upgrade head` before starting the app, every container start. This is what actually matters for crash-restarts or node reschedules, where deploy-app.sh never runs again; the deploy-time run above is a fail-fast check, not a replacement for it.
- **Single-replica assumption:** Alembic has no built-in locking. If `app.replicaCount` is ever raised above 1, migrations should move to a Helm pre-upgrade hook Job instead of running from every replica's `entrypoint.sh`.

**Drift detection:** `alembic check` compares the live DB schema directly against the current ORM models (not against migration history), so it only produces meaningful results *after* `alembic upgrade head` has run against that DB — running it first would flag a legitimately-pending migration as if it were drift. If a model and the DB disagree (a forgotten index, a type mismatch, a missing `server_default`), `alembic check` exits non-zero and `deploy-app.sh` stops before deploying. Run it manually anytime with:

```bash
cd energy-metric-service
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/orchestration_db uv run alembic check
```

To add a new migration:

```bash
cd energy-metric-service
uv run alembic revision -m "describe the change"
# edit the generated file in migrations/versions/
uv run alembic upgrade head   # test it locally against DATABASE_URL
uv run alembic check          # confirm the model changes you made match what the migration produced
```

Always verify a new migration against **both** a fresh/empty database and an existing one before merging — the baseline migration (`512771aab2f7`) exists specifically to make fresh installs and upgrades follow the same path.

---

## 🔌 Grid Integration

`energy_availability` holds both **supply** (grid capacity) and **demand** (workload requirements) rows in one table, distinguished by two columns:

- `record_type`: `supply` or `demand`
- `data_source`: `real` (from live polling) or `predicted` (from forecasting — see below)

### Real Supply Polling

`GridPollingScheduler` (`app/scheduler/grid_polling_scheduler.py`) periodically polls `GRID_API_URL` via `GridAPIClient` for capacity data, and upserts it as `record_type=supply, data_source=real`. It's fail-proof by design: a bad poll cycle (grid unreachable, malformed response, one bad slot in a batch) is logged and skipped — it never crashes the loop or the pod.

Expected response shape from the grid endpoint:

```json
{
  "availability": [
    {
      "slot_start_time": "2026-08-20T18:00:00+00:00",
      "slot_end_time": "2026-08-21T00:00:00+00:00",
      "available_watts": 1500,
      "provider_name": "grid",
      "energy_source_type": "solar",
      "confidence_percentage": 90
    }
  ]
}
```

(This is the same envelope this service's own `/api/energy-availability/future/forecast` endpoint returns.)

### Dev/Test Mock Grid Server

Since there's no real grid API available yet, a lightweight in-cluster stand-in (`charts/app/files/grid_stub.py`) is available for testing — a dependency-free Python `http.server` script holding an in-memory value, exposing:

- `POST /capacity` — set the data it returns
- `GET /capacity` — read the current data back

Deploy it alongside the app:

```bash
./scripts/deploy-app.sh --grid-stub
# or, from the repo root:
bash deploy-full-stack.sh deploy --grid-stub
```

Feed it data (after port-forwarding `svc/grid-stub 8090:80`):

```bash
curl -s -X POST http://localhost:8090/capacity -H "Content-Type: application/json" \
  -d '{"availability":[{"slot_start_time":"2026-08-20T18:00:00+00:00","slot_end_time":"2026-08-21T00:00:00+00:00","available_watts":1500,"provider_name":"grid"}]}'
```

When `gridStub.enabled=true` and `GRID_API_URL` is left empty, the chart auto-points the poller at the stub. Set `GRID_API_URL` explicitly to point at a real grid endpoint instead (this also defaults `gridStub.enabled` to `false`, at the `deploy-full-stack.sh` level, via `--grid-url`).

This is **dev/test only** — never intended for production use.

---

## 📨 Demand Reporting

`energy-aware-operator` reports each EAO custom resource's currently-decided energy demand here, once per reconcile:

- `POST /api/energy-availability/demand` — create/replace the single current demand row for a workload (`identifier` = `<namespace>/<name>`). One row per identifier — a fresh report replaces the previous slot/wattage rather than accumulating history, since a workload only ever has one currently-decided slot.
- `DELETE /api/energy-availability/demand/{identifier}` — soft-deactivate a workload's demand record (called on CR deletion). Returns success (`404`-as-success) even if nothing was there, since the end state — no active demand — is the same either way.

### Demand Resolution: Real vs Predicted vs Estimated

The `required_watts` a report carries (from `spec.energyConsumption`) is only ever the *fallback*. `resolve_demand_watts()` (`app/services/demand_resolution_service.py`) resolves the actually-stored value through three tiers, most accurate first:

1. **Measured** — real Kepler-measured wattage (`ContainerPowerMetricsRepository.get_latest_measured_watts()`), correlated to the workload via the `application_name` field the operator now includes (`spec.applicationRef.name` — pod names are prefixed by their owning Deployment's name).
2. **Predicted** — `EnergyForecastingService`'s trained `RandomForestRegressor` (`app/energy_forecasting_model.pkl`, r²≈0.97), predicting consumption from the workload's live CPU/memory utilization. Used only when direct measurement is momentarily unavailable (e.g. a scrape gap).
3. **Fallback** — `required_watts` verbatim, the operator's static estimate. The only option before deployment, since utilization data can't exist for a workload that isn't running yet.

This mirrors the real-over-predicted precedence already used for supply (see [Supply Forecasting](#-supply-forecasting-predictions)) — never raises, always falls through to a safe value.

The resolved value round-trips back to the operator, which surfaces it on the CR as `status.energyMetrics.measuredWatts` (informational only — `status.energyMetrics.requiredWatts` remains the number the scheduling decision was actually based on).

**Note:** tiers 1–2 depend on `container_power_metrics` actually being populated, which requires `ENABLE_METRICS_SCHEDULER=true` (defaults to `false` in this chart). With it off, every demand report resolves to the fallback tier — confirmed working, but tiers 1–2 are not yet live-verified against real Kepler data (see [Known Limitations](#-known-limitations--next-steps)).

---

## 🔮 Supply Forecasting (Predictions)

For future slots beyond what real grid polling has reached yet, `ForecastingScheduler` (`app/scheduler/forecasting_scheduler.py`) periodically predicts supply and stores it as `record_type=supply, data_source=predicted`.

**How it works today:**
1. For each provider with real supply history, pull the last `LOOKBACK_DAYS` (14) of real data.
2. Group it into the same fixed 6-hour slot-of-day buckets the scheduler uses (`00–06`, `06–12`, `12–18`, `18–24`).
3. Average `available_watts` per bucket, via `PredictionService.predict()` (`app/services/prediction_service.py`).
4. Predict the next `LOOKAHEAD_SLOTS` (8, i.e. 2 days) slots — **only** for buckets that actually have historical data; a bucket with zero history is skipped, never guessed at.
5. Upsert each prediction via `upsert_predicted_supply()` — refreshes the same row on repeat cycles, never touches a real row for the same slot.

**Runs entirely in-process** — no external URL, no separate deployable service. This was a deliberate choice: real ML model-serving infrastructure (SageMaker, Vertex AI, etc.) is always request/response, so the swap point is a function call regardless of whether the model ends up local or hosted (see below).

**Real always wins over predicted at query time.** Since real and predicted rows can coexist independently for the same slot (by design — see migration `4f7cd0a3ac61`), `get_current_availability()`/`get_future_availability()` collapse any slot with both down to just the real row (`_prefer_real_supply()` in `app/repositories/energy_availability.py`), so a caller summing "available capacity" never double-counts a slot.

Config:

| Variable | Default | Purpose |
|---|---|---|
| `ENABLE_FORECASTING` | `true` | Whether the periodic refresh loop runs |
| `FORECASTING_INTERVAL_SECONDS` | `1800` | How often predictions are refreshed |

### How to Swap in a Real ML Model

The entire swap point is `PredictionService.predict()` in `app/services/prediction_service.py`:

```python
def predict(self, history: List[Dict], future_slots: List[Tuple[datetime, datetime]]) -> List[Dict]:
    ...
```

- **Input:** real supply history (`slot_start_time`, `available_watts`) and the future slots to predict for.
- **Output:** one `{slot_start_time, slot_end_time, available_watts}` dict per slot it can confidently predict (skip slots it can't).

Nothing outside this file needs to change — `ForecastingScheduler` only depends on this interface. If the real model:
- **loads locally** (a `.pkl`/`.onnx` file, like the legacy `EnergyForecastingService` pattern) — replace the method body with a local inference call.
- **is hosted externally** (a managed endpoint, a separate microservice) — that's the point to add an HTTP client and a `PREDICTION_API_URL`-style config, following the same pattern as `GridAPIClient`/`GRID_API_URL`. Don't add that infrastructure before it's actually needed.

⚠️ **This is not done yet** — see [Known Limitations](#-known-limitations--next-steps).

---

## 🌐 Accessing the Service

- **API Docs:**
  After deployment, port-forward the service:
  ```bash
  kubectl port-forward -n <namespace> svc/energy-metric-service 8000:8000
  ```
  Open: [http://localhost:8000/docs](http://localhost:8000/docs)

- **PostgreSQL Connection:**
  Get the connection string:
  ```bash
  kubectl get configmap orchestration-api-config -o jsonpath='{.data.databaseURL}'
  ```

---

## 🧹 Uninstallation

### Remove Everything (App + DB)

```bash
# Remove app and DB using scripts
./scripts/deploy-postgres.sh --uninstall
helm uninstall energy-metric-service -n <namespace> || true

# Optionally delete PVC (data loss!)
kubectl delete pvc -n <namespace> -l app=eao-postgres
```

### Remove via Helm

```bash
helm uninstall postgres -n <namespace>
helm uninstall energy-metric-service -n <namespace>
kubectl delete pvc -n <namespace> -l app=eao-postgres
```

---

## 📝 API Endpoints

- **Prometheus Metrics:** `/api/metrics/prometheus/metrics-v2/`
- **Kubernetes APIs:** `/api/kubernetes/`
- **Energy Availability (supply/demand tracking — grid polling, forecasting, demand reporting):** `/api/energy-availability/*` — see [Grid Integration](#-grid-integration), [Demand Reporting](#-demand-reporting), [Supply Forecasting](#-supply-forecasting-predictions)
- **Energy Forecasting (CPU/memory → consumption ML model):** `/energy-forecast/*` — the same trained model backing tier 2 of [Demand Resolution](#demand-resolution-real-vs-predicted-vs-estimated); these HTTP endpoints expose it directly for ad-hoc queries. Not to be confused with supply forecasting above; this predicts a workload's *consumption* from resource utilization, not grid *supply*.
- See [http://localhost:8000/docs](http://localhost:8000/docs) for full OpenAPI docs.

---

## 🐳 Local Development

- Use `docker-compose.yaml` for local dev (optional).
- For Minikube:
  - Start Minikube
  - Start `kubectl proxy`
  - Set environment variables as needed
  - Run the app locally with Uvicorn

---

## ⚠️ Known Limitations & Next Steps

- **Supply forecasting uses a dummy model, not real ML.** `PredictionService` currently just averages historical real supply per slot-of-day bucket — it's a deliberate placeholder with a clean swap interface (see [How to Swap in a Real ML Model](#how-to-swap-in-a-real-ml-model)), not a trained model. **Making this a real model is the next planned step.**
- **Demand resolution tiers 1–2 (measured/predicted) are not yet live-verified.** They depend on `container_power_metrics` being populated, which needs `ENABLE_METRICS_SCHEDULER=true` (default `false`). Only the fallback tier has been confirmed against a real deployment so far — measured and ML-predicted tiers are implemented but still pending a live test with metrics collection turned on.
- **Single-replica migrations.** See [Database Migrations](#-database-migrations) — needs a Helm hook Job if `replicaCount` is ever raised.

---

## Dependencies

- **Python 3.13**
- **FastAPI**: Web framework
- **SQLAlchemy (async) + Alembic**: ORM and migrations
- **httpx**: Async HTTP client (grid polling)
- **Prometheus**: Metrics collection
- **Kubernetes**: Container orchestration
- **Kepler**: Energy consumption monitoring

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Minikube
5. Submit a pull request

---

## 📄 License

[Your License Here]
