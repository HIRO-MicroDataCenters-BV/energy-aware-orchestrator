#!/bin/bash
# Pre-commit hook for automatic CRD generation
# 
# This hook regenerates the CRD YAML when Pydantic models change.
# Install with: make setup-hooks (from energy-metric-service directory)
#
# The hook checks if any CRD-related files have changed and regenerates
# the CRD YAML, then stages the generated files.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the root of the git repository
GIT_ROOT=$(git rev-parse --show-toplevel)
SERVICE_DIR="$GIT_ROOT/energy-metric-service"

# Check if energy-metric-service directory exists
if [ ! -d "$SERVICE_DIR" ]; then
    # Maybe we're in a different structure, try current directory
    if [ -f "app/crd/builder.py" ]; then
        SERVICE_DIR="."
    else
        # Not in the right repo, skip
        exit 0
    fi
fi

cd "$SERVICE_DIR"

# Files that trigger CRD regeneration
CRD_SOURCE_FILES=(
    "app/crd/energy_aware_orchestration_model.py"
    "app/crd/builder.py"
)

# Generated CRD files
CRD_OUTPUT_FILES=(
    "app/crd/energyawareorchestration-crd.yaml"
    "charts/crds/energyawareorchestration-crd.yaml"
    "charts/templates/crd.yaml"
)

# Check if any CRD source files are staged for commit
REGENERATE=false
for file in "${CRD_SOURCE_FILES[@]}"; do
    if git diff --cached --name-only | grep -q "$file"; then
        REGENERATE=true
        break
    fi
done

if [ "$REGENERATE" = true ]; then
    echo -e "${YELLOW}[pre-commit]${NC} CRD source files changed, regenerating CRD YAML..."
    
    # Check if uv is available
    if command -v uv &> /dev/null; then
        uv run python -m app.crd.builder
    elif command -v python3 &> /dev/null; then
        python3 -m app.crd.builder
    else
        echo -e "${RED}[pre-commit]${NC} Error: Neither 'uv' nor 'python3' found!"
        exit 1
    fi
    
    # Stage the regenerated CRD files
    for file in "${CRD_OUTPUT_FILES[@]}"; do
        if [ -f "$file" ]; then
            git add "$file"
            echo -e "${GREEN}[pre-commit]${NC} Staged: $file"
        fi
    done
    
    echo -e "${GREEN}[pre-commit]${NC} CRD regeneration complete!"
fi

exit 0

