#!/bin/bash
set -e

# Simple Install Script - Energy-Aware Operator
# Just run: ./install.sh
# Works with: minikube, kind, Docker Desktop, and remote clusters

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Installing Energy-Aware Operator...${NC}"
echo ""

# Get script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
IMAGE_NAME="energy-aware-operator:latest"

# Detect cluster type
CLUSTER_TYPE="unknown"
PULL_POLICY="IfNotPresent"
KIND_CLUSTER=""

if command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then
    CLUSTER_TYPE="minikube"
    echo "✓ Detected: Minikube"
    eval $(minikube docker-env)
    PULL_POLICY="Never"
    
elif kubectl config current-context 2>/dev/null | grep -q "kind-"; then
    CLUSTER_TYPE="kind"
    KIND_CLUSTER=$(kubectl config current-context | sed 's/kind-//')
    echo "✓ Detected: Kind (cluster: $KIND_CLUSTER)"
    PULL_POLICY="Never"
    
elif command -v microk8s.kubectl &> /dev/null; then
    CLUSTER_TYPE="microk8s"
    echo "✓ Detected: MicroK8s"
    PULL_POLICY="Never"
    
else
    CLUSTER_TYPE="local"
    echo "✓ Detected: Local/Docker Desktop"
    PULL_POLICY="IfNotPresent"
fi

# Build image
echo "Building image..."
cd "$PROJECT_ROOT"
if docker build -q -t "$IMAGE_NAME" . > /dev/null 2>&1; then
    echo "✓ Image built"
else
    echo "Build failed"
    echo "Try manually: docker build -t $IMAGE_NAME ."
    exit 1
fi

# Load image for specific cluster types
case "$CLUSTER_TYPE" in
    "kind")
        echo "Loading image to kind..."
        if kind load docker-image "$IMAGE_NAME" --name "$KIND_CLUSTER" > /dev/null 2>&1; then
            echo "✓ Image loaded to kind"
        else
            echo "Failed to load image to kind"
            exit 1
        fi
        ;;
    "microk8s")
        echo "Loading image to microk8s..."
        if docker save "$IMAGE_NAME" | microk8s ctr image import - > /dev/null 2>&1; then
            echo "✓ Image loaded to microk8s"
        else
            echo "Failed to load image to microk8s"
            exit 1
        fi
        ;;
esac

# Apply CRD
echo "Installing CRD..."
if kubectl apply -f charts/energy-aware-operator/crds/energy-aware-orchestration-crd.yaml > /dev/null 2>&1; then
    echo "✓ CRD installed"
else
    echo "CRD installation failed"
    exit 1
fi

# Install with Helm
echo "Deploying operator..."
if helm upgrade --install energy-operator ./charts/energy-aware-operator \
    --set image.repository=energy-aware-operator \
    --set image.tag=latest \
    --set image.pullPolicy="$PULL_POLICY" \
    --wait --timeout 2m > /dev/null 2>&1; then
    echo "✓ Operator deployed"
else
    echo "Deployment failed"
    echo "Check logs: kubectl logs -l app.kubernetes.io/name=energy-aware-operator"
    exit 1
fi

echo ""
echo -e "${GREEN} Installation complete!${NC}"
echo ""
echo "Cluster type: $CLUSTER_TYPE"
echo "Pull policy: $PULL_POLICY"
echo ""
echo "View pods:"
echo "  kubectl get pods -l app.kubernetes.io/name=energy-aware-operator"
echo ""
echo "View logs:"
echo "  kubectl logs -f -l app.kubernetes.io/name=energy-aware-operator"
echo ""
echo "Try a sample:"
echo "  kubectl apply -f examples/sample-eao.yaml"
echo ""

# Show warning for remote clusters
if [ "$CLUSTER_TYPE" = "local" ] && kubectl cluster-info 2>&1 | grep -qE "(amazonaws\.com|cloud\.google\.com|azure\.com)"; then
    echo -e "${YELLOW}  Note: This appears to be a remote cluster.${NC}"
    echo "   For cloud clusters (EKS/GKE/AKS), consider using:"
    echo "   ./scripts/deploy-cloud.sh --registry <your-registry>"
    echo ""
fi

