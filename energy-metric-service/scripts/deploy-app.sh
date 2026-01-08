#!/bin/bash
set -e

# Deploy Energy Metric Service Application
# Usage: ./scripts/deploy-app.sh

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RELEASE_NAME="${RELEASE_NAME:-energy-metric}"
NAMESPACE="${NAMESPACE:-default}"
BUILD_IMAGE="${BUILD_IMAGE:-true}"

usage() {
    cat << EOF
Deploy Energy Metric Service Application

Usage: $0 [OPTIONS]

Options:
    -h, --help          Show this help
    -n, --namespace NS  Kubernetes namespace (default: default)
    --no-build          Skip Docker image build

Examples:
    $0                  # Build and deploy
    $0 --no-build       # Deploy only (use existing image)

EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        -n|--namespace) NAMESPACE="$2"; shift 2 ;;
        --no-build) BUILD_IMAGE=false; shift ;;
        *) print_error "Unknown option: $1"; usage ;;
    esac
done

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deploy Energy Metric Service          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

print_info "Configuration:"
echo "  Release: $RELEASE_NAME"
echo "  Namespace: $NAMESPACE"
echo "  Build Image: $BUILD_IMAGE"
echo ""

# Check if PostgreSQL is running
print_info "Checking PostgreSQL..."
if ! kubectl get pod -l app=eao-postgres -n "$NAMESPACE" --no-headers 2>/dev/null | grep -q "Running"; then
    print_error "PostgreSQL is not running!"
    echo "  Deploy PostgreSQL first: ./scripts/deploy-db.sh"
    exit 1
fi
print_info "PostgreSQL is running ✓"

# Build Docker image
if [ "$BUILD_IMAGE" = true ]; then
    print_info "Building Docker image..."
    cd "$PROJECT_ROOT"
    
    # Check if using minikube
    if command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then
        print_info "Building in minikube Docker environment..."
        eval $(minikube docker-env)
    fi
    
    docker build -t energy-metric-service:latest .
    
    # Load into minikube if needed
    if command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then
        print_info "Image built in minikube environment"
    fi
fi

# Deploy application
print_info "Deploying application..."
helm upgrade --install "$RELEASE_NAME" "$PROJECT_ROOT/charts/app" \
    --namespace "$NAMESPACE" \
    --wait \
    --timeout 5m

# Wait for app to be ready
print_info "Waiting for application to be ready..."
kubectl wait --for=condition=ready pod \
    -l app=energy-metric-service \
    -n "$NAMESPACE" \
    --timeout=120s

print_info "Application deployed successfully!"
echo ""
echo "Access the API:"
echo "  kubectl port-forward -n $NAMESPACE svc/energy-metric-service 8000:8000"
echo "  Open: http://localhost:8000/docs"
echo ""


