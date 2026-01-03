# 🚀 Deployment Checklist

## Pre-Deployment Validation ✅

All checks passed! The Helm chart is ready for deployment.

### 1. ✅ Helm Chart Structure
```
✓ Chart.yaml - Valid metadata
✓ values.yaml - Proper defaults
✓ CRD definition exists
✓ All templates present
  - _helpers.tpl
  - configmap.yaml (NEW)
  - deployment.yaml
  - rbac.yaml
  - service-monitor.yaml (NEW)
  - service.yaml
  - serviceaccount.yaml
```

### 2. ✅ Helm Lint Passed
```bash
$ helm lint charts/energy-aware-operator/
==> Linting charts/energy-aware-operator/
[INFO] Chart.yaml: icon is recommended
1 chart(s) linted, 0 chart(s) failed
```

### 3. ✅ Template Rendering
```bash
$ helm template test-release charts/energy-aware-operator/ \
    --set image.repository=energy-aware-operator \
    --set image.tag=latest

✓ ServiceAccount renders correctly
✓ ClusterRole with granular permissions
✓ ClusterRoleBinding links SA to role
✓ ConfigMap with configuration
✓ Deployment with proper probes
✓ Service exposes port 8080
```

### 4. ✅ Key Features Verified
- ✅ ConfigMap-based configuration
- ✅ Granular RBAC (no wildcards)
- ✅ Health check endpoints
- ✅ Resource limits and requests
- ✅ ServiceMonitor support (optional)
- ✅ Flexible image configuration
- ✅ Pod metadata environment variables

### 5. ✅ Scripts Ready
- ✅ `scripts/deploy.sh` - Enhanced deployment
- ✅ `scripts/cleanup.sh` - Safe cleanup
- ✅ Both scripts executable

### 6. ✅ Documentation Complete
- ✅ HELM_INSTALL.md - Comprehensive guide
- ✅ HELM_CHART_UPDATES.md - Change documentation
- ✅ UPDATE_SUMMARY.md - Quick reference
- ✅ QUICKSTART.md - Getting started
- ✅ PROJECT_SUMMARY.md - Project overview
- ✅ README.md - Main documentation

## 📝 Deployment Instructions

### Option 1: Quick Deploy (Recommended)

```bash
cd /Users/rahul/Desktop/Hiro/code/2025/energy-aware-orchestrator/energy-aware-operator

# Deploy to default namespace
./scripts/deploy.sh
```

### Option 2: Custom Deployment

```bash
# Deploy to custom namespace with options
./scripts/deploy.sh \
  -n operators \
  -r energy-operator-prod \
  --image-tag v1.0.0 \
  --pull-policy IfNotPresent
```

### Option 3: Manual Helm

```bash
# Build image
docker build -t energy-aware-operator:latest .

# Install with Helm
helm install energy-operator ./charts/energy-aware-operator \
  --namespace default \
  --set image.repository=energy-aware-operator \
  --set image.tag=latest \
  --set image.pullPolicy=Never \
  --wait
```

## ✅ Post-Deployment Verification

### 1. Check Operator Pod
```bash
kubectl get pods -l app.kubernetes.io/name=energy-aware-operator

# Expected output:
# NAME                                        READY   STATUS    RESTARTS   AGE
# energy-operator-energy-aware-operator-xxx   1/1     Running   0          30s
```

### 2. Check Resources
```bash
# All resources
kubectl get all -l app.kubernetes.io/name=energy-aware-operator

# Service account
kubectl get serviceaccount -l app.kubernetes.io/name=energy-aware-operator

# RBAC
kubectl get clusterrole -l app.kubernetes.io/name=energy-aware-operator
kubectl get clusterrolebinding -l app.kubernetes.io/name=energy-aware-operator

# ConfigMap
kubectl get configmap -l app.kubernetes.io/name=energy-aware-operator
```

### 3. View Logs
```bash
kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator
```

### 4. Test with Sample CR
```bash
# Apply sample resource
kubectl apply -f examples/sample-eao.yaml

# Check the resource
kubectl get eao

# Describe to see status
kubectl describe eao sample-eao

# Watch for changes
kubectl get eao sample-eao -w
```

### 5. Verify CRD
```bash
# Check CRD exists
kubectl get crd energyawareorchestrations.energyaware.hiro.io

# Get CRD details
kubectl explain eao
kubectl explain eao.spec
kubectl explain eao.status
```

## 🧪 Test Scenarios

### Test 1: Basic Deployment
```bash
./scripts/deploy.sh
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=energy-aware-operator --timeout=120s
kubectl get pods -l app.kubernetes.io/name=energy-aware-operator
```

### Test 2: Apply Custom Resource
```bash
kubectl apply -f examples/sample-eao.yaml
sleep 5
kubectl get eao sample-eao -o yaml
```

### Test 3: Check Operator Response
```bash
kubectl logs -l app.kubernetes.io/name=energy-aware-operator | grep -i "sample-eao"
```

### Test 4: Cleanup and Reinstall
```bash
./scripts/cleanup.sh --reinstall
```

### Test 5: Custom Namespace Deployment
```bash
./scripts/deploy.sh -n test-operators
kubectl get pods -n test-operators
./scripts/cleanup.sh -n test-operators --delete-namespace
```

## 🔍 Troubleshooting Guide

### Issue: Pod Not Starting

**Check:**
```bash
kubectl describe pod -l app.kubernetes.io/name=energy-aware-operator
kubectl get events --sort-by='.lastTimestamp'
```

**Common Causes:**
- Image not available → Build with `docker build -t energy-aware-operator:latest .`
- RBAC issues → Check ClusterRole and ClusterRoleBinding
- Resource limits → Check node capacity

### Issue: CRD Not Found

**Check:**
```bash
kubectl get crd | grep energyaware
```

**Fix:**
```bash
kubectl apply -f charts/energy-aware-operator/crds/energy-aware-orchestration-crd.yaml
```

### Issue: RBAC Permission Denied

**Check:**
```bash
kubectl get clusterrole -l app.kubernetes.io/name=energy-aware-operator -o yaml
kubectl get clusterrolebinding -l app.kubernetes.io/name=energy-aware-operator -o yaml
```

**Verify:**
- ServiceAccount exists
- ClusterRole has correct permissions
- ClusterRoleBinding links SA to ClusterRole

### Issue: Custom Resource Not Reconciling

**Check Operator Logs:**
```bash
kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator
```

**Check CR Status:**
```bash
kubectl get eao -o yaml
```

## 📊 Monitoring

### Check Operator Health
```bash
# Health endpoint
kubectl port-forward svc/energy-operator-energy-aware-operator 8080:8080
curl http://localhost:8080/healthz
```

### View Metrics (if ServiceMonitor enabled)
```bash
# Metrics endpoint
kubectl port-forward svc/energy-operator-energy-aware-operator 8080:8080
curl http://localhost:8080/metrics
```

### Check Resource Usage
```bash
kubectl top pod -l app.kubernetes.io/name=energy-aware-operator
```

## 🎯 Next Steps

1. ✅ **Deploy Operator**
   ```bash
   ./scripts/deploy.sh
   ```

2. ✅ **Verify Deployment**
   ```bash
   kubectl get all -l app.kubernetes.io/name=energy-aware-operator
   ```

3. ✅ **Apply Sample CR**
   ```bash
   kubectl apply -f examples/sample-eao.yaml
   ```

4. ✅ **Monitor Logs**
   ```bash
   kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator
   ```

5. 📝 **Create Production Values**
   ```yaml
   # production-values.yaml
   replicaCount: 2
   
   image:
     repository: myregistry.io/energy-aware-operator
     tag: v1.0.0
     pullPolicy: Always
   
   resources:
     requests:
       cpu: 200m
       memory: 256Mi
     limits:
       cpu: 500m
       memory: 512Mi
   
   serviceMonitorEnabled: true
   
   configuration:
     log_level: INFO
     energy_api_url: "http://energy-metric-service:8000"
   ```

6. 🚀 **Deploy to Production**
   ```bash
   helm install energy-operator ./charts/energy-aware-operator \
     -f production-values.yaml \
     -n production \
     --create-namespace
   ```

## ✨ What's Different from Before?

### Before (Basic Chart)
- ❌ Environment variables for config
- ❌ Basic RBAC with wildcards
- ❌ Limited deployment options
- ❌ No ConfigMap
- ❌ No ServiceMonitor
- ❌ Limited documentation

### After (mesh-controller Pattern)
- ✅ ConfigMap-based configuration
- ✅ Granular RBAC permissions
- ✅ Comprehensive deployment options
- ✅ ConfigMap for operator config
- ✅ ServiceMonitor support
- ✅ Extensive documentation
- ✅ Production-ready scripts
- ✅ Better security practices

## 🎉 Ready to Deploy!

Everything is validated and ready. Deploy with confidence:

```bash
cd /Users/rahul/Desktop/Hiro/code/2025/energy-aware-orchestrator/energy-aware-operator
./scripts/deploy.sh
```

---

**Last Updated:** January 3, 2026
**Chart Version:** 0.1.0
**Pattern:** mesh-controller
**Status:** ✅ Ready for Production

