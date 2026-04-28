#!/bin/bash
set -e

# Build Energy-Aware Operator Docker Image
# Usage: ./scripts/build.sh [OPTIONS]

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-energy-aware-operator}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
USE_MINIKUBE="${USE_MINIKUBE:-auto}"
GENERATE_CRD="${GENERATE_CRD:-true}"
PUSH_IMAGE="${PUSH_IMAGE:-false}"

usage() {
    cat << EOF
Build Energy-Aware Operator Docker Image

Usage: $0 [OPTIONS]

Options:
    -h, --help                Show this help message
    --image-repo REPO         Docker image repository (default: energy-aware-operator)
    --image-tag TAG           Docker image tag (default: latest)
    --minikube                Force use of minikube Docker environment
    --no-minikube             Don't use minikube Docker environment
    --skip-crd                Skip CRD generation
    --push                    Push image to registry after build

Examples:
    $0                                    # Build with defaults
    $0 --image-tag v1.0.0                 # Build with specific tag
    $0 --minikube --image-tag dev         # Build in minikube
    $0 --image-repo myregistry.io/operator --push  # Build and push to registry

Environment Variables:
    IMAGE_REPOSITORY          Docker image repository
    IMAGE_TAG                 Docker image tag
    USE_MINIKUBE              auto|yes|no (default: auto)

EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        --image-repo) IMAGE_REPOSITORY="$2"; shift 2 ;;
        --image-tag) IMAGE_TAG="$2"; shift 2 ;;
        --minikube) USE_MINIKUBE="yes"; shift ;;
        --no-minikube) USE_MINIKUBE="no"; shift ;;
        --skip-crd) GENERATE_CRD=false; shift ;;
        --push) PUSH_IMAGE=true; shift ;;
        *) print_error "Unknown option: $1"; usage ;;
    esac
done

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Build Energy-Aware Operator Image     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

print_info "Build Configuration:"
echo "  Image:         $IMAGE_REPOSITORY:$IMAGE_TAG"
echo "  Minikube:      $USE_MINIKUBE"
echo "  Generate CRD:  $GENERATE_CRD"
echo "  Push Image:    $PUSH_IMAGE"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."
command -v docker &> /dev/null || { print_error "docker not found"; exit 1; }

# Detect cluster type and set Docker environment
USING_MINIKUBE=false
USING_KIND=false

# Check for kind first
if kubectl config current-context 2>/dev/null | grep -q "kind-"; then
    USING_KIND=true
    KIND_CLUSTER=$(kubectl config current-context | sed 's/kind-//')
    print_info "Detected kind cluster: $KIND_CLUSTER"
    
# Then check for minikube
elif [ "$USE_MINIKUBE" = "yes" ] || [ "$USE_MINIKUBE" = "auto" ]; then
    if command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then
        print_info "Detected minikube - using minikube Docker environment"
        eval $(minikube docker-env)
        USING_MINIKUBE=true
    elif [ "$USE_MINIKUBE" = "yes" ]; then
        print_error "minikube requested but not running"
        exit 1
    fi
fi

if [ "$USING_MINIKUBE" = false ] && [ "$USING_KIND" = false ]; then
    print_info "Using host Docker environment"
fi

# Generate CRD if requested
if [ "$GENERATE_CRD" = true ]; then
    print_info "Generating CRD..."
    cd "$PROJECT_ROOT"
    
    if command -v uv &> /dev/null; then
        if uv run python -m app.crd.builder 2>&1; then
            print_info "CRD generated successfully ✓"
        else
            print_warn "CRD generation failed, will use existing CRD"
        fi
    else
        print_warn "uv not found, skipping CRD generation"
    fi
else
    print_info "Skipping CRD generation"
fi

# Build Docker image
print_info "Building Docker image: $IMAGE_REPOSITORY:$IMAGE_TAG"
cd "$PROJECT_ROOT"

BUILD_START=$(date +%s)

if docker build -t "$IMAGE_REPOSITORY:$IMAGE_TAG" .; then
    BUILD_END=$(date +%s)
    BUILD_TIME=$((BUILD_END - BUILD_START))
    print_info "Docker image built successfully in ${BUILD_TIME}s ✓"
else
    print_error "Docker build failed"
    exit 1
fi

# Load image into kind cluster (kind doesn't share the host Docker daemon)
if [ "$USING_KIND" = true ]; then
    print_info "Loading image into kind cluster '$KIND_CLUSTER'..."
    if kind load docker-image "$IMAGE_REPOSITORY:$IMAGE_TAG" --name "$KIND_CLUSTER"; then
        print_info "Image loaded into kind successfully ✓"
    else
        print_error "Failed to load image into kind cluster"
        exit 1
    fi
fi

# Show image info
print_info "Image details:"
docker images "$IMAGE_REPOSITORY:$IMAGE_TAG" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Push image if requested
if [ "$PUSH_IMAGE" = true ]; then
    if [ "$USING_MINIKUBE" = true ]; then
        print_warn "Skipping push - using minikube Docker environment"
    else
        print_info "Pushing image to registry..."
        if docker push "$IMAGE_REPOSITORY:$IMAGE_TAG"; then
            print_info "Image pushed successfully ✓"
        else
            print_error "Failed to push image"
            exit 1
        fi
    fi
fi

echo ""
print_info "Build complete! ✅"
echo ""
echo "📦 Image: $IMAGE_REPOSITORY:$IMAGE_TAG"
echo ""
echo "🚀 Next steps:"
echo "  # Deploy the operator:"
echo "  ./scripts/deploy.sh --image-repo $IMAGE_REPOSITORY --image-tag $IMAGE_TAG"
echo ""
echo "  # Or just deploy if using defaults:"
echo "  ./scripts/deploy.sh"
echo ""

