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

# Deployment status tracking
DEPLOY_OPERATOR_STATUS="PENDING"
DEPLOY_METRIC_STATUS="PENDING"
DEPLOY_MONITORING_STATUS="PENDING"
DEPLOY_UI_STATUS="PENDING"

echo ""
print_divider
echo -e "${BOLD}${CYAN}   Energy-Aware Orchestrator — Full Stack Deployment${NC}"
print_divider
echo ""
print_info "Namespace: $NAMESPACE"
print_info "Port-forwarding: suggested only (not executed automatically)"
echo ""

# ─── 1. Energy-Aware Operator ────────────────────────────────────────────────
print_header "▶  [1/4] Energy-Aware Operator"
print_divider
if NAMESPACE="$NAMESPACE" SKIP_PORT_FORWARD=true \
       bash "$ROOT_DIR/energy-aware-operator/scripts/deploy.sh"; then
    DEPLOY_OPERATOR_STATUS="OK"
    print_info "Energy-Aware Operator deployed successfully ✓"
else
    DEPLOY_OPERATOR_STATUS="FAILED"
    print_error "Energy-Aware Operator deployment failed"
fi

# ─── 2. Energy Metric Service (PostgreSQL + FastAPI) ─────────────────────────
print_header "▶  [2/4] Energy Metric Service (PostgreSQL + API)"
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
print_header "▶  [3/4] Energy Monitoring Helm Stack"
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
print_header "▶  [4/4] Orchestrator Library UI"
print_divider
if NAMESPACE="$NAMESPACE" SKIP_PORT_FORWARD=true \
       bash "$ROOT_DIR/orchestrator-library-ui/scripts/deploy.sh"; then
    DEPLOY_UI_STATUS="OK"
    print_info "Orchestrator Library UI deployed successfully ✓"
else
    DEPLOY_UI_STATUS="FAILED"
    print_error "Orchestrator Library UI deployment failed"
fi

# ─── DEPLOYMENT SUMMARY ──────────────────────────────────────────────────────
echo ""
print_divider
echo -e "${BOLD}${CYAN}   DEPLOYMENT SUMMARY${NC}"
print_divider

_status_icon() {
    if [ "$1" = "OK" ]; then echo -e "${GREEN}✔  OK${NC}"; else echo -e "${RED}✘  FAILED${NC}"; fi
}

echo ""
printf "  %-42s %s\n" "energy-aware-operator"            "$(_status_icon "$DEPLOY_OPERATOR_STATUS")"
printf "  %-42s %s\n" "energy-metric-service (pg + api)" "$(_status_icon "$DEPLOY_METRIC_STATUS")"
printf "  %-42s %s\n" "energy-monitoring-helm-stack"     "$(_status_icon "$DEPLOY_MONITORING_STATUS")"
printf "  %-42s %s\n" "orchestrator-library-ui"          "$(_status_icon "$DEPLOY_UI_STATUS")"
echo ""

# ─── PORT-FORWARDING INSTRUCTIONS ────────────────────────────────────────────
print_divider
echo -e "${BOLD}${CYAN}   PORT-FORWARDING  (run these manually in separate terminals)${NC}"
print_divider
echo ""
echo -e "${YELLOW}  # Step 1 — Kill any existing port-forwards first:${NC}"
echo    "  pkill -f 'kubectl port-forward' || true"
echo ""
echo -e "${YELLOW}  # Step 2 — Run this block to start all port-forwards in the background at once:${NC}"
echo ""
echo    "  kubectl port-forward -n ${NAMESPACE} svc/energy-metric-service 8000:8000 &"
echo    "  kubectl port-forward -n ${NAMESPACE} svc/eao-postgres 5432:5432 &"
echo    "  kubectl port-forward -n ${NAMESPACE} svc/energy-metrics-grafana 3000:80 &"
echo    "  kubectl port-forward -n ${NAMESPACE} svc/energy-metrics-prometheus-server 9090:80 &"
echo    "  kubectl port-forward -n ${NAMESPACE} svc/energy-metrics-kepler 9102:9102 &"
echo    "  kubectl port-forward -n ${NAMESPACE} svc/aces-orchestrator-library-ui 4200:80 &"
echo    "  kubectl port-forward -n ${NAMESPACE} svc/aces-orchestrator-k8s-proxy 3001:3000 &"
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
