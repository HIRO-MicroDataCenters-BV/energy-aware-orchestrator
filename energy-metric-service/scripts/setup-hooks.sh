#!/bin/bash
# Install pre-commit hook for automatic CRD generation
#
# Usage:
#   ./scripts/setup-hooks.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Setting up git pre-commit hook..."

# Make the hook script executable
chmod +x "$SCRIPT_DIR/pre-commit-crd.sh"

# Check for .git directory in parent (monorepo structure)
if [ -d "$PROJECT_ROOT/../.git/hooks" ]; then
    cp "$SCRIPT_DIR/pre-commit-crd.sh" "$PROJECT_ROOT/../.git/hooks/pre-commit"
    chmod +x "$PROJECT_ROOT/../.git/hooks/pre-commit"
    echo "Pre-commit hook installed at $PROJECT_ROOT/../.git/hooks/pre-commit"
# Check for .git directory in current project
elif [ -d "$PROJECT_ROOT/.git/hooks" ]; then
    cp "$SCRIPT_DIR/pre-commit-crd.sh" "$PROJECT_ROOT/.git/hooks/pre-commit"
    chmod +x "$PROJECT_ROOT/.git/hooks/pre-commit"
    echo "Pre-commit hook installed at $PROJECT_ROOT/.git/hooks/pre-commit"
else
    echo "No .git directory found. Hook not installed."
    echo "   You can manually copy scripts/pre-commit-crd.sh to your .git/hooks/pre-commit"
fi


