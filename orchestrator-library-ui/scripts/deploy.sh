#!/bin/bash

# Orchestrator Library UI Deployment Script
# This script deploys the Angular UI application and k8s-proxy
#
# Docker Build Strategies:
# ------------------------
# FAST BUILD: Uses Dockerfile.prebuilt (~30 seconds)
#   - Requires: Pre-built dist/ folder (run 'pnpm run build:prod' first)
#   - Best for: Development, quick iterations
#   - Command: pnpm run build:prod && ./scripts/deploy.sh
#
# FULL BUILD: Uses Dockerfile (~5-10 minutes)
#   - Requires: Source code only
#   - Best for: CI/CD, clean deployments, first-time builds
#   - Command: ./scripts/deploy.sh
#
# The script automatically detects which build strategy to use based on
# whether the dist/ folder exists.

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Change to the project root directory
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CHART_DIR="$PROJECT_ROOT/charts/orchestrator-library-ui"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
RELEASE_NAME="${RELEASE_NAME:-orchestrator-ui}"
NAMESPACE="${NAMESPACE:-default}"
BUILD_IMAGE="${BUILD_IMAGE:-true}"

# When rebuilding, tag the image from git content so the Deployment spec
# actually changes and Kubernetes rolls the pod on its own -- a mutable
# "latest" tag makes `helm upgrade` a no-op even after the image content
# changes, leaving the old pod running the stale build (this bit us twice).
# When skipping the build (--no-build), fall back to "latest" since no new
# tag was produced.
if [ "$BUILD_IMAGE" = true ]; then
    _GIT_SHA="$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo nogit)"
    _GIT_DIRTY_HASH="$(git -C "$PROJECT_ROOT" diff HEAD 2>/dev/null | shasum -a 256 2>/dev/null | cut -c1-8 || true)"
    if [ -n "$_GIT_DIRTY_HASH" ]; then
        IMAGE_TAG="${IMAGE_TAG:-${_GIT_SHA}-dirty-${_GIT_DIRTY_HASH}}"
    else
        IMAGE_TAG="${IMAGE_TAG:-$_GIT_SHA}"
    fi
else
    IMAGE_TAG="${IMAGE_TAG:-latest}"
fi
SKIP_PORT_FORWARD="${SKIP_PORT_FORWARD:-false}"
COMMAND="deploy"

# Usage function
usage() {
    cat << EOF
🚀 Orchestrator Library UI Deployment

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    deploy   - Deploy the UI application (default)
    cleanup  - Remove the deployment
    status   - Show deployment status
    logs     - Show application logs

Options:
    -h, --help          Show this help
    -n, --namespace NS  Kubernetes namespace (default: default)
    --no-build          Skip Docker image build

Environment Variables:
    NAMESPACE          Set the namespace (default: default)
    RELEASE_NAME       Set the release name (default: orchestrator-ui)
    BUILD_IMAGE        Build Docker image (default: true)

Examples:
    $0                          # Build and deploy to default namespace
    $0 -n ui                    # Deploy to ui namespace
    $0 --no-build               # Deploy without building image
    $0 deploy -n production     # Deploy to production namespace
    $0 cleanup -n ui            # Cleanup from ui namespace
    $0 logs -n default          # Show logs from default namespace

Docker Build Strategies:
    Fast Build (~30 sec):  pnpm run build:prod && $0
    Full Build (~5-10 min): $0

    The script auto-detects which Dockerfile to use:
    - Dockerfile.prebuilt: If dist/ folder exists (fast)
    - Dockerfile: If no dist/ folder (full build from source)

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        -n|--namespace) NAMESPACE="$2"; shift 2 ;;
        --no-build) BUILD_IMAGE=false; shift ;;
        deploy|cleanup|status|logs) COMMAND="$1"; shift ;;
        *) 
            echo -e "${RED}[ERROR]${NC} Unknown option: $1"
            usage
            ;;
    esac
done

echo "Orchestrator Library UI Deployment"
echo "======================================"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        print_error "Helm is not installed. Please install Helm first."
        exit 1
    fi
    
    # Check if docker is installed (if building)
    if [ "$BUILD_IMAGE" = true ] && ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker or use --no-build flag."
        exit 1
    fi
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Display configuration
display_config() {
    print_status "Configuration:"
    echo "  Release: $RELEASE_NAME"
    echo "  Namespace: $NAMESPACE"
    echo "  Build Image: $BUILD_IMAGE"
    echo "  Chart: $CHART_DIR"
    echo ""
}

# Get cluster info
get_cluster_info() {
    print_status "Getting cluster information..."
    
    CLUSTER_TYPE=$(kubectl config current-context)
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "localhost")
    
    print_status "Cluster: $CLUSTER_TYPE"
    print_status "Node IP: $NODE_IP"
}

# Build Docker image
#
# Docker Build Strategy:
# ----------------------
# This function supports two build modes:
#
# 1. FAST BUILD (Dockerfile.prebuilt):
#    - Used when: dist/ folder exists
#    - Build time: ~30 seconds
#    - Process: Packages pre-built Angular app into nginx container
#    - To prepare: Run 'pnpm run build:prod' before deploying
#
# 2. FULL BUILD (Dockerfile):
#    - Used when: No dist/ folder found
#    - Build time: ~5-10 minutes
#    - Process: Multi-stage build (install deps → build Angular → package in nginx)
#    - Self-contained: Builds everything from source
#
# Recommendation: Use fast build for development, full build for CI/CD
#
build_image() {
    if [ "$BUILD_IMAGE" = false ]; then
        print_status "Skipping Docker image build"
        return
    fi

    print_status "Building Docker image..."
    cd "$PROJECT_ROOT"

    USING_MINIKUBE=false

    # Check if using minikube
    if command -v minikube &> /dev/null && minikube status &> /dev/null 2>&1; then
        USING_MINIKUBE=true
        print_status "Detected minikube cluster"
    fi

    # Check if dist folder exists (pre-built)
    if [ -d "dist/orchestration_library-front/browser" ]; then
        echo ""
        print_status "Build Strategy: FAST BUILD"
        print_status "Using: Dockerfile.prebuilt (pre-built dist folder detected)"
        print_status "Estimated time: ~30 seconds"
        echo ""

        # Build with local Docker first
        docker build -f Dockerfile.prebuilt -t orchestrator-library-ui:$IMAGE_TAG -t orchestrator-library-ui:latest .

        if [ $? -ne 0 ]; then
            print_error "Docker image build failed"
            exit 1
        fi

        # Load into minikube if using minikube
        if [ "$USING_MINIKUBE" = true ]; then
            print_status "Loading image into minikube..."
            minikube image load orchestrator-library-ui:$IMAGE_TAG
        fi
    else
        echo ""
        print_status "Build Strategy: FULL BUILD"
        print_status "Using: Dockerfile (multi-stage build from source)"
        print_status "Estimated time: ~5-10 minutes"
        print_warning "TIP: For faster builds, run 'pnpm run build:prod' first, then deploy"
        echo ""

        if [ "$USING_MINIKUBE" = true ]; then
            # Build directly in minikube's Docker for full builds
            print_status "Building in minikube's Docker environment..."
            eval $(minikube docker-env)
        fi

        docker build -t orchestrator-library-ui:$IMAGE_TAG -t orchestrator-library-ui:latest .

        if [ $? -ne 0 ]; then
            print_error "Docker image build failed"
            exit 1
        fi
    fi

    print_success "Docker image built successfully"
}

# Load the Docker image into the cluster (for kind)
load_image_into_kind() {
    if kubectl config current-context 2>/dev/null | grep -q "^kind-"; then
        KIND_CLUSTER=$(kubectl config current-context | sed 's/^kind-//')
        print_status "Loading image into kind cluster: $KIND_CLUSTER..."
        kind load docker-image orchestrator-library-ui:$IMAGE_TAG --name "$KIND_CLUSTER" || true
    fi
}

# Deploy the chart
deploy_chart() {
    print_status "Deploying Orchestrator Library UI..."
    
    cd "$CHART_DIR"
    
    # Install/upgrade the chart
    print_status "Installing Helm chart..."
    helm upgrade --install "$RELEASE_NAME" . \
        --namespace "$NAMESPACE" \
        --create-namespace \
        --set app.image.tag=$IMAGE_TAG \
        --set app.image.pullPolicy=IfNotPresent \
        --wait \
        --timeout 10m
    
    print_success "Chart deployed successfully"
}

# Wait for pods to be ready
wait_for_pods() {
    print_status "Waiting for pods to be ready..."
    
    # Wait for UI pods
    kubectl wait --for=condition=ready pod \
        -l app=orchestrator-library-ui \
        -n "$NAMESPACE" \
        --timeout=300s || print_warning "UI pods not ready yet"
    
    # Wait for k8s-proxy pods if enabled
    if kubectl get deployment -n "$NAMESPACE" -l app=orchestrator-k8s-proxy &> /dev/null; then
        kubectl wait --for=condition=ready pod \
            -l app=orchestrator-k8s-proxy \
            -n "$NAMESPACE" \
            --timeout=300s || print_warning "K8s proxy pods not ready yet"
    fi
    
    print_success "Pods are ready"
}

# Setup port forwarding
setup_port_forwarding() {
    if [ "${SKIP_PORT_FORWARD}" = "true" ]; then
        print_status "Skipping port forwarding (SKIP_PORT_FORWARD=true)"
        return
    fi

    print_status "Setting up port forwarding..."

    # Kill existing port forwards
    pkill -f "kubectl port-forward.*orchestrator" || true

    # Get service name
    UI_SERVICE=$(kubectl get svc -n "$NAMESPACE" -l app=orchestrator-library-ui -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [ -n "$UI_SERVICE" ]; then
        kubectl port-forward -n "$NAMESPACE" svc/$UI_SERVICE 4200:80 &
        print_status "UI available at: http://localhost:4200"
    fi

    # Port forward k8s-proxy if exists
    PROXY_SERVICE=$(kubectl get svc -n "$NAMESPACE" -l app=orchestrator-k8s-proxy -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [ -n "$PROXY_SERVICE" ]; then
        kubectl port-forward -n "$NAMESPACE" svc/$PROXY_SERVICE 3000:3000 &
        print_status "K8s Proxy available at: http://localhost:3000"
    fi

    # Wait a moment for port forwarding to start
    sleep 3

    print_success "Port forwarding setup complete"
}

# Display access information
display_access_info() {
    echo ""
    echo "Deployment Complete!"
    echo "======================"
    echo ""
    echo "Access URLs:"
    echo "  UI Application:    http://localhost:4200"
    echo "  K8s Proxy:         http://localhost:3000"
    echo ""
    echo "Deployment Info:"
    echo "  Release: $RELEASE_NAME"
    echo "  Namespace: $NAMESPACE"
    echo ""
    echo "Useful Commands:"
    echo "  kubectl get pods -n $NAMESPACE"
    echo "  kubectl logs -n $NAMESPACE -l app=orchestrator-library-ui"
    echo "  kubectl logs -n $NAMESPACE -l app=orchestrator-k8s-proxy"
    echo ""
    echo "For more information, see README.md"
    echo ""
}

# Show logs
show_logs() {
    print_status "Showing application logs..."
    
    UI_POD=$(kubectl get pods -n "$NAMESPACE" -l app=orchestrator-library-ui -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [ -n "$UI_POD" ]; then
        print_status "UI Application logs:"
        kubectl logs -n "$NAMESPACE" "$UI_POD" --tail=50
    else
        print_warning "No UI pods found in namespace $NAMESPACE"
    fi
    
    PROXY_POD=$(kubectl get pods -n "$NAMESPACE" -l app=orchestrator-k8s-proxy -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [ -n "$PROXY_POD" ]; then
        echo ""
        print_status "K8s Proxy logs:"
        kubectl logs -n "$NAMESPACE" "$PROXY_POD" --tail=50
    fi
}

# Cleanup function
cleanup() {
    print_status "Cleaning up from namespace: $NAMESPACE..."
    
    # Kill port forwarding
    pkill -f "kubectl port-forward.*orchestrator" || true
    
    # Uninstall chart
    helm uninstall "$RELEASE_NAME" -n "$NAMESPACE" || true
    
    # Delete resources
    kubectl delete all -l app=orchestrator-library-ui -n "$NAMESPACE" 2>/dev/null || true
    kubectl delete all -l app=orchestrator-k8s-proxy -n "$NAMESPACE" 2>/dev/null || true
    kubectl delete configmap -l app=orchestrator-library-ui -n "$NAMESPACE" 2>/dev/null || true
    kubectl delete configmap -l app=orchestrator-k8s-proxy -n "$NAMESPACE" 2>/dev/null || true
    
    # Only delete namespace if it's not default
    if [ "$NAMESPACE" != "default" ]; then
        print_status "Deleting namespace: $NAMESPACE"
        kubectl delete namespace "$NAMESPACE" || true
    else
        print_warning "Skipping namespace deletion (using default namespace)"
    fi
    
    print_success "Cleanup complete"
}

# Show status
show_status() {
    print_status "Deployment status in namespace: $NAMESPACE"
    echo ""
    
    echo "Helm releases:"
    helm list -n "$NAMESPACE" | grep "$RELEASE_NAME" || echo "  No releases found"
    echo ""
    
    echo "Pods:"
    kubectl get pods -n "$NAMESPACE" -l app=orchestrator-library-ui 2>/dev/null || echo "  No UI pods found"
    kubectl get pods -n "$NAMESPACE" -l app=orchestrator-k8s-proxy 2>/dev/null || echo "  No proxy pods found"
    echo ""
    
    echo "Services:"
    kubectl get svc -n "$NAMESPACE" -l app=orchestrator-library-ui 2>/dev/null || echo "  No UI services found"
    kubectl get svc -n "$NAMESPACE" -l app=orchestrator-k8s-proxy 2>/dev/null || echo "  No proxy services found"
}

# Main execution
main() {
    case "$COMMAND" in
        "deploy")
            check_prerequisites
            display_config
            get_cluster_info
            build_image
            load_image_into_kind
            deploy_chart
            wait_for_pods
            setup_port_forwarding
            display_access_info
            ;;
        "cleanup")
            display_config
            cleanup
            ;;
        "logs")
            show_logs
            ;;
        "status")
            show_status
            ;;
        *)
            print_error "Unknown command: $COMMAND"
            usage
            ;;
    esac
}

# Run main function
main


