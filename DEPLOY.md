# Deployment Guide

## Overview

`deploy-stack.sh` is the single entry-point to deploy the entire Energy-Aware Orchestrator platform.
It runs a prerequisites check, deploys all four projects in order, tracks the status of each, and
prints ready-to-run port-forwarding commands at the end.

## Projects Deployed

| # | Project | What it deploys |
|---|---------|----------------|
| 1 | `energy-aware-operator` | Docker image build → CRD apply → Helm install |
| 2 | `energy-metric-service` | PostgreSQL (Helm) + FastAPI app (Docker + Helm) |
| 3 | `energy-monitoring-helm-stack` | Kepler, Prometheus, Grafana, cAdvisor via Helm |
| 4 | `orchestrator-library-ui` | Angular dashboard + K8s proxy (Docker + Helm) |

---

## Prerequisites

The script performs a full prerequisites check **before** touching the cluster. It will exit early
with a clear error if anything is missing.

### Required tools

| Tool | Purpose |
|------|---------|
| `kubectl` | Used by every sub-script |
| `helm` | All four services deploy via Helm |
| `docker` | Operator, metric-service, and UI build Docker images |

### Optional tools

| Tool | Purpose | Effect if missing |
|------|---------|-------------------|
| `uv` | CRD generation inside `build.sh` | CRD regeneration is skipped; existing CRD YAML is used |
| `kind` | Image loading for kind clusters | Promoted to **required** if the current kubeconfig context is a kind cluster |
| `minikube` | Docker environment for minikube clusters | Only needed when minikube is running |

### Cluster checks

- A valid `kubectl config current-context` must exist.
- `kubectl cluster-info` must succeed (cluster reachable, kubeconfig not expired).
- If the context name starts with `kind-`, the `kind` CLI must be present.

### What the check output looks like

```
▶  Prerequisites Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Required tools:
  ✔  kubectl              /usr/local/bin/kubectl
  ✔  helm                 /usr/local/bin/helm
  ✔  docker               /usr/local/bin/docker

  Optional tools:
  ✔  uv                   /usr/local/bin/uv
  ~  kind                 not found — only needed if using a kind cluster
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
# Deploy to default namespace
./deploy-stack.sh

# Deploy to a custom namespace
NAMESPACE=my-namespace ./deploy-stack.sh

# Override the operator image (e.g. for a registry push)
OPERATOR_IMAGE_REPO=myregistry.io/energy-operator OPERATOR_IMAGE_TAG=v1.2.0 ./deploy-stack.sh
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NAMESPACE` | `default` | Kubernetes namespace for all deployments |
| `OPERATOR_IMAGE_REPO` | `energy-aware-operator` | Docker image repository for the operator |
| `OPERATOR_IMAGE_TAG` | `latest` | Docker image tag for the operator |

---

## Deployment Steps (detail)

### Step 1 — Energy-Aware Operator

The operator deployment is split into two explicit sub-steps.

#### 1a — Build (`energy-aware-operator/scripts/build.sh`)

- Detects the cluster type (kind / minikube / other).
- For **minikube**: runs `eval $(minikube docker-env)` so the image is built directly inside
  minikube's Docker daemon and is immediately available in the cluster.
- Runs `uv run python -m app.crd.builder` to regenerate the CRD YAML (skipped if `uv` is absent).
- Runs `docker build` to produce the operator image.
- For **kind**: runs `kind load docker-image <image> --name <cluster>` after the build so the image
  is loaded into the kind node. This matches the minikube behaviour — by the time `build.sh` exits
  the image is already inside the cluster.

#### 1b — Deploy (`energy-aware-operator/scripts/deploy.sh`)

- Applies the CRD YAML (`charts/energy-aware-operator/crds/energy-aware-orchestration-crd.yaml`).
- Creates the target namespace if it does not exist.
- Runs `helm upgrade --install` with the built image coordinates.
- Waits up to 5 minutes for the operator pod to become ready.

Step 1b is skipped automatically if step 1a fails.

### Step 2 — Energy Metric Service

Calls `energy-metric-service/scripts/deploy-all.sh` which runs in two phases:

1. `deploy-postgres.sh` — installs the custom PostgreSQL Helm chart and waits for the pod.
2. `deploy-app.sh` — builds the FastAPI Docker image, loads it into kind if needed, and installs
   the app Helm chart. Fails fast if PostgreSQL is not running.

### Step 3 — Energy Monitoring Helm Stack

Calls `energy-monitoring-helm-stack/scripts/deploy.sh` which:

- Runs `helm dependency update` to pull Kepler, Prometheus, and Grafana sub-charts.
- Installs the umbrella chart with `--wait --timeout 10m`.

### Step 4 — Orchestrator Library UI

Calls `orchestrator-library-ui/scripts/deploy.sh` which:

- Auto-detects the build strategy:
  - **Fast build** (~30 s): uses `Dockerfile.prebuilt` when `dist/` already exists.
  - **Full build** (~5–10 min): uses the multi-stage `Dockerfile` when `dist/` is absent.
- Loads the image into kind if needed.
- Installs the Helm chart for both the Angular app and the K8s proxy sidecar.

---

## Deployment Summary

After all steps complete the script prints a summary table:

```
  DEPLOYMENT SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  energy-aware-operator (build)              ✔  OK
  energy-aware-operator (deploy)             ✔  OK
  energy-metric-service (pg + api)           ✔  OK
  energy-monitoring-helm-stack               ✔  OK
  orchestrator-library-ui                    ✔  OK
```

The operator build and deploy are tracked separately so you can tell at a glance whether a failure
was in the image build phase or the Helm deploy phase.

---

## Port Forwarding

Port-forwarding is **not executed automatically**. After deployment, copy the printed block and run
it manually in a terminal:

```bash
# Kill any existing port-forwards
pkill -f 'kubectl port-forward' || true

# Start all in the background at once
kubectl port-forward -n default svc/energy-metric-service 8000:8000 &
kubectl port-forward -n default svc/eao-postgres 5432:5432 &
kubectl port-forward -n default svc/energy-metrics-grafana 3000:80 &
kubectl port-forward -n default svc/energy-metrics-prometheus-server 9090:80 &
kubectl port-forward -n default svc/energy-metrics-kepler 9102:9102 &
kubectl port-forward -n default svc/aces-orchestrator-library-ui 4200:80 &
kubectl port-forward -n default svc/aces-orchestrator-k8s-proxy 3001:3000 &
```

> K8s Proxy uses local port `3001` (not `3000`) to avoid conflict with Grafana.

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

## Stop Port Forwards

```bash
pkill -f 'kubectl port-forward' || true
```

---

## Troubleshooting

### Prerequisites check fails

The script prints the exact tool that is missing and exits before making any cluster changes.
Install the missing tool and re-run.

### Operator build fails but deploy shows PENDING

If step 1a (`build`) fails, step 1b (`deploy`) is skipped automatically and its status is set to
`FAILED` in the summary. Fix the build error and re-run.

### Kind cluster — image not found after build

`build.sh` now loads the image into kind immediately after `docker build`. If you see an
`ImagePullBackOff` in kind, re-run the build step:

```bash
IMAGE_REPOSITORY=energy-aware-operator IMAGE_TAG=latest \
  bash energy-aware-operator/scripts/build.sh
```

### Minikube cluster — image not found

`build.sh` auto-detects minikube and runs `eval $(minikube docker-env)` before the build, so the
image is built directly inside minikube. If minikube was not running at build time, start it and
re-run.

### Deployment stuck or timed out

Check pod events in the failing namespace:

```bash
kubectl get pods -n default
kubectl describe pod <pod-name> -n default
kubectl logs <pod-name> -n default
```
