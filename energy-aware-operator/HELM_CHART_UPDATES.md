# Helm Chart Updates - Following mesh-controller Pattern

This document describes the updates made to the energy-aware-operator Helm chart to follow the mesh-controller project pattern.

## Overview

The Helm chart has been restructured to follow enterprise-grade Kubernetes operator deployment patterns as demonstrated in the mesh-controller project.

## Key Changes

### 1. Chart Metadata (Chart.yaml)

**Updated:**
- Added proper home URL and maintainer information
- Follows consistent versioning pattern
- Aligned with HIRO-Microdatacenters standards

### 2. Values Configuration (values.yaml)

**Major Improvements:**
- **Simplified structure** with cleaner defaults
- **Empty image repository and tag** - allows flexible configuration at deployment time
- **ServiceMonitor support** for Prometheus metrics scraping
- **Configuration section** - operator settings managed via ConfigMap
- **Better resource defaults** - more conservative limits
- **Comprehensive probe configuration** - separate liveness and readiness probes
- **Service configuration** - proper service port definitions
- **Enhanced service account** - with automount option

**Before:**
```yaml
image:
  repository: energy-aware-operator
  pullPolicy: Never
  tag: "latest"

env:
  - name: LOG_LEVEL
    value: "INFO"
```

**After:**
```yaml
image:
  repository: ""
  tag: ""
  pullPolicy: IfNotPresent

configuration:
  log_level: INFO
  reconcile_interval_seconds: 600
  api_group: "energyaware.hiro.io"
  api_version: "v1"
  plural: "energyawareorchestrations"
```

### 3. Helm Templates

#### _helpers.tpl
- **Improved**: Uses `app.*` naming convention for consistency
- **Added**: Comprehensive helper functions following Helm best practices
- **Standardized**: Naming patterns across all resources

#### serviceaccount.yaml
- **Improved**: Combined ServiceAccount and ClusterRoleBinding in one file
- **Added**: Proper conditional rendering with `serviceAccount.create`
- **Added**: Automount service account token configuration
- **Enhanced**: Annotation support for cloud provider IAM roles

#### rbac.yaml
- **Improved**: More granular permissions
- **Added**: Specific resource and verb definitions
- **Separated**: CRD permissions from core API permissions
- **Added**: Kopf operator framework specific permissions
- **Removed**: Overly broad wildcard permissions

**Before:**
```yaml
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
```

**After:**
```yaml
- apiGroups: [""]
  resources: ["pods", "pods/status", "pods/log"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets", "statefulsets"]
  verbs: ["get", "list", "watch", "update", "patch"]
# ... more specific permissions
```

#### deployment.yaml
- **Added**: ConfigMap volume mount for configuration
- **Added**: POD_NAME and POD_NAMESPACE environment variables
- **Improved**: Proper security contexts
- **Enhanced**: Resource limits and requests
- **Added**: Node selector, affinity, and toleration support
- **Improved**: Probe configuration using values from values.yaml

#### service.yaml
- **Simplified**: Cleaner service definition
- **Improved**: Uses proper port naming
- **Enhanced**: Better label selectors

#### configmap.yaml (NEW)
- **Added**: ConfigMap for operator configuration
- **Pattern**: Configuration as YAML, not environment variables
- **Benefit**: Easier to manage complex configuration
- **Mounted**: As volume in deployment

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "app.fullname" . }}-config
data:
  config.yaml: |-
  {{- .Values.configuration | toYaml | nindent 4 }}
```

#### service-monitor.yaml (NEW)
- **Added**: ServiceMonitor for Prometheus metrics
- **Conditional**: Only deployed if `serviceMonitorEnabled: true`
- **Configured**: Proper endpoint and selector configuration

### 4. Deployment Scripts

#### deploy.sh
**Enhanced:**
- More command-line options (`--image-repo`, `--image-tag`, `--pull-policy`)
- Better error handling and validation
- Minikube auto-detection
- Namespace creation if not exists
- Comprehensive logging and status checking
- Better failure diagnostics

**New Options:**
```bash
-r, --release NAME        # Helm release name
--image-repo REPO         # Docker image repository
--image-tag TAG           # Docker image tag
--pull-policy POLICY      # Image pull policy
--skip-crd                # Skip CRD generation/application
```

#### cleanup.sh
**Enhanced:**
- Better cleanup order (CRs → Helm → CRD → Namespace)
- Forced cleanup on Helm failure
- Timeout handling
- System namespace protection
- Reinstall option
- Comprehensive error handling

**New Options:**
```bash
-r, --release NAME        # Helm release name
--delete-crd              # Delete CRD
--delete-namespace        # Delete namespace
--reinstall               # Cleanup and reinstall
```

### 5. Documentation

#### HELM_INSTALL.md
**Completely Rewritten:**
- Comprehensive installation guide
- Multiple installation methods
- Configuration examples
- Troubleshooting section
- Advanced configuration patterns
- Upgrade and uninstallation procedures

## Benefits of These Changes

### 1. **Production Ready**
- Proper resource limits and requests
- Security contexts and pod security
- Health checks and readiness probes
- Graceful degradation

### 2. **Cloud Native**
- ServiceMonitor for Prometheus
- ConfigMap-based configuration
- Proper RBAC with least privilege
- Support for node affinity and tolerations

### 3. **Enterprise Features**
- Multiple deployment environments
- Custom image repositories
- Flexible namespace management
- Integration with cloud IAM (via service account annotations)

### 4. **Developer Experience**
- Better defaults
- Comprehensive documentation
- Flexible deployment scripts
- Easy troubleshooting

### 5. **Operational Excellence**
- Proper logging and monitoring
- Health check endpoints
- Graceful shutdown
- Configuration management

## Usage Comparison

### Before
```bash
# Limited options
./scripts/deploy.sh -n operators
```

### After
```bash
# Full control
./scripts/deploy.sh \
  -n production \
  -r energy-operator-prod \
  --image-repo myregistry.io/energy-operator \
  --image-tag v1.0.0 \
  --pull-policy Always
```

## Configuration Comparison

### Before (Environment Variables)
```yaml
env:
  - name: LOG_LEVEL
    value: "INFO"
  - name: KOPF_RECONCILE_INTERVAL_SECONDS
    value: "600"
```

### After (ConfigMap)
```yaml
configuration:
  log_level: INFO
  reconcile_interval_seconds: 600
  energy_api_url: "http://energy-metric-service:8000"
  api_group: "energyaware.hiro.io"
```

## Migration Guide

If you have an existing deployment:

1. **Backup current configuration:**
   ```bash
   helm get values energy-operator > old-values.yaml
   ```

2. **Cleanup old deployment:**
   ```bash
   ./scripts/cleanup.sh
   ```

3. **Deploy with new chart:**
   ```bash
   ./scripts/deploy.sh
   ```

4. **Verify deployment:**
   ```bash
   kubectl get pods -l app.kubernetes.io/name=energy-aware-operator
   kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator
   ```

## Alignment with mesh-controller

The following patterns were adopted from mesh-controller:

✅ **Chart Structure**
- Consistent helper templates
- Proper label management
- ServiceAccount + RBAC in same file

✅ **Configuration Management**
- ConfigMap for application config
- Structured YAML configuration
- Environment variables for pod metadata only

✅ **Service Patterns**
- Multiple ports with proper naming
- Health endpoints
- ServiceMonitor support

✅ **Deployment Patterns**
- Pod security contexts
- Resource management
- Probe configuration
- Volume mounts for config

✅ **Values Structure**
- Clean defaults with empty strings
- Comprehensive configuration section
- Feature flags (serviceMonitorEnabled)

✅ **Scripts**
- Comprehensive option parsing
- Better error handling
- Consistent output formatting
- Support for multiple environments

## Testing

Test the deployment:

```bash
# Deploy
./scripts/deploy.sh

# Verify
kubectl get all -l app.kubernetes.io/name=energy-aware-operator

# Test CR
kubectl apply -f examples/sample-eao.yaml
kubectl get eao

# Cleanup
./scripts/cleanup.sh --reinstall
```

## Future Enhancements

Potential improvements based on mesh-controller:

1. **Dashboard Support** - Like mesh-controller's Grafana dashboards
2. **Multi-instance Support** - For high availability
3. **Backup/Restore** - Operator state management
4. **Metrics Endpoint** - For Prometheus scraping
5. **Webhook Support** - For validation and mutation

## References

- mesh-controller Helm chart: `/Users/rahul/Desktop/Hiro/code/2025/multi-cluster/mesh-controller/charts/mesh-controller`
- Helm Best Practices: https://helm.sh/docs/chart_best_practices/
- Kubernetes Operator Patterns: https://kubernetes.io/docs/concepts/extend-kubernetes/operator/

