#!/bin/bash
set -e

# Simple Install Script - Energy-Aware Operator
# Just run: ./install.sh

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Installing Energy-Aware Operator...${NC}"
echo ""

# Get script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Detect minikube
if command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then
    echo "✓ Using minikube"
    eval $(minikube docker-env)
    PULL_POLICY="Never"
else
    echo "✓ Using host Docker"
    PULL_POLICY="IfNotPresent"
fi

# Build image
echo "Building image..."
cd "$PROJECT_ROOT"
docker build -q -t energy-aware-operator:latest . > /dev/null 2>&1
echo "✓ Image built"

# Apply CRD
echo "Installing CRD..."
kubectl apply -f charts/energy-aware-operator/crds/energy-aware-orchestration-crd.yaml > /dev/null 2>&1
echo "✓ CRD installed"

# Install with Helm
echo "Deploying operator..."
helm upgrade --install energy-operator ./charts/energy-aware-operator \
    --set image.repository=energy-aware-operator \
    --set image.tag=latest \
    --set image.pullPolicy="$PULL_POLICY" \
    --wait --timeout 2m > /dev/null 2>&1
echo "✓ Operator deployed"

echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
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

