#!/bin/bash

# Energy Metrics Monitoring Setup Script
# This script deploys Kepler, Prometheus, and Grafana for energy monitoring

set -e

echo "🚀 Energy Metrics Monitoring Setup"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
    helm install energy-metrics . --namespace energy-metrics --create-namespace
    
    print_success "Chart deployed successfully"
}

# Wait for pods to be ready
wait_for_pods() {
    print_status "Waiting for all pods to be ready..."
    
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=kepler -n energy-metrics --timeout=300s
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus -n energy-metrics --timeout=300s
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n energy-metrics --timeout=300s
    
    print_success "All pods are ready"
}

# Setup port forwarding
setup_port_forwarding() {
    print_status "Setting up port forwarding..."
    
    # Kill existing port forwards
    pkill -f "kubectl port-forward" || true
    
    # Start new port forwards
    kubectl port-forward -n energy-metrics svc/energy-metrics-grafana 3000:80 &
    kubectl port-forward -n energy-metrics svc/energy-metrics-prometheus-server 9090:80 &
    kubectl port-forward -n energy-metrics svc/energy-metrics-kepler 9102:9102 &
    
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
    echo "📋 Next Steps:"
    echo "  1. Open Grafana: http://localhost:3000"
    echo "  2. Add Prometheus data source: http://energy-metrics-prometheus-server:80"
    echo "  3. Import dashboards from the JSON files in this directory"
    echo ""
    echo "📚 For more information, see README.md"
    echo ""
}

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    
    # Kill port forwarding
    pkill -f "kubectl port-forward" || true
    
    # Uninstall chart
    helm uninstall energy-metrics -n energy-metrics || true
    
    # Delete namespace
    kubectl delete namespace energy-metrics || true
    
    print_success "Cleanup complete"
}

# Main execution
main() {
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            get_cluster_info
            deploy_chart
            wait_for_pods
            setup_port_forwarding
            test_deployment
            display_access_info
            ;;
        "cleanup")
            cleanup
            ;;
        "test")
            test_deployment
            ;;
        "status")
            kubectl get pods -n energy-metrics
            ;;
        *)
            echo "Usage: $0 {deploy|cleanup|test|status}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Deploy the energy metrics stack (default)"
            echo "  cleanup  - Remove the deployment"
            echo "  test     - Test the deployment"
            echo "  status   - Show pod status"
            exit 1
            ;;
    esac
}

# Run main function
main "$@" 