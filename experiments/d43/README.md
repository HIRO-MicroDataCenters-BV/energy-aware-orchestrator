# D4.3 simulation runs: Energy-Aware Orchestrator (EAO)

Simulated runs of the EAO under a synthetic, dynamic energy-availability
profile, for Shift2DC deliverable D4.3 ("Data Centre Demonstrator -
Orchestration Contribution"). Results and KPIs: [RESULTS.md](RESULTS.md).
Screenshot instructions: [SCREENSHOTS.md](SCREENSHOTS.md).

Everything runs on the local kind cluster `kind-sample`. Every kubectl/helm
call passes `--context kind-sample`.

## Layout

```
profiles/            workloads.json + supply_profile.json (generated, seed 42)
profiles/dryrun/     3 zero-CPU workloads used to dry-run the harness
config/original/     snapshot of the deployments/values/DB rows before setup
config/              calibration Job manifest, IDs of rows deactivated by setup
scripts/
  setup_cluster.sh   env changes + DB row deactivation + namespace (undo: restore_cluster.sh)
  design.py          seeded workload set + synthetic supply profile
  run_scenario.py    drives one run (S0 or EAO), writes results/<run>/raw/
  cleanup_run.sh     deletes one run's Jobs/Deployments/CRs/profiles
  capture_terminal.sh  saves kubectl output (CRs, pods, held pods) at given UTC times
  build_outputs.py   raw + Prometheus -> CSVs per run
  kpis.py            KPI table from the CSVs only
  plot_figures.py    F1-F5 (PNG, 300 dpi)
results/
  calibration/       Kepler W per busy core
  smoke_test/        gate-path smoke test (zero-CPU pod)
  dryrun/            harness dry run (zero-CPU pods)
  S0_baseline/       default scheduler, no EAO (2026-11-17 18:25-19:30 UTC)
  S0_baseline_run1_INTERRUPTED/  first S0 attempt, host slept; not used (see its NOT_USED_FOR_KPIS.md)
  S1-S3_eao/         EAO + scheduler-plugin energy gate, phases S1/S2/S3 (17:15-18:20 UTC)
  <run>/terminal/    kubectl output captured during the run (scripts/capture_terminal.sh)
  kpis/ figures/
```

Each run folder holds `raw/` (harness samples, final object dumps; large
files gzipped) and the derived CSVs: `timeseries.csv`, `events.csv`,
`pod_events.csv`, `decision_log.csv`, `supply_observed.csv`,
`kepler_pod_power.csv` and `cadvisor_pod_cpu.csv`.

Some raw dumps contain the scheduler plugin's own objects or messages. These
are kept locally and are not in the repository (listed in `.gitignore`), and
the plugin's name is redacted in `raw/samples.jsonl` (RESULTS.md section 8).
Because `build_outputs.py` also needs `raw/final_pods.json` and the run's
Prometheus data, the CSVs in the repository are the published record.

## Reproduce

```bash
cd experiments/d43
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -r requirements.txt
./scripts/setup_cluster.sh
kubectl --context kind-sample apply -f config/calibration-jobs.yaml      # 5 min, then read W/core from Prometheus
.venv/bin/python -I scripts/design.py --watts-per-core 42 --seed 42 --out profiles

# keep the host awake for the whole run (a sleeping laptop freezes the cluster)
caffeinate -i -s -t 14400 &
# the EAO run must start 45 min before a 6 h UTC slot boundary (00/06/12/18 UTC)
.venv/bin/python -I scripts/run_scenario.py --scenario EAO --out results/S1-S3_eao --start-at 2026-11-17T17:15:00Z
./scripts/cleanup_run.sh
.venv/bin/python -I scripts/run_scenario.py --scenario S0 --out results/S0_baseline --start-at 2026-11-17T18:25:00Z
./scripts/cleanup_run.sh

.venv/bin/python -I scripts/build_outputs.py --run results/S0_baseline
.venv/bin/python -I scripts/build_outputs.py --run results/S1-S3_eao
.venv/bin/python -I scripts/kpis.py --baseline results/S0_baseline --eao results/S1-S3_eao --out results/kpis
.venv/bin/python -I scripts/plot_figures.py --baseline results/S0_baseline --eao results/S1-S3_eao \
    --kpis results/kpis/kpis.csv --out results/figures

./scripts/restore_cluster.sh
```

`build_outputs.py` queries Prometheus, so run it while the run's window is
still within Prometheus retention.
