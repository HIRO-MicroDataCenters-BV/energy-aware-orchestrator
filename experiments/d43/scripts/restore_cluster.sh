#!/usr/bin/env bash
# Undoes setup_cluster.sh: restores the original env values (see
# ../config/original/*.yaml), re-activates the supply rows it deactivated,
# deactivates the synthetic d43-* supply rows and empties the grid-stub.
# Deleting the d43 namespace is left as a separate, explicit step.
set -euo pipefail

CTX=kind-sample
NS=default
HERE="$(cd "$(dirname "$0")" && pwd)"
CFG="$HERE/../config"
K="kubectl --context $CTX"

$K -n $NS exec -i deploy/grid-stub -- python -c \
  "import sys, urllib.request; print(urllib.request.urlopen(urllib.request.Request('http://localhost:8080/capacity', data=sys.stdin.buffer.read(), headers={'Content-Type': 'application/json'})).read().decode())" \
  <<<'{"availability": []}'

# Deactivate the synthetic rows before forecasting is re-enabled: the
# forecaster predicts for every provider with active real rows.
D43_OFF="UPDATE energy_availability SET is_active=false WHERE provider_name LIKE 'd43-%' AND is_active"
$K -n $NS exec eao-postgres-0 -- psql -U postgres -d orchestration_db -c "$D43_OFF"

$K -n $NS set env deploy/energy-metric-service \
  GRID_POLL_INTERVAL_SECONDS=300 ENABLE_FORECASTING=true GRID_MODBUS_HOST=modbus-pdu-stub
$K -n $NS rollout status deploy/energy-metric-service --timeout=180s

IDS=$(paste -sd, "$CFG/deactivated-supply-ids.txt")
if [ -n "$IDS" ]; then
  $K -n $NS exec eao-postgres-0 -- psql -U postgres -d orchestration_db -c \
    "UPDATE energy_availability SET is_active=true WHERE id IN ($IDS)"
fi
# again, in case a poll or forecast wrote d43 rows while the EMS restarted
$K -n $NS exec eao-postgres-0 -- psql -U postgres -d orchestration_db -c "$D43_OFF"

$K -n $NS set env deploy/energy-operator-energy-aware-operator KOPF_RECONCILE_INTERVAL_SECONDS=600
$K -n $NS rollout status deploy/energy-operator-energy-aware-operator --timeout=180s

echo "restore done (namespace d43 kept; delete with: $K delete namespace d43)"
