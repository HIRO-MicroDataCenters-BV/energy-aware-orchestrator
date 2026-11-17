# D4.3: Orchestration contribution, simulated EAO runs

**Status: complete for review. Both runs were done on 2026-11-17. Section 8 lists items for HIRO to check before publishing.**

Everything here comes from runs on a **local kind test cluster**, not from the
Bachmann site. The energy-availability profile is **synthetic**, and power
values are **Kepler estimates**. Each number cites its source: a file in
`results/`, a query or command, or a code location.

## 1. Setup

### Testbed
| Item | Value | Source |
|---|---|---|
| Host | Apple M4 Max laptop, 16 cores, 64 GB RAM | `sysctl machdep.cpu.brand_string hw.ncpu hw.memsize` |
| Container VM | Docker Desktop 29.5.3, 16 vCPU, 46.5 GiB, kernel 6.12.76-linuxkit | `docker info` |
| Cluster | kind v0.31.0 cluster `sample`, Kubernetes v1.35.0, 3 nodes (1 control plane + 2 workers), each reporting 16 CPU / 46.5 GiB. **All three nodes are containers on the same VM and share its 16 vCPUs.** | `kubectl --context kind-sample get nodes -o wide`, `kind version` |

### Components
| Component | Version | Source |
|---|---|---|
| Energy-Aware Operator (Kopf, CRD `eas.hiro.io/v1`) | image `energy-aware-operator:373791e-dirty-e3b0c442`, chart `energy-aware-operator-0.1.0` | `kubectl get pods -o jsonpath=...image`, `helm list` |
| Energy Metric Service (FastAPI + PostgreSQL 14) | image `energy-metric-service:373791e-dirty-e3b0c442`, chart `energy-metric-service-1.0.0` | same |
| Source commit | `development` @ `373791e`. The `-dirty-e3b0c442` tag suffix is the SHA-256 of an empty diff, i.e. no uncommitted changes. | `deploy-full-stack.sh:56`, `printf '' \| shasum -a 256` |
| Scheduler-plugin energy gate | secondary scheduler `hiro-scheduler` (image `hiro-scheduler:verify-k8sv1.35.0`) | `kubectl get pods -A` |
| Kepler | image `quay.io/sustainable_computing_io/kepler:release-0.8.0` | pod image |
| Prometheus | v2.52.0, global scrape interval 60 s (applies to Kepler) | pod image, `prometheus.yml` |
| Grafana | 10.4.1 | pod image |

### Configuration used for the runs (vs. deployed defaults)
| Setting | Deployed | Runs | Why |
|---|---|---|---|
| `KOPF_RECONCILE_INTERVAL_SECONDS` (operator) | 600 | **30** | re-evaluate CRs within the compressed timeline |
| `GRID_POLL_INTERVAL_SECONDS` (EMS) | 300 | **15** | supply changes reach the EMS within 15 s |
| `ENABLE_FORECASTING` (EMS) | true | **false** | no predicted supply rows mixed into the synthetic profile |
| `GRID_MODBUS_HOST` (EMS) | modbus-pdu-stub | **(empty)** | Modbus stub would add 1000 W of supply to every slot |
| active supply rows of `modbus-pdu` for now/future | 9 | **deactivated** (`is_active=false`) | same reason. IDs in `config/deactivated-supply-ids.txt` |

Commands: `scripts/setup_cluster.sh`; undo: `scripts/restore_cluster.sh`;
originals: `config/original/`.

`restore_cluster.sh` was run after both runs (2026-11-17 about 19:45 UTC) and then checked:
- The env lists of both Deployments are identical to `config/original/*.yaml`.
- The 9 `modbus-pdu` rows are active again, and the synthetic `d43-*` supply rows are inactive.
- The grid stub is empty, as it is at start-up.
- Both pods were restarted by the env change.
- The empty namespace `d43` was kept.

## 2. How the EAO decides (from code, `energy-aware-operator/app/services/scheduler.py`)

- **Critical:** always `DeployImmediately`, with no energy check.
- **Preferred:** `DeployImmediately` if the current slot's available supply is at least the CR's `spec.energyConsumption`. Otherwise `Scheduled` into the first future slot (within 24 h) that meets the requirement, falling back to now + 6 h.
- **Optional:** never deploys into the current slot unless it is the slot it committed to on an earlier reconcile. Otherwise `Scheduled` into the highest-supply future slot within 24 h that meets the requirement, falling back to now + 12 h.
- **Slots** are fixed 6 h UTC windows (00/06/12/18). The supply of a slot is the sum of all supply rows (all providers) inside it (`energy_api_client.py:224`).
- **The decision is advisory.** The operator only writes the CR status. A pod is held by the scheduler-plugin energy gate, which rejects a pod while its EAO decision is `Scheduled` and the slot has not started. **Pods that are already running are never stopped.**
- **There is no "cancel" action.** The CRD action enum is `DeployImmediately|Scheduled|Delayed|Waiting`, and the operator emits only the first two (`Waiting` on errors).

## 3. Method

### Time compression
Slot length (6 h), slot numbering and the 24 h horizon are hard-coded, so
neither a compressed 24 h profile nor 1-min slots are possible without code
changes. The runs use real time instead:
- The **current** 6 h slot's supply is changed live through the grid stub (one run = 65 min wall clock = 65 min simulated).
- The EAO run starts 45 min before a real 6 h UTC boundary (18:00 UTC), so the "surplus" window is the EAO's real next slot.

### Synthetic supply profile (`profiles/supply_profile.json`, SYNTHETIC)
Two providers, `d43-feed-a` and `d43-feed-b`, model Feed A and Feed B. Values are
in watts on the same scale as Kepler's per-pod estimates (section 3.4).

| Window (min from start) | Feed A | Feed B | Total |
|---|---|---|---|
| 0-15 normal (S1) | 75.6 W | 92.4 W | 168 W |
| 15-35 contingency, Feed B lost (S2) | 75.6 W | 0 W | 75.6 W (45 %) |
| 35-45 recovery (S3a) | 75.6 W | 92.4 W | 168 W |
| 45-65 next 6 h slot, surplus (S3b) | 168 W | 168 W | 336 W |
| later slots (forecast only) | 75.6 / 75.6 / 75.6 W | 50.4 / 92.4 / 92.4 W | 126 / 168 / 168 W |

### Workload set (`profiles/workloads.json`, seed 42)
- 9 workloads, each a CPU busy loop (`python:3.11-slim`, 1 core per pod, request = limit = 1 CPU):
  - 2 **Critical** Deployments (1 pod each, run until the end);
  - 4 **Preferred** Jobs and 3 **Optional** Jobs (2 pods each, 480 s per pod).
- Submit times are drawn from fixed windows with `random.Random(42)` (`scripts/design.py`).
- `spec.energyConsumption` = pods × 42 W (Critical 42 W, Preferred/Optional 84 W).
- 42 W per busy core is Kepler's estimate from a calibration run (`results/calibration/`: 1-core pod 42.7-42.8 W, 2-core pod 82.4-84.0 W).
- The contingency supply (75.6 W) is deliberately just below one flexible job's requirement (84 W). Section 2 explains why: the EAO compares each job against the total, not against the remaining supply.

### Runs
| Run | Scheduler | EAO | Window (UTC) |
|---|---|---|---|
| S1-S3 (one continuous profile) | `hiro-scheduler` with energy gate | one EAO CR + one OrchestrationProfile (energy awareness on) per workload | 2026-11-17 17:15:00-18:20:00 |
| S0 baseline | default kube-scheduler | none | 2026-11-17 18:25:00-19:30:00 |

S0 uses the same workloads and the same relative submit times. In S0 nothing
reads the supply profile; it is the reference curve in the figures.

A first S0 run (15:22-16:27 UTC) is kept in `results/S0_baseline_run1_INTERRUPTED/`
but **not used**. The laptop went into system sleep during it, which froze
the cluster for about 10 min. The harness log has a gap from t = 2280 s to
2861 s, and one Job ran for 9 min 47 s instead of 8 min (`pmset -g log`;
details in that folder's `NOT_USED_FOR_KPIS.md`). Both runs used in this
report ran under `caffeinate -i -s`, with no sleep events in `pmset -g log`.

## 4. Observed EAO behaviour (S1-S3)

All times are seconds from run start (t0 = 17:15:00 UTC). Sources:
- `harness_log` and `stdout.log`: supply pushes;
- `supply_observed.csv`: the harness polls the EMS every 15 s;
- `decision_log.csv`: CR status changes, from 5 s samples;
- `events.csv` and `pod_events.csv`: pod timestamps from the API server;
- `FailedScheduling` and `Scheduled` events from `hiro-scheduler`. The raw event dump is kept locally and not published (section 8).

| t (s) | UTC | What happened |
|---|---|---|
| 0-596 | 17:15-17:25 | c1 (Critical), p1 and p2 (Preferred): `DeployImmediately`, started within 1-3 s. o1 (Optional, submitted at 549 s): `Scheduled` for the 18:00 slot (336 W). Both its pods were rejected by the energy gate at 550 s. |
| 900.4 | 17:30:00 | **Contingency**: Feed B is set to 0 W, so 75.6 W is left. |
| 922.9 | 17:30:23 | The EMS reports 75.6 W for the current slot. |
| 924.0-929.1 | 17:30:24-29 | p1 and p2 are re-evaluated to `Scheduled` for 18:00 (75.6 W < 84 W). p1 had already completed. **p2's two pods keep running until they finish at 1077 s**, because the EAO does not stop running pods. |
| 1040.7-1043 | 17:32:20-23 | c2 (Critical) is submitted during the contingency and is `DeployImmediately`. Its pod runs 2 s later. |
| 1089-1093 | 17:33 | o2 is `Scheduled` for 18:00, and its pods are held. |
| 1330-1334 | 17:37 | p3 is **postponed**: `Scheduled` for 18:00 ("first sufficient energy slot", 336 W), and its pods are held. |
| 1785-1786 | 17:44:45 | p4 is **postponed** in the same way. |
| 2100.9 | 17:50:01 | **Recovery**: Feed B is restored, back to 168 W. |
| 2119.3-2144.9 | 17:50:19-45 | All four Preferred CRs are back to `DeployImmediately` (168 W >= 84 W). |
| 2251-2252 | 17:52:31-32 | **p3 and p4 pods are scheduled.** That is 151 s after the supply came back and 107 s after the last CR change (scheduler re-queue latency; see section 7). |
| 2313-2314 | 17:53:33 | o3 is submitted and `Scheduled` for 18:00. |
| 2700 | 18:00:00 | The next 6 h slot starts, with 336 W (surplus). |
| 2703.9-2714.2 | 18:00:04-14 | o1, o2 and o3 switch to `DeployImmediately` ("honoring previously committed slot"). |
| 2733-2735 | 18:00:33-35 | **All 6 Optional pods are scheduled**, 33-35 s after the slot boundary. |
| 3214-3215 | 18:08:34 | The Optional Jobs complete. |

**What this shows:**
- The EAO reacts to a supply change within one operator reconcile (30 s in this setup).
- The energy gate held every pod whose CR was `Scheduled`: 5 of 5 workloads, 10 pods, and no pod started early (`events.csv`, `gate_held`).
- Critical workloads were never delayed, not even during the contingency.

## 5. KPIs

All values were computed by `scripts/kpis.py` from `timeseries.csv`, `events.csv` and `pod_events.csv` only. They are listed in full in `results/kpis/kpis.csv`; the key names are shown in the table.

Conventions used throughout:
- **Window:** run start to 65 min, on a 30 s grid (131 samples).
- **Declared:** the sum of `spec.energyConsumption` of workloads with a running pod.
- **Kepler:** `sum by (pod_name)(rate(kepler_container_joules_total{container_namespace="d43"}[2m]))`, mapped to classes.
- **Available:** the synthetic profile.

| KPI | S0 baseline | S1-S3 with EAO | Key in `kpis.csv` |
|---|---|---|---|
| **Critical continuity**: share of time from start to run end that every Critical pod was running | 100 % | 100 % | `critical_continuity_pct` |
| Critical admission delay, submit to container start (max) | 0 s | 2.9 s (c1; includes the harness waiting about 1 s for the EAO decision before creating the Deployment) | `critical_admission_delay_s_max` |
| **Preferred postponed** (of 4) | 0 | 2 (p3, p4) | `preferred_postponed` |
| **Mean deferral of postponed Preferred** | n/a | 11.6 min (p3 15.4 min, p4 7.8 min) | `preferred_mean_deferral_min`, `events.csv` |
| **Optional cancelled** (of 3) | 0 | 0. The EAO has no cancel action. | `optional_cancelled` |
| Optional deferred (of 3), mean deferral | 0 | 3, 23.6 min (o1 36.4, o2 27.4, o3 7.0 min) | `optional_deferred`, `optional_mean_deferral_min` |
| **Demand above availability**, declared: energy | 42.0 Wh | 15.1 Wh (**-64.0 %**) | `exceed_declared_wh` |
| Demand above availability, declared: share of time | 38.9 % | 41.2 % | `exceed_declared_pct_time` |
| Demand above availability, Kepler: energy | 20.4 Wh | 12.9 Wh (**-36.8 %**) | `exceed_measured_wh` |
| Demand above availability, Kepler: share of time | 30.5 % | 30.5 % | `exceed_measured_pct_time` |
| Peak excess over availability, declared / Kepler | 176.4 W / 79.4 W | 92.4 W / 54.1 W (-47.6 % / -31.9 %) | `peak_excess_*_w` |
| **Peak demand in the contingency window**, declared / Kepler | 252 W / 155.0 W | 168 W / 129.7 W (**-33.3 % / -16.3 %**) | `peak_*_contingency_w` |
| Peak demand over the whole run, declared / Kepler | 252 W / 155.0 W | 336 W / 166.8 W (+33.3 % / +7.6 %). The EAO peak falls in the surplus slot, where 336 W is available. | `peak_*_w` |
| Energy in the contingency window, declared / Kepler / CPU core-min | 63.4 Wh / 45.6 Wh / 80.9 | 30.4 Wh / 38.1 Wh / 43.0 | `energy_*_contingency_wh`, `cpu_core_min_contingency` |
| **Energy shifted into the surplus slot** (336 W), declared / Kepler / CPU core-min | 30.8 Wh / 38.3 Wh / 42.1 | 64.4 Wh / 44.8 Wh / 86.0 (**+33.6 Wh** / +6.5 Wh / +43.9) | `shift_*_into_surplus_wh` |
| Energy shifted into recovery + surplus, declared / Kepler | n/a | +40.6 Wh / +6.3 Wh | `shift_*_into_high_availability_wh` |
| Total energy over the run, declared / Kepler | 157.2 Wh / 133.0 Wh | 156.8 Wh / 130.3 Wh | `energy_*_total_wh` |

**Reading the KPIs:**
- **Same work, moved in time.**
  - Total declared energy is unchanged (157.2 vs 156.8 Wh).
  - With the EAO, declared energy in the contingency window halves (63.4 to 30.4 Wh), and declared energy in the surplus slot doubles (30.8 to 64.4 Wh).
  - CPU core-minutes (cAdvisor, independent of Kepler) show the same shift: contingency 80.9 to 43.0, surplus 42.1 to 86.0.
- **What still exceeds supply in the contingency.**
  - p2 was already running when Feed B was lost and was not stopped (no preemption). It finished 3 min into the contingency.
  - After that, the only load was the two Critical workloads: 2 × 42 W = 84 W against 75.6 W. The EAO always admits Critical workloads, so every contingency sample still exceeds supply in both runs.
- **Why exceedance time does not fall.**
  - At recovery the EAO released p3 and p4 together. Each passes its own check (84 W ≤ 168 W). Together with the Critical workloads, the declared demand was 252 W against 168 W for 7 min (14 samples in `S1-S3_eao/timeseries.csv`).
  - In S0 the excess fell into the normal (5.5 min) and contingency (20 min) windows. With the EAO it fell into the contingency (20 min) and recovery (7 min) windows.
  - So the EAO lowers how much demand exceeds supply (-64 % Wh, peak excess -48 %), but not how long. A check against the remaining supply (aggregate admission) would close this gap.
- **Kepler shows the same direction with smaller effects.**
  - Kepler's per-pod split depends on the co-running pods (section 7), which inflates the Critical share whenever fewer pods run.
  - Kepler is also smoothed by the 60 s scrape and the `rate[2m]` window.
  - The declared and CPU-time columns are the more direct measure of what the EAO changed.

## 6. Figures and captions

Files are in `results/figures/` (PNG, 300 dpi, no titles in the images). All
figures come from the local kind testbed with the synthetic supply profile,
not from the Bachmann site.

**F1 (`F1_available_vs_demand.png`): available power vs. demand.**
The synthetic available-power profile (black step: 168 W normal; 75.6 W while Feed B is lost, 15-35 min; 168 W recovery; 336 W in the next 6 h slot from 45 min) is plotted against the demand of the S0 baseline (grey, default scheduler, no EAO) and of S1-S3 with the EAO (purple).
- (a) Declared demand: the sum of `spec.energyConsumption` over workloads with running pods.
- (b) Kepler-estimated power of the experiment pods. These are model estimates, scraped every 60 s with `rate` over 2 min.

The pale red band marks the contingency (Feed B lost) and the pale blue band the surplus slot.
Source: `results/S0_baseline/timeseries.csv`, `results/S1-S3_eao/timeseries.csv`.

**F2 (`F2_power_by_class.png`): Kepler-estimated power by priority class.**
- (a) S0 baseline; (b) S1-S3 with the EAO.
- With the EAO, Optional load is absent from the contingency window. Preferred load is absent once p2 (already running at the supply drop, not preempted) finishes at 18 min.
- Preferred load resumes after recovery, and Optional load runs in the surplus slot. Critical load is never reduced.
- The Critical band rises when fewer pods run because of how Kepler attributes power to pods (section 7), not because Critical pods used more CPU.

Source: `timeseries.csv` (`kepler_<class>_w`).

**F3 (`F3_workload_timeline.png`): workload timeline.**
- Solid bars: workload running (both pods of a Job; the single pod of a Critical Deployment).
- Hatched bars: submitted but held by the scheduler-plugin energy gate, because the EAO decision was `Scheduled`.
- Black tick: submit time. "postponed" marks a Preferred workload, "deferred" an Optional one.
- (a) S0 baseline: every workload starts at submission. (b) S1-S3 with the EAO: p3/p4 are held until 2-3 min after recovery, and o1/o2/o3 until the next slot starts (+34 s).

Source: `events.csv`.

**F4 (`F4_energy_shift.png`): energy per window, S0 vs. EAO, stacked by class.**
- (a) Declared energy (`spec.energyConsumption` × running time); (b) Kepler-estimated energy.
- Totals over the run are nearly equal (declared 157.2 vs 156.8 Wh; Kepler 133.0 vs 130.3 Wh). The EAO moves work out of the contingency window and into the surplus slot; it does not remove work.
- In (b) the Critical share in the contingency window grows with the EAO, although the Critical pods are identical in both runs. Kepler gives each pod more power when fewer pods run (section 7).

Source: `results/kpis/kpis.csv` (`energy_<declared|measured>_<window>_<class>_wh`).

**F5 (`F5_architecture.png`): experiment set-up.**
1. The harness pushes the synthetic Feed A / Feed B profile into a mock grid source (grid stub).
2. The Energy Metric Service polls the stub every 15 s and stores the supply per 6 h slot.
3. The Energy-Aware Operator reconciles every 30 s and writes a decision into each EnergyAwareOrchestration CR.
4. The scheduler-plugin energy gate holds a pod while its decision is `Scheduled` and the slot has not started.
5. Kepler and Prometheus record per-pod power estimates. Dashed arrows: demand reported to the EMS.

Everything runs on one local kind cluster (3 nodes in one Docker VM on a laptop).

## 7. Limitations

- **Testbed is not the site.** Everything runs on a local kind cluster: three Kubernetes nodes in one Docker VM on one laptop. No Bachmann hardware, no DC power path, no Feed A / Feed B.
- **The supply profile is synthetic.** It is pushed to a mock HTTP grid source (`grid-stub`). The EMS's real supply forecasting (`PredictionService`) is a historical-average placeholder and was disabled. No real grid, PV or PDU data is used.
- **Power values are Kepler model estimates.**
  - The host is ARM (Apple M4 Max) inside a VM: no RAPL or hardware energy counters, so Kepler estimates power from a model.
  - Per-pod values summed over all pods (~350 W) exceed Kepler's own node-level estimate (~123 W per node) (`sum by (mode)(rate(kepler_container_joules_total[2m]))` vs `kepler_node_platform_joules_total`, 2026-11-17 15:26 UTC).
  - **Absolute watts are therefore not physical measurements**; only comparisons between runs on the same testbed are meaningful.
  - **A pod's estimate depends on what else is running.** c1-critical used one core the whole time (cAdvisor: 0.93-0.99 cores). Kepler estimated it at 43.3 W while the p1 pods also ran (t = 300-540 s) and at 55.3 W when only c1 and c2 ran (t = 1260-2100 s) (`S1-S3_eao/kepler_pod_power.csv`, `cadvisor_pod_cpu.csv`).
    - Kepler splits a modelled node power across the running containers.
    - So per-class Kepler energy is biased between S0 and EAO: with fewer pods running, the remaining Critical pods look larger.
    - The model-independent comparisons are the declared energy (F4a) and the CPU core-minutes in the KPI table.
  - Prometheus scrapes Kepler every 60 s and the queries use `rate(...[2m])`, so the power curves are smoothed and lag by about 1-2 min.
- **Per-workload threshold.** The EAO compares each workload's `energyConsumption` against the total supply of the slot, not against what is left after other workloads. It does no aggregate admission control, so the sum of admitted demand can exceed supply.
  - In S2 the remaining declared demand was the two Critical workloads alone: 2 × 42 W = 84 W against 75.6 W available. The EAO admits Critical workloads by design, so that excess is not something it can remove.
- **No preemption.** A drop in supply does not stop running workloads, including Preferred and Optional ones. The EAO decision only gates new pods.
- **No cancellation.** Optional workloads are deferred to the best slot, never cancelled.
- **Release latency after recovery.** A held pod is retried only when the scheduler re-queues it: on another cluster event, or on its periodic flush of unschedulable pods. A change of the EAO CR status is not such an event.
  - Measured: 107 s after the last CR change in S1-S3 (section 4), and about 5.5 min in the smoke test (`results/smoke_test/NOTES.md`).
  - No other component was set up to retry held pods, to keep the experiment to the EAO.
- **6 h slot granularity.** It is hard-coded; time compression was done by changing the current slot's supply in real time rather than by shortening slots.
- **Not implemented / not exercised:** energy feedback to the grid or DC power system; demand response signalling to the site; real Feed A/Feed B telemetry (the EMS has a Modbus PDU client, which was not used here).

## 8. Notes for HIRO review before the text goes into D4.3

### Scheduler-plugin details kept out of this report
The energy gate runs in HIRO's scheduler (`hiro-scheduler`) and is switched
on per workload with an OrchestrationProfile. This report describes only the
gate behaviour that the EAO experiment needs. To keep the scheduler plugin's
internals out of the public repository:
- **Kept local, not published:** the raw dumps that contain the plugin's own objects or messages. These are `final_pods.json`, `final_events.json(.gz)` and `final_orchestrationprofiles.json` of the EAO run and the dry run, plus the smoke-test object and event dumps. They are listed in `.gitignore`.
- **Redacted:** the plugin's internal name in the scheduler messages in `raw/samples.jsonl`, replaced by `[scheduler plugin name redacted]`. Rebuilding the CSVs from the redacted file gives byte-identical output.
- **Terminal captures** show only the scheduling reason (`Unschedulable`), not the scheduler's message.

Please confirm with HIRO before any further scheduler-plugin detail goes into the deliverable.

### Findings in the EAO stack (observed, not changed)
1. **Supply double count in the EMS.**
   - `_prefer_real_supply` (`energy-metric-service/app/repositories/energy_availability.py:17`) merges rows only when provider, slot start and slot end are all identical.
   - At setup time, the 12:00-18:00 slot held both a 1000 W `predicted` 6 h row and a 1000 W `real` 5-min row from `modbus-pdu` (`config/original/active-supply-rows.csv`). The two rows have different slot times, so both were kept.
   - The operator sums every supply row in a slot (`energy-aware-operator/app/services/energy_api_client.py:224`), so the slot would count 2000 W. These runs avoided the problem by deactivating the Modbus rows (section 1).
2. **Finished workloads are re-evaluated.** p1-preferred completed at t = 593 s, and its CR was still switched to `Scheduled` at 924 s (`decision_log.csv`). This does no harm, but the CR status of a finished Job no longer describes what happened to it.
3. **Stale `scheduledSlot`.** After switching back to `DeployImmediately`, the CR keeps the earlier `scheduledSlot.slotStart` (terminal captures T2a-T3).
4. **Kubernetes event volume.** Kopf event posting is on (`energy-aware-operator/app/operator.py:160`). During the 65 min EAO run, namespace d43 received 29,759 events with reason `Logging` (raw event dump, kept locally; 9 CRs, 30 s reconcile).
5. **No re-queue on decision change.** A change in the CR status does not trigger a scheduling retry of held pods (section 7, release latency).
