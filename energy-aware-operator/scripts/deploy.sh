#!/bin/bash
set -e

# Deploy Energy-Aware Operator
# Usage: ./scripts/deploy.sh [OPTIONS]

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CHART_PATH="${PROJECT_ROOT}/charts/energy-aware-operator"
RELEASE_NAME="${RELEASE_NAME:-energy-operator}"
NAMESPACE="${NAMESPACE:-default}"
IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-energy-aware-operator}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_PULL_POLICY="${IMAGE_PULL_POLICY:-IfNotPresent}"
BUILD_IMAGE="${BUILD_IMAGE:-true}"

usage() {
    cat << EOF
Deploy Energy-Aware Kubernetes Operator

Usage: $0 [OPTIONS]

Options:
    -h, --help                Show this help message
    -n, --namespace NS        Kubernetes namespace (default: default)
    -r, --release NAME        Helm release name (default: energy-operator)
    --image-repo REPO         Docker image repository (default: energy-aware-operator)
    --image-tag TAG           Docker image tag (default: latest)
    --pull-policy POLICY      Image pull policy (default: IfNotPresent)
    --no-build                Skip Docker image build
    --skip-crd                Skip CRD generation/application

Examples:
    $0                                    # Build and deploy to default namespace
    $0 -n operators                       # Deploy to operators namespace
    $0 --no-build                         # Deploy without building image
    $0 -r my-operator --image-tag v1.0.0  # Custom release name and tag

EOF
    exit 0
}

SKIP_CRD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        -n|--namespace) NAMESPACE="$2"; shift 2 ;;
        -r|--release) RELEASE_NAME="$2"; shift 2 ;;
        --image-repo) IMAGE_REPOSITORY="$2"; shift 2 ;;
        --image-tag) IMAGE_TAG="$2"; shift 2 ;;
        --pull-policy) IMAGE_PULL_POLICY="$2"; shift 2 ;;
        --no-build) BUILD_IMAGE=false; shift ;;
        --skip-crd) SKIP_CRD=true; shift ;;
        *) print_error "Unknown option: $1"; usage ;;
    esac
done

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deploy Energy-Aware Operator          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

print_info "Configuration:"
echo "  Release:       $RELEASE_NAME"
echo "  Namespace:     $NAMESPACE"
echo "  Image:         $IMAGE_REPOSITORY:$IMAGE_TAG"
echo "  Pull Policy:   $IMAGE_PULL_POLICY"
echo "  Build Image:   $BUILD_IMAGE"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."
command -v kubectl &> /dev/null || { print_error "kubectl not found"; exit 1; }
command -v helm &> /dev/null || { print_error "helm not found"; exit 1; }
command -v docker &> /dev/null || { print_error "docker not found"; exit 1; }

# Build Docker image
if [ "$BUILD_IMAGE" = true ]; then
    print_info "Building Docker image..."
    cd "$PROJECT_ROOT"
    
    # Check if using minikube
    if command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then
        print_info "Detected minikube - building in minikube Docker environment..."
        eval $(minikube docker-env)
        IMAGE_PULL_POLICY="Never"
    fi
    
    docker build -t "$IMAGE_REPOSITORY:$IMAGE_TAG" .
    if [ $? -eq 0 ]; then
        print_info "Docker image built successfully ✓"
    else
        print_error "Docker build failed"
        exit 1
    fi
fi

# Generate and apply CRD
if [ "$SKIP_CRD" = false ]; then
    print_info "Generating CRD..."
    cd "$PROJECT_ROOT"
    
    if command -v uv &> /dev/null; then
        uv run python -m app.crd.builder || print_warn "CRD generation failed, using existing"
    else
        print_warn "uv not found, skipping CRD generation"
    fi
    
    if [ -f "$CHART_PATH/crds/energy-aware-orchestration-crd.yaml" ]; then
        print_info "Applying CRD..."
        kubectl apply -f "$CHART_PATH/crds/energy-aware-orchestration-crd.yaml"
    else
        print_warn "CRD file not found, skipping"
    fi
fi

# Create namespace if it doesn't exist
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    print_info "Creating namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE"
fi

# Deploy with Helm
print_info "Deploying operator with Helm..."
helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
    --namespace "$NAMESPACE" \
    --set "image.repository=$IMAGE_REPOSITORY" \
    --set "image.tag=$IMAGE_TAG" \
    --set "image.pullPolicy=$IMAGE_PULL_POLICY" \
    --wait \
    --timeout 5m

if [ $? -ne 0 ]; then
    print_error "Helm deployment failed"
    exit 1
fi

# Wait for operator to be ready
print_info "Waiting for operator to be ready..."
kubectl wait --for=condition=ready pod \
    -l app.kubernetes.io/name=energy-aware-operator \
    -n "$NAMESPACE" \
    --timeout=120s || {
    print_error "Operator failed to become ready"
    print_info "Checking pod status..."
    kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=energy-aware-operator
    print_info "Checking pod logs..."
    kubectl logs -n "$NAMESPACE" -l app.kubernetes.io/name=energy-aware-operator --tail=50
    exit 1
}

print_info "Operator deployed successfully! ✅"
echo ""
echo "📊 Verify deployment:"
echo "  kubectl get pods -n $NAMESPACE -l app.kubernetes.io/name=energy-aware-operator"
echo "  kubectl logs -f -n $NAMESPACE -l app.kubernetes.io/name=energy-aware-operator"
echo ""
echo "📝 Apply sample CR:"
echo "  kubectl apply -f examples/sample-eao.yaml"
echo "  kubectl get eao -A"
echo ""
echo "🔍 View operator service:"
echo "  kubectl get svc -n $NAMESPACE"
echo ""
