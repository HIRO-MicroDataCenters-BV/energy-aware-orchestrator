#!/bin/bash

# Cleanup script for workload-type-1 Kubernetes resources

set -e

NAMESPACE="workspace"

echo "Cleaning up workload-type-1 Kubernetes resources..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
    echo "Namespace ${NAMESPACE} does not exist. Nothing to clean up."
    exit 0
fi

echo "Found namespace: ${NAMESPACE}"

# Delete deployment first to stop pods gracefully
echo "Deleting deployment..."
if kubectl get deployment workload-type-1 -n "${NAMESPACE}" &> /dev/null; then
    kubectl delete deployment workload-type-1 -n "${NAMESPACE}" --timeout=60s
    echo "✓ Deployment deleted"
else
    echo "⚠ Deployment not found"
fi

# Delete service
echo "Deleting service..."
if kubectl get service workload-type-1-service -n "${NAMESPACE}" &> /dev/null; then
    kubectl delete service workload-type-1-service -n "${NAMESPACE}"
    echo "✓ Service deleted"
else
    echo "⚠ Service not found"
fi

# Delete configmap
echo "Deleting ConfigMap..."
if kubectl get configmap workload-type-1-config -n "${NAMESPACE}" &> /dev/null; then
    kubectl delete configmap workload-type-1-config -n "${NAMESPACE}"
    echo "✓ ConfigMap deleted"
else
    echo "⚠ ConfigMap not found"
fi

# Delete namespace (this will clean up any remaining resources)
echo "Deleting namespace..."
kubectl delete namespace "${NAMESPACE}" --timeout=120s

echo ""
echo "✅ Cleanup completed successfully!"
echo ""
echo "All workload-type-1 resources have been removed from the cluster."
echo ""
echo "Note: The Docker image 'workload-type-1:v1' is still available locally."
echo "To remove it, run: docker rmi workload-type-1:v1"