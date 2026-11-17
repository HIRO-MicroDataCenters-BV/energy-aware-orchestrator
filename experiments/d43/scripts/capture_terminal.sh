#!/usr/bin/env bash
# Captures the "terminal screenshot" commands at fixed UTC times during the
# EAO run and saves each output verbatim (with the command lines and a UTC
# timestamp) so it can be shown/screenshotted later.
# Usage: capture_terminal.sh <out_dir> <label>@<HH:MM:SS UTC> ...
set -uo pipefail

OUT=$1; shift
mkdir -p "$OUT"
K="kubectl --context kind-sample -n d43"
CMDS=(
  "$K get eao -o custom-columns='NAME:.metadata.name,PRIORITY:.spec.priority,REQUIRED_W:.spec.energyConsumption,ACTION:.status.decision.action,SLOT_START:.status.decision.scheduledSlot.slotStart,AVAILABLE_W:.status.energyMetrics.currentSlotAvailableWatts'"
  "$K get pods -o wide"
  "$K get pods --field-selector=status.phase=Pending -o custom-columns='POD:.metadata.name,SCHEDULED:.status.conditions[?(@.type==\"PodScheduled\")].status,REASON:.status.conditions[?(@.type==\"PodScheduled\")].reason'"
)

for spec in "$@"; do
  label=${spec%@*}; at=${spec#*@}
  target=$(date -u -j -f "%Y-%m-%d %H:%M:%S" "$(date -u +%Y-%m-%d) $at" +%s)
  # wall-clock loop: a single long `sleep` does not count host sleep time
  while [ "$(date -u +%s)" -lt "$target" ]; do sleep 2; done
  f="$OUT/${label}.txt"
  {
    echo "\$ date -u"; date -u
    for c in "${CMDS[@]}"; do echo; echo "\$ $c"; eval "$c" 2>&1; done
  } > "$f"
  echo "captured $f"
done
