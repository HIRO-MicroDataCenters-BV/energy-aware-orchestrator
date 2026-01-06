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

## Priority Levels

Understanding how the operator schedules workloads based on priority:

| Priority | Scheduling Behavior | Energy Check | Use Case | Examples |
|----------|---------------------|-----------|----------|----------|
| **Critical** |  Deploy immediately (24/7)<br/>No delays, no energy checks |  No | Mission-critical services that must run regardless of cost | • Production APIs<br/>• Payment systems<br/>• Safety-critical services<br/>• Real-time monitoring |
| **Preferred** |  Deploy now if energy sufficient<br/>Otherwise schedule for next available slot (6h) |  Yes | Important workloads that should run when energy is available | • ML training jobs<br/>• Data processing<br/>• Report generation<br/>• Database backups |
| **Optional** |  Wait for optimal energy window<br/>Schedule for best slot in 24h period |  Yes | Low-priority tasks that can wait for cheapest/cleanest energy | • Batch processing<br/>• Cleanup jobs<br/>• Analytics<br/>• Archive tasks |

### Scheduling Logic Flow

```
Critical:   User Request → Deploy Immediately (No Energy Check)
                         ↓
                    Status: Scheduled (Action: DeployImmediately)

Preferred:  User Request → Check Current Energy
                         ↓
            ┌────────────┴────────────┐
            ↓                         ↓
      Sufficient?                 Insufficient?
            ↓                         ↓
    Deploy Now              Find Next Slot (6h+)
            ↓                         ↓
    Action: DeployImmediately   Action: Scheduled
    
Optional:   User Request → Find Best Slot in 24h
                         ↓
                   Schedule for Optimal Time
                         ↓
                   Action: Scheduled
```


### Create an Energy-Aware Orchestration

The operator supports three priority levels, each with different scheduling behavior:

#### 1. Critical Workload - Always On (24/7)

**Use Case:** Production services, APIs, safety-critical systems that must run regardless of energy cost.

```yaml
# critical-workload.yaml
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: critical-api-service
  namespace: default
spec:
  # Energy consumption in Watts
  energyConsumption: 100
  
  # Forecast window (1-30 days)
  forecastWindowDays: 14
  
  # Priority: Critical = Deploy immediately, always on
  priority: Critical
  
  # Application reference
  applicationRef:
    name: api-gateway
    namespace: production
```

**Expected Behavior:**
-  **Immediate Deployment**: No energy checks performed
-  **24/7 Operation**: Runs continuously regardless of energy availability
-  **No Delays**: Bypasses all energy scheduling logic
-  **Status**: `phase: Scheduled`, `action: DeployImmediately`

**Expected Status:**
```yaml
status:
  phase: Scheduled
  decision:
    action: DeployImmediately
    reason: "Critical priority workload - deploying immediately for 24/7 operation"
  energyMetrics:
    requiredWatts: 100
    sufficient: true
  lastUpdated: "2026-01-06T10:30:00Z"
```

---

#### 2. Preferred Workload - Schedule When Energy Available

**Use Case:** Important batch jobs, ML training, data processing that should run when energy is available but can be delayed if needed.

```yaml
# preferred-workload.yaml
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: ml-training-job
  namespace: default
spec:
  energyConsumption: 500
  forecastWindowDays: 7
  
  # Priority: Preferred = Run when energy sufficient, else delay
  priority: Preferred
  
  applicationRef:
    name: ml-training-deployment
    namespace: default
```

**Expected Behavior:**
-  **Energy Check**: Fetches current and future energy availability
-  **If Sufficient Now**: Deploys immediately
-  **If Insufficient Now**: Schedules for next 6-hour slot with sufficient energy
-  **Re-evaluation**: Checks again after 10 minutes (configurable)
-  **Status**: `phase: Scheduled`, `action: DeployImmediately` or `Scheduled`

**Expected Status (Sufficient Energy):**
```yaml
status:
  phase: Scheduled
  decision:
    action: DeployImmediately
    reason: "Preferred priority - current slot has sufficient energy (15000W >= 500W)"
  energyMetrics:
    currentSlotAvailableWatts: 15000
    requiredWatts: 500
    sufficient: true
  lastUpdated: "2026-01-06T14:00:00Z"
```

**Expected Status (Insufficient Energy - Scheduled for Later):**
```yaml
status:
  phase: Scheduled
  decision:
    action: Scheduled
    reason: "Preferred priority - scheduled for first sufficient energy slot (18000W >= 500W)"
    scheduledSlot:
      slotNumber: 3
      slotStart: "2026-01-06T12:00:00Z"
      slotEnd: "2026-01-06T18:00:00Z"
      availableEnergyWatts: 18000
      requiredEnergyWatts: 500
      confidencePercentage: 85.5
    nextEvaluationTime: "2026-01-06T12:00:00Z"
  lastUpdated: "2026-01-06T08:30:00Z"
```

---

#### 3. Optional Workload - Run Only During Optimal Energy

**Use Case:** Low-priority tasks, cleanup jobs, non-urgent analytics that should only run during excess/cheap energy periods.

```yaml
# optional-workload.yaml
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: batch-processing-job
  namespace: default
spec:
  energyConsumption: 200
  forecastWindowDays: 3
  
  # Priority: Optional = Wait for best energy availability in 24h window
  priority: Optional
  
  applicationRef:
    name: batch-processor
    namespace: default
```

**Expected Behavior:**
-  **Find Best Slot**: Scans next 24 hours for optimal energy availability
- ️ **Skip Current Slot**: Does not deploy in current slot (waits for better timing)
-  **Maximize Efficiency**: Schedules for slot with highest available energy
-  **Continuous Optimization**: Re-evaluates periodically to find better slots
-  **Status**: `phase: Scheduled`, `action: Scheduled`

**Expected Status:**
```yaml
status:
  phase: Scheduled
  decision:
    action: Scheduled
    reason: "Optional priority - scheduled for optimal energy slot (25000W >= 200W)"
    scheduledSlot:
      slotNumber: 3
      slotStart: "2026-01-06T12:00:00Z"
      slotEnd: "2026-01-06T18:00:00Z"
      availableEnergyWatts: 25000
      requiredEnergyWatts: 200
      confidencePercentage: 92.3
    nextEvaluationTime: "2026-01-06T12:00:00Z"
  lastUpdated: "2026-01-06T08:30:00Z"
```

---

#### Apply Your Workload

```bash
# Apply any of the above examples
kubectl apply -f critical-workload.yaml
# OR
kubectl apply -f preferred-workload.yaml
# OR
kubectl apply -f optional-workload.yaml

# Or apply all examples at once
kubectl apply -f examples/sample-eao.yaml
```

### Check Status

```bash
# View all energy-aware orchestrations
kubectl get eao

# Describe to see detailed schedule and status
kubectl describe eao critical-api-service
kubectl describe eao ml-training-job
kubectl describe eao batch-processing-job

# Watch operator logs in real-time
kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator

# View events for a specific resource
kubectl get events --field-selector involvedObject.name=ml-training-job
```

### Example Output

```bash
$ kubectl get eao
NAME                   PRIORITY    PHASE       AGE
critical-api-service   Critical    Scheduled   5m
ml-training-job        Preferred   Scheduled   3m
batch-processing-job   Optional    Scheduled   2m
```

#### Critical Workload Status

```bash
$ kubectl describe eao critical-api-service
Name:         critical-api-service
Namespace:    default
API Version:  eas.hiro.io/v1
Kind:         EnergyAwareOrchestration
Spec:
  Energy Consumption:    100
  Forecast Window Days:  14
  Priority:              Critical
  Application Ref:
    Name:       api-gateway
    Namespace:  production
Status:
  Phase:        Scheduled
  Decision:
    Action:     DeployImmediately
    Reason:     Critical priority workload - deploying immediately for 24/7 operation
  Energy Metrics:
    Required Watts:  100
    Sufficient:      true
  Last Updated:      2026-01-06T10:30:00Z
Events:
  Type    Reason     Age   Message
  ----    ------     ----  -------
  Normal  Scheduling 5m    [Event 1] Calculating schedule for 'critical-api-service' (Priority: Critical, Energy: 100W)
  Normal  Scheduled  5m    [Event 2] DeployImmediately: Critical priority workload - deploying immediately for 24/7 operation
```

#### Preferred Workload Status (With Energy Available Now)

```bash
$ kubectl describe eao ml-training-job
Name:         ml-training-job
Namespace:    default
API Version:  eas.hiro.io/v1
Kind:         EnergyAwareOrchestration
Spec:
  Energy Consumption:    500
  Forecast Window Days:  7
  Priority:              Preferred
  Application Ref:
    Name:       ml-training-deployment
    Namespace:  default
Status:
  Phase:        Scheduled
  Decision:
    Action:     DeployImmediately
    Reason:     Preferred priority - current slot has sufficient energy (15000W >= 500W)
  Energy Metrics:
    Current Slot Available Watts:  15000
    Required Watts:                500
    Sufficient:                    true
  Last Updated:                    2026-01-06T14:00:00Z
Events:
  Type    Reason     Age   Message
  ----    ------     ----  -------
  Normal  Scheduling 3m    [Event 1] Calculating schedule for 'ml-training-job' (Priority: Preferred, Energy: 500W)
  Normal  Scheduled  3m    [Event 2] DeployImmediately: Preferred priority - current slot has sufficient energy (15000W >= 500W)
```

#### Preferred Workload Status (Scheduled for Later)

```bash
$ kubectl describe eao ml-training-job
Status:
  Phase:        Scheduled
  Decision:
    Action:     Scheduled
    Reason:     Preferred priority - scheduled for first sufficient energy slot (18000W >= 500W)
    Scheduled Slot:
      Slot Number:               3
      Slot Start:                2026-01-06T12:00:00Z
      Slot End:                  2026-01-06T18:00:00Z
      Available Energy Watts:    18000
      Required Energy Watts:     500
      Confidence Percentage:     85.5
    Next Evaluation Time:        2026-01-06T12:00:00Z
  Energy Metrics:
    Current Slot Available Watts:  300
    Required Watts:                500
    Sufficient:                    false
  Last Updated:                    2026-01-06T08:30:00Z
```

#### Optional Workload Status

```bash
$ kubectl describe eao batch-processing-job
Name:         batch-processing-job
Namespace:    default
API Version:  eas.hiro.io/v1
Kind:         EnergyAwareOrchestration
Spec:
  Energy Consumption:    200
  Forecast Window Days:  3
  Priority:              Optional
  Application Ref:
    Name:       batch-processor
    Namespace:  default
Status:
  Phase:        Scheduled
  Decision:
    Action:     Scheduled
    Reason:     Optional priority - scheduled for optimal energy slot (25000W >= 200W)
    Scheduled Slot:
      Slot Number:               3
      Slot Start:                2026-01-06T12:00:00Z
      Slot End:                  2026-01-06T18:00:00Z
      Available Energy Watts:    25000
      Required Energy Watts:     200
      Confidence Percentage:     92.3
    Next Evaluation Time:        2026-01-06T12:00:00Z
  Energy Metrics:
    Current Slot Available Watts:  8000
    Required Watts:                200
    Sufficient:                    false
  Last Updated:                    2026-01-06T08:30:00Z
Events:
  Type    Reason     Age   Message
  ----    ------     ----  -------
  Normal  Scheduling 2m    [Event 1] Calculating schedule for 'batch-processing-job' (Priority: Optional, Energy: 200W)
  Normal  Scheduled  2m    [Event 2] Scheduled: Optional priority - scheduled for optimal energy slot (25000W >= 200W)
```


### Time Slot Windows

The operator divides each day into **4 six-hour slots**:

| Slot | Time Window (UTC) | Typical Use |
|------|-------------------|-------------|
| **Slot 1** | 00:00 - 06:00 | Night processing, off-peak |
| **Slot 2** | 06:00 - 12:00 | Morning operations |
| **Slot 3** | 12:00 - 18:00 | Afternoon (often highest solar) |
| **Slot 4** | 18:00 - 24:00 | Evening operations |

**Note:** The operator fetches energy forecasts and schedules workloads for slots with the best energy availability and cost.

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

---

## Local Development Without Kubernetes

You can develop and test the operator locally without deploying to Kubernetes.

### Prerequisites

```bash
# Install Python dependencies
uv sync
```

### Apply CRD to Cluster

```bash
# Generate the CRD
uv run python -m app.crd.builder

# Apply it to your cluster
kubectl apply -f charts/energy-aware-operator/crds/energy-aware-orchestration-crd.yaml

# Verify CRD is installed
kubectl get crd energyawareorchestrations.eas.hiro.io
```

### Run Kopf Operator Locally

```bash
# Set PYTHONPATH
export PYTHONPATH=/Users/rahul/Desktop/Hiro/code/2025/energy-aware-orchestrator/energy-aware-operator

# Set environment variables (optional)
export LOG_LEVEL=INFO
export KOPF_RECONCILE_INTERVAL_SECONDS=600
export ENERGY_API_URL=http://localhost:8000

# Run the operator locally
uv run kopf run app/operator.py --verbose

# Or with python directly
python -m kopf run app/operator.py --verbose
```

**Environment Variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `KOPF_RECONCILE_INTERVAL_SECONDS` | `600` | How often to re-evaluate schedules (seconds) |
| `ENERGY_API_URL` | `http://energy-metric-service:8000` | Energy metrics service endpoint |

**One-line with environment variables:**
```bash
PYTHONPATH=. LOG_LEVEL=DEBUG ENERGY_API_URL=http://localhost:8000 uv run kopf run app/operator.py --verbose
```

**Or create a `.env` file:**
```bash
# Copy the example
cp env.local.example .env

# Edit with your values
vim .env

# Source it and run
source .env
uv run kopf run app/operator.py --verbose
```

### Test Local Changes

```bash
# Terminal 1: Run operator locally
uv run kopf run app/operator.py --verbose

# Terminal 2: Apply a test resource
kubectl apply -f examples/sample-eao.yaml

# Watch the operator logs in Terminal 1
```


# Check what CRDs operator will watch
kubectl get crd | grep eas.hiro.io
```
