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
# Dev/test-only mock grid server (see charts/app/templates/grid-stub.yaml).
# Off by default - never enabled in a normal deploy.
ENABLE_GRID_STUB="${ENABLE_GRID_STUB:-false}"
# A real grid endpoint, if provided. Takes priority over the mock server
# (see deployment.yaml's GRID_API_URL derivation).
GRID_API_URL="${GRID_API_URL:-}"

# When rebuilding, tag the image from git content so the Deployment spec
# actually changes and Kubernetes rolls the pod on its own -- a mutable
# "latest" tag makes `helm upgrade` a no-op even after the image content
# changes, leaving the old pod running the stale build. When skipping the
# build (--no-build), fall back to "latest" since no new tag was produced.
if [ "$BUILD_IMAGE" = true ]; then
    _GIT_SHA="$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)"
    _GIT_DIRTY_HASH="$( { git -C "$PROJECT_ROOT" diff HEAD; git -C "$PROJECT_ROOT" status --porcelain; } 2>/dev/null | shasum -a 256 2>/dev/null | cut -c1-8 || true)"
    if [ -n "$_GIT_DIRTY_HASH" ]; then
        IMAGE_TAG="${IMAGE_TAG:-${_GIT_SHA}-dirty-${_GIT_DIRTY_HASH}}"
    else
        IMAGE_TAG="${IMAGE_TAG:-$_GIT_SHA}"
    fi
else
    IMAGE_TAG="${IMAGE_TAG:-latest}"
fi

usage() {
    cat << EOF
Deploy Energy Metric Service Application

Usage: $0 [OPTIONS]

Options:
    -h, --help          Show this help
    -n, --namespace NS  Kubernetes namespace (default: default)
    --no-build          Skip Docker image build
    --grid-stub         Deploy the dev/test mock grid server and point
                         GRID_API_URL at it (see grid_stub.py)
    --grid-url URL      Point GRID_API_URL at a real grid endpoint instead

Examples:
    $0                  # Build and deploy
    $0 --no-build       # Deploy only (use existing image)
    $0 --grid-stub      # Deploy with the mock grid server for testing

EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        -n|--namespace) NAMESPACE="$2"; shift 2 ;;
        --no-build) BUILD_IMAGE=false; shift ;;
        --grid-stub) ENABLE_GRID_STUB=true; shift ;;
        --grid-url) GRID_API_URL="$2"; shift 2 ;;
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
echo "  Grid Stub: $ENABLE_GRID_STUB"
echo "  Grid API URL: ${GRID_API_URL:-<none>}"
echo ""

# Check if PostgreSQL is running
print_info "Checking PostgreSQL..."
if ! kubectl get pod -l app=eao-postgres -n "$NAMESPACE" --no-headers 2>/dev/null | grep -q "Running"; then
    print_error "PostgreSQL is not running!"
    echo "  Deploy PostgreSQL first: ./scripts/deploy-db.sh"
    exit 1
fi
print_info "PostgreSQL is running ✓"

# Apply migrations and check for ORM/DB schema drift before rolling a new
# pod. entrypoint.sh also runs `alembic upgrade head` on pod start (belt
# and suspenders for crash-restarts), but doing it here too means a broken
# migration or a model that's drifted from the DB fails the deploy loudly,
# instead of surfacing later as a CrashLoopBackOff.
print_info "Applying migrations and checking for schema drift..."
DB_SVC_NAME=$(kubectl get svc -n "$NAMESPACE" -l app=eao-postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$DB_SVC_NAME" ]; then
    print_error "Could not find the PostgreSQL service in namespace $NAMESPACE"
    exit 1
fi

DB_NAME="${POSTGRES_DB:-orchestration_db}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
ALEMBIC_CHECK_PORT=15432

kubectl port-forward -n "$NAMESPACE" "svc/$DB_SVC_NAME" "${ALEMBIC_CHECK_PORT}:5432" > /tmp/alembic-check-pf.log 2>&1 &
PF_PID=$!
trap 'kill $PF_PID 2>/dev/null || true' EXIT

PF_READY=false
for _ in $(seq 1 15); do
    if nc -z localhost "$ALEMBIC_CHECK_PORT" 2>/dev/null; then
        PF_READY=true
        break
    fi
    sleep 1
done
if [ "$PF_READY" != true ]; then
    print_error "Could not reach PostgreSQL via port-forward to run migrations"
    exit 1
fi

MIGRATION_DB_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@localhost:${ALEMBIC_CHECK_PORT}/${DB_NAME}"
if ! (cd "$PROJECT_ROOT" && DATABASE_URL="$MIGRATION_DB_URL" uv run alembic upgrade head); then
    print_error "Migration failed - aborting deploy"
    exit 1
fi
if ! (cd "$PROJECT_ROOT" && DATABASE_URL="$MIGRATION_DB_URL" uv run alembic check); then
    print_error "ORM models have drifted from the DB schema - fix before deploying (see diff above)"
    exit 1
fi
print_info "Migrations applied, no schema drift ✓"
kill $PF_PID 2>/dev/null || true

# Build Docker image
if [ "$BUILD_IMAGE" = true ]; then
    print_info "Building Docker image..."
    cd "$PROJECT_ROOT"
    
    # Check if using minikube
    if command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then
        print_info "Building in minikube Docker environment..."
        eval $(minikube docker-env)
    fi
    
    docker build -t energy-metric-service:$IMAGE_TAG -t energy-metric-service:latest .

    # Load into minikube if needed
    if command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then
        print_info "Image built in minikube environment"
    fi

    # Load the Docker image into the cluster (for kind)
    if kubectl config current-context 2>/dev/null | grep -q "^kind-"; then
        KIND_CLUSTER=$(kubectl config current-context | sed 's/^kind-//')
        print_info "Loading image into kind cluster: $KIND_CLUSTER..."
        kind load docker-image energy-metric-service:$IMAGE_TAG --name "$KIND_CLUSTER" || true
    fi
fi

# Deploy application
print_info "Deploying application (image tag: $IMAGE_TAG)..."
HELM_ARGS=(
    --namespace "$NAMESPACE"
    --set "app.image.tag=$IMAGE_TAG"
    --set "gridStub.enabled=$ENABLE_GRID_STUB"
    --wait
    --timeout 5m
)
if [ -n "$GRID_API_URL" ]; then
    HELM_ARGS+=(--set "app.env.GRID_API_URL=$GRID_API_URL")
fi

helm upgrade --install "$RELEASE_NAME" "$PROJECT_ROOT/charts/app" "${HELM_ARGS[@]}"

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


