# ✅ Helm Chart Ready!

## 🎯 Quick Install Commands

### Method 1: Using Deploy Script (Recommended)
```bash
cd energy-aware-operator

# Deploy to default namespace (includes image build & CRD)
./scripts/deploy.sh

# Deploy to custom namespace
./scripts/deploy.sh -n operators

# Deploy without building image
./scripts/deploy.sh --no-build
```

### Method 2: Manual Helm Install
```bash
cd energy-aware-operator

# 1. Build image (for minikube)
eval $(minikube docker-env)
docker build -t energy-aware-operator:latest .

# 2. Generate CRD
uv run python -m app.crd.builder

# 3. Apply CRD
kubectl apply -f charts/energy-aware-operator/crds/energy-aware-orchestration-crd.yaml

# 4. Install with Helm
helm install energy-operator ./charts/energy-aware-operator \
  --namespace default \
  --create-namespace \
  --wait
```

## 📦 What's Included

### Helm Chart Components
```
charts/energy-aware-operator/
├── Chart.yaml                    # Chart metadata
├── values.yaml                   # Default configuration
├── crds/
│   └── energy-aware-orchestration-crd.yaml
└── templates/
    ├── _helpers.tpl             # Template helpers
    ├── serviceaccount.yaml      # Service account
    ├── rbac.yaml                # ClusterRole & binding
    ├── deployment.yaml          # Operator deployment
    └── service.yaml             # Service (port 8080)
```

### RBAC Permissions
- ✅ Read/write EnergyAwareOrchestration CRs
- ✅ Update CR status
- ✅ Post Kubernetes events
- ✅ Watch CRDs and namespaces (Kopf framework)
- ✅ Optional: Manage deployments

## 🔧 Configuration Options

### Key Values
```yaml
replicaCount: 1
image:
  repository: energy-aware-operator
  tag: latest
  pullPolicy: Never  # For minikube

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 256Mi

env:
  - name: LOG_LEVEL
    value: "INFO"
  - name: KOPF_RECONCILE_INTERVAL_SECONDS
    value: "600"
```

## ✅ Verify Installation

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=energy-aware-operator

# View logs
kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator

# Check CRD
kubectl get crd energyawareorchestrations.eas.hiro.io

# Test with sample CR
kubectl apply -f examples/sample-eao.yaml
kubectl get eao
```

## 🧹 Cleanup

```bash
# Using script
./scripts/cleanup.sh

# Manual
helm uninstall energy-operator
kubectl delete crd energyawareorchestrations.eas.hiro.io
```

## 📚 Full Documentation

See `HELM_INSTALL.md` for:
- Custom values examples
- Troubleshooting guide
- Advanced configuration
- Integration with energy-metric-service

---

**Status**: ✅ **Helm chart complete and ready to deploy!**

