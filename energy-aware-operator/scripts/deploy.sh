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
BUILD_IMAGE="${BUILD_IMAGE:-false}"
APPLY_CRD="${APPLY_CRD:-true}"
WAIT="${WAIT:-true}"
TIMEOUT="${TIMEOUT:-5m}"

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
    --build                   Build image before deploying (runs build.sh)
    --skip-crd                Skip CRD application
    --no-wait                 Don't wait for deployment to be ready
    --timeout DURATION        Wait timeout (default: 5m)

Examples:
    $0                                    # Deploy with defaults
    $0 --build                            # Build then deploy
    $0 -n operators                       # Deploy to operators namespace
    $0 --no-wait                          # Deploy without waiting
    $0 -r my-operator --image-tag v1.0.0  # Custom release and tag

Environment Variables:
    RELEASE_NAME              Helm release name
    NAMESPACE                 Kubernetes namespace
    IMAGE_REPOSITORY          Docker image repository
    IMAGE_TAG                 Docker image tag
    IMAGE_PULL_POLICY         Image pull policy

EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        -n|--namespace) NAMESPACE="$2"; shift 2 ;;
        -r|--release) RELEASE_NAME="$2"; shift 2 ;;
        --image-repo) IMAGE_REPOSITORY="$2"; shift 2 ;;
        --image-tag) IMAGE_TAG="$2"; shift 2 ;;
        --pull-policy) IMAGE_PULL_POLICY="$2"; shift 2 ;;
        --build) BUILD_IMAGE=true; shift ;;
        --skip-crd) APPLY_CRD=false; shift ;;
        --no-wait) WAIT=false; shift ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        *) print_error "Unknown option: $1"; usage ;;
    esac
done

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deploy Energy-Aware Operator          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

print_info "Deployment Configuration:"
echo "  Release:       $RELEASE_NAME"
echo "  Namespace:     $NAMESPACE"
echo "  Image:         $IMAGE_REPOSITORY:$IMAGE_TAG"
echo "  Pull Policy:   $IMAGE_PULL_POLICY"
echo "  Build Image:   $BUILD_IMAGE"
echo "  Apply CRD:     $APPLY_CRD"
echo "  Wait:          $WAIT"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."
command -v kubectl &> /dev/null || { print_error "kubectl not found"; exit 1; }
command -v helm &> /dev/null || { print_error "helm not found"; exit 1; }

# Detect cluster type (check kind first to avoid conflicts)
CLUSTER_TYPE="unknown"
KIND_CLUSTER=""
USING_MINIKUBE=false

if kubectl config current-context 2>/dev/null | grep -q "kind-"; then
    CLUSTER_TYPE="kind"
    KIND_CLUSTER=$(kubectl config current-context | sed 's/kind-//')
    print_info "Detected kind cluster: $KIND_CLUSTER"
elif command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then
    CLUSTER_TYPE="minikube"
    USING_MINIKUBE=true
    print_info "Detected minikube cluster"
fi

# Build image if requested
if [ "$BUILD_IMAGE" = true ]; then
    print_info "Building Docker image..."
    
    # For minikube, use minikube Docker environment
    if [ "$USING_MINIKUBE" = true ]; then
        print_info "Using minikube Docker environment for build"
        eval $(minikube docker-env)
    fi
    
    "$SCRIPT_DIR/build.sh" --image-repo "$IMAGE_REPOSITORY" --image-tag "$IMAGE_TAG"
    echo ""
fi

# Handle image loading for local clusters
IMAGE_FULL="${IMAGE_REPOSITORY}:${IMAGE_TAG}"

if [ "$IMAGE_PULL_POLICY" != "Always" ]; then
    # For kind cluster - load image explicitly
    if [ "$CLUSTER_TYPE" = "kind" ]; then
        print_info "Checking/loading image to kind cluster..."
        
        # Check if image exists in local Docker
        if docker image inspect "$IMAGE_FULL" &> /dev/null; then
            if kind load docker-image "$IMAGE_FULL" --name "$KIND_CLUSTER" 2>&1; then
                print_info "Image loaded to kind successfully ✓"
                IMAGE_PULL_POLICY="Never"
            else
                print_warn "Failed to load image to kind"
                print_warn "Run: ./scripts/build.sh && kind load docker-image $IMAGE_FULL --name $KIND_CLUSTER"
            fi
        else
            print_warn "Image $IMAGE_FULL not found locally"
            print_warn "Run: ./scripts/build.sh to build the image first"
        fi
    
    # For minikube cluster - check image in minikube Docker
    elif [ "$USING_MINIKUBE" = true ]; then
        print_info "Checking image in minikube Docker environment..."
        
        # Switch to minikube Docker env to check image
        eval $(minikube docker-env)
        
        if docker image inspect "$IMAGE_FULL" &> /dev/null; then
            print_info "Image found in minikube Docker environment ✓"
            IMAGE_PULL_POLICY="Never"
        else
            print_warn "Image not found in minikube Docker environment"
            print_warn "Run: eval \$(minikube docker-env) && ./scripts/build.sh"
            print_warn "Or: ./scripts/build.sh (auto-detects minikube)"
        fi
    fi
fi

# Apply CRD if requested
if [ "$APPLY_CRD" = true ]; then
    CRD_FILE="$CHART_PATH/crds/energy-aware-orchestration-crd.yaml"
    
    if [ -f "$CRD_FILE" ]; then
        print_info "Applying CRD..."
        if kubectl apply -f "$CRD_FILE"; then
            print_info "CRD applied successfully ✓"
        else
            print_error "Failed to apply CRD"
            exit 1
        fi
    else
        print_warn "CRD file not found: $CRD_FILE"
    fi
else
    print_info "Skipping CRD application"
fi

# Create namespace if it doesn't exist
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    print_info "Creating namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE"
fi

# Deploy with Helm
print_info "Deploying operator with Helm..."
HELM_CMD="helm upgrade --install $RELEASE_NAME $CHART_PATH \
    --namespace $NAMESPACE \
    --set image.repository=$IMAGE_REPOSITORY \
    --set image.tag=$IMAGE_TAG \
    --set image.pullPolicy=$IMAGE_PULL_POLICY"

if [ "$WAIT" = true ]; then
    HELM_CMD="$HELM_CMD --wait --timeout $TIMEOUT"
fi

if eval "$HELM_CMD"; then
    print_info "Helm deployment successful ✓"
else
    print_error "Helm deployment failed"
    exit 1
fi

# Wait for operator to be ready
if [ "$WAIT" = true ]; then
    print_info "Waiting for operator pod to be ready..."
    if kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/name=energy-aware-operator \
        -n "$NAMESPACE" \
        --timeout=120s 2>/dev/null; then
        print_info "Operator pod is ready ✓"
    else
        print_warn "Timeout waiting for pod readiness (pod may still be starting)"
        print_info "Checking pod status..."
        kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=energy-aware-operator
    fi
fi

echo ""
print_info "Deployment complete! ✅"
echo ""

# Show deployment status
print_info "Deployment Status:"
kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=energy-aware-operator

echo ""
echo "📊 Useful commands:"
echo ""
echo "  # View pods"
echo "  kubectl get pods -n $NAMESPACE -l app.kubernetes.io/name=energy-aware-operator"
echo ""
echo "  # View logs"
echo "  kubectl logs -f -n $NAMESPACE -l app.kubernetes.io/name=energy-aware-operator"
echo ""
echo "  # View all resources"
echo "  kubectl get all -n $NAMESPACE -l app.kubernetes.io/name=energy-aware-operator"
echo ""
echo "  # View Helm release"
echo "  helm status $RELEASE_NAME -n $NAMESPACE"
echo ""
echo "📝 Apply sample CR:"
echo "  kubectl apply -f examples/sample-eao.yaml"
echo "  kubectl get eao -A"
echo ""
echo "🧹 Cleanup:"
echo "  ./scripts/cleanup.sh -n $NAMESPACE -r $RELEASE_NAME"
echo ""
