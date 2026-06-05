# Energy-Aware Orchestrator

A Kubernetes platform that schedules workloads based on real-time and forecasted energy availability. It collects node-level power consumption data, exposes an ML-backed forecast API, and uses a custom operator to decide when each workload should run — favouring slots with cheap or renewable energy.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Kubernetes Cluster                              │
│                                                                          │
│  ┌─────────────────────┐        ┌──────────────────────────────────┐   │
│  │  energy-aware-      │  calls │  energy-metric-service           │   │
│  │  operator           │───────▶│  (FastAPI + PostgreSQL)          │   │
│  │  (Kopf / Python)    │        │  /api/energy-availability/...    │   │
│  │                     │        └──────────────┬───────────────────┘   │
│  │  Watches EAO CRDs   │                       │ reads                  │
│  │  Schedules workloads│        ┌──────────────▼───────────────────┐   │
│  └─────────────────────┘        │  energy-monitoring-helm-stack    │   │
│                                  │  Kepler → Prometheus → Grafana  │   │
│  ┌─────────────────────┐        └──────────────────────────────────┘   │
│  │  orchestrator-      │                                                │
│  │  library-ui         │  ◀─────── talks to energy-metric-service      │
│  │  (Angular 20 + Nx)  │          via K8s proxy                        │
│  └─────────────────────┘                                                │
│                                                                          │
│  ┌─────────────────────┐                                                │
│  │  workload/          │  ◀─────── EAO CRs applied by the user         │
│  │  (sample manifests) │                                                │
│  └─────────────────────┘                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data flow

```
Node hardware
    │  (eBPF / RAPL / ACPI)
    ▼
Kepler  ──▶  Prometheus  ──▶  energy-metric-service  ──▶  PostgreSQL
                                       │
                         ML forecasting model (.pkl)
                                       │
                                       ▼
                          energy-aware-operator
                          (scheduling decisions)
                                       │
                                       ▼
                         EAO CR status updated
                         (DeployImmediately / Scheduled)
```

---

## Components

### 1 · `energy-aware-operator`

A Kubernetes operator written in Python using the [Kopf](https://kopf.readthedocs.io/) framework. It watches `EnergyAwareOrchestration` (EAO) custom resources and calculates when each workload should run.

**Scheduling priorities:**

| Priority | Behaviour |
|----------|-----------|
| `Critical` | Deploy immediately — no energy checks |
| `Preferred` | Deploy now if energy is sufficient; otherwise schedule for the next 6-hour slot |
| `Optional` | Find the optimal slot in the next 24 hours |

The operator re-evaluates every 10 minutes (configurable) and updates the CR status with the scheduling decision.

→ [energy-aware-operator/README.md](energy-aware-operator/README.md)

---

### 2 · `energy-metric-service`

A FastAPI service that acts as the energy data backend for the operator and the UI.

- Scrapes Kepler energy metrics from Prometheus on a schedule and persists them in PostgreSQL.
- Exposes a REST API including `/api/energy-availability/future/forecast` which the operator calls.
- Contains a pre-trained **Linear Regression** model (`energy_forecasting_linear_regression.pkl`) trained on node CPU/memory metrics to predict energy consumption in Watts.
- Includes a Jupyter notebook (`energy_forecasting_model.ipynb`) and training script (`train_model.py`) for retraining the model.

**Helm charts included:**

| Chart | Purpose |
|-------|---------|
| `charts/app` | FastAPI application |
| `charts/postgres` | Custom PostgreSQL StatefulSet |

→ [energy-metric-service/README.md](energy-metric-service/README.md)

---

### 3 · `energy-monitoring-helm-stack`

An umbrella Helm chart that deploys the full observability stack for energy monitoring.

| Component | Version | Purpose |
|-----------|---------|---------|
| Kepler | 0.6.0 | eBPF-based node energy metrics collector |
| Prometheus | 25.21.0 | Metrics storage and PromQL queries |
| Grafana | 7.3.9 | Dashboards and visualisation |
| Node Exporter | 4.24.0 | Host-level CPU/memory metrics |

Pre-built Grafana dashboards are included in `dashboards/`:
- `pod-node-energy-dashboard.json` — pod & node energy with CPU/memory overlays
- `simple-kepler-dashboard.json` — minimal energy consumption view

→ [energy-monitoring-helm-stack/README.md](energy-monitoring-helm-stack/README.md)

---

### 4 · `orchestrator-library-ui`

An Angular 20 + Nx frontend dashboard.

**Key routes:**

| Route | Purpose |
|-------|---------|
| `/energy-metrics` | Real-time energy consumption charts (default page) |
| `/emdc/workloads/system-utilization` | Node CPU & memory utilisation |
| `/emdc/workloads/workload-deployment` | View and manage deployed workloads |
| `/emdc/workloads/register-workload` | Register a new EAO workload |

The app talks to `energy-metric-service` through an nginx proxy (`orchestrator-k8s-proxy`). In development it reads API endpoints from `.env.local`; in production it proxies via relative paths (`/api`, `/app`).

→ [orchestrator-library-ui/README.md](orchestrator-library-ui/README.md)

---

### 5 · `workload/`

Sample Kubernetes manifests for testing the operator end-to-end.

```
workload/
├── workload_cr_eao_critical.yaml   # EAO CR — Critical priority
├── workload_cr_eao_preferred.yaml  # EAO CR — Preferred priority
├── workload_cr_eao_optional.yaml   # EAO CR — Optional priority
├── workload_k8s_critical.yaml      # Backing Deployment for Critical
├── workload_k8s_preferred.yaml     # Backing Deployment for Preferred
└── workload_k8s_optional.yaml      # Backing Deployment for Optional
```

Apply with:

```bash
kubectl apply -f workload/workload_k8s_preferred.yaml
kubectl apply -f workload/workload_cr_eao_preferred.yaml
kubectl get eao
```

---

## Quick Start

See **[DEPLOY.md](DEPLOY.md)** for the full deployment guide.

```bash
# Deploy the entire stack in one command
./deploy-full-stack.sh
```

The script will:
1. Run a prerequisites check (`kubectl`, `helm`, `docker`, cluster reachability, cluster type)
2. Build + load the operator Docker image and deploy it via Helm
3. Deploy PostgreSQL and the energy-metric-service
4. Deploy the Kepler / Prometheus / Grafana monitoring stack
5. Build and deploy the Angular UI
6. Print port-forwarding commands and access URLs

---

## Repository Layout

```
energy-aware-orchestrator/
├── deploy-full-stack.sh                  # One-command full-stack deployment
├── DEPLOY.md                        # Deployment guide (prerequisites, steps, troubleshooting)
├── README.md                        # This file
│
├── energy-aware-operator/           # Kubernetes operator (Python / Kopf)
├── energy-metric-service/           # Energy API + forecasting (FastAPI / PostgreSQL)
├── energy-monitoring-helm-stack/    # Observability stack (Kepler / Prometheus / Grafana)
├── orchestrator-library-ui/         # Web dashboard (Angular 20 / Nx)
└── workload/                        # Sample EAO custom resources and workload manifests
```

---

## Service URLs (after port-forwarding)

| Service | URL | Notes |
|---------|-----|-------|
| Orchestrator UI | http://localhost:4200 | Angular dashboard |
| Energy Metric API | http://localhost:8000/docs | FastAPI Swagger |
| Grafana | http://localhost:3000 | `admin` / `admin` |
| Prometheus | http://localhost:9090 | — |
| Kepler Metrics | http://localhost:9102/metrics | Raw eBPF metrics |
| PostgreSQL | localhost:5432 | `postgres` / `postgres` / `orchestration_db` |
| K8s Proxy | http://localhost:3001 | UI backend proxy |
