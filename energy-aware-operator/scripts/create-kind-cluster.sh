#!/bin/bash
set -e

# Create kind cluster for testing Energy-Aware Operator
# Usage: ./scripts/create-kind-cluster.sh [cluster-name]

GREEN='\033[0;32m'
NC='\033[0m'

CLUSTER_NAME="${1:-eao-cluster}"

echo -e "${GREEN}Creating kind cluster: $CLUSTER_NAME${NC}"
echo ""

# Check if kind is installed
if ! command -v kind &> /dev/null; then
    echo "Error: kind not found"
    echo "Install: brew install kind  (or see https://kind.sigs.k8s.io)"
    exit 1
fi

# Check if cluster already exists
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo "Cluster '$CLUSTER_NAME' already exists"
    echo ""
    echo "To delete and recreate:"
    echo "  kind delete cluster --name $CLUSTER_NAME"
    exit 1
fi

# Create cluster
echo "Creating cluster..."
kind create cluster --name "$CLUSTER_NAME" --wait 60s

echo ""
echo -e "${GREEN}✅ Kind cluster ready!${NC}"
echo ""

# Show cluster info
echo "Cluster: kind-${CLUSTER_NAME}"
kubectl get nodes

echo ""
echo -e "${GREEN}Next steps:${NC}"
echo ""
echo "  # Install operator"
echo "  ./install.sh"
echo ""
echo "  # Apply sample resources"
echo "  kubectl apply -f examples/sample-eao.yaml"
echo ""
echo "  # Delete cluster when done"
echo "  kind delete cluster --name $CLUSTER_NAME"
echo ""
