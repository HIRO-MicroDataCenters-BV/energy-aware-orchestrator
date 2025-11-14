#!/bin/bash

# Deployment script for workload-type-3 Kubernetes resources

set -e

NAMESPACE="workspace"
IMAGE_NAME="workload-type-3:v1"

echo "Deploying workload-type-3 to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we can connect to Kubernetes cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Cannot connect to Kubernetes cluster"
    exit 1
fi

echo "✓ Kubernetes cluster connection verified"

# Check if Docker image exists
if ! docker image inspect "${IMAGE_NAME}" &> /dev/null; then
    echo "Error: Docker image ${IMAGE_NAME} not found"
    echo "Please run ./build.sh first to build the image"
    exit 1
fi

echo "✓ Docker image ${IMAGE_NAME} found"

# Apply Kubernetes manifests in order
echo "Creating namespace..."
kubectl apply -f k8s/namespace.yaml

echo "Creating ConfigMap..."
kubectl apply -f k8s/configmap.yaml

echo "Creating Service..."
kubectl apply -f k8s/service.yaml

echo "Creating Deployment..."
kubectl apply -f k8s/deployment.yaml

echo "Waiting for deployment to be ready..."
kubectl rollout status deployment/workload-type-3 -n "${NAMESPACE}" --timeout=300s

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "Application Information:"
echo "  Namespace: ${NAMESPACE}"
echo "  Service: workload-type-3-service"
echo "  Port: 8002 (NodePort: 32004)"
echo ""
echo "Workload Pattern:"
echo "  Active Phase: 20 minutes (random intensity 0.3-1.0)"
echo "  Idle Phase: 60 minutes (minimal activity)"
echo "  Total Cycle: 80 minutes"
echo ""
echo "Useful Commands:"
echo "  Check pod status:"
echo "    kubectl get pods -n ${NAMESPACE} -l app=workload-type-3"
echo ""
echo "  View logs:"
echo "    kubectl logs -n ${NAMESPACE} -l app=workload-type-3 -f"
echo ""
echo "  Check current cycle status:"
echo "    curl http://\$(minikube ip):32004/status"
echo ""
echo "  Get detailed cycle information:"
echo "    curl http://\$(minikube ip):32004/cycle-info"
echo ""
echo "  Health check:"
echo "    curl http://\$(minikube ip):32004/health"
echo ""
echo "  Manual trigger (for testing):"
echo "    curl -X POST http://\$(minikube ip):32004/trigger-active"
echo ""
echo "  Monitor resource usage:"
echo "    kubectl top pods -n ${NAMESPACE} -l app=workload-type-3"