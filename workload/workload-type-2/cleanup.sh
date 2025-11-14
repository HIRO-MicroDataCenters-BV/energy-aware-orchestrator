#!/bin/bash

# Cleanup script for workload application
set -e

NAMESPACE="workspace"
APP_NAME="workload-type-2"

echo "Cleaning up $APP_NAME from Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Delete all resources created by this app
echo "Deleting Kubernetes resources..."
kubectl delete -f k8s/service.yaml --ignore-not-found=true
kubectl delete -f k8s/deployment.yaml --ignore-not-found=true
kubectl delete -f k8s/configmap.yaml --ignore-not-found=true
kubectl delete -f k8s/namespace.yaml --ignore-not-found=true

# Wait a moment for resources to be cleaned up
sleep 5

# Verify cleanup
echo "Verifying cleanup..."
REMAINING_PODS=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME --no-headers 2>/dev/null | wc -l)
if [ $REMAINING_PODS -eq 0 ]; then
    echo "All pods cleaned up successfully!"
else
    echo "Warning: $REMAINING_PODS pods still exist"
    kubectl get pods -n $NAMESPACE -l app=$APP_NAME
fi

echo "Cleanup completed!"