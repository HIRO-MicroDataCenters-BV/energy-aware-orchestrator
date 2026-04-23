# Deployment Guide

## Overview

`deploy-stack.sh` is the single entry-point to deploy the entire Energy-Aware Orchestrator platform. It deploys all four projects in order, tracks the status of each, and prints ready-to-run port-forwarding commands at the end.

## Projects Deployed

| # | Project | What it deploys |
|---|---------|----------------|
| 1 | `energy-aware-operator` | Kubernetes operator + CRD via Helm |
| 2 | `energy-metric-service` | PostgreSQL (Helm) + FastAPI app (Docker + Helm) |
| 3 | `energy-monitoring-helm-stack` | Kepler, Prometheus, Grafana, cAdvisor via Helm |
| 4 | `orchestrator-library-ui` | Angular dashboard + K8s proxy (Docker + Helm) |

## Prerequisites

- `kubectl` connected to a running cluster (kind or minikube)
- `helm` installed
- `docker` installed (for image builds)

## Usage

```bash
# Deploy to default namespace
./deploy-stack.sh

# Deploy to a custom namespace
NAMESPACE=my-namespace ./deploy-stack.sh
```

After the script finishes it prints:
1. A **deployment summary** — shows OK / FAILED per project
2. A **port-forwarding block** — paste it in your terminal to access services locally
3. An **access URL table** — all service URLs with credentials

## Port Forwarding

Port-forwarding is **not executed automatically**. After deployment, copy the printed block and run it manually:

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

## Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Energy Metric Service API | http://localhost:8000/docs | — |
| PostgreSQL | localhost:5432 | user: `postgres` / db: `orchestration_db` |
| Grafana | http://localhost:3000 | `admin` / `admin` |
| Prometheus | http://localhost:9090 | — |
| Kepler Metrics | http://localhost:9102/metrics | — |
| Orchestrator Library UI | http://localhost:4200 | — |
| K8s Proxy | http://localhost:3001 | — |

## Stop Port Forwards

```bash
pkill -f 'kubectl port-forward' || true
```
