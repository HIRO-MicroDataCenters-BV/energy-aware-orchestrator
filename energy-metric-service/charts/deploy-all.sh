#!/bin/bash
set -e

# Complete Deployment Script - PostgreSQL + FastAPI Application

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Energy Metric Service - DB & app Complete Deployment ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
RELEASE_NAME="${RELEASE_NAME:-energy-metric}"
NAMESPACE="${NAMESPACE:-default}"
BUILD_IMAGE="${BUILD_IMAGE:-true}"

usage() {
    cat << EOF
Complete Deployment Script

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help
    -n, --namespace NS      Kubernetes namespace (default: default)
    -r, --release NAME      Helm release name (default: energy-system)
    --no-build              Skip Docker image build
    --postgres-only         Deploy only PostgreSQL
    --app-only              Deploy only application

Examples:
    # Deploy everything
    $0

    # Deploy in production namespace
    $0 --namespace production --release energy-prod

    # Deploy without building image
    $0 --no-build

    # Deploy only PostgreSQL
    $0 --postgres-only

EOF
    exit 0
}

POSTGRES_ONLY=false
APP_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -r|--release)
            RELEASE_NAME="$2"
            shift 2
            ;;
        --no-build)
            BUILD_IMAGE=false
            shift
            ;;
        --postgres-only)
            POSTGRES_ONLY=true
            shift
            ;;
        --app-only)
            APP_ONLY=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

print_info "Configuration:"
echo "============================================"
echo "  Release: $RELEASE_NAME"
echo "  Namespace: $NAMESPACE"
echo "  Build Image: $BUILD_IMAGE"
echo "============================================"
echo ""

# Create namespace
if [ "$NAMESPACE" != "default" ]; then
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        print_info "Creating namespace: $NAMESPACE"
        kubectl create namespace "$NAMESPACE"
    fi
fi

# Step 1: Build Docker image
echo "============================================>"
if [ "$BUILD_IMAGE" = true ] && [ "$POSTGRES_ONLY" = false ]; then
    print_info "Building energy-metric-service app Docker image..."
    cd "$SCRIPT_DIR/.."
    docker build -t energy-metric-service:latest .

    # Load into cluster if needed
    if command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then
        echo "local minikube cluster detected"
        print_info "Loading image into minikube cluster..."
        minikube image load energy-metric-service:latest
    elif command -v kind &> /dev/null; then
        print_info "Loading image into kind cluster..."
        kind load docker-image energy-metric-service:latest 2>/dev/null || true
    fi
    cd "$SCRIPT_DIR"
fi
echo "<============================================"
echo ""


# Step 2: Deploy with Helm
echo "============================================>"
print_info "Deploying to Kubernetes using Helm..."

if [ "$APP_ONLY" = false ]; then
    print_info "Installing PostgreSQL..."
fi

if [ "$POSTGRES_ONLY" = false ]; then
    print_info "Installing Application..."
fi

HELM_CMD=(helm upgrade --install "$RELEASE_NAME" "$SCRIPT_DIR" \
    --namespace "$NAMESPACE" \
    --wait \
    --timeout 10m)
print_info "Running Helm command:"
echo "  ${HELM_CMD[*]}"
"${HELM_CMD[@]}"
helm upgrade --install "$RELEASE_NAME" "$SCRIPT_DIR" \
    --namespace "$NAMESPACE" \
    --wait \
    --timeout 10m

echo " "

# Step 3: Verify deployment
print_info "Verifying deployment..."
kubectl get pods -n "$NAMESPACE"

echo " "

# Wait for pods
print_info "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod \
    -l app=eao-postgres \
    -n "$NAMESPACE" \
    --timeout=300s || true

echo " "
if [ "$POSTGRES_ONLY" = false ]; then
    print_info "Waiting for application to be ready..."
    kubectl wait --for=condition=ready pod \
        -l app=energy-metric-service \
        -n "$NAMESPACE" \
        --timeout=300s || true
fi

echo " "
# Get connection details
print_info "Deployment complete!"
echo "<============================================"

echo ""
echo "============================================"
echo "  Connection Details"
echo "============================================"
echo ""
echo "PostgreSQL:"
echo "  Host: eao-postgres.$NAMESPACE.svc.cluster.local"
echo "  Port: 5432"
echo "  Database: orchestration_db"
echo "  Username: postgres"
echo "  Password: postgres"
echo ""

if [ "$POSTGRES_ONLY" = false ]; then
    echo "Application:"
    echo "  Service: energy-metric-service.$NAMESPACE.svc.cluster.local"
    echo "  Port: 8000"
    echo ""
    echo "  Access API:"
    echo "  kubectl port-forward -n $NAMESPACE svc/energy-metric-service 8000:8000"
    echo "  Open: http://localhost:8000/docs"
fi

echo ""
echo "============================================"
echo "  Useful Commands"
echo "============================================"
echo ""
echo "# View all resources"
echo "kubectl get all -n $NAMESPACE"
echo ""
echo "# View logs"
echo "kubectl logs -n $NAMESPACE -l app=energy-metric-service -f"
echo ""
