# Energy-Aware Kubernetes Operator

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Kopf](https://img.shields.io/badge/kopf-1.37+-green.svg)](https://kopf.readthedocs.io/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

A production-ready Kubernetes operator that enables energy-aware workload orchestration using the [Kopf framework](https://kopf.readthedocs.io/).

## 🎯 Features

- **Custom Resource Definition (CRD)**: `EnergyAwareOrchestration` for declarative workload scheduling
- **Priority-Based Scheduling**: Critical, Preferred, and Optional priority levels
- **Energy-Aware**: Integration with energy availability services for intelligent scheduling
- **Production Ready**: Comprehensive error handling, logging, and observability
- **Event-Driven**: Posts Kubernetes events for full observability
- **Async Architecture**: Built on Kopf's async framework for high performance

## 📋 Table of Contents

- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [Deployment](#deployment)
- [Configuration](#configuration)
- [Testing](#testing)
- [Contributing](#contributing)

## 🏗️ Architecture

The operator follows Kubernetes operator best practices and consists of:

### Core Components

1. **Operator Core** (`operator.py`)
   - Main reconciliation loop
   - Handles CR create, update, delete events
   - Periodic re-evaluation timer

2. **CRD Builder** (`crd/builder.py`)
   - Generates CRD from Pydantic models
   - Ensures type safety and validation

3. **Handlers**
   - **Validation Handler**: Validates CR specifications
   - **Scheduler Handler**: Calculates execution schedules
   - **Status Handler**: Manages CR status updates
   - **Event Handler**: Posts Kubernetes events

### Scheduling Logic

#### Priority Levels

| Priority | Behavior |
|----------|----------|
| **Critical** | Deploy immediately (24/7 operation) |
| **Preferred** | If energy insufficient, delay by 6 hours |
| **Optional** | Find best slot in next 24 hours |

#### Time Slots

The operator uses 6-hour time windows:
- Slot 1: 00:00 - 06:00 (midnight to 6am)
- Slot 2: 06:00 - 12:00 (6am to noon)
- Slot 3: 12:00 - 18:00 (noon to 6pm)
- Slot 4: 18:00 - 24:00 (6pm to midnight)

## 📦 Installation

### Prerequisites

- Python 3.11+
- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3.x (for deployment)

### From Source

```bash
# Clone the repository
git clone https://github.com/your-org/energy-aware-operator.git
cd energy-aware-operator

# Install dependencies
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### Using uv (recommended)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install with dev dependencies
uv sync --all-extras
```

## 🚀 Usage

### 1. Generate and Apply CRD

```bash
# Generate CRD
python -m app.crd.builder

# Apply to cluster
kubectl apply -f charts/energy-aware-operator/crds/energy-aware-orchestration-crd.yaml
```

### 2. Deploy the Operator

```bash
# Using Helm
./scripts/deploy.sh

# Or deploy to specific namespace
./scripts/deploy.sh -n energy-system
```

### 3. Create EnergyAwareOrchestration Resources

```yaml
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: ml-training-job
  namespace: default
spec:
  # Energy consumption in Watts
  energyConsumption: 500
  
  # Forecast window (1-30 days)
  forecastWindowDays: 7
  
  # Priority: Critical, Preferred, or Optional
  priority: Preferred
  
  # Application reference
  applicationRef:
    name: ml-training-deployment
    namespace: default
```

```bash
kubectl apply -f examples/sample-eao.yaml
```

### 4. Monitor the Operator

```bash
# Watch operator logs
kubectl logs -f -l app=energy-aware-operator -n default

# Check CR status
kubectl get eao
kubectl describe eao ml-training-job

# View events
kubectl get events --sort-by=.metadata.creationTimestamp
```

## 🛠️ Development

### Project Structure

```
energy-aware-operator/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   ├── operator.py              # Core operator logic
│   ├── config.py                # Configuration
│   ├── crd/
│   │   ├── __init__.py
│   │   ├── builder.py           # CRD generator
│   │   └── models.py            # Pydantic models
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── validation.py        # Validation logic
│   │   ├── scheduler.py         # Scheduling logic
│   │   ├── status.py            # Status management
│   │   └── events.py            # Event posting
│   └── services/
│       ├── __init__.py
│       ├── scheduler_service.py # Core scheduling
│       └── energy_client.py     # Energy API client
├── charts/
│   └── energy-aware-operator/   # Helm chart
├── scripts/
│   ├── deploy.sh                # Deployment script
│   ├── cleanup.sh               # Cleanup script
│   └── generate-crd.sh          # CRD generation
├── examples/
│   └── sample-eao.yaml          # Sample CRs
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
├── pyproject.toml
└── README.md
```

### Running Locally

```bash
# Set up Python environment
uv venv
source .venv/bin/activate

# Install in development mode
uv pip install -e ".[dev]"

# Run the operator (requires kubeconfig)
kopf run app/operator.py --verbose
```

### Code Quality

```bash
# Format code
black app/

# Lint
ruff app/

# Type check
mypy app/

# Run tests
pytest
```

## 🐳 Deployment

### Docker Build

```bash
# Build image
docker build -t energy-aware-operator:latest .

# For minikube
eval $(minikube docker-env)
docker build -t energy-aware-operator:latest .
```

### Helm Deployment

```bash
# Install
helm install energy-operator ./charts/energy-aware-operator \
  --namespace energy-system \
  --create-namespace

# Upgrade
helm upgrade energy-operator ./charts/energy-aware-operator \
  --namespace energy-system

# Uninstall
helm uninstall energy-operator -n energy-system
```

### Using Scripts

```bash
# Deploy (builds image, applies CRD, installs helm chart)
./scripts/deploy.sh

# Deploy to specific namespace
./scripts/deploy.sh -n production

# Skip image build
./scripts/deploy.sh --no-build

# Cleanup
./scripts/cleanup.sh

# Cleanup and reinstall
./scripts/cleanup.sh --reinstall
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KOPF_RECONCILE_INTERVAL_SECONDS` | Re-evaluation interval | `600` (10 min) |
| `ENERGY_API_URL` | Energy service endpoint | - |
| `LOG_LEVEL` | Logging level | `INFO` |

### Operator Settings

Configure in `charts/energy-aware-operator/values.yaml`:

```yaml
operator:
  replicas: 1
  image:
    repository: energy-aware-operator
    tag: latest
  resources:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "500m"
  env:
    - name: KOPF_RECONCILE_INTERVAL_SECONDS
      value: "600"
    - name: LOG_LEVEL
      value: "INFO"
```

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_validation.py
```

### Integration Tests

```bash
# Requires a running cluster
pytest tests/integration/

# End-to-end test
./scripts/test-e2e.sh
```

## 📝 Examples

### Critical Workload (Always On)

```yaml
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: critical-api
spec:
  energyConsumption: 100
  forecastWindowDays: 14
  priority: Critical
  applicationRef:
    name: api-gateway
    namespace: production
```

### Batch Processing (Flexible)

```yaml
apiVersion: eas.hiro.io/v1
kind: EnergyAwareOrchestration
metadata:
  name: batch-job
spec:
  energyConsumption: 200
  forecastWindowDays: 3
  priority: Optional
  applicationRef:
    name: batch-processor
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## 🔗 Links

- [Kopf Documentation](https://kopf.readthedocs.io/)
- [Kubernetes Operators](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
- [Custom Resource Definitions](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)

## 📞 Support

- Issues: [GitHub Issues](https://github.com/your-org/energy-aware-operator/issues)
- Discussions: [GitHub Discussions](https://github.com/your-org/energy-aware-operator/discussions)

---

**Built with ❤️ using [Kopf](https://kopf.readthedocs.io/)**

