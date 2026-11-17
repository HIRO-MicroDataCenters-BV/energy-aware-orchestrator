#!/usr/bin/env bash
# Prepares the kind-sample cluster for the D4.3 simulation runs.
# Every change here is undone by restore_cluster.sh; the original objects are
# snapshotted in ../config/original/ before this runs.
set -euo pipefail

CTX=kind-sample
NS=default
HERE="$(cd "$(dirname "$0")" && pwd)"
CFG="$HERE/../config"
K="kubectl --context $CTX"

[ "$(kubectl config get-contexts -o name | grep -x "$CTX")" = "$CTX" ] || { echo "context $CTX missing"; exit 1; }

# 1. energy-metric-service: poll the grid-stub every 15 s, stop the in-process
#    supply forecaster, and drop the Modbus PDU stub as a supply source, so
#    the synthetic profile pushed to the grid-stub is the only supply signal.
$K -n $NS set env deploy/energy-metric-service \
  GRID_POLL_INTERVAL_SECONDS=15 ENABLE_FORECASTING=false GRID_MODBUS_HOST=
$K -n $NS rollout status deploy/energy-metric-service --timeout=180s

# 2. Deactivate every supply row still active for now or later (modbus-pdu
#    predicted 6 h rows + its current 5 min reading). IDs are saved so
#    restore_cluster.sh re-activates exactly these rows.
$K -n $NS exec eao-postgres-0 -- psql -U postgres -d orchestration_db -tAc \
  "SELECT id FROM energy_availability WHERE record_type='supply' AND is_active AND slot_end_time >= now() AND provider_name NOT LIKE 'd43-%'" \
  > "$CFG/deactivated-supply-ids.txt"
IDS=$(paste -sd, "$CFG/deactivated-supply-ids.txt")
if [ -n "$IDS" ]; then
  $K -n $NS exec eao-postgres-0 -- psql -U postgres -d orchestration_db -c \
    "UPDATE energy_availability SET is_active=false WHERE id IN ($IDS)"
fi

# 3. energy-aware-operator: re-evaluate every CR every 30 s instead of 600 s.
$K -n $NS set env deploy/energy-operator-energy-aware-operator KOPF_RECONCILE_INTERVAL_SECONDS=30
$K -n $NS rollout status deploy/energy-operator-energy-aware-operator --timeout=180s

# 4. Experiment namespace.
$K create namespace d43 --dry-run=client -o yaml | $K apply -f -

echo "setup done"
