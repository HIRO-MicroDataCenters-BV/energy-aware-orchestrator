#!/bin/bash
set -e

# Delete kind cluster
# Usage: ./scripts/delete-kind-cluster.sh [cluster-name]

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CLUSTER_NAME="${1:-eao-cluster}"

echo -e "${GREEN}Deleting kind cluster: $CLUSTER_NAME${NC}"
echo ""

# Check if kind is installed
if ! command -v kind &> /dev/null; then
    echo "Error: kind not found"
    exit 1
fi

# Check if cluster exists
if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo "Cluster '$CLUSTER_NAME' not found"
    echo ""
    echo "Available clusters:"
    kind get clusters
    exit 1
fi

# Confirm deletion
echo -e "${YELLOW}This will delete the cluster and all resources.${NC}"
echo -n "Continue? (y/N) "
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

# Delete cluster
echo ""
echo "Deleting cluster..."
kind delete cluster --name "$CLUSTER_NAME"

echo ""
echo -e "${GREEN}✅ Cluster deleted!${NC}"
echo ""
