#!/bin/bash
set -e

# Unified deployment script for all projects in the monorepo
# Projects: energy-aware-operator, energy-metric-service, energy-monitoring-helm-stack, orchestrator-library-ui
#
# Port-forwarding is NOT executed automatically. Commands are printed at the end
# for you to run manually in separate terminals.

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_info()    { echo -e "${GREEN}[INFO]${NC}  $1"; }
print_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
print_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
print_header()  { echo -e "\n${BOLD}${BLUE}$1${NC}"; }
print_divider() { echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
NAMESPACE="${NAMESPACE:-default}"

# Energy-Aware Operator image config (override via env vars)
OPERATOR_IMAGE_REPO="${OPERATOR_IMAGE_REPO:-energy-aware-operator}"
OPERATOR_IMAGE_TAG="${OPERATOR_IMAGE_TAG:-latest}"

# Sample testing workload manifests
SAMPLE_K8S_MANIFEST="$ROOT_DIR/workload/workload_k8s_critical_testing.yaml"
SAMPLE_EAO_CR="$ROOT_DIR/workload/workload_cr_eao_critical_testing.yaml"

# Deployment status tracking
DEPLOY_OPERATOR_BUILD_STATUS="PENDING"
DEPLOY_OPERATOR_STATUS="PENDING"
DEPLOY_METRIC_STATUS="PENDING"
DEPLOY_MONITORING_STATUS="PENDING"
DEPLOY_UI_STATUS="PENDING"
DEPLOY_SAMPLE_WORKLOAD_STATUS="PENDING"

echo ""
print_divider
echo -e "${BOLD}${CYAN}   Energy-Aware Orchestrator — Full Stack Deployment${NC}"
print_divider
echo ""
print_info "Namespace:          $NAMESPACE"
print_info "Operator image:     $OPERATOR_IMAGE_REPO:$OPERATOR_IMAGE_TAG"
print_info "Port-forwarding:    suggested only (not executed automatically)"
echo ""

# ─── PREREQUISITES CHECK ─────────────────────────────────────────────────────
print_header "▶  Prerequisites Check"
print_divider

PREREQ_FAILED=false

_check() {
    local label="$1"
    local cmd="$2"
    if command -v "$cmd" &>/dev/null; then
        printf "  ${GREEN}✔${NC}  %-20s %s\n" "$label" "$(command -v "$cmd")"
    else
        printf "  ${RED}✘${NC}  %-20s NOT FOUND\n" "$label"
        PREREQ_FAILED=true
    fi
}

_check_optional() {
    local label="$1"
    local cmd="$2"
    local note="$3"
    if command -v "$cmd" &>/dev/null; then
        printf "  ${GREEN}✔${NC}  %-20s %s\n" "$label" "$(command -v "$cmd")"
    else
        printf "  ${YELLOW}~${NC}  %-20s not found — %s\n" "$label" "$note"
    fi
}

echo ""
echo -e "  ${BOLD}Required tools:${NC}"
_check "kubectl"   kubectl
_check "helm"      helm
_check "docker"    docker

echo ""
echo -e "  ${BOLD}Optional tools:${NC}"
_check_optional "uv"       uv       "CRD generation will be skipped in operator build"
_check_optional "kind"     kind     "only needed if using a kind cluster"
_check_optional "minikube" minikube "only needed if using a minikube cluster"

# Abort early if any required tool is missing
if [ "$PREREQ_FAILED" = true ]; then
    echo ""
    print_error "One or more required tools are missing. Install them and re-run."
    exit 1
fi

# Cluster connectivity
echo ""
echo -e "  ${BOLD}Cluster:${NC}"
if ! kubectl config current-context &>/dev/null; then
    printf "  ${RED}✘${NC}  %-20s no current context set\n" "kubeconfig"
    print_error "No kubectl context found. Run: kubectl config use-context <name>"
    exit 1
fi

KUBE_CONTEXT=$(kubectl config current-context)
printf "  ${GREEN}✔${NC}  %-20s %s\n" "context" "$KUBE_CONTEXT"

if ! kubectl cluster-info &>/dev/null 2>&1; then
    printf "  ${RED}✘${NC}  %-20s unreachable\n" "cluster"
    print_error "Cannot reach the Kubernetes cluster. Check your kubeconfig / VPN."
    exit 1
fi
printf "  ${GREEN}✔${NC}  %-20s reachable\n" "cluster"

# Cluster-type specific checks
if echo "$KUBE_CONTEXT" | grep -q "^kind-"; then
    CLUSTER_TYPE="kind"
    if ! command -v kind &>/dev/null; then
        printf "  ${RED}✘${NC}  %-20s kind context detected but 'kind' CLI missing\n" "kind CLI"
        print_error "Install kind: https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
        exit 1
    fi
    printf "  ${GREEN}✔${NC}  %-20s %s\n" "kind CLI" "$(command -v kind)"
elif command -v minikube &>/dev/null && minikube status &>/dev/null 2>&1; then
    CLUSTER_TYPE="minikube"
    printf "  ${GREEN}✔${NC}  %-20s running\n" "minikube"
else
    CLUSTER_TYPE="other"
fi

echo ""
printf "  ${BOLD}Cluster type:${NC} %s\n" "$CLUSTER_TYPE"
echo ""
print_info "All prerequisites satisfied ✓"
print_divider

# ─── 1. Energy-Aware Operator ────────────────────────────────────────────────
print_header "▶  [1/5] Energy-Aware Operator"
print_divider

# 1a. Build the operator Docker image (generates CRD + builds image)
print_info "[1a] Building operator image ($OPERATOR_IMAGE_REPO:$OPERATOR_IMAGE_TAG)..."
if IMAGE_REPOSITORY="$OPERATOR_IMAGE_REPO" IMAGE_TAG="$OPERATOR_IMAGE_TAG" \
       bash "$ROOT_DIR/energy-aware-operator/scripts/build.sh"; then
    DEPLOY_OPERATOR_BUILD_STATUS="OK"
    print_info "Operator image built ✓"
else
    DEPLOY_OPERATOR_BUILD_STATUS="FAILED"
    print_error "Operator image build failed — skipping operator deploy"
fi

# 1b. Deploy the operator via Helm (applies CRD + helm upgrade --install)
if [ "$DEPLOY_OPERATOR_BUILD_STATUS" = "OK" ]; then
    print_info "[1b] Deploying operator via Helm..."
    if NAMESPACE="$NAMESPACE" \
       IMAGE_REPOSITORY="$OPERATOR_IMAGE_REPO" \
       IMAGE_TAG="$OPERATOR_IMAGE_TAG" \
       SKIP_PORT_FORWARD=true \
           bash "$ROOT_DIR/energy-aware-operator/scripts/deploy.sh"; then
        DEPLOY_OPERATOR_STATUS="OK"
        print_info "Energy-Aware Operator deployed successfully ✓"
    else
        DEPLOY_OPERATOR_STATUS="FAILED"
        print_error "Energy-Aware Operator deployment failed"
    fi
else
    DEPLOY_OPERATOR_STATUS="FAILED"
fi

# ─── 2. Energy Metric Service (PostgreSQL + FastAPI) ─────────────────────────
print_header "▶  [2/5] Energy Metric Service (PostgreSQL + API)"
print_divider
if NAMESPACE="$NAMESPACE" SKIP_PORT_FORWARD=true \
       bash "$ROOT_DIR/energy-metric-service/scripts/deploy-all.sh"; then
    DEPLOY_METRIC_STATUS="OK"
    print_info "Energy Metric Service deployed successfully ✓"
else
    DEPLOY_METRIC_STATUS="FAILED"
    print_error "Energy Metric Service deployment failed"
fi

# ─── 3. Energy Monitoring Helm Stack (Kepler / Prometheus / Grafana) ─────────
print_header "▶  [3/5] Energy Monitoring Helm Stack"
print_divider
if NAMESPACE="$NAMESPACE" SKIP_PORT_FORWARD=true \
       bash "$ROOT_DIR/energy-monitoring-helm-stack/scripts/deploy.sh"; then
    DEPLOY_MONITORING_STATUS="OK"
    print_info "Energy Monitoring Stack deployed successfully ✓"
else
    DEPLOY_MONITORING_STATUS="FAILED"
    print_error "Energy Monitoring Stack deployment failed"
fi

# ─── 4. Orchestrator Library UI ──────────────────────────────────────────────
print_header "▶  [4/5] Orchestrator Library UI"
print_divider
if NAMESPACE="$NAMESPACE" SKIP_PORT_FORWARD=true \
       bash "$ROOT_DIR/orchestrator-library-ui/scripts/deploy.sh"; then
    DEPLOY_UI_STATUS="OK"
    print_info "Orchestrator Library UI deployed successfully ✓"
else
    DEPLOY_UI_STATUS="FAILED"
    print_error "Orchestrator Library UI deployment failed"
fi

# ─── 5. Sample Testing Workload ──────────────────────────────────────────────
print_header "▶  [5/5] Sample Testing Workload (Critical EAO)"
print_divider

if [ "$DEPLOY_OPERATOR_STATUS" = "OK" ]; then
    # Apply the backing nginx Deployment + Service
    print_info "Applying backing workload: $(basename "$SAMPLE_K8S_MANIFEST")..."
    if kubectl apply -f "$SAMPLE_K8S_MANIFEST" -n "$NAMESPACE"; then
        print_info "Backing workload applied ✓"
    else
        print_warn "Failed to apply backing workload — continuing with EAO CR"
    fi

    # Apply the EAO CR
    print_info "Applying EAO CR: $(basename "$SAMPLE_EAO_CR")..."
    if kubectl apply -f "$SAMPLE_EAO_CR" -n "$NAMESPACE"; then
        DEPLOY_SAMPLE_WORKLOAD_STATUS="OK"
        print_info "EAO CR applied ✓"

        print_info "Waiting 5s for operator to reconcile..."
        sleep 5
        echo ""
        kubectl get eao -n "$NAMESPACE" 2>/dev/null || true
    else
        DEPLOY_SAMPLE_WORKLOAD_STATUS="FAILED"
        print_error "Failed to apply EAO CR"
    fi
else
    DEPLOY_SAMPLE_WORKLOAD_STATUS="SKIPPED"
    print_warn "Operator not running — skipping sample workload"
fi
print_divider

# ─── DEPLOYMENT SUMMARY ──────────────────────────────────────────────────────
echo ""
print_divider
echo -e "${BOLD}${CYAN}   DEPLOYMENT SUMMARY${NC}"
print_divider

_status_icon() {
    case "$1" in
        OK)      echo -e "${GREEN}✔  OK${NC}" ;;
        SKIPPED) echo -e "${YELLOW}~  SKIPPED${NC}" ;;
        *)       echo -e "${RED}✘  FAILED${NC}" ;;
    esac
}

echo ""
printf "  %-42s %s\n" "energy-aware-operator (build)"    "$(_status_icon "$DEPLOY_OPERATOR_BUILD_STATUS")"
printf "  %-42s %s\n" "energy-aware-operator (deploy)"   "$(_status_icon "$DEPLOY_OPERATOR_STATUS")"
printf "  %-42s %s\n" "energy-metric-service (pg + api)" "$(_status_icon "$DEPLOY_METRIC_STATUS")"
printf "  %-42s %s\n" "energy-monitoring-helm-stack"     "$(_status_icon "$DEPLOY_MONITORING_STATUS")"
printf "  %-42s %s\n" "orchestrator-library-ui"          "$(_status_icon "$DEPLOY_UI_STATUS")"
printf "  %-42s %s\n" "sample workload (critical-testing)" "$(_status_icon "$DEPLOY_SAMPLE_WORKLOAD_STATUS")"
echo ""

# ─── PORT-FORWARDING INSTRUCTIONS ────────────────────────────────────────────
print_divider
echo -e "${BOLD}${CYAN}   PORT-FORWARDING  (run these manually in separate terminals)${NC}"
print_divider
echo ""
echo -e "${YELLOW}  # Step 1 — Kill only this repo's port-forwards:${NC}"
echo    "  pkill -f 'svc/energy-metric-service'           || true"
echo    "  pkill -f 'svc/eao-postgres'                    || true"
echo    "  pkill -f 'svc/energy-metrics-grafana'          || true"
echo    "  pkill -f 'svc/energy-metrics-prometheus-server'|| true"
echo    "  pkill -f 'svc/energy-metrics-kepler'           || true"
echo    "  pkill -f 'svc/orchestrator-library-ui'    || true"
echo    "  pkill -f 'svc/orchestrator-k8s-proxy'     || true"
echo ""
echo -e "${YELLOW}  # Step 2 — Run this block to start all port-forwards in the background at once:${NC}"
echo ""
echo    "  kubectl port-forward -n ${NAMESPACE} svc/energy-metric-service 8000:8000 &"
echo    "  kubectl port-forward -n ${NAMESPACE} svc/eao-postgres 5432:5432 &"
echo    "  kubectl port-forward -n ${NAMESPACE} svc/energy-metrics-grafana 3000:80 &"
echo    "  kubectl port-forward -n ${NAMESPACE} svc/energy-metrics-prometheus-server 9090:80 &"
echo    "  kubectl port-forward -n ${NAMESPACE} svc/energy-metrics-kepler 9102:9102 &"
echo    "  kubectl port-forward -n ${NAMESPACE} svc/orchestrator-library-ui 4200:80 &"
echo    "  kubectl port-forward -n ${NAMESPACE} svc/orchestrator-k8s-proxy 3001:3000 &"
echo ""
echo -e "${YELLOW}  # Note: K8s Proxy uses local port 3001 to avoid conflict with Grafana on 3000.${NC}"
echo ""

# ─── ACCESS URLS ─────────────────────────────────────────────────────────────
print_divider
echo -e "${BOLD}${CYAN}   ACCESS URLS  (available after port-forwarding)${NC}"
print_divider
echo ""
printf "  %-36s %s\n" "Energy Metric Service API"   "http://localhost:8000/docs"
printf "  %-36s %s\n" "Energy Metric Service Docs"  "http://localhost:8000/redoc"
printf "  %-36s %s\n" "PostgreSQL"                  "localhost:5432  (user: postgres / db: orchestration_db)"
printf "  %-36s %s\n" "Grafana Dashboard"           "http://localhost:3000  (admin / admin)"
printf "  %-36s %s\n" "Prometheus"                  "http://localhost:9090"
printf "  %-36s %s\n" "Kepler Metrics"              "http://localhost:9102/metrics"
printf "  %-36s %s\n" "Orchestrator Library UI"     "http://localhost:4200"
printf "  %-36s %s\n" "K8s Proxy"                   "http://localhost:3001"
echo ""
print_divider
echo ""
