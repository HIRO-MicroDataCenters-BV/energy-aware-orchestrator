#!/usr/bin/env bash
#
# Live, narrated demo of the energy-aware orchestrator's end-to-end cycle:
# Kepler/cAdvisor metrics -> supply forecasting -> demand reporting ->
# scheduling decision. Companion to E2E_DEMO.md (same scenarios, same order).
#
# Designed to be run interactively during a presentation: each scenario
# prints *why* it's being run, shows the exact command, runs it, shows the
# real result, then pauses so you can tab away and show something else
# before continuing.
#
# Assumes the usual port-forwards are already up:
#   kubectl port-forward -n default svc/energy-metric-service 8000:8000 &
#   kubectl port-forward -n default svc/eao-postgres 5432:5432 &
#   kubectl port-forward -n default svc/energy-metrics-prometheus-server 9090:80 &
#   kubectl port-forward -n default svc/grid-stub 8090:80 &
#
# Usage: ./e2e_demo.sh [--yes] [--context=kind-sample] [--scenario=<1-6|e|a>]
#   --yes         don't pause within a scenario (for a dry run / CI smoke test)
#   --context     expected kubectl context (safety check), default kind-sample
#   --scenario    which scenario to run (1-6, e for end-to-end, a for all).
#                 Skips the interactive menu if given.

set -uo pipefail

# ---------------------------------------------------------------------------
# Config (override via env if your setup differs)
# ---------------------------------------------------------------------------
APP_URL="${APP_URL:-http://localhost:8000}"
PROM_URL="${PROM_URL:-http://localhost:9090}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PGPASSWORD="${PGPASSWORD:-postgres}"
PGDATABASE="${PGDATABASE:-orchestration_db}"
NAMESPACE="${NAMESPACE:-default}"
CRITICAL_CR="${CRITICAL_CR:-eaoprofile-critical}"
OPTIONAL_CR="${OPTIONAL_CR:-eaoprofile-optional}"
PROVIDER="${PROVIDER:-grid}"
GRID_STUB_URL="${GRID_STUB_URL:-http://localhost:8090}"
PUSH_TEST_PROVIDER="${PUSH_TEST_PROVIDER:-demo-push-test}"
APP_DEPLOYMENT="${APP_DEPLOYMENT:-energy-metric-service}"
APP_PYTHON="${APP_PYTHON:-/code/.venv/bin/python}"  # venv python inside the app pod (uv-managed, not the bare system python)
EXPECTED_CONTEXT="kind-sample"
AUTO_CONTINUE=false
SCENARIO_CHOICE="${SCENARIO_CHOICE:-}"

for arg in "$@"; do
  case "$arg" in
    --yes) AUTO_CONTINUE=true ;;
    --context=*) EXPECTED_CONTEXT="${arg#--context=}" ;;
    --scenario=*) SCENARIO_CHOICE="${arg#--scenario=}" ;;
  esac
done

export PGPASSWORD

# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------
BOLD=$'\033[1m'; DIM=$'\033[2m'; CYAN=$'\033[36m'; YELLOW=$'\033[33m'; GREEN=$'\033[32m'; RED=$'\033[31m'; RESET=$'\033[0m'

psql_q() {
  psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -t -A -c "$1"
}
psql_pretty() {
  psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -c "$1"
}

print_scenario_header() {
  # print_scenario_header <number> <title> <why-explanation>
  echo
  echo "${BOLD}${CYAN}=== Scenario $1: $2 ===${RESET}"
  echo "${DIM}$3${RESET}"
  echo
}

run() {
  # run "description (unused, kept for call-site readability)" "command string"
  echo "${YELLOW}\$ $2${RESET}"
  eval "$2"
  local status=$?
  if [ $status -ne 0 ]; then
    echo "${RED}(command exited $status - continuing anyway)${RESET}"
  fi
  return 0
}

pause() {
  $AUTO_CONTINUE && return 0
  echo
  read -r -p "${BOLD}-- press Enter to continue (or Ctrl-C to stop the demo) -- ${RESET}"
}

# ---------------------------------------------------------------------------
# Date helpers - fixed 6-hour slot boundaries (00-06/06-12/12-18/18-24 UTC),
# matching the scheduler's own bucketing. Written to work on both BSD date
# (macOS) and GNU date (Linux).
# ---------------------------------------------------------------------------
next_day() {
  date -u -d "$1 +1 day" +%Y-%m-%d 2>/dev/null || date -u -v+1d -j -f '%Y-%m-%d' "$1" +%Y-%m-%d
}

# Sets CURRENT_SLOT_START / CURRENT_SLOT_END / CURRENT_SLOT_DAY to the
# current 6-hour bucket, e.g. "09:xx UTC" -> 06:00-12:00 today.
current_slot_bounds() {
  local hour bucket_start end_hour
  hour=$(date -u +%H)
  bucket_start=$(( (10#$hour / 6) * 6 ))
  CURRENT_SLOT_DAY=$(date -u +%Y-%m-%d)
  CURRENT_SLOT_START=$(printf '%sT%02d:00:00+00:00' "$CURRENT_SLOT_DAY" "$bucket_start")
  end_hour=$(( bucket_start + 6 ))
  if [ "$end_hour" -eq 24 ]; then
    CURRENT_SLOT_END="$(next_day "$CURRENT_SLOT_DAY")T00:00:00+00:00"
  else
    CURRENT_SLOT_END=$(printf '%sT%02d:00:00+00:00' "$CURRENT_SLOT_DAY" "$end_hour")
  fi
}

# Sets NEXT_SLOT_START / NEXT_SLOT_END to the bucket right after
# CURRENT_SLOT_*. Call current_slot_bounds first.
next_slot_bounds() {
  local end_hour
  NEXT_SLOT_START="$CURRENT_SLOT_END"
  end_hour=$(( 10#$(date -u -d "$NEXT_SLOT_START" +%H 2>/dev/null || echo "${NEXT_SLOT_START:11:2}") + 6 ))
  if [ "$end_hour" -ge 24 ]; then
    NEXT_SLOT_END="$(next_day "$CURRENT_SLOT_DAY")T$(printf '%02d' $((end_hour - 24))):00:00+00:00"
  else
    NEXT_SLOT_END="${NEXT_SLOT_START:0:11}$(printf '%02d' "$end_hour"):00:00+00:00"
  fi
}

# ---------------------------------------------------------------------------
# Cleanup: always remove any test rows/pushes we made, even on Ctrl-C
# ---------------------------------------------------------------------------
PRECEDENCE_TEST_SLOT_START=""
PRECEDENCE_TEST_SLOT_END=""
PUSHED_TO_STUB=false
cleanup() {
  if [ -n "$PRECEDENCE_TEST_SLOT_START" ]; then
    echo
    echo "${DIM}Cleaning up test rows inserted for the precedence demo...${RESET}"
    psql_q "DELETE FROM energy_availability WHERE provider_name='${PROVIDER}' AND slot_start_time='${PRECEDENCE_TEST_SLOT_START}' AND slot_end_time='${PRECEDENCE_TEST_SLOT_END}';" >/dev/null 2>&1
  fi
  if $PUSHED_TO_STUB; then
    echo "${DIM}Resetting grid-stub back to empty and removing pushed test rows...${RESET}"
    curl -s -X POST "$GRID_STUB_URL/capacity" -H "Content-Type: application/json" -d '{"availability": []}' >/dev/null 2>&1
    psql_q "DELETE FROM energy_availability WHERE provider_name='${PUSH_TEST_PROVIDER}';" >/dev/null 2>&1
  fi
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
preflight() {
  echo "${BOLD}Preflight checks${RESET}"
  local ctx
  ctx=$(kubectl config current-context 2>/dev/null)
  echo "kubectl context: $ctx"
  if [ "$ctx" != "$EXPECTED_CONTEXT" ]; then
    echo "${RED}Expected context '$EXPECTED_CONTEXT', got '$ctx'.${RESET}"
    echo "This script annotates CRs and writes/deletes test DB rows - refusing to run against the wrong cluster."
    echo "Pass --context=<name> if this is intentional, or switch context first."
    exit 1
  fi

  for target in "$APP_URL/docs" "$PROM_URL/-/healthy" "$GRID_STUB_URL/capacity"; do
    if ! curl -s -o /dev/null -w '' --max-time 3 "$target"; then
      echo "${RED}Can't reach $target - is the port-forward up?${RESET}"
      exit 1
    fi
  done
  echo "${GREEN}All good.${RESET}"
  pause
}

# ---------------------------------------------------------------------------
# Scenario selection
# ---------------------------------------------------------------------------
prompt_scenario_choice() {
  [ -n "$SCENARIO_CHOICE" ] && return
  echo
  echo "${BOLD}Which scenario do you want to run?${RESET}"
  echo "  1) Kepler + cAdvisor metric collection is live"
  echo "  2) Push test grid capacity in, watch it land in the DB"
  echo "  3) Predicted supply gap in the placeholder model"
  echo "  4) Real supply wins over predicted for the same slot"
  echo "  5) Demand reporting and resolution"
  echo "  6) Critical vs. Optional decision logic"
  echo "  e) End-to-end - forced live reconcile"
  echo "  a) All scenarios in order"
  read -r -p "Enter choice [1-6/e/a]: " SCENARIO_CHOICE
}

run_selected_scenario() {
  case "$SCENARIO_CHOICE" in
    1) check_metric_collection_is_live ;;
    2) demo_push_supply_and_verify_it_lands ;;
    3) show_forecast_gap_in_placeholder_model ;;
    4) demo_real_beats_predicted_for_same_slot ;;
    5) show_demand_reporting_and_resolution ;;
    6) show_priority_decision_logic ;;
    e|E) force_reconcile_and_observe_full_cycle ;;
    a|A|all)
      check_metric_collection_is_live
      demo_push_supply_and_verify_it_lands
      show_forecast_gap_in_placeholder_model
      demo_real_beats_predicted_for_same_slot
      show_demand_reporting_and_resolution
      show_priority_decision_logic
      force_reconcile_and_observe_full_cycle
      ;;
    *)
      echo "${RED}Unrecognized choice: '$SCENARIO_CHOICE'${RESET}"
      exit 1
      ;;
  esac
}

# ---------------------------------------------------------------------------
# Scenario 1 - Kepler + cAdvisor collection is live
# ---------------------------------------------------------------------------
check_metric_collection_is_live() {
  print_scenario_header 1 "Kepler + cAdvisor metric collection is live" \
    "Why: MetricCollectorScheduler should be joining Kepler energy data with cAdvisor
utilization data, per container, every ~30s. This is the foundation everything
else in the demo depends on."

  run "kepler/prometheus pods" \
    "kubectl get pods -n $NAMESPACE -o wide | grep -E 'kepler|prometheus-server'"
  echo
  run "Kepler series in Prometheus" \
    "curl -s '$PROM_URL/api/v1/query?query=kepler_container_core_joules_total' | jq '.data.result | length'"
  run "built-in cAdvisor series in Prometheus" \
    "curl -s -G '$PROM_URL/api/v1/query' --data-urlencode 'query=container_cpu_usage_seconds_total{job=\"kubernetes-nodes-cadvisor\"}' | jq '.data.result | length'"
  echo
  run "container_power_metrics freshness + metric_source join" \
    "psql_pretty \"SELECT metric_source, count(*), max(timestamp) FROM container_power_metrics GROUP BY metric_source ORDER BY max DESC;\""

  echo
  echo "${GREEN}Expect: recent max(timestamp) (within the last collection cycle), and${RESET}"
  echo "${GREEN}the 'kepler+cadvisor' row present - confirms both sources are being joined.${RESET}"
  pause
}

# ---------------------------------------------------------------------------
# Scenario 2 - push test grid capacity, trigger a poll, verify it lands
# ---------------------------------------------------------------------------
show_existing_supply_baseline() {
  echo "First, a baseline: what's already there before we push anything."
  run "existing supply/demand rows by source" \
    "psql_pretty \"SELECT record_type, data_source, provider_name, count(*), min(slot_start_time), max(slot_start_time)
     FROM energy_availability GROUP BY record_type, data_source, provider_name ORDER BY record_type, data_source;\""
  pause
}

push_test_capacity_to_grid_stub() {
  current_slot_bounds
  next_slot_bounds
  echo "Pushing two test slots for provider='$PUSH_TEST_PROVIDER': current slot ($CURRENT_SLOT_START) at 1777W,"
  echo "next slot ($NEXT_SLOT_START) at 1888W - distinct, made-up values so they're unmistakable in the output."
  run "POST test capacity to the grid-stub" \
    "curl -s -X POST $GRID_STUB_URL/capacity -H 'Content-Type: application/json' -d '{\"availability\": [
       {\"slot_start_time\": \"$CURRENT_SLOT_START\", \"slot_end_time\": \"$CURRENT_SLOT_END\", \"available_watts\": 1777, \"provider_name\": \"$PUSH_TEST_PROVIDER\", \"energy_source_type\": \"solar\", \"confidence_percentage\": 88},
       {\"slot_start_time\": \"$NEXT_SLOT_START\", \"slot_end_time\": \"$NEXT_SLOT_END\", \"available_watts\": 1888, \"provider_name\": \"$PUSH_TEST_PROVIDER\", \"energy_source_type\": \"solar\", \"confidence_percentage\": 88}
     ]}'"
  PUSHED_TO_STUB=true
  run "GET it back from the stub itself (proves the push landed at the mock source)" \
    "curl -s $GRID_STUB_URL/capacity | jq"
}

trigger_grid_poll_now() {
  echo
  echo "${BOLD}Instead of waiting up to 300s for the real poll loop, trigger one cycle now${RESET}"
  echo "${DIM}via kubectl exec - same GridPollingScheduler code, called directly inside the${RESET}"
  echo "${DIM}running pod. No restart, no port-forward disruption.${RESET}"
  run "trigger one poll cycle inside the running pod" \
    "kubectl exec -n $NAMESPACE deploy/$APP_DEPLOYMENT -- $APP_PYTHON -c \"
import asyncio, os
from app.scheduler.grid_polling_scheduler import GridPollingScheduler

async def main():
    s = GridPollingScheduler(api_url=os.environ['GRID_API_URL'])
    slots = await s.grid_client.fetch_grid_capacity()
    stored = await s._store_slots(slots)
    print(f'stored {stored}/{len(slots)} slot(s)')
    await s.grid_client.close()

asyncio.run(main())
\""
}

verify_push_landed() {
  local count
  count=$(psql_q "SELECT count(*) FROM energy_availability WHERE provider_name='$PUSH_TEST_PROVIDER';")
  if [ "${count:-0}" -eq 0 ]; then
    echo "${RED}Didn't land - check ENABLE_GRID_POLLING/GRID_API_URL on the app deployment, or that $APP_PYTHON exists in the pod.${RESET}"
    return
  fi
  echo "${GREEN}Landed.${RESET}"
  run "confirm in the DB" \
    "psql_pretty \"SELECT provider_name, slot_start_time, slot_end_time, available_watts, data_source
     FROM energy_availability WHERE provider_name='$PUSH_TEST_PROVIDER' ORDER BY slot_start_time;\""
  run "confirm via GET /current/active" \
    "curl -s $APP_URL/api/energy-availability/current/active | jq '.availability[] | select(.provider_name==\"$PUSH_TEST_PROVIDER\")'"
  run "confirm via GET /future/forecast" \
    "curl -s $APP_URL/api/energy-availability/future/forecast | jq '.availability[] | select(.provider_name==\"$PUSH_TEST_PROVIDER\")'"
}

reset_grid_stub_test_data() {
  run "cleanup: reset the stub to empty and delete the test rows" \
    "curl -s -X POST $GRID_STUB_URL/capacity -H 'Content-Type: application/json' -d '{\"availability\": []}' >/dev/null; \
     psql_q \"DELETE FROM energy_availability WHERE provider_name='$PUSH_TEST_PROVIDER';\""
  PUSHED_TO_STUB=false
}

demo_push_supply_and_verify_it_lands() {
  print_scenario_header 2 "Push test grid capacity in, watch it land in the DB" \
    "Why: GridPollingScheduler doesn't accept pushes directly - it PULLS from
whatever GRID_API_URL points at, on a fixed interval (GRID_POLL_INTERVAL_SECONDS,
default 300s). On this cluster that's the dev/test grid-stub
(charts/app/files/grid_stub.py), which exposes POST /capacity (set data) and
GET /capacity (read it back). We push fake capacity there, then trigger ONE
poll cycle immediately via 'kubectl exec' - calling GridPollingScheduler's own
fetch_grid_capacity()/_store_slots() methods directly inside the running pod,
using the real app code - instead of waiting out the full 300s interval or
restarting the pod (which would kill the app's port-forward). Same code path
the real background loop uses, just invoked once, on demand."

  show_existing_supply_baseline
  push_test_capacity_to_grid_stub
  trigger_grid_poll_now
  verify_push_landed
  pause
  reset_grid_stub_test_data
  pause
}

# ---------------------------------------------------------------------------
# Scenario 3 - Predicted supply + gap detection (fully dynamic, no hardcoded dates)
# ---------------------------------------------------------------------------
find_missing_buckets() {
  # Echoes the space-separated list of 6h buckets (0-3) with zero real
  # history for $PROVIDER. Empty output means no gap.
  local covered
  covered=$(psql_q "SELECT DISTINCT (extract(hour from slot_start_time)::int / 6) FROM energy_availability WHERE record_type='supply' AND data_source='real' AND provider_name='$PROVIDER';")
  local missing=()
  for b in 0 1 2 3; do
    grep -qx "$b" <<< "$covered" || missing+=("$b")
  done
  echo "${missing[@]:-}"
}

warn_if_now_is_in_a_gap() {
  local missing="$1"
  [ -z "$missing" ] && { echo "${GREEN}No permanently-blind bucket right now for provider=$PROVIDER - every bucket has at least one real sample.${RESET}"; return; }

  local labels=("00-06" "06-12" "12-18" "18-24")
  echo "${RED}Permanently-blind bucket(s) for provider=$PROVIDER: ${RESET}"
  for b in $missing; do
    echo "  - ${labels[$b]} UTC  (never predicted, on any day, until real data lands there)"
  done

  local now_bucket
  now_bucket=$(( 10#$(date -u +%H) / 6 ))
  if grep -qx "$now_bucket" <<< "$(tr ' ' '\n' <<< "$missing")"; then
    echo
    echo "${RED}Right now ($(date -u +%H):00 UTC) falls inside that gap.${RESET}"
    run "current/active right now" "curl -s $APP_URL/api/energy-availability/current/active | jq"
    echo "${YELLOW}This empty/missing result is the model's structural limitation caught live,${RESET}"
    echo "${YELLOW}not a stalled scheduler - see Scenario 4 for proof the scheduler is still ticking.${RESET}"
  fi
}

show_forecast_gap_in_placeholder_model() {
  print_scenario_header 3 "Predicted supply, and checking for gaps in the placeholder model" \
    "Why: PredictionService buckets real history into four 6-hour slots-of-day
(00-06, 06-12, 12-18, 18-24) and predicts a future slot only if its bucket
has ANY real history - otherwise it's skipped, never guessed at. A bucket
with zero real samples is a PERMANENT blind spot, every day, forever.
This step checks live whether provider '$PROVIDER' currently has one."

  run "real history hours for provider=$PROVIDER" \
    "psql_pretty \"SELECT slot_start_time, available_watts, extract(hour from slot_start_time) AS hour
     FROM energy_availability WHERE record_type='supply' AND data_source='real' AND provider_name='$PROVIDER' ORDER BY slot_start_time;\""

  echo
  echo "${DIM}Deriving which of the four 6-hour buckets have zero real history...${RESET}"
  warn_if_now_is_in_a_gap "$(find_missing_buckets)"
  pause
}

# ---------------------------------------------------------------------------
# Scenario 4 - Real-over-predicted precedence (dynamic slot, self-cleaning)
# ---------------------------------------------------------------------------
insert_precedence_test_rows() {
  current_slot_bounds
  PRECEDENCE_TEST_SLOT_START="$CURRENT_SLOT_START"
  PRECEDENCE_TEST_SLOT_END="$CURRENT_SLOT_END"

  echo "Current slot (computed): $CURRENT_SLOT_START -> $CURRENT_SLOT_END"
  echo
  run "baseline: what's covering now, before we insert anything" \
    "curl -s $APP_URL/api/energy-availability/current/active | jq '.count'"

  run "insert a TEST real-supply row for the current slot" \
    "psql_q \"INSERT INTO energy_availability (provider_name, slot_start_time, slot_end_time, available_watts, forecast_date, record_type, data_source, energy_source_type, confidence_percentage) VALUES ('$PROVIDER', '$CURRENT_SLOT_START', '$CURRENT_SLOT_END', 1234.0, '$CURRENT_SLOT_DAY', 'supply', 'real', 'solar', 90) ON CONFLICT DO NOTHING;\""
  run "confirm it shows up" \
    "curl -s $APP_URL/api/energy-availability/current/active | jq '.availability[] | {data_source, available_watts}'"

  run "now also insert a TEST predicted row for the SAME slot, different wattage" \
    "psql_q \"INSERT INTO energy_availability (provider_name, slot_start_time, slot_end_time, available_watts, forecast_date, record_type, data_source, energy_source_type, confidence_percentage) VALUES ('$PROVIDER', '$CURRENT_SLOT_START', '$CURRENT_SLOT_END', 500.0, '$CURRENT_SLOT_DAY', 'supply', 'predicted', 'solar', 90) ON CONFLICT DO NOTHING;\""
  run "both rows genuinely exist in the DB now" \
    "psql_pretty \"SELECT data_source, available_watts FROM energy_availability WHERE provider_name='$PROVIDER' AND slot_start_time='$CURRENT_SLOT_START';\""
  run "but the API only ever returns the real one" \
    "curl -s $APP_URL/api/energy-availability/current/active | jq '.availability[] | {data_source, available_watts}'"

  echo
  echo "${GREEN}Expect: only {\"data_source\": \"real\", \"available_watts\": 1234} - never the predicted 500, never both.${RESET}"
}

cleanup_precedence_test_rows() {
  run "cleanup: delete both test rows" \
    "psql_q \"DELETE FROM energy_availability WHERE provider_name='$PROVIDER' AND slot_start_time='$PRECEDENCE_TEST_SLOT_START' AND slot_end_time='$PRECEDENCE_TEST_SLOT_END';\""
  PRECEDENCE_TEST_SLOT_START=""
  PRECEDENCE_TEST_SLOT_END=""
  run "confirm cleanup" "curl -s $APP_URL/api/energy-availability/current/active | jq '.count'"
}

demo_real_beats_predicted_for_same_slot() {
  print_scenario_header 4 "Real supply wins over predicted for the same slot" \
    "Why: _prefer_real_supply() must collapse a slot that has both a real and a
predicted row down to just the real one, so a caller never double-counts.
We prove this live with one temporary, reversible test insert for the
CURRENT slot (computed dynamically), then delete it immediately after."

  insert_precedence_test_rows
  pause
  cleanup_precedence_test_rows
  pause
}

# ---------------------------------------------------------------------------
# Scenario 5 - Demand reporting + resolution
# ---------------------------------------------------------------------------
show_demand_reporting_and_resolution() {
  print_scenario_header 5 "Demand reporting and resolution" \
    "Why: energy-aware-operator reports each CR's demand as a rolling
forecast - the current slot plus the next several predefined slots (1 day
ahead) - via POST /api/energy-availability/demand/batch, one row per
(identifier, slot). A Scheduled (not-yet-running) workload reports 0W for
slots before its own start slot, then its real required wattage from
there on, so a consumer sees exactly when the draw begins, not just that
it eventually will."

  run "demand forecast rows in the DB, per workload" \
    "psql_pretty \"SELECT provider_name, slot_start_time, slot_end_time, available_watts FROM energy_availability WHERE record_type='demand' ORDER BY provider_name, slot_start_time;\""
  echo
  run "$CRITICAL_CR status.energyMetrics" \
    "kubectl get eao $CRITICAL_CR -n $NAMESPACE -o jsonpath='{.status.energyMetrics}'; echo"
  run "$OPTIONAL_CR status.energyMetrics" \
    "kubectl get eao $OPTIONAL_CR -n $NAMESPACE -o jsonpath='{.status.energyMetrics}'; echo"

  echo
  echo "${BOLD}Now readable externally via the GET /demand endpoint${RESET}"
  echo "${DIM}(e.g. a grid operator querying this to know what demand to plan supply for, today and tomorrow)${RESET}"
  run "all current + future demand, across every workload" \
    "curl -s $APP_URL/api/energy-availability/demand | jq '.demand[] | {provider_name, slot_start_time, slot_end_time, available_watts}'"
  run "filtered to one workload - its full forecast curve" \
    "curl -s \"$APP_URL/api/energy-availability/demand?identifier=$NAMESPACE/$OPTIONAL_CR\" | jq '.demand[] | {slot_start_time, slot_end_time, available_watts}'"
  pause
}

# ---------------------------------------------------------------------------
# Scenario 6 - Critical vs Optional decision logic
# ---------------------------------------------------------------------------
show_priority_decision_logic() {
  print_scenario_header 6 "Critical vs. Optional decision logic" \
    "Why: Critical should bypass the energy check entirely; Optional should
evaluate a future slot's availability against the requirement."

  run "$CRITICAL_CR decision" \
    "kubectl get eao $CRITICAL_CR -n $NAMESPACE -o jsonpath='{.status.decision}'; echo"
  run "$OPTIONAL_CR decision" \
    "kubectl get eao $OPTIONAL_CR -n $NAMESPACE -o jsonpath='{.status.decision}'; echo"
  pause
}

# ---------------------------------------------------------------------------
# End-to-end - forced live reconcile
# ---------------------------------------------------------------------------
force_reconcile_and_observe_full_cycle() {
  print_scenario_header "E2E" "One full cycle, forced and observed live" \
    "Why: trigger a real reconcile on a live CR and watch every layer respond,
in order - metrics -> demand -> forecast -> decision -> CR status."

  run "baseline lastUpdated" \
    "kubectl get eao $OPTIONAL_CR -n $NAMESPACE -o jsonpath='{.status.lastUpdated}'; echo"
  run "force reconcile" \
    "kubectl annotate eao $OPTIONAL_CR -n $NAMESPACE force-reconcile=\"\$(date +%s)\" --overwrite"
  echo "${DIM}(waiting a few seconds for the operator to pick it up...)${RESET}"
  sleep 8
  run "lastUpdated after" \
    "kubectl get eao $OPTIONAL_CR -n $NAMESPACE -o jsonpath='{.status.lastUpdated}'; echo"
  run "decision recomputed" \
    "kubectl get eao $OPTIONAL_CR -n $NAMESPACE -o jsonpath='{.status.decision}'; echo"

  echo
  echo "${GREEN}Expect: lastUpdated timestamp bumped to just now - proof the reconcile${RESET}"
  echo "${GREEN}genuinely ran (not cached), pulling live data through the whole chain.${RESET}"
  pause
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
echo "${BOLD}Energy-Aware Orchestrator - Live End-to-End Demo${RESET}"
echo "See E2E_DEMO.md for the narrative writeup this script mirrors."
pause

preflight
prompt_scenario_choice
run_selected_scenario

echo
echo "${BOLD}${GREEN}Demo complete.${RESET}"
