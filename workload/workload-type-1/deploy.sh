#!/bin/bash

# Deployment script for workload-type-1 Kubernetes resources

set -e

NAMESPACE="workspace"
IMAGE_NAME="workload-type-1:v1"

echo "Deploying workload-type-1 to Kubernetes..."

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
kubectl rollout status deployment/workload-type-1 -n "${NAMESPACE}" --timeout=300s

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "Application Information:"
echo "  Namespace: ${NAMESPACE}"
echo "  Service: workload-type-1-service"
echo "  Port: 8001 (NodePort: 32003)"
echo ""
echo "Time Windows:"
echo "  Morning: 08:00-10:00 (2 hours)"
echo "  Evening: 18:00-21:00 (3 hours, but runs only 2 hours)"
echo ""
echo "Useful Commands:"
echo "  Check pod status:"
echo "    kubectl get pods -n ${NAMESPACE} -l app=workload-type-1"
echo ""
echo "  View logs:"
echo "    kubectl logs -n ${NAMESPACE} -l app=workload-type-1 -f"
echo ""
echo "  Check application status:"
echo "    curl http://\$(minikube ip):32003/status"
echo ""
echo "  Health check:"
echo "    curl http://\$(minikube ip):32003/health"
echo ""
echo "  Manual triggers (for testing):"
echo "    curl -X POST http://\$(minikube ip):32003/trigger-morning"
echo "    curl -X POST http://\$(minikube ip):32003/trigger-evening"