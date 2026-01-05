#!/bin/bash
set -e

# Cleanup Energy-Aware Operator
# Usage: ./scripts/cleanup.sh [OPTIONS]

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
DELETE_CRD="${DELETE_CRD:-false}"
DELETE_NAMESPACE="${DELETE_NAMESPACE:-false}"
REINSTALL="${REINSTALL:-false}"

usage() {
    cat << EOF
Cleanup Energy-Aware Kubernetes Operator

Usage: $0 [OPTIONS]

Options:
    -h, --help             Show this help message
    -n, --namespace NS     Kubernetes namespace (default: default)
    -r, --release NAME     Helm release name (default: energy-operator)
    --delete-crd           Delete CRD (default: keep CRD)
    --delete-namespace     Delete namespace (default: keep namespace)
    --reinstall            Reinstall after cleanup

Examples:
    $0                              # Cleanup from default namespace
    $0 -n operators                 # Cleanup from operators namespace
    $0 --delete-crd --delete-namespace # Full cleanup including CRD and namespace
    $0 --reinstall                  # Cleanup and reinstall

EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        -n|--namespace) NAMESPACE="$2"; shift 2 ;;
        -r|--release) RELEASE_NAME="$2"; shift 2 ;;
        --delete-crd) DELETE_CRD=true; shift ;;
        --delete-namespace) DELETE_NAMESPACE=true; shift ;;
        --reinstall) REINSTALL=true; shift ;;
        *) print_error "Unknown option: $1"; usage ;;
    esac
done

echo -e "${YELLOW}╔════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║  Cleanup Energy-Aware Operator         ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════╝${NC}"
echo ""

print_info "Configuration:"
echo "  Release:           $RELEASE_NAME"
echo "  Namespace:         $NAMESPACE"
echo "  Delete CRD:        $DELETE_CRD"
echo "  Delete Namespace:  $DELETE_NAMESPACE"
echo "  Reinstall:         $REINSTALL"
echo ""

# Check prerequisites
command -v kubectl &> /dev/null || { print_error "kubectl not found"; exit 1; }
command -v helm &> /dev/null || { print_error "helm not found"; exit 1; }

# Delete custom resources first
print_info "Deleting EnergyAwareOrchestration resources..."
kubectl delete eao --all -n "$NAMESPACE" --ignore-not-found=true --timeout=60s || true

# Give time for finalizers to complete
sleep 2

# Uninstall Helm release
print_info "Uninstalling Helm release..."
if helm status "$RELEASE_NAME" -n "$NAMESPACE" &> /dev/null; then
    helm uninstall "$RELEASE_NAME" --namespace "$NAMESPACE" --wait --timeout 2m || {
        print_warn "Helm uninstall failed, forcing cleanup..."
        kubectl delete deployment -l app.kubernetes.io/name=energy-aware-operator -n "$NAMESPACE" --ignore-not-found=true
        kubectl delete service -l app.kubernetes.io/name=energy-aware-operator -n "$NAMESPACE" --ignore-not-found=true
        kubectl delete configmap -l app.kubernetes.io/name=energy-aware-operator -n "$NAMESPACE" --ignore-not-found=true
        kubectl delete serviceaccount -l app.kubernetes.io/name=energy-aware-operator -n "$NAMESPACE" --ignore-not-found=true
        kubectl delete clusterrole -l app.kubernetes.io/name=energy-aware-operator --ignore-not-found=true
        kubectl delete clusterrolebinding -l app.kubernetes.io/name=energy-aware-operator --ignore-not-found=true
    }
    print_info "Helm release uninstalled ✓"
else
    print_warn "Helm release not found, skipping"
fi

# Delete CRD if requested
if [ "$DELETE_CRD" = true ]; then
    print_info "Deleting CRD..."
    kubectl delete crd energyawareorchestrations.energyaware.hiro.io --ignore-not-found=true --timeout=30s || {
        print_warn "CRD deletion failed or CRD not found"
    }
    print_info "CRD deleted ✓"
else
    print_warn "Keeping CRD (use --delete-crd to remove)"
fi

# Delete namespace if requested and not default
if [ "$DELETE_NAMESPACE" = true ]; then
    if [ "$NAMESPACE" = "default" ] || [ "$NAMESPACE" = "kube-system" ] || [ "$NAMESPACE" = "kube-public" ]; then
        print_warn "Skipping system namespace deletion: $NAMESPACE"
    else
        print_info "Deleting namespace: $NAMESPACE"
        kubectl delete namespace "$NAMESPACE" --ignore-not-found=true --timeout=60s || {
            print_warn "Namespace deletion failed or namespace not found"
        }
        print_info "Namespace deleted ✓"
    fi
else
    print_warn "Keeping namespace (use --delete-namespace to remove)"
fi

print_info "Cleanup complete! ✅"
echo ""

# Reinstall if requested
if [ "$REINSTALL" = true ]; then
    print_info "Reinstalling operator..."
    echo ""
    "$SCRIPT_DIR/deploy.sh" -n "$NAMESPACE" -r "$RELEASE_NAME"
fi
