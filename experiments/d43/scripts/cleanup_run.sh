#!/usr/bin/env bash
# Removes one run's experiment objects (after run_scenario.py has dumped them)
# so the next run starts from an empty namespace. Usage: cleanup_run.sh [namespace]
set -euo pipefail
CTX=kind-sample
NS=${1:-d43}
K="kubectl --context $CTX"
$K -n "$NS" delete jobs,deployments -l d43/workload --wait=true --timeout=120s
$K -n "$NS" delete eao -l d43/workload --wait=true --timeout=120s
$K delete orchestrationprofiles -l "d43/workload" --wait=true --timeout=120s
$K -n "$NS" get pods -l d43/workload
