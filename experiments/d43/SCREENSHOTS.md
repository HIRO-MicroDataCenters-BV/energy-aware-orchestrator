# Screenshots to capture (runs of 2026-11-17)

Run S1-S3 starts at **17:15:00 UTC (18:15 CET)** and ends at 18:20 UTC (19:20 CET).

| Phase | UTC | CET | Synthetic supply (current slot) |
|---|---|---|---|
| S1 normal | 17:15-17:30 | 18:15-18:30 | 168 W (Feed A 75.6 + Feed B 92.4) |
| S2 contingency (Feed B lost) | 17:30-17:50 | 18:30-18:50 | 75.6 W (45 %) |
| S3a recovery | 17:50-18:00 | 18:50-19:00 | 168 W |
| S3b surplus slot (next 6 h slot) | 18:00-18:20 | 19:00-19:20 | 336 W |

Planned submissions (seed 42): o1-optional 17:24:08, p2-preferred 17:24:54,
c2-critical 17:32:20, o2-optional 17:33:08, p3-preferred 17:37:09,
p4-preferred 17:44:44, o3-optional 17:53:32 UTC.

## Grafana (open a port-forward first)

```
kubectl --context kind-sample -n default port-forward svc/energy-metrics-grafana 3000:80
```
Then open the links below at http://localhost:3000 (Grafana 10.4.1, Explore
view, Prometheus datasource). Kepler instance 172.18.0.3 = sample-worker2,
172.18.0.4 = sample-worker.

| # | When to take it | What | Link |
|---|---|---|---|
| G1 | any time after 17:56 UTC | Kepler-estimated power **per pod** in namespace d43, 17:20-17:55 UTC (contingency 17:30-17:50) | [G1](http://localhost:3000/explore?schemaVersion=1&orgId=1&panes=%7B%22a%22%3A%7B%22datasource%22%3A%22prometheus%22%2C%22queries%22%3A%5B%7B%22refId%22%3A%22A%22%2C%22datasource%22%3A%7B%22type%22%3A%22prometheus%22%2C%22uid%22%3A%22prometheus%22%7D%2C%22expr%22%3A%22sum%20by%20%28pod_name%29%20%28rate%28kepler_container_joules_total%7Bcontainer_namespace%3D%5C%22d43%5C%22%7D%5B2m%5D%29%29%22%2C%22legendFormat%22%3A%22%7B%7Bpod_name%7D%7D%22%2C%22range%22%3Atrue%2C%22editorMode%22%3A%22code%22%7D%5D%2C%22range%22%3A%7B%22from%22%3A%221794936000000%22%2C%22to%22%3A%221794938100000%22%7D%7D%7D) |
| G2 | any time after 17:56 UTC | Same window, d43 power **per node** (by Kepler instance) | [G2](http://localhost:3000/explore?schemaVersion=1&orgId=1&panes=%7B%22a%22%3A%7B%22datasource%22%3A%22prometheus%22%2C%22queries%22%3A%5B%7B%22refId%22%3A%22A%22%2C%22datasource%22%3A%7B%22type%22%3A%22prometheus%22%2C%22uid%22%3A%22prometheus%22%7D%2C%22expr%22%3A%22label_replace%28sum%20by%20%28instance%29%20%28rate%28kepler_container_joules_total%7Bcontainer_namespace%3D%5C%22d43%5C%22%7D%5B2m%5D%29%29%2C%20%5C%22node%5C%22%2C%20%5C%22%241%5C%22%2C%20%5C%22instance%5C%22%2C%20%5C%22%28.%2A%29%3A9102%5C%22%29%22%2C%22legendFormat%22%3A%22Kepler%20on%20%7B%7Bnode%7D%7D%22%2C%22range%22%3Atrue%2C%22editorMode%22%3A%22code%22%7D%5D%2C%22range%22%3A%7B%22from%22%3A%221794936000000%22%2C%22to%22%3A%221794938100000%22%7D%7D%7D) |
| G3 | after 18:22 UTC | Whole EAO run per pod, 17:12-18:22 UTC (shows the Optional jobs starting at 18:00) | [G3](http://localhost:3000/explore?schemaVersion=1&orgId=1&panes=%7B%22a%22%3A%7B%22datasource%22%3A%22prometheus%22%2C%22queries%22%3A%5B%7B%22refId%22%3A%22A%22%2C%22datasource%22%3A%7B%22type%22%3A%22prometheus%22%2C%22uid%22%3A%22prometheus%22%7D%2C%22expr%22%3A%22sum%20by%20%28pod_name%29%20%28rate%28kepler_container_joules_total%7Bcontainer_namespace%3D%5C%22d43%5C%22%7D%5B2m%5D%29%29%22%2C%22legendFormat%22%3A%22%7B%7Bpod_name%7D%7D%22%2C%22range%22%3Atrue%2C%22editorMode%22%3A%22code%22%7D%5D%2C%22range%22%3A%7B%22from%22%3A%221794935520000%22%2C%22to%22%3A%221794939720000%22%7D%7D%7D) |
| G4 | after 18:22 UTC | Stock dashboard "Kepler Container Energy Metrics Dashboard", namespace=d43, panel "Power Consumption Rate (Watts) by Container" (legend shows container name `burn` for every pod) | [G4](http://localhost:3000/d/kepler-container-energy/?orgId=1&var-namespace=d43&var-container=All&from=1794935520000&to=1794939720000) |
| G0 | optional, any time | S0 baseline per pod, 18:22-19:32 UTC (run 18:25-19:30, contingency 18:40-19:00), for side-by-side comparison | [G0](http://localhost:3000/explore?schemaVersion=1&orgId=1&panes=%7B%22a%22%3A%7B%22datasource%22%3A%22prometheus%22%2C%22queries%22%3A%5B%7B%22refId%22%3A%22A%22%2C%22datasource%22%3A%7B%22type%22%3A%22prometheus%22%2C%22uid%22%3A%22prometheus%22%7D%2C%22expr%22%3A%22sum%20by%20%28pod_name%29%20%28rate%28kepler_container_joules_total%7Bcontainer_namespace%3D%5C%22d43%5C%22%7D%5B2m%5D%29%29%22%2C%22legendFormat%22%3A%22%7B%7Bpod_name%7D%7D%22%2C%22range%22%3Atrue%2C%22editorMode%22%3A%22code%22%7D%5D%2C%22range%22%3A%7B%22from%22%3A%221794939720000%22%2C%22to%22%3A%221794943920000%22%7D%7D%7D) |

Use the Graph view with the legend visible. Add "Kepler estimate, kind testbed" in the caption.

## Terminal: captured automatically, screenshot whenever convenient

`scripts/capture_terminal.sh` runs the three commands below at fixed times
and saves each output verbatim, with the command lines and a `date -u`
header, to `results/S1-S3_eao/terminal/`:
`T1_contingency_1747UTC.txt`, `T2a_recovery_1756UTC.txt`,
`T2b_recovery_1759UTC.txt`, `T3_surplus_1805UTC.txt`, `T4_end_1819UTC.txt`.
Show one with `cat <file>` and screenshot it. The S0 baseline captures
(same commands, no EAO CRs) are `results/S0_baseline/terminal/S0_contingency_1847UTC.txt`
(during S0's contingency window, 18:40-19:00 UTC) and `S0_end_1929UTC.txt`.

What each capture shows (checked after the run):

- **T1 (17:47:30 UTC, contingency, 75.6 W).** c1/c2 are `DeployImmediately` and Running. p3/p4 are `Scheduled` (postponed) and o1/o2 are `Scheduled` (deferred), all for 18:00. All 8 of their pods are Pending/`Unschedulable`. p1/p2 also show `Scheduled`, although their Jobs had already completed: the operator keeps re-evaluating finished workloads. Say so in the caption.
- **T2a (17:56:30) and T2b (17:59:30), recovery, 168 W.** All four Preferred are back to `DeployImmediately`, and the p3/p4 pods are Running (started 17:52:32). o1/o2/o3 are still `Scheduled` for 18:00, with their 6 pods `Unschedulable`.
- **T3 (18:05:30), surplus slot, 336 W.** Everything is `DeployImmediately`, and all 6 Optional pods are Running (started 18:00:34-35). No pods are Pending.
- **T4 (18:19:30), end of the run.**

`SLOT_START` keeps the last scheduled slot even after the action switches to
`DeployImmediately`. It is a stale status field, not a new decision.

The commands for each capture:

```
kubectl --context kind-sample -n d43 get eao -o custom-columns='NAME:.metadata.name,PRIORITY:.spec.priority,REQUIRED_W:.spec.energyConsumption,ACTION:.status.decision.action,SLOT_START:.status.decision.scheduledSlot.slotStart,AVAILABLE_W:.status.energyMetrics.currentSlotAvailableWatts'
kubectl --context kind-sample -n d43 get pods -o wide
kubectl --context kind-sample -n d43 get pods --field-selector=status.phase=Pending -o custom-columns='POD:.metadata.name,SCHEDULED:.status.conditions[?(@.type=="PodScheduled")].status,REASON:.status.conditions[?(@.type=="PodScheduled")].reason'
```

Note: the scheduler's rejection message for a held pod begins with the
scheduler plugin's internal name. That is why the third command shows only
the reason (`Unschedulable`), not the message. Use
`kubectl --context kind-sample -n d43 describe pod <pod> | tail -5` only if the
plugin name may appear in the deliverable.
