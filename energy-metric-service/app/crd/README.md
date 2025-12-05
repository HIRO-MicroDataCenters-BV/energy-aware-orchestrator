# EnergyAwareOrchestration CRD

This module defines and generates the **EnergyAwareOrchestration** Custom Resource Definition (CRD) for Kubernetes.

## Overview

The EnergyAwareOrchestration CRD enables energy-aware scheduling of workloads in Kubernetes. It allows you to:

- Define energy consumption estimates for workloads
- Set business priority levels (Critical, NonCritical, Optional)
- Configure forecast windows for schedule optimization
- Automatically compute optimal execution schedules based on energy availability

## CRD Structure

```yaml
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: my-workload
spec:
  energyConsumption: 500        # Estimated energy in kWh
  forecastWindowDays: 7         # Days to forecast (1-30)
  priority: NonCritical         # Critical | NonCritical | Optional
  applicationRef:
    name: my-deployment         # Target deployment name
    namespace: default          # Target namespace
status:
  executionSchedule:
    updated: "2025-12-05T10:00:00Z"
    schedule:
      - date: "2025-12-05"
        times:
          - start: "02:00:00"
            stop: "06:00:00"
            cost: 0.12
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

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `spec.energyConsumption` | integer | Yes | Estimated energy consumption (kWh) |
| `spec.forecastWindowDays` | integer | Yes | Forecast window (1-30 days) |
| `spec.priority` | enum | No | `Critical`, `NonCritical`, `Optional` (default: `NonCritical`) |
| `spec.applicationRef.name` | string | Yes | Target application/deployment name |
| `spec.applicationRef.namespace` | string | No | Target namespace |
| `status.executionSchedule.updated` | datetime | - | Last schedule update timestamp |
| `status.executionSchedule.schedule` | array | - | List of daily schedules |

