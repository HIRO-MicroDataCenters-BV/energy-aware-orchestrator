#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Change to the parent directory (helm chart root)
CHART_DIR="$(dirname "$SCRIPT_DIR")"
cd "$CHART_DIR"

# Default configuration
RELEASE_NAME="${RELEASE_NAME:-energy-metrics}"
NAMESPACE="${NAMESPACE:-default}"
REINSTALL="${REINSTALL:-false}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace) NAMESPACE="$2"; shift 2 ;;
        --reinstall) REINSTALL=true; shift ;;
        -h|--help)
            cat << EOF
🧹 Energy Metrics Cleanup Script

Usage: $0 [OPTIONS]

Options:
    -n, --namespace NS  Kubernetes namespace (default: default)
    --reinstall         Reinstall after cleanup
    -h, --help          Show this help

Examples:
    $0                       # Cleanup from default namespace
    $0 -n monitoring         # Cleanup from monitoring namespace
    $0 --reinstall           # Cleanup and reinstall

EOF
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "🧹 Starting complete cleanup..."
echo "  Release: $RELEASE_NAME"
echo "  Namespace: $NAMESPACE"
echo ""

# 1. Kill port forwarding
echo "1. Stopping port forwarding..."
pkill -f "kubectl port-forward" || true

# 2. Uninstall any existing Helm releases
echo "2. Removing Helm releases..."
helm uninstall "$RELEASE_NAME" --namespace "$NAMESPACE" 2>/dev/null || true

# 3. Delete all resources in the namespace
echo "3. Deleting all resources in $NAMESPACE namespace..."
kubectl delete all --all -n "$NAMESPACE" 2>/dev/null || true

# 4. Delete specific problematic resources
echo "4. Cleaning up persistent resources..."
kubectl delete serviceaccount,service,daemonset -l app.kubernetes.io/instance="$RELEASE_NAME" -n "$NAMESPACE" 2>/dev/null || true
kubectl delete configmap,secret -l app.kubernetes.io/instance="$RELEASE_NAME" -n "$NAMESPACE" 2>/dev/null || true
kubectl delete pvc --all -n "$NAMESPACE" 2>/dev/null || true

# 5. Delete the namespace completely (if not default)
if [ "$NAMESPACE" != "default" ]; then
    echo "5. Deleting namespace..."
    kubectl delete namespace "$NAMESPACE" 2>/dev/null || true
    
    # Wait for namespace to be fully deleted
    echo "6. Waiting for namespace deletion..."
    while kubectl get namespace "$NAMESPACE" 2>/dev/null; do
      echo "   Waiting for namespace to be deleted..."
      sleep 2
    done
else
    echo "5. Skipping namespace deletion (using default namespace)"
fi

# 6. Clean up any finalizers that might be stuck
echo "7. Cleaning up any stuck finalizers..."
kubectl patch pv prometheus-hostpath-pv -p '{"spec":{"claimRef":null}}' 2>/dev/null || true

echo "✅ Cleanup complete!"

# Reinstall if requested
if [ "$REINSTALL" = true ]; then
    echo ""
    echo "🚀 Reinstalling helm chart..."
    
    # Check if using minikube
    if command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then
        echo "Setting up minikube hostPath..."
        # Fix permissions on the host directory
        minikube ssh -- sudo mkdir -p /tmp/prometheus-data
        minikube ssh -- sudo chown -R 65534:65534 /tmp/prometheus-data
        minikube ssh -- sudo chmod -R 777 /tmp/prometheus-data
    fi
    
    # Install the helm chart
    helm upgrade --install "$RELEASE_NAME" . \
        --namespace "$NAMESPACE" \
        --create-namespace \
        --wait \
        --timeout=10m
    
    echo ""
    echo "📊 Installation complete! Check status:"
    echo "   kubectl get pods -n $NAMESPACE"
    echo "   helm list -n $NAMESPACE"
fi