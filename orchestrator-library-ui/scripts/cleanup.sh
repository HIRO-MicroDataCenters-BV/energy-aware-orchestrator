#!/bin/bash

# Orchestrator Library UI Cleanup Script

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Default configuration
RELEASE_NAME="${RELEASE_NAME:-orchestrator-ui}"
NAMESPACE="${NAMESPACE:-default}"
REINSTALL="${REINSTALL:-false}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace) NAMESPACE="$2"; shift 2 ;;
        --reinstall) REINSTALL=true; shift ;;
        -h|--help)
            cat << EOF
🧹 Orchestrator Library UI Cleanup Script

Usage: $0 [OPTIONS]

Options:
    -n, --namespace NS  Kubernetes namespace (default: default)
    --reinstall         Reinstall after cleanup
    -h, --help          Show this help

Examples:
    $0                       # Cleanup from default namespace
    $0 -n ui                 # Cleanup from ui namespace
    $0 --reinstall           # Cleanup and reinstall

EOF
            exit 0
            ;;
        *) print_error "Unknown option: $1"; exit 1 ;;
    esac
done

echo "🧹 Orchestrator Library UI Cleanup"
echo "===================================="
echo "  Release: $RELEASE_NAME"
echo "  Namespace: $NAMESPACE"
echo ""

# 1. Kill port forwarding
print_info "Stopping port forwarding..."
pkill -f "kubectl port-forward.*orchestrator" || true

# 2. Uninstall Helm release
print_info "Removing Helm release..."
helm uninstall "$RELEASE_NAME" --namespace "$NAMESPACE" 2>/dev/null || true

# 3. Delete all UI resources
print_info "Deleting UI resources..."
kubectl delete all -l app=aces-orchestrator-library-ui -n "$NAMESPACE" 2>/dev/null || true
kubectl delete configmap -l app=aces-orchestrator-library-ui -n "$NAMESPACE" 2>/dev/null || true
kubectl delete secret -l app=aces-orchestrator-library-ui -n "$NAMESPACE" 2>/dev/null || true
kubectl delete ingress -l app=aces-orchestrator-library-ui -n "$NAMESPACE" 2>/dev/null || true

# 4. Delete k8s-proxy resources
print_info "Deleting k8s-proxy resources..."
kubectl delete all -l app=aces-orchestrator-k8s-proxy -n "$NAMESPACE" 2>/dev/null || true
kubectl delete configmap -l app=aces-orchestrator-k8s-proxy -n "$NAMESPACE" 2>/dev/null || true
kubectl delete ingress -l app=aces-orchestrator-k8s-proxy -n "$NAMESPACE" 2>/dev/null || true

# 5. Delete namespace (if not default)
if [ "$NAMESPACE" != "default" ]; then
    print_info "Deleting namespace..."
    kubectl delete namespace "$NAMESPACE" 2>/dev/null || true
    
    # Wait for namespace to be fully deleted
    print_info "Waiting for namespace deletion..."
    while kubectl get namespace "$NAMESPACE" 2>/dev/null; do
      echo "   Waiting for namespace to be deleted..."
      sleep 2
    done
else
    print_warn "Skipping namespace deletion (using default namespace)"
fi

print_info "Cleanup complete!"

# Reinstall if requested
if [ "$REINSTALL" = true ]; then
    echo ""
    print_info "Reinstalling application..."
    "$SCRIPT_DIR/deploy.sh" -n "$NAMESPACE"
fi


