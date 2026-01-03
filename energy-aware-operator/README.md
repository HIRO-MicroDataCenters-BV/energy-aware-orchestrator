# Energy-Aware Kubernetes Operator

A Kubernetes operator that enables intelligent workload scheduling based on energy availability and cost.

---

## What Does This Do?

This operator watches for **EnergyAwareOrchestration** custom resources and automatically:

1. **Schedules workloads** during optimal energy availability windows
2. **Prioritizes tasks** based on criticality (Critical, Preferred, Optional)
3. **Integrates with energy services** to get real-time energy availability data
4. **Updates application deployments** based on energy schedules

### Example Use Case

> "Run my batch processing job only when renewable energy is available and electricity is cheap"

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Energy-Aware Operator (this project)              │    │
│  │                                                     │    │
│  │  ┌──────────────┐                                  │    │
│  │  │   Operator   │  Watches CRDs                    │    │
│  │  │   (Kopf)     │◄──────────────────┐              │    │
│  │  └──────────────┘                   │              │    │
│  │         │                            │              │    │
│  │         │ Calls                      │              │    │
│  │         ▼                            │              │    │
│  │  ┌──────────────┐            ┌──────────────┐     │    │
│  │  │  Scheduler   │            │     CRD      │     │    │
│  │  │   Service    │            │   (EAO)      │     │    │
│  │  └──────────────┘            └──────────────┘     │    │
│  │         │                                          │    │
│  │         │ Updates                                  │    │
│  │         ▼                                          │    │
│  │  ┌──────────────┐                                 │    │
│  │  │  Status      │                                 │    │
│  │  │  Handler     │                                 │    │
│  │  └──────────────┘                                 │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Your Applications                          │    │
│  │  (Managed based on energy schedules)               │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ Queries energy data
                         ▼
              ┌──────────────────────┐
              │  Energy Metric       │
              │  Service (external)  │
              └──────────────────────┘
```

### Components

| Component | Purpose |
|-----------|---------|
| **Operator** | Main reconciliation loop using Kopf framework |
| **CRD** | Custom Resource Definition for EnergyAwareOrchestration |
| **Scheduler** | Calculates optimal execution schedules |
| **Handlers** | Validation, status updates, and event posting |
| **ConfigMap** | Operator configuration |

---

## What Gets Installed

- **Custom Resource Definition**: `energyawareorchestrations.eas.hiro.io`
- **Operator Deployment**: 1 pod running the reconciliation loop
- **ServiceAccount + RBAC**: Permissions to watch and manage resources
- **ConfigMap**: Operator configuration

---

## Quick Install

### Prerequisites

- Kubernetes cluster (minikube, kind, or any k8s cluster)
- kubectl configured
- Docker (for building the image)

### Install

```bash
./install.sh
```

That's it! The script will:
- ✅ Build the Docker image
- ✅ Apply the CRD
- ✅ Deploy the operator with Helm
- ✅ Wait until ready

### Verify Installation

```bash
# Check operator is running
kubectl get pods -l app.kubernetes.io/name=energy-aware-operator

# Should show:
# NAME                                     READY   STATUS    RESTARTS   AGE
# energy-operator-energy-aware-...         1/1     Running   0          30s

# Check CRD is installed
kubectl get crd energyawareorchestrations.eas.hiro.io
```

---

## Usage

### Create an Energy-Aware Orchestration

```yaml
# sample-eao.yaml
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: batch-processing-job
spec:
  priority: preferred              # critical | preferred | optional
  energyConsumption: 1000          # Estimated watts
  minDuration: 7200                # Minimum 2 hours
  applicationRef:
    apiVersion: apps/v1
    kind: Deployment
    name: batch-processor
    namespace: default
  schedule:
    type: daily
    preferredStartTime: "02:00:00"
    preferredEndTime: "06:00:00"
```

Apply it:
```bash
kubectl apply -f sample-eao.yaml
```

### Check Status

```bash
# View all energy-aware orchestrations
kubectl get eao

# Describe to see schedule and status
kubectl describe eao batch-processing-job

# Watch operator logs
kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator
```

### Example Output

```bash
$ kubectl get eao
NAME                   PRIORITY    PHASE       AGE
batch-processing-job   preferred   Scheduled   5m

$ kubectl describe eao batch-processing-job
...
Status:
  Execution Schedule:
    Schedule:
      Date: 2026-01-04
      Times:
        Cost: 0.05
        Start: 02:00:00
        Stop: 06:00:00
    Updated: 2026-01-03T10:30:00Z
  Phase: Scheduled
...
```

---

## Local Development

### Build the Image

```bash
./scripts/build.sh
```

### Deploy

```bash
./scripts/deploy.sh
```

### View Logs

```bash
kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator
```

---

## Helm Installation

### Option 1: Simple Install (Recommended)

```bash
./install.sh
```

### Option 2: Manual Helm Install

```bash
# Build image first
./scripts/build.sh

# Install with Helm
helm install energy-operator ./charts/energy-aware-operator \
  --set image.repository=energy-aware-operator \
  --set image.tag=latest \
  --set image.pullPolicy=Never
```

### Option 3: Deploy to Custom Namespace

```bash
./scripts/deploy.sh -n my-namespace
```

### Option 4: Production Deployment

```bash
# Build and push to registry
./scripts/build.sh \
  --image-repo myregistry.io/energy-operator \
  --image-tag v1.0.0 \
  --push

# Deploy from registry
./scripts/deploy.sh \
  -n production \
  --image-repo myregistry.io/energy-operator \
  --image-tag v1.0.0 \
  --pull-policy Always
```

### Helm Configuration

Edit `charts/energy-aware-operator/values.yaml`:

```yaml
configuration:
  log_level: DEBUG                           # INFO | DEBUG | WARNING | ERROR
  reconcile_interval_seconds: 300            # How often to re-evaluate
  energy_api_url: "http://your-api:8000"    # Your energy service

resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

Then deploy:
```bash
helm upgrade energy-operator ./charts/energy-aware-operator
```

---

## Uninstall

### Simple Uninstall

```bash
./uninstall.sh
```

### Manual Uninstall

```bash
# Delete custom resources
kubectl delete eao --all

# Uninstall Helm release
helm uninstall energy-operator

# Delete CRD (optional)
kubectl delete crd energyawareorchestrations.eas.hiro.io
```

---

## 🔧 Configuration

### Operator Configuration

Edit `charts/energy-aware-operator/values.yaml`:

```yaml
configuration:
  # Logging level
  log_level: INFO
  
  # How often to re-evaluate schedules (seconds)
  reconcile_interval_seconds: 600
  
  # Energy API endpoint (optional)
  energy_api_url: "http://energy-metric-service:8000"
  
  # CRD configuration
  api_group: "eas.hiro.io"
  api_version: "v1"
  plural: "energyawareorchestrations"
```

### Resource Limits

```yaml
resources:
  requests:
    cpu: 100m      # Minimum CPU
    memory: 128Mi  # Minimum memory
  limits:
    cpu: 200m      # Maximum CPU
    memory: 256Mi  # Maximum memory
```

### Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10
```

---

## Priority Levels

| Priority | Behavior | Use Case |
|----------|----------|----------|
| **critical** | Must run regardless of energy cost | Production services, safety systems |
| **preferred** | Run when energy is available/cheap | Batch processing, data analysis |
| **optional** | Run only when excess energy available | Nice-to-have tasks, cleanup jobs |

---

## Monitoring

### Check Operator Health

```bash
# Port forward to health endpoint
kubectl port-forward svc/energy-operator-energy-aware-operator 8080:8080

# Check health
curl http://localhost:8080/healthz

# Check metrics (if enabled)
curl http://localhost:8080/metrics
```

### View Events

```bash
# All events
kubectl get events --sort-by='.lastTimestamp'

# Events for specific resource
kubectl describe eao batch-processing-job
```

### View Logs

```bash
# Follow logs
kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator

# Last 100 lines
kubectl logs -l app.kubernetes.io/name=energy-aware-operator --tail=100

# Specific pod
kubectl logs energy-operator-energy-aware-operator-xxxxx-xxxxx
```

---

## Troubleshooting

### Operator Not Starting

```bash
# Check pod status
kubectl describe pod -l app.kubernetes.io/name=energy-aware-operator

# Check logs
kubectl logs -l app.kubernetes.io/name=energy-aware-operator

# Common fix: rebuild image
./scripts/build.sh
kubectl delete pod -l app.kubernetes.io/name=energy-aware-operator
```


## Testing

### Run Sample Resource

```bash
# Apply sample
kubectl apply -f examples/sample-eao.yaml

# Check it was created
kubectl get eao

# Watch operator process it
kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator

# Check status
kubectl describe eao sample-eao
```

## Quick Reference

```bash
# Install
./install.sh

# Check status
kubectl get pods -l app.kubernetes.io/name=energy-aware-operator

# View logs
kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator

# Apply sample
kubectl apply -f examples/sample-eao.yaml

# Check resources
kubectl get eao

# Uninstall
./uninstall.sh
```
