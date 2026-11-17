"""
Drives one D4.3 simulation run on the kind-sample cluster.

  S0   baseline: default kube-scheduler, no EAO CRs, no energy gate.
  EAO  S1-S3: same workloads; each one gets an EnergyAwareOrchestration CR
       plus an OrchestrationProfile (energy awareness on, rebalancing off)
       and runs through hiro-scheduler, whose energy gate holds pods the
       EAO has deferred. The synthetic supply profile is pushed to the
       grid-stub, from which energy-metric-service polls it.

Every kubectl call is pinned to --context kind-sample. Raw observations go to
<out>/raw/; build_outputs.py turns them into the CSVs.

Usage:
  python run_scenario.py --scenario S0  --out ../results/S0_baseline
  python run_scenario.py --scenario EAO --out ../results/S1-S3_eao --start-at 2026-11-17T17:15:00Z
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

CTX = "kind-sample"
NS = "d43"  # overridable with --namespace (dry runs)
EMS = "/api/v1/namespaces/default/services/energy-metric-service:8000/proxy"
GRID_STUB_POST = (
    "import sys, urllib.request; print(urllib.request.urlopen(urllib.request.Request("
    "'http://localhost:8080/capacity', data=sys.stdin.buffer.read(), "
    "headers={'Content-Type': 'application/json'})).read().decode())"
)
SAMPLE_EVERY_S = 5
SUPPLY_OBS_EVERY_S = 15
IMAGE = "python:3.11-slim"

BURN = """
import multiprocessing as mp, os, time
d = float(os.environ["DURATION_S"])
end = time.time() + d if d > 0 else float("inf")
def burn():
    while time.time() < end:
        pass
ps = [mp.Process(target=burn) for _ in range(int(os.environ["CORES"]))]
[p.start() for p in ps]
[p.join() for p in ps]
"""


def kubectl(*args, stdin=None, check=True):
    cmd = ["kubectl", "--context", CTX, *args]
    res = subprocess.run(cmd, input=stdin, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {res.stderr.strip()}")
    return res.stdout


def apply(obj):
    return kubectl("apply", "-f", "-", stdin=json.dumps(obj))


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


class Run:
    def __init__(self, scenario, out, workloads, profile, t0, boundary):
        self.scenario = scenario
        self.out = out
        self.raw = out / "raw"
        self.raw.mkdir(parents=True, exist_ok=True)
        self.workloads = workloads
        self.profile = profile
        self.t0 = t0
        self.boundary = boundary
        self.end = t0 + timedelta(minutes=profile["run_min"])
        self.log_f = open(self.raw / "harness_log.jsonl", "a")
        self.cmd_f = open(self.raw / "commands.log", "a")

    def log(self, event, **data):
        rec = {"ts": iso(now_utc()), "t_s": round((now_utc() - self.t0).total_seconds(), 1), "event": event, **data}
        self.log_f.write(json.dumps(rec) + "\n")
        self.log_f.flush()
        print(f"[{rec['t_s']:>7}s] {event} {json.dumps(data)[:160]}", flush=True)

    def record_cmd(self, text):
        self.cmd_f.write(f"{iso(now_utc())} {text}\n")
        self.cmd_f.flush()

    # ---------------------------------------------------------------- supply
    def supply_rows(self, phase):
        """Current-slot rows carry the phase's values; slots after the
        boundary carry the fixed forecast. Feed B is always sent explicitly
        (also as 0 W) so its previous value is overwritten, not left behind."""
        rows = []
        cur_start = self.boundary - timedelta(hours=6)
        slots = [(cur_start, self.boundary, phase["feed_a_w"], phase["feed_b_w"])]
        for fs in self.profile["future_slots"]:
            s = self.boundary + timedelta(hours=6 * fs["index"])
            slots.append((s, s + timedelta(hours=6), fs["feed_a_w"], fs["feed_b_w"]))
        for s, e, a, b in slots:
            for feed, w in (("d43-feed-a", a), ("d43-feed-b", b)):
                rows.append({
                    "provider_name": feed,
                    "location": "kind-testbed (synthetic)",
                    "energy_source_type": "synthetic",
                    "slot_start_time": s.isoformat(),
                    "slot_end_time": e.isoformat(),
                    "available_watts": w,
                })
        return rows

    def push_supply(self, phase):
        # Posted from inside the grid-stub pod: the stub needs a
        # Content-Length header, which the API-server service proxy drops.
        body = json.dumps({"availability": self.supply_rows(phase)})
        args = ("-n", "default", "exec", "-i", "deploy/grid-stub", "--", "python", "-c", GRID_STUB_POST)
        self.record_cmd(f"kubectl --context {CTX} {' '.join(args[:-1])} '<post>' <<< '{body}'")
        resp = kubectl(*args, stdin=body)
        self.log("supply_push", phase=phase["name"], feed_a_w=phase["feed_a_w"], feed_b_w=phase["feed_b_w"], resp=resp.strip())

    def observe_supply(self):
        try:
            data = json.loads(kubectl("get", "--raw", f"{EMS}/api/energy-availability/future/forecast?hours_ahead=1&limit=100"))
        except Exception as e:  # observation only - never stop the run for it
            self.log("supply_obs_error", error=str(e))
            return None
        now = now_utc()
        total = 0.0
        rows = []
        for r in data.get("availability", []):
            s = datetime.fromisoformat(r["slot_start_time"])
            e = datetime.fromisoformat(r["slot_end_time"])
            if s <= now < e:
                total += r["available_watts"]
                rows.append((r["provider_name"], r["available_watts"], r["data_source"]))
        self.log("supply_obs", current_slot_total_w=total, rows=rows)
        return total

    # ------------------------------------------------------------- workloads
    def labels(self, w):
        return {"d43/workload": w["name"], "d43/class": w["class"], "d43/scenario": self.scenario}

    def pod_template(self, w):
        spec = {
            "restartPolicy": "Never" if w["kind"] == "Job" else "Always",
            "terminationGracePeriodSeconds": 5,
            "containers": [{
                "name": "burn",
                "image": IMAGE,
                "imagePullPolicy": "IfNotPresent",
                "command": ["python", "-c", BURN],
                "env": [
                    {"name": "DURATION_S", "value": str(w["duration_s"] or 0)},
                    {"name": "CORES", "value": str(w["cores_per_pod"])},
                ],
                "resources": {
                    "requests": {"cpu": str(w["cores_per_pod"]), "memory": "64Mi"},
                    "limits": {"cpu": str(w["cores_per_pod"]), "memory": "128Mi"},
                },
            }],
        }
        if self.scenario == "EAO":
            spec["schedulerName"] = "hiro-scheduler"
        return {"metadata": {"labels": self.labels(w)}, "spec": spec}

    def workload_obj(self, w):
        meta = {"name": w["name"], "namespace": NS, "labels": self.labels(w)}
        if w["kind"] == "Job":
            return {"apiVersion": "batch/v1", "kind": "Job", "metadata": meta, "spec": {
                "backoffLimit": 0, "parallelism": w["pods"], "completions": w["pods"],
                "template": self.pod_template(w)}}
        return {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": meta, "spec": {
            "replicas": w["pods"], "selector": {"matchLabels": {"d43/workload": w["name"]}},
            "template": self.pod_template(w)}}

    def app_ref(self, w):
        return {"apiVersion": "batch/v1" if w["kind"] == "Job" else "apps/v1",
                "kind": w["kind"], "name": w["name"], "namespace": NS}

    def submit(self, w):
        if self.scenario == "EAO":
            apply({"apiVersion": "orchestration.hiro.io/v1alpha1", "kind": "OrchestrationProfile",
                   "metadata": {"name": f"d43-{w['name']}", "labels": self.labels(w)},
                   "spec": {"applicationRef": self.app_ref(w),
                            "placement": {"strategy": "Spread",
                                          "awareness": {"cpu": False, "energy": True, "gpu": False, "memory": False}},
                            "rebalancing": {"enabled": False}}})
            apply({"apiVersion": "eas.hiro.io/v1", "kind": "EnergyAwareOrchestration",
                   "metadata": {"name": w["name"], "namespace": NS, "labels": self.labels(w)},
                   "spec": {"priority": w["class"], "energyConsumption": w["energy_consumption_w"],
                            "forecastWindowDays": 1, "applicationRef": self.app_ref(w)}})
            self.log("eao_cr_created", workload=w["name"], cls=w["class"], energy_w=w["energy_consumption_w"])
            # The workload is submitted only once the EAO has decided, so the
            # gate never sees a pod whose CR has no decision yet.
            decision = None
            for _ in range(60):
                st = json.loads(kubectl("get", "eao", w["name"], "-n", NS, "-o", "json")).get("status") or {}
                decision = (st.get("decision") or {}).get("action")
                if decision:
                    break
                time.sleep(1)
            self.log("eao_first_decision", workload=w["name"], action=decision,
                     reason=(st.get("decision") or {}).get("reason"),
                     slot_start=((st.get("decision") or {}).get("scheduledSlot") or {}).get("slotStart"),
                     current_slot_available_w=(st.get("energyMetrics") or {}).get("currentSlotAvailableWatts"))
        apply(self.workload_obj(w))
        self.log("workload_submitted", workload=w["name"], cls=w["class"], kind=w["kind"], pods=w["pods"])

    # -------------------------------------------------------------- sampling
    def sample(self):
        pods = json.loads(kubectl("get", "pods", "-n", NS, "-l", "d43/workload", "-o", "json"))["items"]
        crs = []
        if self.scenario == "EAO":
            crs = json.loads(kubectl("get", "eao", "-n", NS, "-o", "json"))["items"]
        rec = {"ts": iso(now_utc()), "t_s": round((now_utc() - self.t0).total_seconds(), 1), "pods": [], "crs": []}
        for p in pods:
            cond = {c["type"]: c for c in p["status"].get("conditions", [])}
            ps = cond.get("PodScheduled", {})
            rec["pods"].append({
                "name": p["metadata"]["name"],
                "workload": p["metadata"]["labels"].get("d43/workload"),
                "phase": p["status"].get("phase"),
                "node": p["spec"].get("nodeName"),
                "scheduled": ps.get("status") == "True",
                "unsched_reason": ps.get("reason") if ps.get("status") != "True" else None,
                "unsched_msg": ps.get("message") if ps.get("status") != "True" else None,
            })
        for c in crs:
            st = c.get("status") or {}
            d = st.get("decision") or {}
            em = st.get("energyMetrics") or {}
            rec["crs"].append({
                "workload": c["metadata"]["name"],
                "action": d.get("action"),
                "reason": d.get("reason"),
                "slot_start": (d.get("scheduledSlot") or {}).get("slotStart"),
                "current_slot_available_w": em.get("currentSlotAvailableWatts"),
                "required_w": em.get("requiredWatts"),
                "measured_w": em.get("measuredWatts"),
                "sufficient": em.get("sufficient"),
                "last_updated": st.get("lastUpdated"),
            })
        with open(self.raw / "samples.jsonl", "a") as f:
            f.write(json.dumps(rec) + "\n")

    # ------------------------------------------------------------------ main
    def run(self):
        meta = {"scenario": self.scenario, "context": CTX, "namespace": NS, "t0": iso(self.t0),
                "boundary": iso(self.boundary), "end": iso(self.end),
                "sample_every_s": SAMPLE_EVERY_S, "image": IMAGE}
        (self.raw / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
        pending_phases = list(self.profile["phases"]) if self.scenario == "EAO" else []

        if self.scenario == "EAO":
            # Initial supply goes in before t0 so the first decision already sees it.
            self.push_supply(pending_phases.pop(0))
            deadline = time.time() + 120
            want = self.profile["phases"][0]["feed_a_w"] + self.profile["phases"][0]["feed_b_w"]
            while time.time() < deadline:
                if abs((self.observe_supply() or 0) - want) < 0.01:
                    break
                time.sleep(5)
            else:
                sys.exit("initial supply did not reach energy-metric-service within 120 s")

        wait = (self.t0 - now_utc()).total_seconds()
        if wait > 0:
            print(f"waiting {wait:.0f} s for t0 {iso(self.t0)}", flush=True)
        while now_utc() < self.t0:  # wall-clock loop, robust to host sleep
            time.sleep(min(2.0, max(0.05, (self.t0 - now_utc()).total_seconds())))
        self.log("run_start", **meta)

        todo = sorted(self.workloads, key=lambda w: w["submit_s"])
        next_sample = next_obs = 0.0
        while now_utc() < self.end:
            t = (now_utc() - self.t0).total_seconds()
            while pending_phases and t >= pending_phases[0]["start_s"]:
                self.push_supply(pending_phases.pop(0))
            while todo and t >= todo[0]["submit_s"]:
                self.submit(todo.pop(0))
            if time.time() >= next_sample:
                self.sample()
                next_sample = time.time() + SAMPLE_EVERY_S
            if self.scenario == "EAO" and time.time() >= next_obs:
                self.observe_supply()
                next_obs = time.time() + SUPPLY_OBS_EVERY_S
            time.sleep(1)

        self.log("run_end")
        self.dump_final()

    def dump_final(self):
        for kind in ("pods", "jobs", "deployments", "events"):
            (self.raw / f"final_{kind}.json").write_text(kubectl("get", kind, "-n", NS, "-o", "json"))
        if self.scenario == "EAO":
            (self.raw / "final_eao.json").write_text(kubectl("get", "eao", "-n", NS, "-o", "json"))
            (self.raw / "final_orchestrationprofiles.json").write_text(
                kubectl("get", "orchestrationprofiles", "-l", "d43/scenario=EAO", "-o", "json"))
            (self.raw / "operator.log").write_text(kubectl(
                "logs", "-n", "default", "deploy/energy-operator-energy-aware-operator",
                f"--since-time={iso(self.t0 - timedelta(minutes=2))}", check=False))
            (self.raw / "ems_demand.json").write_text(kubectl(
                "get", "--raw", f"{EMS}/api/energy-availability/demand?limit=1000", check=False))
        self.log("final_dump_done")


def main():
    global NS
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", choices=["S0", "EAO"], required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--profiles", type=Path, default=Path(__file__).parent.parent / "profiles")
    ap.add_argument("--start-at", help="UTC start time, e.g. 2026-11-17T17:15:00Z (default: now + 30 s)")
    ap.add_argument("--namespace", default=NS, help="experiment namespace (dry runs use another one)")
    ap.add_argument("--boundary-at", help="dry runs only: real 6 h slot boundary to align supply rows to")
    args = ap.parse_args()
    NS = args.namespace

    workloads = json.loads((args.profiles / "workloads.json").read_text())
    profile = json.loads((args.profiles / "supply_profile.json").read_text())
    t0 = (datetime.fromisoformat(args.start_at.replace("Z", "+00:00")) if args.start_at
          else now_utc().replace(microsecond=0) + timedelta(seconds=30))

    boundary = (datetime.fromisoformat(args.boundary_at.replace("Z", "+00:00")) if args.boundary_at
                else t0 + timedelta(minutes=profile["boundary_min"]))
    if args.scenario == "EAO":
        if boundary.hour % 6 or boundary.minute or boundary.second:
            sys.exit(f"EAO run must start {profile['boundary_min']} min before a 6 h UTC boundary; "
                     f"t0={iso(t0)} gives boundary {iso(boundary)}")

    left = kubectl("get", "jobs,deployments,eao", "-n", NS, "-l", "d43/workload", "-o", "name")
    if left.strip():
        sys.exit(f"namespace {NS} still has experiment objects:\n{left}")

    Run(args.scenario, args.out, workloads, profile, t0, boundary).run()


if __name__ == "__main__":
    main()
