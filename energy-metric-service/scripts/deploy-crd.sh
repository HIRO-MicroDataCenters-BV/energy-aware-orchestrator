#!/bin/bash
# Deploy only the CRD to Kubernetes
#
# Usage:
#   ./scripts/deploy-crd.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# First regenerate the CRD
echo "🔧 Regenerating CRD..."
./scripts/generate-crd.sh

echo ""
echo "📦 Deploying CRD to Kubernetes..."
kubectl apply -f charts/app/crds/energy-aware-orchestration-crd.yaml

echo ""
echo "✅ CRD deployed successfully!"
echo ""
echo "Verify with: kubectl get crd energyawareorchestrations.eas.hiro.io"

