#!/bin/bash

# Energy Metrics Monitoring Setup Script
# This script deploys Kepler, Prometheus, and Grafana for energy monitoring

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Change to the parent directory (helm chart root)
CHART_DIR="$(dirname "$SCRIPT_DIR")"
cd "$CHART_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
RELEASE_NAME="${RELEASE_NAME:-energy-metrics}"
NAMESPACE="${NAMESPACE:-default}"
COMMAND="deploy"

# Usage function
usage() {
    cat << EOF
🚀 Energy Metrics Monitoring Setup

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    deploy   - Deploy the energy metrics stack (default)
    cleanup  - Remove the deployment
    test     - Test the deployment
    status   - Show pod status

Options:
    -h, --help          Show this help
    -n, --namespace NS  Kubernetes namespace (default: default)

Environment Variables:
    NAMESPACE          Set the namespace (default: default)
    RELEASE_NAME       Set the release name (default: energy-metrics)

Examples:
    $0                          # Deploy to default namespace
    $0 -n monitoring            # Deploy to monitoring namespace
    $0 deploy -n energy-metrics # Deploy to energy-metrics namespace
    $0 cleanup -n monitoring    # Cleanup from monitoring namespace

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        -n|--namespace) NAMESPACE="$2"; shift 2 ;;
        deploy|cleanup|test|status) COMMAND="$1"; shift ;;
        *) print_error "Unknown option: $1"; usage ;;
    esac
done

echo "🚀 Energy Metrics Monitoring Setup"
echo "=================================="

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

# Deploy the chart
deploy_chart() {
    print_status "Deploying energy metrics monitoring stack..."
    
    # Update dependencies
    print_status "Updating Helm dependencies..."
    helm dependency update
    
    # Install the chart
    print_status "Installing Helm chart..."
    helm upgrade --install "$RELEASE_NAME" . \
        --namespace "$NAMESPACE" \
        --create-namespace \
        --wait \
        --timeout 10m
    
    print_success "Chart deployed successfully"
}

# Wait for pods to be ready
wait_for_pods() {
    print_status "Waiting for all pods to be ready..."
    
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=kepler -n "$NAMESPACE" --timeout=300s || print_warning "Kepler pods not ready"
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus -n "$NAMESPACE" --timeout=300s || print_warning "Prometheus pods not ready"
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n "$NAMESPACE" --timeout=300s || print_warning "Grafana pods not ready"
    
    print_success "Pods are ready"
}

# Setup port forwarding
setup_port_forwarding() {
    print_status "Setting up port forwarding..."
    
    # Kill existing port forwards
    pkill -f "kubectl port-forward" || true
    
    # Start new port forwards
    kubectl port-forward -n "$NAMESPACE" svc/${RELEASE_NAME}-grafana 3000:80 &
    kubectl port-forward -n "$NAMESPACE" svc/${RELEASE_NAME}-prometheus-server 9090:80 &
    kubectl port-forward -n "$NAMESPACE" svc/${RELEASE_NAME}-kepler 9102:9102 &
    
    # Wait a moment for port forwarding to start
    sleep 3
    
    print_success "Port forwarding setup complete"
}

# Test the deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Test Kepler
    if curl -s http://localhost:9102/metrics | grep -q "kepler_container_joules_total"; then
        print_success "Kepler metrics are available"
    else
        print_warning "Kepler metrics not yet available (may take a few minutes)"
    fi
    
    # Test Prometheus
    if curl -s http://localhost:9090/api/v1/query?query=up | grep -q "result"; then
        print_success "Prometheus is responding"
    else
        print_warning "Prometheus not yet responding (may take a few minutes)"
    fi
    
    # Test Grafana
    if curl -s http://localhost:3000/api/health | grep -q "ok"; then
        print_success "Grafana is responding"
    else
        print_warning "Grafana not yet responding (may take a few minutes)"
    fi
}

# Display access information
display_access_info() {
    echo ""
    echo "🎉 Deployment Complete!"
    echo "======================"
    echo ""
    echo "📊 Access URLs:"
    echo "  Grafana Dashboard: http://localhost:3000"
    echo "  Prometheus:        http://localhost:9090"
    echo "  Kepler Metrics:    http://localhost:9102/metrics"
    echo ""
    echo "🔐 Grafana Login:"
    echo "  Username: admin"
    echo "  Password: admin"
    echo ""
    echo "📋 Deployment Info:"
    echo "  Release: $RELEASE_NAME"
    echo "  Namespace: $NAMESPACE"
    echo ""
    echo "📋 Next Steps:"
    echo "  1. Open Grafana: http://localhost:3000"
    echo "  2. Add Prometheus data source: http://${RELEASE_NAME}-prometheus-server:80"
    echo "  3. Import dashboards from the JSON files in this directory"
    echo ""
    echo "🔧 Useful Commands:"
    echo "  kubectl get pods -n $NAMESPACE"
    echo "  kubectl logs -n $NAMESPACE -l app.kubernetes.io/name=kepler"
    echo ""
    echo "📚 For more information, see README.md"
    echo ""
}

# Cleanup function
cleanup() {
    print_status "Cleaning up from namespace: $NAMESPACE..."
    
    # Kill port forwarding
    pkill -f "kubectl port-forward" || true
    
    # Uninstall chart
    helm uninstall "$RELEASE_NAME" -n "$NAMESPACE" || true
    
    # Delete resources
    kubectl delete all --all -n "$NAMESPACE" 2>/dev/null || true
    
    # Only delete namespace if it's not default
    if [ "$NAMESPACE" != "default" ]; then
        print_status "Deleting namespace: $NAMESPACE"
        kubectl delete namespace "$NAMESPACE" || true
    else
        print_warning "Skipping namespace deletion (using default namespace)"
    fi
    
    print_success "Cleanup complete"
}

# Main execution
main() {
    case "$COMMAND" in
        "deploy")
            check_prerequisites
            display_config
            get_cluster_info
            deploy_chart
            wait_for_pods
            setup_port_forwarding
            test_deployment
            display_access_info
            ;;
        "cleanup")
            display_config
            cleanup
            ;;
        "test")
            test_deployment
            ;;
        "status")
            kubectl get pods -n "$NAMESPACE"
            ;;
        *)
            print_error "Unknown command: $COMMAND"
            usage
            ;;
    esac
}

# Run main function
main 