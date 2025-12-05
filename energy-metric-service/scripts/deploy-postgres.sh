#!/bin/bash
set -e

# Simple PostgreSQL Deployment Script
# For your custom PostgreSQL Helm chart

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
RELEASE_NAME="${RELEASE_NAME:-postgres}"
NAMESPACE="${NAMESPACE:-default}"
VALUES_FILE=""

usage() {
    cat << EOF
PostgreSQL Deployment Script

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help
    -n, --namespace NS      Kubernetes namespace (default: default)
    -r, --release NAME      Helm release name (default: postgres)
    -f, --values FILE       Custom values file
    --db NAME               Database name
    --user USER             Database username
    --password PASS         Database password
    --storage SIZE          Storage size (e.g., 20Gi)
    --uninstall             Uninstall PostgreSQL

Environment Variables:
    RELEASE_NAME            Helm release name
    NAMESPACE               Kubernetes namespace
    POSTGRES_DB             Database name
    POSTGRES_USER           Username
    POSTGRES_PASSWORD       Password
    STORAGE_SIZE            Storage size

Examples:
    # Install with defaults
    $0

    # Install with custom settings
    $0 --db mydb --user myuser --password mypass --storage 20Gi

    # Install with values file
    $0 -f my-values.yaml

    # Install in specific namespace
    $0 --namespace production --release postgres-prod

    # Uninstall
    $0 --uninstall

EOF
    exit 0
}

# Parse arguments
UNINSTALL=false
DB_NAME="${POSTGRES_DB:-}"
DB_USER="${POSTGRES_USER:-}"
DB_PASSWORD="${POSTGRES_PASSWORD:-}"
STORAGE_SIZE="${STORAGE_SIZE:-}"

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -r|--release)
            RELEASE_NAME="$2"
            shift 2
            ;;
        -f|--values)
            VALUES_FILE="$2"
            shift 2
            ;;
        --db)
            DB_NAME="$2"
            shift 2
            ;;
        --user)
            DB_USER="$2"
            shift 2
            ;;
        --password)
            DB_PASSWORD="$2"
            shift 2
            ;;
        --storage)
            STORAGE_SIZE="$2"
            shift 2
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Get script directory and project paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CHARTS_DIR="$PROJECT_ROOT/charts"

# Uninstall
if [ "$UNINSTALL" = true ]; then
    print_info "Uninstalling PostgreSQL release: $RELEASE_NAME"
    helm uninstall "$RELEASE_NAME" -n "$NAMESPACE" || true

    read -p "Delete PVC? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete pvc -n "$NAMESPACE" -l app=eao-postgres || true
        print_info "PVC deleted"
    fi
    exit 0
fi

# Display configuration
print_info "PostgreSQL Deployment Configuration:"
echo "  Release: $RELEASE_NAME"
echo "  Namespace: $NAMESPACE"
[ -n "$DB_NAME" ] && echo "  Database: $DB_NAME"
[ -n "$DB_USER" ] && echo "  Username: $DB_USER"
[ -n "$STORAGE_SIZE" ] && echo "  Storage: $STORAGE_SIZE"
[ -n "$VALUES_FILE" ] && echo "  Values File: $VALUES_FILE"

# Create namespace if needed
if [ "$NAMESPACE" != "default" ]; then
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        print_info "Creating namespace: $NAMESPACE"
        kubectl create namespace "$NAMESPACE"
    fi
fi

# Build helm command
HELM_ARGS=()

if [ -n "$VALUES_FILE" ]; then
    if [ ! -f "$VALUES_FILE" ]; then
        print_error "Values file not found: $VALUES_FILE"
        exit 1
    fi
    HELM_ARGS+=("-f" "$VALUES_FILE")
fi

# Add inline overrides
[ -n "$DB_NAME" ] && HELM_ARGS+=("--set" "postgres.credentials.database=$DB_NAME")
[ -n "$DB_USER" ] && HELM_ARGS+=("--set" "postgres.credentials.username=$DB_USER")
[ -n "$DB_PASSWORD" ] && HELM_ARGS+=("--set" "postgres.credentials.password=$DB_PASSWORD")
[ -n "$STORAGE_SIZE" ] && HELM_ARGS+=("--set" "postgres.persistence.size=$STORAGE_SIZE")

# Install or upgrade
print_info "Deploying PostgreSQL..."
if helm list -n "$NAMESPACE" | grep -q "^$RELEASE_NAME"; then
    print_info "Upgrading existing release..."
    helm upgrade "$RELEASE_NAME" "$CHARTS_DIR" \
        --namespace "$NAMESPACE" \
        "${HELM_ARGS[@]}" \
        --wait
else
    print_info "Installing new release..."
    helm install "$RELEASE_NAME" "$CHARTS_DIR" \
        --namespace "$NAMESPACE" \
        "${HELM_ARGS[@]}" \
        --wait
fi

# Wait for pod
print_info "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod \
    -l app=eao-postgres \
    -n "$NAMESPACE" \
    --timeout=300s || true

# Get connection details
POD_NAME=$(kubectl get pod -n "$NAMESPACE" -l app=eao-postgres -o jsonpath='{.items[0].metadata.name}')
SVC_NAME=$(kubectl get svc -n "$NAMESPACE" -l app=eao-postgres -o jsonpath='{.items[0].metadata.name}')

# Get values from chart
DB_NAME_ACTUAL=$(helm get values "$RELEASE_NAME" -n "$NAMESPACE" -o json | grep -o '"database":"[^"]*"' | cut -d'"' -f4 || echo "orchestration_db")
DB_USER_ACTUAL=$(helm get values "$RELEASE_NAME" -n "$NAMESPACE" -o json | grep -o '"username":"[^"]*"' | cut -d'"' -f4 || echo "postgres")
DB_PASSWORD_ACTUAL=$(helm get values "$RELEASE_NAME" -n "$NAMESPACE" -o json | grep -o '"password":"[^"]*"' | cut -d'"' -f4 || echo "postgres")

print_info "PostgreSQL deployed successfully!"
echo ""
echo "============================================"
echo "  Connection Details"
echo "============================================"
echo "  Host: $SVC_NAME.$NAMESPACE.svc.cluster.local"
echo "  Port: 5432"
echo "  Database: ${DB_NAME_ACTUAL}"
echo "  Username: ${DB_USER_ACTUAL}"
echo "  Password: ${DB_PASSWORD_ACTUAL}"
echo ""
echo "  Connection String:"
echo "  postgresql://${DB_USER_ACTUAL}:${DB_PASSWORD_ACTUAL}@${SVC_NAME}.${NAMESPACE}.svc.cluster.local:5432/${DB_NAME_ACTUAL}"
echo ""
echo "============================================"
echo "  Quick Access"
echo "============================================"
echo "  # Connect from pod:"
echo "  kubectl run psql-client --rm -it --restart=Never \\"
echo "    --namespace $NAMESPACE \\"
echo "    --image=postgres:14 \\"
echo "    --env=\"PGPASSWORD=${DB_PASSWORD_ACTUAL}\" \\"
echo "    -- psql -h $SVC_NAME -U ${DB_USER_ACTUAL} -d ${DB_NAME_ACTUAL}"
echo ""
echo "  # Port-forward:"
echo "  kubectl port-forward -n $NAMESPACE svc/$SVC_NAME 5432:5432"
echo ""
echo "  # View logs:"
echo "  kubectl logs -n $NAMESPACE $POD_NAME -f"
echo ""
echo "  # Get ConfigMap with DATABASE_URL:"
echo "  kubectl get configmap orchestration-api-config -n $NAMESPACE -o jsonpath='{.data.databaseURL}'"
echo ""

