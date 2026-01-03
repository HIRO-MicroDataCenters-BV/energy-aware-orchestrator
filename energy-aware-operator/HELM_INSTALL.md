# Helm Installation Guide

This guide explains how to install the Energy-Aware Operator using Helm.

## Prerequisites

- Kubernetes cluster (v1.19+)
- kubectl configured to access your cluster
- Helm 3.0+
- Docker (if building custom images)
- Python 3.11+ with uv (optional, for CRD generation)

## Quick Install

The simplest way to install:

```bash
cd energy-aware-operator
./scripts/deploy.sh
```

This will:
1. Build the Docker image
2. Generate and apply the CRD
3. Deploy the operator with Helm
4. Wait for the operator to be ready

## Installation Options

### 1. Basic Installation

Deploy to the default namespace with all defaults:

```bash
./scripts/deploy.sh
```

### 2. Custom Namespace

Deploy to a specific namespace:

```bash
./scripts/deploy.sh -n operators
```

### 3. Skip Image Build

If you already have the image built:

```bash
./scripts/deploy.sh --no-build
```

### 4. Custom Release Name

Use a custom Helm release name:

```bash
./scripts/deploy.sh -r my-energy-operator
```

### 5. Custom Image

Use a custom image repository and tag:

```bash
./scripts/deploy.sh \
  --image-repo myregistry.io/energy-operator \
  --image-tag v1.0.0 \
  --pull-policy Always
```

### 6. Full Custom Installation

```bash
./scripts/deploy.sh \
  -n production \
  -r energy-operator-prod \
  --image-repo myregistry.io/energy-operator \
  --image-tag v1.0.0 \
  --pull-policy Always
```

## Manual Helm Installation

If you prefer to use Helm directly:

### Step 1: Build the Image (if needed)

```bash
cd energy-aware-operator

# For minikube
eval $(minikube docker-env)
docker build -t energy-aware-operator:latest .

# For remote registry
docker build -t myregistry.io/energy-operator:v1.0.0 .
docker push myregistry.io/energy-operator:v1.0.0
```

### Step 2: Generate and Apply CRD

```bash
# Generate CRD (optional - pre-generated version exists)
uv run python -m app.crd.builder

# Apply CRD
kubectl apply -f charts/energy-aware-operator/crds/energy-aware-orchestration-crd.yaml
```

### Step 3: Install with Helm

```bash
helm install energy-operator ./charts/energy-aware-operator \
  --namespace default \
  --set image.repository=energy-aware-operator \
  --set image.tag=latest \
  --set image.pullPolicy=Never
```

For production with custom image:

```bash
helm install energy-operator ./charts/energy-aware-operator \
  --namespace operators \
  --create-namespace \
  --set image.repository=myregistry.io/energy-operator \
  --set image.tag=v1.0.0 \
  --set image.pullPolicy=Always \
  --set resources.requests.cpu=200m \
  --set resources.requests.memory=256Mi \
  --set resources.limits.cpu=500m \
  --set resources.limits.memory=512Mi
```

## Configuration

### Image Configuration

```bash
helm install energy-operator ./charts/energy-aware-operator \
  --set image.repository=myregistry.io/energy-operator \
  --set image.tag=v1.0.0 \
  --set image.pullPolicy=Always
```

### Resource Limits

```bash
helm install energy-operator ./charts/energy-aware-operator \
  --set resources.requests.cpu=200m \
  --set resources.requests.memory=256Mi \
  --set resources.limits.cpu=500m \
  --set resources.limits.memory=512Mi
```

### Replica Count

```bash
helm install energy-operator ./charts/energy-aware-operator \
  --set replicaCount=2
```

### Service Account

```bash
helm install energy-operator ./charts/energy-aware-operator \
  --set serviceAccount.create=true \
  --set serviceAccount.name=custom-sa \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="arn:aws:iam::123456789012:role/my-role"
```

### Operator Configuration

Edit the configuration values:

```bash
helm install energy-operator ./charts/energy-aware-operator \
  --set configuration.log_level=DEBUG \
  --set configuration.reconcile_interval_seconds=300
```

Or create a custom values file:

```yaml
# custom-values.yaml
replicaCount: 2

image:
  repository: myregistry.io/energy-operator
  tag: v1.0.0
  pullPolicy: Always

resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi

configuration:
  log_level: DEBUG
  reconcile_interval_seconds: 300
  energy_api_url: "http://energy-metric-service:8000"

serviceMonitorEnabled: true
```

Then install:

```bash
helm install energy-operator ./charts/energy-aware-operator \
  -f custom-values.yaml \
  --namespace operators \
  --create-namespace
```

## Verification

### Check Operator Status

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=energy-aware-operator

# Check deployment
kubectl get deployment -l app.kubernetes.io/name=energy-aware-operator

# Check service
kubectl get svc -l app.kubernetes.io/name=energy-aware-operator

# View logs
kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator
```

### Verify CRD

```bash
kubectl get crd energyawareorchestrations.energyaware.hiro.io
kubectl explain eao
```

### Test with Sample CR

```bash
# Apply sample custom resource
kubectl apply -f examples/sample-eao.yaml

# Check the custom resource
kubectl get eao

# Describe the resource
kubectl describe eao sample-eao

# Watch for status updates
kubectl get eao sample-eao -w
```

## Upgrading

### Using Script

```bash
./scripts/deploy.sh  # Will automatically upgrade if already installed
```

### Using Helm

```bash
helm upgrade energy-operator ./charts/energy-aware-operator \
  --namespace default \
  --set image.tag=v2.0.0
```

## Uninstallation

### Using Script

```bash
# Basic cleanup
./scripts/cleanup.sh

# Cleanup with CRD deletion
./scripts/cleanup.sh --delete-crd

# Full cleanup including namespace
./scripts/cleanup.sh --delete-crd --delete-namespace

# Cleanup from specific namespace
./scripts/cleanup.sh -n operators
```

### Using Helm

```bash
# Delete custom resources first
kubectl delete eao --all

# Uninstall operator
helm uninstall energy-operator -n default

# Delete CRD (optional)
kubectl delete crd energyawareorchestrations.energyaware.hiro.io

# Delete namespace (optional, if not default)
kubectl delete namespace operators
```

## Troubleshooting

### Operator Pod Not Starting

Check the pod events and logs:

```bash
kubectl describe pod -l app.kubernetes.io/name=energy-aware-operator
kubectl logs -l app.kubernetes.io/name=energy-aware-operator
```

### Image Pull Errors

For minikube, ensure you're using the minikube Docker daemon:

```bash
eval $(minikube docker-env)
docker images | grep energy-aware-operator
```

Verify image pull policy:

```bash
helm get values energy-operator
```

### RBAC Permissions

Check service account and RBAC:

```bash
kubectl get serviceaccount -l app.kubernetes.io/name=energy-aware-operator
kubectl get clusterrole -l app.kubernetes.io/name=energy-aware-operator
kubectl get clusterrolebinding -l app.kubernetes.io/name=energy-aware-operator
```

### CRD Issues

Verify CRD is installed:

```bash
kubectl get crd energyawareorchestrations.energyaware.hiro.io -o yaml
```

### View Operator Configuration

```bash
kubectl get configmap -l app.kubernetes.io/name=energy-aware-operator -o yaml
```

## Advanced Configuration

### Enable Prometheus Metrics

```bash
helm install energy-operator ./charts/energy-aware-operator \
  --set serviceMonitorEnabled=true
```

### Node Affinity

```yaml
# values.yaml
nodeSelector:
  node-role.kubernetes.io/control-plane: ""

tolerations:
  - key: node-role.kubernetes.io/control-plane
    operator: Exists
    effect: NoSchedule
```

### Pod Security Context

```yaml
# values.yaml
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: true
```

## Next Steps

- Read the [Quick Start Guide](QUICKSTART.md)
- Review the [Project Summary](PROJECT_SUMMARY.md)
- Check the [examples](examples/) directory
- Integrate with [energy-metric-service](../energy-metric-service/)
