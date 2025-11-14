#!/bin/bash

echo "🧹 Starting complete cleanup..."

# 1. Uninstall any existing Helm releases
echo "1. Removing Helm releases..."
helm uninstall energy-metrics --namespace energy-metrics 2>/dev/null || true

# 2. Delete all resources in the namespace
echo "2. Deleting all resources in energy-metrics namespace..."
kubectl delete all --all -n energy-metrics 2>/dev/null || true

# 3. Delete specific problematic resources
echo "3. Cleaning up persistent resources..."
kubectl delete serviceaccount,service,daemonset -l app.kubernetes.io/instance=energy-metrics -n energy-metrics 2>/dev/null || true
kubectl delete configmap,secret -l app.kubernetes.io/instance=energy-metrics -n energy-metrics 2>/dev/null || true
kubectl delete pvc --all -n energy-metrics 2>/dev/null || true

# 4. Delete the namespace completely
echo "4. Deleting namespace..."
kubectl delete namespace energy-metrics 2>/dev/null || true

# 5. Wait for namespace to be fully deleted
echo "5. Waiting for namespace deletion..."
while kubectl get namespace energy-metrics 2>/dev/null; do
  echo "   Waiting for namespace to be deleted..."
  sleep 2
done

# 6. Clean up any finalizers that might be stuck
echo "6. Cleaning up any stuck finalizers..."
kubectl patch pv prometheus-hostpath-pv -p '{"spec":{"claimRef":null}}' 2>/dev/null || true

echo "✅ Cleanup complete!"
echo ""
echo "🚀 Creating hostPath PV and installing helm chart..."
# Create the hostPath PV for Prometheus
kubectl apply -f prometheus-pv.yaml

# Fix permissions on the host directory
minikube ssh -- sudo mkdir -p /tmp/prometheus-data
minikube ssh -- sudo chown -R 65534:65534 /tmp/prometheus-data
minikube ssh -- sudo chmod -R 777 /tmp/prometheus-data

# Install the helm chart
helm install energy-metrics . --namespace energy-metrics --create-namespace --wait --timeout=10m

echo ""
echo "📊 Installation complete! Check status:"
echo "   kubectl get pods -n energy-metrics"
echo "   helm list -n energy-metrics"