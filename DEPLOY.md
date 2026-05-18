# Deployment Guide

## Overview

`deploy-stack.sh` is the single entry-point to deploy and tear down the entire
Energy-Aware Orchestrator platform. It supports two commands:

| Command | What it does |
|---------|-------------|
| `deploy` | Prerequisites check → build images → deploy all 5 components in order |
| `cleanup` | Stop port-forwards → tear down all 5 components in **LIFO** order |

The script is structured with discrete functions for each step, making it easy
to read and maintain.

---

## Projects / Components

| # | Component | What it deploys |
|---|-----------|----------------|
| 1 | `energy-aware-operator` | Docker image build → CRD apply → Helm install |
| 2 | `energy-metric-service` | PostgreSQL (Helm) + FastAPI app (Docker + Helm) |
| 3 | `energy-monitoring-helm-stack` | Kepler, Prometheus, Grafana, cAdvisor via Helm |
| 4 | `orchestrator-library-ui` | Angular dashboard + K8s proxy (Docker + Helm) |
| 5 | `sample workload` | Backing nginx workload + EAO custom resource |

---

## Prerequisites

The script performs a full prerequisites check **before** touching the cluster.
It exits early with a clear error if anything is missing.

### Required tools

| Tool | Purpose |
|------|---------|
| `kubectl` | Used by every sub-script |
| `helm` | All components deploy via Helm |
| `docker` | Operator, metric-service, and UI build Docker images |

### Optional tools

| Tool | Purpose | Effect if missing |
|------|---------|-------------------|
| `uv` | CRD regeneration inside `build.sh` | Skipped; existing CRD YAML is used |
| `kind` | Image loading for kind clusters | Promoted to **required** if context is `kind-*` |
| `minikube` | Docker env for minikube builds | Only needed when minikube is running |

### Cluster checks

- A valid `kubectl config current-context` must exist.
- `kubectl cluster-info` must succeed (cluster reachable, kubeconfig not expired).
- If the context starts with `kind-`, the `kind` CLI must be present.

### Sample output

```
▶  Prerequisites Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Required tools:
  ✔  kubectl              /usr/local/bin/kubectl
  ✔  helm                 /usr/local/bin/helm
  ✔  docker               /usr/local/bin/docker

  Optional tools:
  ✔  uv                   /usr/local/bin/uv
  ~  kind                 not found — only needed for kind clusters
  ✔  minikube             /usr/local/bin/minikube

  Cluster:
  ✔  context              minikube
  ✔  cluster              reachable
  ✔  minikube             running

  Cluster type: minikube
```

---

## Usage

```bash
# Deploy everything (default namespace)
./deploy-stack.sh

# Deploy to a custom namespace
./deploy-stack.sh deploy -n my-namespace

# Override operator image
OPERATOR_IMAGE_REPO=myregistry.io/energy-operator \
OPERATOR_IMAGE_TAG=v1.2.0 \
  ./deploy-stack.sh

# Tear down everything
./deploy-stack.sh cleanup

# Full teardown including CRD and Postgres PVCs
./deploy-stack.sh cleanup --delete-crd --delete-pvc
```

### Options

| Option | Commands | Default | Description |
|--------|----------|---------|-------------|
| `-n, --namespace NS` | both | `default` | Kubernetes namespace |
| `--delete-crd` | cleanup | `false` | Also delete the operator CRD |
| `--delete-pvc` | cleanup | `false` | Also delete PostgreSQL PVCs |

### Environment variable overrides

| Variable | Default | Description |
|----------|---------|-------------|
| `NAMESPACE` | `default` | Equivalent to `-n` |
| `OPERATOR_IMAGE_REPO` | `energy-aware-operator` | Operator Docker image repository |
| `OPERATOR_IMAGE_TAG` | `latest` | Operator Docker image tag |

---

## Deploy — Step-by-Step

### Step 1 — Energy-Aware Operator

Split into two sub-steps; step 1b is skipped automatically if 1a fails.

**1a — Build** (`energy-aware-operator/scripts/build.sh`)
- Detects cluster type (kind / minikube / other).
- For **minikube**: runs `eval $(minikube docker-env)` so the image is built inside minikube's daemon.
- Runs `uv run python -m app.crd.builder` to regenerate the CRD YAML (skipped if `uv` absent).
- Runs `docker build` to produce the operator image.
- For **kind**: runs `kind load docker-image` immediately after build so the image is available in the node.

**1b — Deploy** (`energy-aware-operator/scripts/deploy.sh`)
- Applies the CRD YAML from `charts/energy-aware-operator/crds/`.
- Creates the target namespace if it does not exist.
- Runs `helm upgrade --install` with the built image coordinates.
- Waits up to 5 minutes for the operator pod to become ready.

### Step 2 — Energy Metric Service

Calls `energy-metric-service/scripts/deploy-all.sh` which runs two phases:

1. `deploy-postgres.sh` — installs the custom PostgreSQL Helm chart and waits for the pod.
2. `deploy-app.sh` — builds the FastAPI Docker image, loads it into kind if needed, installs the app Helm chart. Fails fast if PostgreSQL is not running.

### Step 3 — Energy Monitoring Helm Stack

Calls `energy-monitoring-helm-stack/scripts/deploy.sh` which:
- Runs `helm dependency update` to pull Kepler, Prometheus, and Grafana sub-charts.
- Installs the umbrella chart with `--wait --timeout 10m`.

### Step 4 — Orchestrator Library UI

Calls `orchestrator-library-ui/scripts/deploy.sh` which:
- Auto-detects build strategy:
  - **Fast build** (~30 s): uses `Dockerfile.prebuilt` when `dist/` already exists.
  - **Full build** (~5–10 min): uses the multi-stage `Dockerfile` when `dist/` is absent.
- Loads the image into kind if needed.
- Installs the Helm chart for both the Angular app and the K8s proxy sidecar.

### Step 5 — Sample Testing Workload

Skipped automatically if the operator (step 1) did not deploy successfully.

- Applies `workload/workload_k8s_critical_testing.yaml` — backing nginx Deployment + Service.
- Applies `workload/workload_cr_eao_critical_testing.yaml` — the EAO custom resource.
- Waits 5 seconds and prints the current EAO resource status.

---

## Cleanup — Step-by-Step

Cleanup runs in **LIFO order** (reverse of deploy) so dependencies are removed last.

| Step | Component | Script called |
|------|-----------|--------------|
| 1 | Sample workload | `kubectl delete -f workload/…` |
| 2 | Orchestrator Library UI | `orchestrator-library-ui/scripts/cleanup.sh` |
| 3 | Energy Monitoring Stack | `energy-monitoring-helm-stack/scripts/cleanup.sh` |
| 4 | Energy Metric Service | `energy-metric-service/scripts/cleanup.sh` |
| 5 | Energy-Aware Operator | `energy-aware-operator/scripts/cleanup.sh` |

Port-forwards are killed first, before any cluster resources are removed.

### Cleanup flags

| Flag | Effect |
|------|--------|
| `--delete-crd` | Passes `--delete-crd` to the operator cleanup script, removing the `EnergyAwareOrchestration` CRD |
| `--delete-pvc` | Passes `--delete-pvc` to the metric-service cleanup script, deleting PostgreSQL PVCs |

> By default both CRD and PVCs are **kept** so you can redeploy without losing data.

---

## Deployment Summary

```
  DEPLOYMENT SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  energy-aware-operator (build)              ✔  OK
  energy-aware-operator (deploy)             ✔  OK
  energy-metric-service (pg + api)           ✔  OK
  energy-monitoring-helm-stack               ✔  OK
  orchestrator-library-ui                    ✔  OK
  sample workload (critical-testing)         ✔  OK
```

## Cleanup Summary

```
  CLEANUP SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  sample workload (critical-testing)         ✔  OK
  orchestrator-library-ui                    ✔  OK
  energy-monitoring-helm-stack               ✔  OK
  energy-metric-service (pg + api)           ✔  OK
  energy-aware-operator                      ✔  OK
```

---

## Port Forwarding

Port-forwarding is **not executed automatically**. After `deploy`, the script
prints a ready-to-paste block. Run it in your terminal:

```bash
# Step 1 — Kill existing port-forwards for this stack
pkill -f 'svc/energy-metric-service'            || true
pkill -f 'svc/eao-postgres'                     || true
pkill -f 'svc/energy-metrics-grafana'           || true
pkill -f 'svc/energy-metrics-prometheus-server' || true
pkill -f 'svc/energy-metrics-kepler'            || true
pkill -f 'svc/aces-orchestrator-library-ui'     || true
pkill -f 'svc/aces-orchestrator-k8s-proxy'      || true

# Step 2 — Start all in the background at once
kubectl port-forward -n default svc/energy-metric-service 8000:8000 &
kubectl port-forward -n default svc/eao-postgres 5432:5432 &
kubectl port-forward -n default svc/energy-metrics-grafana 3000:80 &
kubectl port-forward -n default svc/energy-metrics-prometheus-server 9090:80 &
kubectl port-forward -n default svc/energy-metrics-kepler 9102:9102 &
kubectl port-forward -n default svc/aces-orchestrator-library-ui 4200:80 &
kubectl port-forward -n default svc/aces-orchestrator-k8s-proxy 3001:3000 &
```

> K8s Proxy uses local port `3001` (not `3000`) to avoid conflict with Grafana.

### Stop all port-forwards

```bash
pkill -f 'kubectl port-forward' || true
```

---

## Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Energy Metric Service API | http://localhost:8000/docs | — |
| Energy Metric Service Redoc | http://localhost:8000/redoc | — |
| PostgreSQL | localhost:5432 | user: `postgres` / db: `orchestration_db` |
| Grafana | http://localhost:3000 | `admin` / `admin` |
| Prometheus | http://localhost:9090 | — |
| Kepler Metrics | http://localhost:9102/metrics | — |
| Orchestrator Library UI | http://localhost:4200 | — |
| K8s Proxy | http://localhost:3001 | — |

---

## Troubleshooting

### Prerequisites check fails

The script prints the exact missing tool and exits before touching the cluster.
Install it and re-run.

### Operator build fails (step 1a)

Step 1b (Helm deploy) is skipped automatically and shown as `FAILED` in the
summary. Fix the build error and re-run the full stack or just the operator:

```bash
IMAGE_REPOSITORY=energy-aware-operator IMAGE_TAG=latest \
  bash energy-aware-operator/scripts/build.sh
```

### Kind — ImagePullBackOff after build

`build.sh` loads the image into kind immediately after `docker build`. If you
still see `ImagePullBackOff`, the image may be stale. Re-run the build step above.

### Minikube — image not found

`build.sh` auto-detects minikube and runs `eval $(minikube docker-env)` before
the build. Make sure minikube is running before deploying.

### Pod stuck / timed out

```bash
kubectl get pods -n default
kubectl describe pod <pod-name> -n default
kubectl logs <pod-name> -n default
```

### Cleanup leaves orphaned resources

Use the extended cleanup flags for a full teardown:

```bash
./deploy-stack.sh cleanup --delete-crd --delete-pvc
```
