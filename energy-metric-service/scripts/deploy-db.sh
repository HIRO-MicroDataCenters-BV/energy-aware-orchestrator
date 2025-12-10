#!/bin/bash
set -e

# Deploy PostgreSQL Database
# Usage: ./scripts/deploy-db.sh

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RELEASE_NAME="${RELEASE_NAME:-eao-postgres}"
NAMESPACE="${NAMESPACE:-default}"

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deploy PostgreSQL Database            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

print_info "Configuration:"
echo "  Release: $RELEASE_NAME"
echo "  Namespace: $NAMESPACE"
echo ""

# Deploy PostgreSQL
print_info "Deploying PostgreSQL..."
helm upgrade --install "$RELEASE_NAME" "$PROJECT_ROOT/charts/postgres" \
    --namespace "$NAMESPACE" \
    --wait \
    --timeout 5m

# Wait for PostgreSQL to be ready
print_info "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod \
    -l app=eao-postgres \
    -n "$NAMESPACE" \
    --timeout=120s

print_info "PostgreSQL deployed successfully!"
echo ""
echo "Connection details:"
echo "  Host: eao-postgres.$NAMESPACE.svc.cluster.local"
echo "  Port: 5432"
echo "  Database: orchestration_db"
echo ""


