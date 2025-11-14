#!/bin/bash

# Deployment script for workload application
set -e

NAMESPACE="workspace"
APP_NAME="workload-type-2"

echo "Deploying $APP_NAME to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if namespace exists, create if not
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    echo "Creating namespace $NAMESPACE..."
    kubectl apply -f k8s/namespace.yaml
fi

# Apply all Kubernetes resources
echo "Applying Kubernetes resources..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Wait for deployment to be ready
echo "Waiting for deployment to be ready..."
kubectl rollout status deployment/$APP_NAME -n $NAMESPACE --timeout=300s

# Show deployment status
echo "Deployment status:"
kubectl get pods -n $NAMESPACE -l app=$APP_NAME

# Show services
echo "Services:"
kubectl get services -n $NAMESPACE -l app=$APP_NAME

echo "Deployment completed successfully!"

# Get external access information
NODE_PORT=$(kubectl get service $APP_NAME-nodeport -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}')
echo ""
echo "Access the application:"
echo "- Internal: http://$APP_NAME-service.$NAMESPACE.svc.cluster.local:8000"
echo "- External (NodePort): http://<node-ip>:$NODE_PORT"
echo ""
echo "Useful endpoints:"
echo "- Health check: /health"
echo "- Status: /status"
echo "- Metrics: /metrics"
echo "- Manual trigger: POST /trigger-computation"