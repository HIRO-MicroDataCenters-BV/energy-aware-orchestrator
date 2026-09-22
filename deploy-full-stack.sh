#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────────────────────────
#  deploy-full-stack.sh — Energy-Aware Orchestrator full-stack manager
#
#  Commands:
#    deploy   Build and deploy all 5 components (default)
#    cleanup  Tear down all components in LIFO order
#
#  Usage:
#    ./deploy-full-stack.sh [deploy|cleanup] [OPTIONS]
#    ./deploy-full-stack.sh cleanup --delete-crd --delete-pvc
#    NAMESPACE=staging ./deploy-full-stack.sh deploy
# ─────────────────────────────────────────────────────────────────────────────

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Print helpers ─────────────────────────────────────────────────────────────
info()     { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn()     { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()    { echo -e "${RED}[ERROR]${NC} $1"; }
header()   { echo -e "\n${BOLD}${BLUE}$1${NC}"; }
divider()  { echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
banner()   { divider; echo -e "${BOLD}${CYAN}   $1${NC}"; divider; }

status_icon() {
    case "$1" in
        OK)      echo -e "${GREEN}✔  OK${NC}" ;;
        SKIPPED) echo -e "${YELLOW}~  SKIPPED${NC}" ;;
        *)       echo -e "${RED}✘  FAILED${NC}" ;;
    esac
}

# ── Globals ───────────────────────────────────────────────────────────────────
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

NAMESPACE="${NAMESPACE:-default}"
OPERATOR_IMAGE_REPO="${OPERATOR_IMAGE_REPO:-energy-aware-operator}"

# Default to a content-derived tag (git commit, plus a hash of any uncommitted
# diff) instead of "latest". A mutable "latest" tag makes `helm upgrade` a
# no-op from Kubernetes' point of view even after rebuilding the image, so
# already-running pods never pick up the new content without a manual
# `kubectl rollout restart`. A tag that changes whenever the source changes
# makes the Deployment spec genuinely different, so Kubernetes rolls pods
# on its own -- and stays a no-op (no unnecessary restart) when nothing changed.
_GIT_SHA="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo nogit)"
_GIT_DIRTY_HASH="$( { git -C "$ROOT_DIR" diff HEAD; git -C "$ROOT_DIR" status --porcelain; } 2>/dev/null | shasum -a 256 2>/dev/null | cut -c1-8 || true)"
if [ -n "$_GIT_DIRTY_HASH" ]; then
    _DEFAULT_IMAGE_TAG="${_GIT_SHA}-dirty-${_GIT_DIRTY_HASH}"
else
    _DEFAULT_IMAGE_TAG="$_GIT_SHA"
fi
OPERATOR_IMAGE_TAG="${OPERATOR_IMAGE_TAG:-$_DEFAULT_IMAGE_TAG}"

SAMPLE_K8S_MANIFESTS=(
    "$ROOT_DIR/workload/workload_k8s_critical_testing.yaml"
    "$ROOT_DIR/workload/workload_k8s_optional_testing.yaml"
)
SAMPLE_EAO_CRS=(
    "$ROOT_DIR/workload/workload_cr_eao_critical_testing.yaml"
    "$ROOT_DIR/workload/workload_cr_eao_optional_testing.yaml"
)

DELETE_CRD="${DELETE_CRD:-false}"
DELETE_PVC="${DELETE_PVC:-false}"

# GRID_API_URL: a real grid endpoint, if you have one. ENABLE_GRID_STUB
# defaults based on whether that's set (resolved after arg parsing, since
# --grid-url/--grid-stub may arrive as flags rather than env vars) - a real
# URL means the dev/test mock grid server
# (energy-metric-service/charts/app/templates/grid-stub.yaml) has nothing to
# add, so it defaults off; no URL means there's nothing to poll otherwise,
# so the stub defaults on. Either can still be set explicitly to override
# this default (e.g. both a real URL and the stub, for comparison).
GRID_API_URL="${GRID_API_URL:-}"
ENABLE_GRID_STUB="${ENABLE_GRID_STUB:-}"

# ENABLE_METRICS_SCHEDULER: scrapes Kepler power/utilization data via
# Prometheus into container_power_metrics, feeding demand resolution tiers
# 1-2 (measured/ML-predicted). On by default - the monitoring stack is
# deployed later in this same run (step 3/5), so there's a brief window of
# harmless no-op connection errors until it's up, then it self-heals.
ENABLE_METRICS_SCHEDULER="${ENABLE_METRICS_SCHEDULER:-true}"
# Override where PROMETHEUS_BASE_URL points. Empty means auto-derive from
# MONITORING_RELEASE_NAME.
PROMETHEUS_BASE_URL="${PROMETHEUS_BASE_URL:-}"
# Helm release name the monitoring stack gets installed under (step 3/5) -
# only matters if you're overriding its default.
MONITORING_RELEASE_NAME="${MONITORING_RELEASE_NAME:-energy-metrics}"

# ─────────────────────────────────────────────────────────────────────────────
#  ARGUMENT PARSING
# ─────────────────────────────────────────────────────────────────────────────
usage() {
    cat << 'EOF'
Usage: ./deploy-full-stack.sh [deploy|cleanup] [OPTIONS]

Commands:
  deploy   Build and deploy all projects (default)
  cleanup  Remove all deployments in LIFO order

Options (both commands):
  -n, --namespace NS   Kubernetes namespace  (default: default)

Options (deploy only):
  --grid-stub           Deploy the dev/test mock grid server
                         (energy-metric-service). Defaults on when no
                         --grid-url is given, off when one is.
  --no-grid-stub        Force the mock grid server off
  --grid-url URL        Point GRID_API_URL at a real grid endpoint instead
                         of the mock server (implies --no-grid-stub unless
                         --grid-stub is also passed)
  --disable-metrics-scheduler
                         Don't scrape Kepler data via Prometheus into
                         container_power_metrics (feeds demand resolution
                         tiers 1-2). On by default.
  --prometheus-url URL  Override PROMETHEUS_BASE_URL (default: auto-derived
                         from --monitoring-release)
  --monitoring-release NAME
                         Helm release name for the monitoring stack
                         (default: energy-metrics)

Options (cleanup only):
  --delete-crd         Also delete the operator CRD   (default: keep)
  --delete-pvc         Also delete PostgreSQL PVCs     (default: keep)

Environment overrides:
  NAMESPACE            Same as -n
  OPERATOR_IMAGE_REPO  Operator Docker image repo  (default: energy-aware-operator)
  OPERATOR_IMAGE_TAG   Operator Docker image tag   (default: latest)
  ENABLE_GRID_STUB     Same as --grid-stub
  GRID_API_URL         Same as --grid-url
  ENABLE_METRICS_SCHEDULER  Same as --disable-metrics-scheduler (set to false)
  PROMETHEUS_BASE_URL       Same as --prometheus-url
  MONITORING_RELEASE_NAME   Same as --monitoring-release

Examples:
  ./deploy-full-stack.sh                       # deploy, mock grid server + metrics scheduler on by default
  ./deploy-full-stack.sh deploy --no-grid-stub
  ./deploy-full-stack.sh deploy --grid-url http://real-grid.example.com/capacity
  ./deploy-full-stack.sh deploy --disable-metrics-scheduler
  ./deploy-full-stack.sh cleanup
  ./deploy-full-stack.sh cleanup --delete-crd --delete-pvc
  NAMESPACE=staging ./deploy-full-stack.sh deploy
EOF
    exit 0
}

parse_args() {
    COMMAND="${1:-deploy}"
    case "$COMMAND" in
        deploy|cleanup) shift ;;
        -h|--help)      usage ;;
        *)
            error "Unknown command: $COMMAND  (use: deploy | cleanup)"
            exit 1
            ;;
    esac

    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--namespace) NAMESPACE="$2"; shift 2 ;;
            --grid-stub)    ENABLE_GRID_STUB=true; shift ;;
            --no-grid-stub) ENABLE_GRID_STUB=false; shift ;;
            --grid-url)     GRID_API_URL="$2"; shift 2 ;;
            --disable-metrics-scheduler) ENABLE_METRICS_SCHEDULER=false; shift ;;
            --prometheus-url) PROMETHEUS_BASE_URL="$2"; shift 2 ;;
            --monitoring-release) MONITORING_RELEASE_NAME="$2"; shift 2 ;;
            --delete-crd)   DELETE_CRD=true; shift ;;
            --delete-pvc)   DELETE_PVC=true; shift ;;
            -h|--help)      usage ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Resolve ENABLE_GRID_STUB's default now that --grid-url/--grid-stub
    # have both had a chance to be set, from either flags or env vars.
    if [ -z "$ENABLE_GRID_STUB" ]; then
        if [ -n "$GRID_API_URL" ]; then
            ENABLE_GRID_STUB=false
        else
            ENABLE_GRID_STUB=true
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
#  PREREQUISITES CHECK  (deploy only)
# ─────────────────────────────────────────────────────────────────────────────
_require_tool() {
    local label="$1" cmd="$2"
    if command -v "$cmd" &>/dev/null; then
        printf "  ${GREEN}✔${NC}  %-20s %s\n" "$label" "$(command -v "$cmd")"
    else
        printf "  ${RED}✘${NC}  %-20s NOT FOUND\n" "$label"
        PREREQ_FAILED=true
    fi
}

_optional_tool() {
    local label="$1" cmd="$2" note="$3"
    if command -v "$cmd" &>/dev/null; then
        printf "  ${GREEN}✔${NC}  %-20s %s\n" "$label" "$(command -v "$cmd")"
    else
        printf "  ${YELLOW}~${NC}  %-20s not found — %s\n" "$label" "$note"
    fi
}

check_prerequisites() {
    header "▶  Prerequisites Check"
    divider

    PREREQ_FAILED=false

    echo ""
    echo -e "  ${BOLD}Required tools:${NC}"
    _require_tool "kubectl" kubectl
    _require_tool "helm"    helm
    _require_tool "docker"  docker

    echo ""
    echo -e "  ${BOLD}Optional tools:${NC}"
    _optional_tool "uv"       uv       "CRD generation skipped in operator build"
    _optional_tool "kind"     kind     "only needed for kind clusters"
    _optional_tool "minikube" minikube "only needed for minikube clusters"

    if [ "$PREREQ_FAILED" = true ]; then
        echo ""
        error "One or more required tools are missing. Install them and re-run."
        exit 1
    fi

    echo ""
    echo -e "  ${BOLD}Cluster:${NC}"

    if ! kubectl config current-context &>/dev/null; then
        printf "  ${RED}✘${NC}  %-20s no current context\n" "kubeconfig"
        error "No kubectl context. Run: kubectl config use-context <name>"
        exit 1
    fi

    KUBE_CONTEXT=$(kubectl config current-context)
    printf "  ${GREEN}✔${NC}  %-20s %s\n" "context" "$KUBE_CONTEXT"

    if ! kubectl cluster-info &>/dev/null 2>&1; then
        printf "  ${RED}✘${NC}  %-20s unreachable\n" "cluster"
        error "Cannot reach cluster. Check your kubeconfig / VPN."
        exit 1
    fi
    printf "  ${GREEN}✔${NC}  %-20s reachable\n" "cluster"

    if echo "$KUBE_CONTEXT" | grep -q "^kind-"; then
        CLUSTER_TYPE="kind"
        if ! command -v kind &>/dev/null; then
            printf "  ${RED}✘${NC}  %-20s kind context detected but 'kind' CLI missing\n" "kind CLI"
            error "Install kind: https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
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
    info "All prerequisites satisfied ✓"
    divider
}

# ─────────────────────────────────────────────────────────────────────────────
#  DEPLOY STEPS
# ─────────────────────────────────────────────────────────────────────────────
deploy_operator() {
    header "▶  [1/5] Energy-Aware Operator"
    divider

    info "[1a] Building operator image ($OPERATOR_IMAGE_REPO:$OPERATOR_IMAGE_TAG)..."
    if IMAGE_REPOSITORY="$OPERATOR_IMAGE_REPO" IMAGE_TAG="$OPERATOR_IMAGE_TAG" \
           bash "$ROOT_DIR/energy-aware-operator/scripts/build.sh"; then
        DEPLOY_OPERATOR_BUILD_STATUS="OK"
        info "Operator image built ✓"
    else
        DEPLOY_OPERATOR_BUILD_STATUS="FAILED"
        DEPLOY_OPERATOR_STATUS="FAILED"
        error "Operator image build failed — skipping operator deploy"
        return
    fi

    info "[1b] Deploying operator via Helm..."
    if NAMESPACE="$NAMESPACE" \
       IMAGE_REPOSITORY="$OPERATOR_IMAGE_REPO" \
       IMAGE_TAG="$OPERATOR_IMAGE_TAG" \
       SKIP_PORT_FORWARD=true \
           bash "$ROOT_DIR/energy-aware-operator/scripts/deploy.sh"; then
        DEPLOY_OPERATOR_STATUS="OK"
        info "Energy-Aware Operator deployed ✓"
    else
        DEPLOY_OPERATOR_STATUS="FAILED"
        error "Energy-Aware Operator deployment failed"
    fi
}

deploy_metric_service() {
    header "▶  [2/5] Energy Metric Service (PostgreSQL + API)"
    divider

    if NAMESPACE="$NAMESPACE" SKIP_PORT_FORWARD=true \
           ENABLE_GRID_STUB="$ENABLE_GRID_STUB" GRID_API_URL="$GRID_API_URL" \
           ENABLE_METRICS_SCHEDULER="$ENABLE_METRICS_SCHEDULER" \
           PROMETHEUS_BASE_URL="$PROMETHEUS_BASE_URL" \
           MONITORING_RELEASE_NAME="$MONITORING_RELEASE_NAME" \
           bash "$ROOT_DIR/energy-metric-service/scripts/deploy-all.sh"; then
        DEPLOY_METRIC_STATUS="OK"
        info "Energy Metric Service deployed ✓"
    else
        DEPLOY_METRIC_STATUS="FAILED"
        error "Energy Metric Service deployment failed"
    fi
}

deploy_monitoring() {
    header "▶  [3/5] Energy Monitoring Helm Stack"
    divider

    if NAMESPACE="$NAMESPACE" SKIP_PORT_FORWARD=true \
           bash "$ROOT_DIR/energy-monitoring-helm-stack/scripts/deploy.sh"; then
        DEPLOY_MONITORING_STATUS="OK"
        info "Energy Monitoring Stack deployed ✓"
    else
        DEPLOY_MONITORING_STATUS="FAILED"
        error "Energy Monitoring Stack deployment failed"
    fi
}

deploy_ui() {
    header "▶  [4/5] Orchestrator Library UI"
    divider

    if NAMESPACE="$NAMESPACE" SKIP_PORT_FORWARD=true \
           bash "$ROOT_DIR/orchestrator-library-ui/scripts/deploy.sh"; then
        DEPLOY_UI_STATUS="OK"
        info "Orchestrator Library UI deployed ✓"
    else
        DEPLOY_UI_STATUS="FAILED"
        error "Orchestrator Library UI deployment failed"
    fi
}

deploy_workload() {
    header "▶  [5/5] Sample Testing Workload (Critical EAO)"
    divider

    if [ "$DEPLOY_OPERATOR_STATUS" != "OK" ]; then
        DEPLOY_SAMPLE_WORKLOAD_STATUS="SKIPPED"
        warn "Operator not running — skipping sample workload"
        divider
        return
    fi

    local manifest_failed=0
    for manifest in "${SAMPLE_K8S_MANIFESTS[@]}"; do
        info "Applying backing workload: $(basename "$manifest")..."
        if kubectl apply -f "$manifest" -n "$NAMESPACE"; then
            info "Backing workload applied ✓"
        else
            warn "Failed to apply backing workload — continuing with EAO CR"
            manifest_failed=1
        fi
    done

    for cr in "${SAMPLE_EAO_CRS[@]}"; do
        info "Applying EAO CR: $(basename "$cr")..."
        if kubectl apply -f "$cr" -n "$NAMESPACE"; then
            if [ "$manifest_failed" -eq 0 ]; then
                DEPLOY_SAMPLE_WORKLOAD_STATUS="OK"
            else
                DEPLOY_SAMPLE_WORKLOAD_STATUS="FAILED"
            fi
            info "EAO CR applied ✓"
            info "Waiting 5s for operator to reconcile..."
            sleep 5
            echo ""
            kubectl get eao -n "$NAMESPACE" 2>/dev/null || true
        else
            DEPLOY_SAMPLE_WORKLOAD_STATUS="FAILED"
            error "Failed to apply EAO CR"
        fi
    done
    divider
}

# ─────────────────────────────────────────────────────────────────────────────
#  CLEANUP STEPS  (LIFO — reverse of deploy order)
# ─────────────────────────────────────────────────────────────────────────────
cleanup_workload() {
    header "▶  [1/5] Sample Testing Workload — Cleanup"
    divider

    local failed=0
    for cr in "${SAMPLE_EAO_CRS[@]}"; do
        kubectl delete -f "$cr" -n "$NAMESPACE" --ignore-not-found=true 2>/dev/null || failed=1
    done
    for manifest in "${SAMPLE_K8S_MANIFESTS[@]}"; do
        kubectl delete -f "$manifest" -n "$NAMESPACE" --ignore-not-found=true 2>/dev/null || failed=1
    done

    if [ "$failed" -eq 0 ]; then
        CLEANUP_WORKLOAD_STATUS="OK"
        info "Sample workload cleaned ✓"
    else
        CLEANUP_WORKLOAD_STATUS="FAILED"
        error "Sample workload cleanup failed"
    fi
}

cleanup_ui() {
    header "▶  [2/5] Orchestrator Library UI — Cleanup"
    divider

    if NAMESPACE="$NAMESPACE" bash "$ROOT_DIR/orchestrator-library-ui/scripts/cleanup.sh"; then
        CLEANUP_UI_STATUS="OK"
        info "Orchestrator Library UI cleaned ✓"
    else
        CLEANUP_UI_STATUS="FAILED"
        error "Orchestrator Library UI cleanup failed"
    fi
}

cleanup_monitoring() {
    header "▶  [3/5] Energy Monitoring Helm Stack — Cleanup"
    divider

    if NAMESPACE="$NAMESPACE" bash "$ROOT_DIR/energy-monitoring-helm-stack/scripts/cleanup.sh"; then
        CLEANUP_MONITORING_STATUS="OK"
        info "Energy Monitoring Stack cleaned ✓"
    else
        CLEANUP_MONITORING_STATUS="FAILED"
        error "Energy Monitoring Stack cleanup failed"
    fi
}

cleanup_metric_service() {
    header "▶  [4/5] Energy Metric Service — Cleanup"
    divider

    local pvc_arg=""
    [ "$DELETE_PVC" = true ] && pvc_arg="--delete-pvc"

    if NAMESPACE="$NAMESPACE" bash "$ROOT_DIR/energy-metric-service/scripts/cleanup.sh" $pvc_arg; then
        CLEANUP_METRIC_STATUS="OK"
        info "Energy Metric Service cleaned ✓"
    else
        CLEANUP_METRIC_STATUS="FAILED"
        error "Energy Metric Service cleanup failed"
    fi
}

cleanup_operator() {
    header "▶  [5/5] Energy-Aware Operator — Cleanup"
    divider

    local crd_arg=""
    [ "$DELETE_CRD" = true ] && crd_arg="--delete-crd"

    if NAMESPACE="$NAMESPACE" bash "$ROOT_DIR/energy-aware-operator/scripts/cleanup.sh" $crd_arg; then
        CLEANUP_OPERATOR_STATUS="OK"
        info "Energy-Aware Operator cleaned ✓"
    else
        CLEANUP_OPERATOR_STATUS="FAILED"
        error "Energy-Aware Operator cleanup failed"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
#  SUMMARIES & GUIDES
# ─────────────────────────────────────────────────────────────────────────────
print_deploy_summary() {
    echo ""
    banner "DEPLOYMENT SUMMARY"
    echo ""
    printf "  %-42s %s\n" "energy-aware-operator (build)"      "$(status_icon "$DEPLOY_OPERATOR_BUILD_STATUS")"
    printf "  %-42s %s\n" "energy-aware-operator (deploy)"     "$(status_icon "$DEPLOY_OPERATOR_STATUS")"
    printf "  %-42s %s\n" "energy-metric-service (pg + api)"   "$(status_icon "$DEPLOY_METRIC_STATUS")"
    printf "  %-42s %s\n" "energy-monitoring-helm-stack"       "$(status_icon "$DEPLOY_MONITORING_STATUS")"
    printf "  %-42s %s\n" "orchestrator-library-ui"            "$(status_icon "$DEPLOY_UI_STATUS")"
    printf "  %-42s %s\n" "sample workload (critical-testing)"  "$(status_icon "$DEPLOY_SAMPLE_WORKLOAD_STATUS")"
    echo ""
}

print_cleanup_summary() {
    echo ""
    banner "CLEANUP SUMMARY"
    echo ""
    printf "  %-42s %s\n" "sample workload (critical-testing)"  "$(status_icon "$CLEANUP_WORKLOAD_STATUS")"
    printf "  %-42s %s\n" "orchestrator-library-ui"             "$(status_icon "$CLEANUP_UI_STATUS")"
    printf "  %-42s %s\n" "energy-monitoring-helm-stack"        "$(status_icon "$CLEANUP_MONITORING_STATUS")"
    printf "  %-42s %s\n" "energy-metric-service (pg + api)"    "$(status_icon "$CLEANUP_METRIC_STATUS")"
    printf "  %-42s %s\n" "energy-aware-operator"               "$(status_icon "$CLEANUP_OPERATOR_STATUS")"
    echo ""
    divider
    echo ""
}

print_port_forward_guide() {
    divider
    echo -e "${BOLD}${CYAN}   PORT-FORWARDING  (run manually after deploy)${NC}"
    divider
    echo ""
    echo -e "${YELLOW}  # Step 1 — Kill existing port-forwards for this stack:${NC}"
    echo    "  pkill -f 'svc/energy-metric-service'            || true"
    echo    "  pkill -f 'svc/eao-postgres'                     || true"
    echo    "  pkill -f 'svc/energy-metrics-grafana'           || true"
    echo    "  pkill -f 'svc/energy-metrics-prometheus-server' || true"
    echo    "  pkill -f 'svc/energy-metrics-kepler'            || true"
    echo    "  pkill -f 'svc/orchestrator-library-ui'     || true"
    echo    "  pkill -f 'svc/orchestrator-k8s-proxy'      || true"
    if [ "$ENABLE_GRID_STUB" = true ]; then
        echo    "  pkill -f 'svc/grid-stub'                   || true"
    fi
    echo ""
    echo -e "${YELLOW}  # Step 2 — Start all port-forwards in the background:${NC}"
    echo ""
    echo    "  kubectl port-forward -n ${NAMESPACE} svc/energy-metric-service 8000:8000 &"
    echo    "  kubectl port-forward -n ${NAMESPACE} svc/eao-postgres 5432:5432 &"
    echo    "  kubectl port-forward -n ${NAMESPACE} svc/energy-metrics-grafana 3000:80 &"
    echo    "  kubectl port-forward -n ${NAMESPACE} svc/energy-metrics-prometheus-server 9090:80 &"
    echo    "  kubectl port-forward -n ${NAMESPACE} svc/energy-metrics-kepler 9102:9102 &"
    echo    "  kubectl port-forward -n ${NAMESPACE} svc/orchestrator-library-ui 4200:80 &"
    echo    "  kubectl port-forward -n ${NAMESPACE} svc/orchestrator-k8s-proxy 3001:3000 &"
    if [ "$ENABLE_GRID_STUB" = true ]; then
        echo    "  kubectl port-forward -n ${NAMESPACE} svc/grid-stub 8090:80 &"
    fi
    echo ""
    echo -e "${YELLOW}  # Note: K8s Proxy uses port 3001 to avoid conflict with Grafana on 3000.${NC}"
    echo ""
}

print_access_urls() {
    divider
    echo -e "${BOLD}${CYAN}   ACCESS URLS  (available after port-forwarding)${NC}"
    divider
    echo ""
    printf "  %-36s %s\n" "Energy Metric Service API"   "http://localhost:8000/docs"
    printf "  %-36s %s\n" "Energy Metric Service Docs"  "http://localhost:8000/redoc"
    printf "  %-36s %s\n" "PostgreSQL"                  "localhost:5432  (user: postgres / db: orchestration_db)"
    printf "  %-36s %s\n" "Grafana Dashboard"           "http://localhost:3000  (admin / admin)"
    printf "  %-36s %s\n" "Prometheus"                  "http://localhost:9090"
    printf "  %-36s %s\n" "Kepler Metrics"              "http://localhost:9102/metrics"
    printf "  %-36s %s\n" "Orchestrator Library UI"     "http://localhost:4200"
    printf "  %-36s %s\n" "K8s Proxy"                   "http://localhost:3001"
    if [ "$ENABLE_GRID_STUB" = true ]; then
        printf "  %-36s %s\n" "Grid Stub (dev/test only)"   "http://localhost:8090/capacity  (GET/POST)"
    fi
    echo ""
    divider
    echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
#  TOP-LEVEL COMMANDS
# ─────────────────────────────────────────────────────────────────────────────
cmd_deploy() {
    # Status vars
    DEPLOY_OPERATOR_BUILD_STATUS="PENDING"
    DEPLOY_OPERATOR_STATUS="PENDING"
    DEPLOY_METRIC_STATUS="PENDING"
    DEPLOY_MONITORING_STATUS="PENDING"
    DEPLOY_UI_STATUS="PENDING"
    DEPLOY_SAMPLE_WORKLOAD_STATUS="PENDING"

    echo ""
    banner "Energy-Aware Orchestrator — Full Stack Deployment"
    echo ""
    info "Namespace:        $NAMESPACE"
    info "Operator image:   $OPERATOR_IMAGE_REPO:$OPERATOR_IMAGE_TAG"
    info "Port-forwarding:  suggested only (not executed automatically)"
    echo ""

    check_prerequisites

    deploy_operator
    deploy_metric_service
    deploy_monitoring
    deploy_ui
    deploy_workload

    print_deploy_summary
    print_port_forward_guide
    print_access_urls
}

cmd_cleanup() {
    # Status vars
    CLEANUP_WORKLOAD_STATUS="PENDING"
    CLEANUP_UI_STATUS="PENDING"
    CLEANUP_MONITORING_STATUS="PENDING"
    CLEANUP_METRIC_STATUS="PENDING"
    CLEANUP_OPERATOR_STATUS="PENDING"

    echo ""
    banner "Energy-Aware Orchestrator — Full Stack Cleanup"
    echo ""
    info "Namespace:   $NAMESPACE"
    info "Delete CRD:  $DELETE_CRD"
    info "Delete PVCs: $DELETE_PVC"
    info "Order:       LIFO (last deployed → first cleaned)"
    echo ""

    header "▶  Stopping port-forwards"
    divider
    pkill -f 'kubectl port-forward' || true
    info "Port-forwards stopped ✓"

    cleanup_workload
    cleanup_ui
    cleanup_monitoring
    cleanup_metric_service
    cleanup_operator

    print_cleanup_summary
}

# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
main() {
    parse_args "$@"

    case "$COMMAND" in
        deploy)  cmd_deploy  ;;
        cleanup) cmd_cleanup ;;
    esac
}

main "$@"
