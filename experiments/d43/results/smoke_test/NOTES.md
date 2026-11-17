# Smoke test of the gate path (2026-11-17, kind-sample, namespace d43-smoke)

Zero-CPU `sleep` pod; Preferred EAO CR, energyConsumption 84 W;
OrchestrationProfile with energy awareness on.

| UTC | Event | Source |
|---|---|---|
| 15:10:32 | Synthetic supply visible in EMS: current slot 75.6 W (Feed A only), 18:00 slot 336 W | EMS `/future/forecast` |
| ~15:10:41 | EAO decision `Scheduled`, slot 18:00Z, currentSlotAvailableWatts 75.6 | CR status |
| 15:10:45 | Pod rejected: "energy gate: ... held until 2026-11-17T18:00:00Z" | pod PodScheduled condition |
| 15:11:10 | Feed B restored (current slot 168 W) pushed to grid-stub | harness |
| ~15:11:41 | EAO decision `DeployImmediately`, currentSlotAvailableWatts 168 (+31 s) | CR status (polled every 3 s) |
| 15:16:16 | Pod scheduled on sample-worker | pod PodScheduled condition |

Finding: the EAO reacted within one reconcile interval (30 s) + one grid poll
(15 s), but the held pod was only retried ~5.5 min after its rejection - the
scheduler re-queues unschedulable pods on cluster events or on its periodic
flush, and an EAO CR status change is not such an event. Nothing else
was set up to retry the pod sooner.
