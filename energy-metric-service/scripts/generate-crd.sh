#!/bin/bash
# Generate CRD YAML from Pydantic models
#
# Usage:
#   ./scripts/generate-crd.sh
#
# This generates the CRD in three locations:
#   - app/crd/energyawareorchestration-crd.yaml (local reference)
#   - charts/crds/energyawareorchestration-crd.yaml (Helm auto-install)
#   - charts/templates/crd.yaml (Helm upgrade support)

set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Generating EnergyAwareOrchestration CRD..."

# Run the builder
if command -v uv &> /dev/null; then
    uv run python -m app.crd.builder
elif command -v python3 &> /dev/null; then
    python3 -m app.crd.builder
else
    echo "Error: Neither 'uv' nor 'python3' found!"
    exit 1
fi

