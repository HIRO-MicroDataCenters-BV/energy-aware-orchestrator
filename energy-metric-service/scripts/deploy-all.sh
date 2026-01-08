#!/bin/bash
set -e

# Complete Deployment Script - PostgreSQL + Application
# Usage: ./scripts/deploy-all.sh

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NAMESPACE="${NAMESPACE:-default}"
BUILD_IMAGE="${BUILD_IMAGE:-true}"

usage() {
    cat << EOF
Complete Deployment Script - PostgreSQL + Application

Usage: $0 [OPTIONS]

Options:
    -h, --help          Show this help
    -n, --namespace NS  Kubernetes namespace (default: default)
    --no-build          Skip Docker image build
    --db-only           Deploy only PostgreSQL
    --app-only          Deploy only Application

Examples:
    $0                  # Deploy everything
    $0 --no-build       # Deploy without building image
    $0 --db-only        # Deploy only PostgreSQL
    $0 --app-only       # Deploy only Application

EOF
    exit 0
}

DB_ONLY=false
APP_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        -n|--namespace) NAMESPACE="$2"; shift 2 ;;
        --no-build) BUILD_IMAGE=false; shift ;;
        --db-only) DB_ONLY=true; shift ;;
        --app-only) APP_ONLY=true; shift ;;
        *) print_error "Unknown option: $1"; usage ;;
    esac
done

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Energy Metric Service - Complete Deployment           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

print_info "Configuration:"
echo "  Namespace: $NAMESPACE"
echo "  Build Image: $BUILD_IMAGE"
echo ""

# Create namespace if needed
if [ "$NAMESPACE" != "default" ]; then
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        print_info "Creating namespace: $NAMESPACE"
        kubectl create namespace "$NAMESPACE"
    fi
fi

# Step 1: Deploy PostgreSQL
if [ "$APP_ONLY" = false ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════"
    print_info "Step 1: Deploying PostgreSQL..."
    echo "═══════════════════════════════════════════════════════"
    NAMESPACE="$NAMESPACE" "$SCRIPT_DIR/deploy-db.sh"
fi

# Step 2: Deploy Application
if [ "$DB_ONLY" = false ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════"
    print_info "Step 2: Deploying Application..."
    echo "═══════════════════════════════════════════════════════"
    
    BUILD_ARG=""
    if [ "$BUILD_IMAGE" = false ]; then
        BUILD_ARG="--no-build"
    fi
    
    NAMESPACE="$NAMESPACE" "$SCRIPT_DIR/deploy-app.sh" $BUILD_ARG
fi

echo ""
echo "═══════════════════════════════════════════════════════"
print_info "Deployment Complete!"
echo "═══════════════════════════════════════════════════════"
echo ""

# Show status
kubectl get pods -n "$NAMESPACE"
echo ""

echo "Quick commands:"
echo "  # Access API"
echo "  kubectl port-forward -n $NAMESPACE svc/energy-metric-service 8000:8000"
echo ""
echo "  # View logs"
echo "  kubectl logs -n $NAMESPACE -l app=energy-metric-service -f"
echo ""
