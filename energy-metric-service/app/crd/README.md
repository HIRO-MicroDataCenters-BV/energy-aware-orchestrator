# EnergyAwareOrchestration CRD

This module defines and generates the **EnergyAwareOrchestration** Custom Resource Definition (CRD) for Kubernetes.

> 📖 **For detailed architecture documentation, see [SCHEDULER_ARCHITECTURE.md](../../docs/SCHEDULER_ARCHITECTURE.md)**

## Overview

The EnergyAwareOrchestration CRD enables energy-aware scheduling of workloads in Kubernetes. It allows you to:

- Define energy consumption estimates for workloads (in Watts)
- Set business priority levels (Critical, NonCritical, Optional)
- Configure forecast windows for schedule optimization
- Automatically compute optimal execution schedules based on energy availability
- View scheduling decisions and energy metrics in CR status

## Scheduling Logic

| Priority | Behavior |
|----------|----------|
| **Critical** | Deploy immediately (24/7 operation) |
| **NonCritical** | If energy insufficient → delay 6 hours |
| **Optional** | Find best slot in next 24 hours |

**Time Slots:** Day divided into 4 × 6-hour slots (00:00-06:00, 06:00-12:00, 12:00-18:00, 18:00-24:00)

## CRD Structure

```yaml
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: my-workload
spec:
  energyConsumption: 500        # Required energy in Watts
  forecastWindowDays: 7         # Days to forecast (1-30)
  priority: NonCritical         # Critical | NonCritical | Optional
  applicationRef:
    name: my-deployment         # Target deployment name
    namespace: default          # Target namespace
status:
  phase: Scheduled              # Pending | Scheduled | Running | Completed | Failed
  decision:
    action: Scheduled           # DeployImmediately | Scheduled | Delayed | Waiting
    reason: "Human-readable explanation"
    scheduledSlot:
      slotNumber: 2             # 1-4
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

## File Structure

```
app/crd/
├── README.md                              # This file
├── energy_aware_orchestration_model.py    # Pydantic models (source of truth)
├── builder.py                             # CRD generator script
└── energy-aware-orchestration-crd.yaml    # Generated CRD (local copy)

charts/
├── crds/
│   └── energy-aware-orchestration-crd.yaml  # Helm auto-install + kubectl apply for updates
└── templates/
    └── rbac.yaml                            # RBAC permissions

scripts/
├── generate-crd.sh      # Generate CRD
├── deploy-crd.sh        # Deploy CRD to cluster
├── deploy-all.sh        # Full deployment (CRD + App + DB)
├── setup-hooks.sh       # Install pre-commit hook
└── pre-commit-crd.sh    # Auto-regenerate on commit
```

## How It Works

### Source of Truth

The Pydantic models in `energy_aware_orchestration_model.py` are the **single source of truth** for the CRD schema:

```python
class EnergyAwareOrchestrationSpec(BaseModel):
    energyConsumption: int = Field(..., ge=0)
    forecastWindowDays: int = Field(..., ge=1, le=30)
    priority: Priority = Field(default=Priority.NON_CRITICAL)
    applicationRef: ApplicationRef
```

### Generation Process

The `builder.py` script converts Pydantic models to Kubernetes CRD YAML:

```
┌─────────────────────────────┐
│  Pydantic Models            │
│  (energy_aware_             │
│   orchestration_model.py)   │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  builder.py                 │
│  - Converts to JSON Schema  │
│  - Adds K8s CRD structure   │
│  - Adds Helm annotations    │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Generated YAML files       │
│  - app/crd/ (local)         │
│  - charts/crds/ (install)   │
│  - charts/templates/ (hooks)│
└─────────────────────────────┘
```

### Helm Deployment Strategy

We use the **Helm 3 crds/ folder** following Kubernetes best practices:

| Location | Purpose | Behavior |
|----------|---------|----------|
| `charts/crds/` | CRD installation | Auto-installed by Helm 3 before other resources. NOT deleted on uninstall (protects data). |

**CRD Updates:** The deploy script runs `kubectl apply` before Helm to handle CRD schema updates (idempotent operation).

## Usage

### Generate CRD

```bash
# Using the script
./scripts/generate-crd.sh

# Or directly with Python
uv run python -m app.crd.builder

# Or from the crd directory
cd app/crd && python builder.py
```

### Deploy CRD Only

```bash
# Using the script
./scripts/deploy-crd.sh

# Or manually
kubectl apply -f charts/crds/energy-aware-orchestration-crd.yaml
```

### Deploy Everything (with Helm)

```bash
./scripts/deploy-all.sh
```

The deploy script will:
1. Regenerate CRD from Pydantic models
2. Build Docker image
3. Deploy with Helm (CRD + App + PostgreSQL)

### Verify CRD Installation

```bash
# Check CRD exists
kubectl get crd energyawareorchestrations.eas.hiro.io

# List all EnergyAwareOrchestration resources
kubectl get eao

# Describe a specific resource
kubectl describe eao my-workload
```

## Automation

### Pre-commit Hook

Automatically regenerates CRD when models change:

```bash
# Install the hook
./scripts/setup-hooks.sh
```

After installation, any commit that modifies `energy_aware_orchestration_model.py` or `builder.py` will trigger automatic CRD regeneration.

### CI/CD Integration

Add to your pipeline:

```yaml
# Example GitHub Actions step
- name: Verify CRD is up to date
  run: |
    ./scripts/generate-crd.sh
    git diff --exit-code charts/crds/
```

## Creating EnergyAwareOrchestration Resources

### Example Resources

```yaml
# High-priority API service
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: api-gateway
spec:
  energyConsumption: 100
  forecastWindowDays: 14
  priority: Critical
  applicationRef:
    name: api-gateway-deployment
    namespace: production
---
# ML training job (can run during low-cost periods)
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: ml-training
spec:
  energyConsumption: 500
  forecastWindowDays: 7
  priority: Optional
  applicationRef:
    name: ml-training-job
    namespace: ml-workloads
```

### Apply Resources

```bash
kubectl apply -f sample_deployments/sample-eao.yaml
```

## Modifying the CRD

To add new fields or change the schema:

1. **Edit the Pydantic models** in `energy_aware_orchestration_model.py`
2. **Regenerate the CRD**: `./scripts/generate-crd.sh`
3. **Test locally**: `kubectl apply -f charts/crds/energy-aware-orchestration-crd.yaml`
4. **Commit changes** (pre-commit hook will verify regeneration)

### Example: Adding a New Field

```python
# In energy_aware_orchestration_model.py
class EnergyAwareOrchestrationSpec(BaseModel):
    energyConsumption: int = Field(...)
    forecastWindowDays: int = Field(...)
    priority: Priority = Field(...)
    applicationRef: ApplicationRef
    
    # Add new field
    maxCostPerKwh: float = Field(
        default=0.0,
        ge=0,
        description="Maximum acceptable cost per kWh"
    )
```

Then regenerate:
```bash
./scripts/generate-crd.sh
```

## Troubleshooting

### CRD Not Found

```bash
# Check if CRD is installed
kubectl get crd | grep energyaware

# If missing, install manually
kubectl apply -f charts/crds/energy-aware-orchestration-crd.yaml
```

### Import Error When Running builder.py

```bash
# Run as module from project root
cd /path/to/energy-metric-service
uv run python -m app.crd.builder

# Or use the script
./scripts/generate-crd.sh
```

### Permission Denied

```bash
# Ensure RBAC is deployed
kubectl get clusterrole | grep energy-metric-service
kubectl get clusterrolebinding | grep energy-metric-service

# If missing, deploy with Helm or apply manually
kubectl apply -f charts/templates/rbac.yaml
```

## API Reference

### Spec Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `spec.energyConsumption` | integer | Yes | Required energy in Watts |
| `spec.forecastWindowDays` | integer | Yes | Forecast window (1-30 days) |
| `spec.priority` | enum | No | `Critical`, `NonCritical`, `Optional` (default: `NonCritical`) |
| `spec.applicationRef.name` | string | Yes | Target application/deployment name |
| `spec.applicationRef.namespace` | string | No | Target namespace |

### Status Fields

| Field | Type | Description |
|-------|------|-------------|
| `status.phase` | enum | `Pending`, `Scheduled`, `Running`, `Completed`, `Failed` |
| `status.decision.action` | enum | `DeployImmediately`, `Scheduled`, `Delayed`, `Waiting` |
| `status.decision.reason` | string | Human-readable explanation |
| `status.decision.scheduledSlot.slotNumber` | integer | Slot number (1-4) |
| `status.decision.scheduledSlot.slotStart` | datetime | Slot start time (ISO 8601) |
| `status.decision.scheduledSlot.slotEnd` | datetime | Slot end time (ISO 8601) |
| `status.decision.scheduledSlot.availableEnergyWatts` | number | Available energy in slot |
| `status.decision.nextEvaluationTime` | datetime | When to re-evaluate |
| `status.energyMetrics.currentSlotAvailableWatts` | number | Energy available now |
| `status.energyMetrics.requiredWatts` | number | Energy required by workload |
| `status.energyMetrics.sufficient` | boolean | Is energy sufficient? |
| `status.lastUpdated` | datetime | Last status update time |

## Related Documentation

- [Scheduler Architecture](../../docs/SCHEDULER_ARCHITECTURE.md) - Detailed architecture documentation
- [Sample EAOs](../../sample_deployments/sample-eao.yaml) - Example custom resources

