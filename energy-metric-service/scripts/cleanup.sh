#!/bin/bash
set -e

# Cleanup Energy Metric Service (PostgreSQL + FastAPI app)

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
print_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

NAMESPACE="${NAMESPACE:-default}"
APP_RELEASE="${APP_RELEASE:-energy-metric}"
DB_RELEASE="${DB_RELEASE:-postgres}"
DELETE_PVC="${DELETE_PVC:-false}"

usage() {
    cat << EOF
Cleanup Energy Metric Service (PostgreSQL + FastAPI app)

Usage: $0 [OPTIONS]

Options:
    -h, --help          Show this help
    -n, --namespace NS  Kubernetes namespace (default: default)
    --delete-pvc        Also delete PostgreSQL PVCs (default: keep)

Examples:
    $0                  # Cleanup app + postgres, keep PVCs
    $0 --delete-pvc     # Full cleanup including PVCs

EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage ;;
        -n|--namespace) NAMESPACE="$2"; shift 2 ;;
        --delete-pvc) DELETE_PVC=true; shift ;;
        *) print_error "Unknown option: $1"; usage ;;
    esac
done

echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║  Energy Metric Service — Cleanup                       ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
print_info "Namespace:   $NAMESPACE"
print_info "App release: $APP_RELEASE"
print_info "DB release:  $DB_RELEASE"
print_info "Delete PVCs: $DELETE_PVC"
echo ""

# Uninstall FastAPI app
print_info "Uninstalling FastAPI app ($APP_RELEASE)..."
if helm status "$APP_RELEASE" -n "$NAMESPACE" &>/dev/null; then
    helm uninstall "$APP_RELEASE" -n "$NAMESPACE" || true
    print_info "App uninstalled ✓"
else
    print_warn "Release '$APP_RELEASE' not found, skipping"
fi
kubectl delete all       -l app=energy-metric-service -n "$NAMESPACE" --ignore-not-found=true 2>/dev/null || true
kubectl delete configmap -l app=energy-metric-service -n "$NAMESPACE" --ignore-not-found=true 2>/dev/null || true
kubectl delete secret    -l app=energy-metric-service -n "$NAMESPACE" --ignore-not-found=true 2>/dev/null || true

# Uninstall PostgreSQL
print_info "Uninstalling PostgreSQL ($DB_RELEASE)..."
if helm status "$DB_RELEASE" -n "$NAMESPACE" &>/dev/null; then
    helm uninstall "$DB_RELEASE" -n "$NAMESPACE" || true
    print_info "PostgreSQL uninstalled ✓"
else
    print_warn "Release '$DB_RELEASE' not found, skipping"
fi

# Delete PVCs (opt-in)
if [ "$DELETE_PVC" = true ]; then
    print_info "Deleting PostgreSQL PVCs..."
    kubectl delete pvc -n "$NAMESPACE" -l app=eao-postgres                    --ignore-not-found=true 2>/dev/null || true
    kubectl delete pvc -n "$NAMESPACE" -l "app.kubernetes.io/name=postgresql" --ignore-not-found=true 2>/dev/null || true
    print_info "PVCs deleted ✓"
else
    print_warn "Keeping PVCs (use --delete-pvc to remove)"
fi

echo ""
print_info "Cleanup complete! ✅"
