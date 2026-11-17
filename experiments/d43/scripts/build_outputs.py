"""
Turns one run's raw observations (<run>/raw/) plus Prometheus data into the
CSV deliverables:

  kepler_pod_power.csv  Kepler-estimated W per pod, 30 s step (long format)
  cadvisor_pod_cpu.csv  CPU cores used per pod (cAdvisor), 30 s step
  pod_events.csv        per pod: node, created/scheduled/started/finished
  events.csv            per workload: submit, EAO decision, start/end, node(s)
  decision_log.csv      every change of an EAO CR's decision during the run
  supply_observed.csv   current-slot supply as seen by energy-metric-service
  timeseries.csv        30 s grid: available vs declared vs Kepler power

Usage: python build_outputs.py --run ../results/S0_baseline
"""

import argparse
import json
import subprocess
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

CTX = "kind-sample"
PROM = "/api/v1/namespaces/default/services/energy-metrics-prometheus-server:80/proxy/api/v1/query_range?"
STEP_S = 30
CLASSES = ["Critical", "Preferred", "Optional"]


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def prom_range(query, start, end, step=STEP_S):
    url = PROM + urllib.parse.urlencode({"query": query, "start": start.timestamp(), "end": end.timestamp(), "step": step})
    out = subprocess.run(["kubectl", "--context", CTX, "get", "--raw", url], capture_output=True, text=True, check=True).stdout
    return json.loads(out)["data"]["result"]


def phase_at(t_s, profile):
    for p in profile["phases"]:
        if p["start_s"] <= t_s < p["end_s"]:
            return p["name"]
    return "surplus" if t_s >= profile["boundary_min"] * 60 else None


def available_at(t_s, profile):
    """Synthetic available power (W) at run-relative time t_s: phase values
    of the current slot until the slot boundary, then the first future
    slot (the surplus window)."""
    for p in profile["phases"]:
        if p["start_s"] <= t_s < p["end_s"]:
            return p["feed_a_w"] + p["feed_b_w"]
    s = profile["future_slots"][0]
    return s["feed_a_w"] + s["feed_b_w"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--profiles", type=Path, default=Path(__file__).parent.parent / "profiles")
    args = ap.parse_args()

    raw = args.run / "raw"
    meta = json.loads((raw / "run_meta.json").read_text())
    workloads = {w["name"]: w for w in json.loads((args.profiles / "workloads.json").read_text())}
    profile = json.loads((args.profiles / "supply_profile.json").read_text())
    scenario = meta["scenario"]
    t0, t_end = ts(meta["t0"]), ts(meta["end"])
    rel = lambda dt: None if dt is None else round((dt - t0).total_seconds(), 1)
    harness = [json.loads(l) for l in (raw / "harness_log.jsonl").read_text().splitlines()]
    samples = [json.loads(l) for l in (raw / "samples.jsonl").read_text().splitlines()]

    # ---------------------------------------------------------------- pods
    pods = json.loads((raw / "final_pods.json").read_text())["items"]
    pod_rows = []
    for p in pods:
        wl = p["metadata"]["labels"].get("d43/workload")
        if wl not in workloads:
            continue
        cond = {c["type"]: c for c in p["status"].get("conditions", [])}
        sched = cond.get("PodScheduled", {})
        cs = (p["status"].get("containerStatuses") or [{}])[0].get("state", {})
        started = (cs.get("running") or cs.get("terminated") or {}).get("startedAt")
        finished = (cs.get("terminated") or {}).get("finishedAt")
        pod_rows.append({
            "scenario": scenario, "workload": wl, "class": workloads[wl]["class"], "pod": p["metadata"]["name"],
            "node": p["spec"].get("nodeName"),
            "created_utc": p["metadata"]["creationTimestamp"],
            "scheduled_utc": sched.get("lastTransitionTime") if sched.get("status") == "True" else None,
            "started_utc": started, "finished_utc": finished,
            "running_at_run_end": finished is None and started is not None,
        })
    pod_df = pd.DataFrame(pod_rows).sort_values(["workload", "pod"])
    for c in ("created", "scheduled", "started", "finished"):
        pod_df[f"{c}_t_s"] = pod_df[f"{c}_utc"].map(lambda s: rel(ts(s)))
    pod_df.to_csv(args.run / "pod_events.csv", index=False)

    # ------------------------------------------------- EAO decisions (samples)
    dec_rows, last = [], {}
    gate_held, gate_msg = {}, {}
    for s in samples:
        for c in s.get("crs", []):
            key = (c["action"], c["slot_start"])
            if last.get(c["workload"]) != key:
                last[c["workload"]] = key
                dec_rows.append({"scenario": scenario, "t_s": s["t_s"], "utc": s["ts"], "workload": c["workload"],
                                 "class": workloads.get(c["workload"], {}).get("class"), "action": c["action"],
                                 "scheduled_slot_start": c["slot_start"],
                                 "current_slot_available_w": c["current_slot_available_w"],
                                 "required_w": c["required_w"], "reason": c["reason"]})
        for p in s["pods"]:
            if p["unsched_msg"] and "energy gate" in p["unsched_msg"]:
                gate_held.setdefault(p["workload"], s["t_s"])
                gate = p["unsched_msg"].split("energy gate: ", 1)[-1].split(". no new claims")[0]
                gate_msg.setdefault(p["workload"], "energy gate: " + gate)
    dec_df = pd.DataFrame(dec_rows, columns=["scenario", "t_s", "utc", "workload", "class", "action", "scheduled_slot_start",
                                             "current_slot_available_w", "required_w", "reason"])
    dec_df.to_csv(args.run / "decision_log.csv", index=False)

    # ------------------------------------------------------------ events.csv
    first_dec = {h["workload"]: h for h in harness if h["event"] == "eao_first_decision"}
    submitted = {}
    for h in harness:
        if h["event"] in ("eao_cr_created", "workload_submitted"):
            submitted.setdefault(h["workload"], h)
    ev_rows = []
    for name, w in sorted(workloads.items(), key=lambda kv: kv[1]["submit_s"]):
        wp = pod_df[pod_df.workload == name]
        sub = submitted.get(name)
        fd = first_dec.get(name, {})
        action = fd.get("action")
        if scenario == "S0":
            decision = "placed (default scheduler, no EAO)"
        elif w["class"] == "Critical" or action == "DeployImmediately":
            decision = "placed"
        elif w["class"] == "Preferred":
            decision = "postponed"
        else:
            decision = "deferred (EAO has no cancel action)"
        changes = dec_df[dec_df.workload == name]
        start_t = wp.started_t_s.min() if len(wp) else None
        if len(wp) and not wp.running_at_run_end.any():
            end_t = wp.finished_t_s.max()
        else:
            end_t = rel(t_end) if len(wp) and start_t is not None else None
        sub_t = rel(ts(sub["ts"])) if sub else None
        ev_rows.append({
            "scenario": scenario, "workload": name, "class": w["class"], "kind": w["kind"], "pods": w["pods"],
            "energy_consumption_w": w["energy_consumption_w"],
            "planned_submit_t_s": w["submit_s"], "submit_utc": sub["ts"] if sub else None, "submit_t_s": sub_t,
            "eao_first_action": action, "eao_first_scheduled_slot": fd.get("slot_start"),
            "eao_first_current_slot_available_w": fd.get("current_slot_available_w"),
            "eao_first_reason": fd.get("reason"),
            "decision": decision,
            "eao_decision_history": ";".join(f"{a}@{t:.0f}s" for a, t in zip(changes.action, changes.t_s)),
            "gate_held": name in gate_held, "gate_first_seen_t_s": gate_held.get(name), "gate_message": gate_msg.get(name),
            "first_pod_scheduled_t_s": wp.scheduled_t_s.min() if len(wp) else None,
            "start_t_s": start_t, "end_t_s": end_t,
            "running_at_run_end": bool(len(wp) and wp.running_at_run_end.any()),
            # API timestamps are whole seconds, so a start can appear up to 1 s before submit; clip at 0.
            "wait_before_start_s": None if start_t is None or sub_t is None else max(0.0, round(start_t - sub_t, 1)),
            "nodes": ";".join(sorted(set(wp.node.dropna()))),
        })
    pd.DataFrame(ev_rows).to_csv(args.run / "events.csv", index=False)

    # ------------------------------------------------------- supply observed
    obs = [{"utc": h["ts"], "t_s": h["t_s"], "current_slot_total_w": h["current_slot_total_w"]}
           for h in harness if h["event"] == "supply_obs"]
    pd.DataFrame(obs, columns=["utc", "t_s", "current_slot_total_w"]).to_csv(args.run / "supply_observed.csv", index=False)

    # ------------------------------------------------------------ Prometheus
    q_start, q_end = t0, t_end + timedelta(minutes=2)
    ns = meta["namespace"]
    pod_to_wl = dict(zip(pod_df.pod, pod_df.workload))
    k_rows = []
    for r in prom_range(f'sum by (pod_name) (rate(kepler_container_joules_total{{container_namespace="{ns}"}}[2m]))', q_start, q_end):
        pod = r["metric"].get("pod_name")
        for t, v in r["values"]:
            wl = pod_to_wl.get(pod)
            k_rows.append({"utc": datetime.fromtimestamp(t, timezone.utc).isoformat(), "t_s": round(t - t0.timestamp()),
                           "pod": pod, "workload": wl, "class": workloads.get(wl, {}).get("class"), "watts": float(v)})
    kdf = pd.DataFrame(k_rows, columns=["utc", "t_s", "pod", "workload", "class", "watts"])
    kdf.to_csv(args.run / "kepler_pod_power.csv", index=False)
    c_rows = []
    for r in prom_range(f'sum by (pod) (rate(container_cpu_usage_seconds_total{{namespace="{ns}",container!=""}}[2m]))', q_start, q_end):
        pod = r["metric"].get("pod")
        for t, v in r["values"]:
            c_rows.append({"utc": datetime.fromtimestamp(t, timezone.utc).isoformat(), "t_s": round(t - t0.timestamp()),
                           "pod": pod, "workload": pod_to_wl.get(pod), "cpu_cores": float(v)})
    cdf = pd.DataFrame(c_rows, columns=["utc", "t_s", "pod", "workload", "cpu_cores"])
    cdf.to_csv(args.run / "cadvisor_pod_cpu.csv", index=False)

    # ------------------------------------------------------------ timeseries
    grid = list(range(0, int((t_end - t0).total_seconds()) + 1, STEP_S))
    obs_df = pd.DataFrame(obs)
    rows = []
    for t in grid:
        row = {"t_s": t, "utc": (t0 + timedelta(seconds=t)).isoformat(), "phase": phase_at(t, profile),
               "available_w_profile": available_at(t, profile)}
        if len(obs_df):
            prior = obs_df[obs_df.t_s <= t]
            row["available_w_observed_ems"] = prior.current_slot_total_w.iloc[-1] if len(prior) else None
        else:
            row["available_w_observed_ems"] = None
        # Declared demand: spec.energyConsumption (the figure the EAO decides
        # on), spread evenly over a workload's pods.
        req = run = 0.0
        run_cls = dict.fromkeys(CLASSES, 0.0)
        for e in ev_rows:
            if e["submit_t_s"] is not None and e["submit_t_s"] <= t and (e["end_t_s"] is None or t < e["end_t_s"]):
                req += e["energy_consumption_w"]
        for _, p in pod_df.iterrows():
            end = p.finished_t_s if pd.notna(p.finished_t_s) else (t_end - t0).total_seconds()
            if pd.notna(p.started_t_s) and p.started_t_s <= t < end:
                w = workloads[p.workload]
                share = w["energy_consumption_w"] / w["pods"]
                run += share
                run_cls[w["class"]] += share
        row["declared_demand_submitted_w"] = req
        row["declared_demand_running_w"] = run
        for c in CLASSES:
            row[f"declared_running_{c.lower()}_w"] = run_cls[c]
        at = kdf[(kdf.t_s == t) & kdf.workload.notna()]
        row["kepler_total_w"] = at.watts.sum()
        for c in CLASSES:
            row[f"kepler_{c.lower()}_w"] = at[at["class"] == c].watts.sum()
        row["cpu_cores_total"] = cdf[(cdf.t_s == t) & cdf.workload.notna()].cpu_cores.sum()
        rows.append(row)
    pd.DataFrame(rows).to_csv(args.run / "timeseries.csv", index=False)
    print(f"wrote CSVs for {scenario} to {args.run}")


if __name__ == "__main__":
    main()
