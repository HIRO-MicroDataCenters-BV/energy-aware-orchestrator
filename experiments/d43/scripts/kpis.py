"""
Computes the D4.3 KPI table from the per-run CSVs only (timeseries.csv,
events.csv, pod_events.csv) - no cluster access, no raw logs.

Windows (minutes from run start, from profiles/supply_profile.json):
normal 0-15, contingency 15-35, recovery 35-45, surplus 45-65.

Usage: python kpis.py --baseline ../results/S0_baseline --eao ../results/S1-S3_eao --out ../results/kpis
"""

import argparse
import json
from pathlib import Path

import pandas as pd

STEP_H = 30 / 3600  # timeseries step in hours


def windows(profile):
    w = {p["name"]: (p["start_s"], p["end_s"]) for p in profile["phases"]}
    w["surplus"] = (profile["boundary_min"] * 60, profile["run_min"] * 60)
    return w


def energy_wh(ts, col, lo, hi):
    sel = ts[(ts.t_s >= lo) & (ts.t_s < hi)]
    return float(sel[col].sum() * STEP_H)


def exceedance(ts, col):
    over = (ts[col] - ts.available_w_profile).clip(lower=0)
    return float(over.sum() * STEP_H), float(100 * (over > 0).mean())


def run_kpis(run_dir, profile):
    ts = pd.read_csv(run_dir / "timeseries.csv")
    ev = pd.read_csv(run_dir / "events.csv")
    pe = pd.read_csv(run_dir / "pod_events.csv")
    run_end = profile["run_min"] * 60
    win = windows(profile)
    k = {}

    # Critical continuity: share of time from first start to run end during
    # which every Critical pod was running (pod_events.csv).
    crit = pe[pe["class"] == "Critical"]
    cont = []
    for _, p in crit.iterrows():
        if pd.isna(p.started_t_s):
            cont.append(0.0)
            continue
        end = p.finished_t_s if pd.notna(p.finished_t_s) else run_end
        cont.append(100 * (min(end, run_end) - p.started_t_s) / (run_end - p.started_t_s))
    k["critical_workloads"] = int((ev["class"] == "Critical").sum())
    k["critical_continuity_pct"] = round(min(cont), 1) if cont else None
    ce = ev[ev["class"] == "Critical"]
    k["critical_admission_delay_s_max"] = float(ce.wait_before_start_s.max())

    pref = ev[ev["class"] == "Preferred"]
    post = pref[pref.decision == "postponed"]
    k["preferred_workloads"] = len(pref)
    k["preferred_postponed"] = len(post)
    k["preferred_mean_deferral_min"] = round(float(post.wait_before_start_s.mean()) / 60, 1) if len(post) else 0.0
    k["preferred_placed_wait_s_mean"] = round(float(pref[pref.decision != "postponed"].wait_before_start_s.mean()), 1)

    opt = ev[ev["class"] == "Optional"]
    k["optional_workloads"] = len(opt)
    k["optional_cancelled"] = int(opt.decision.str.startswith("cancel").sum())
    k["optional_deferred"] = int(opt.decision.str.startswith("deferred").sum())
    k["optional_mean_deferral_min"] = round(float(opt.wait_before_start_s.mean()) / 60, 1)

    for col, tag in (("kepler_total_w", "measured"), ("declared_demand_running_w", "declared")):
        wh, pct = exceedance(ts, col)
        k[f"exceed_{tag}_wh"] = round(wh, 1)
        k[f"exceed_{tag}_pct_time"] = round(pct, 1)
        k[f"peak_excess_{tag}_w"] = round(float((ts[col] - ts.available_w_profile).clip(lower=0).max()), 1)
        k[f"peak_{tag}_w"] = round(float(ts[col].max()), 1)
        lo, hi = win["contingency"]
        k[f"peak_{tag}_contingency_w"] = round(float(ts[(ts.t_s >= lo) & (ts.t_s < hi)][col].max()), 1)
        for name, (lo, hi) in win.items():
            k[f"energy_{tag}_{name}_wh"] = round(energy_wh(ts, col, lo, hi), 1)
            for cls in ("critical", "preferred", "optional"):
                ccol = f"kepler_{cls}_w" if tag == "measured" else f"declared_running_{cls}_w"
                k[f"energy_{tag}_{name}_{cls}_wh"] = round(energy_wh(ts, ccol, lo, hi), 1)
        k[f"energy_{tag}_total_wh"] = round(energy_wh(ts, col, 0, run_end), 1)
    # Model-independent cross-check of the Kepler numbers: CPU core-minutes
    # used by experiment pods per window (cAdvisor, cpu_cores_total).
    for name, (lo, hi) in win.items():
        k[f"cpu_core_min_{name}"] = round(energy_wh(ts, "cpu_cores_total", lo, hi) * 60, 1)
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--eao", type=Path, required=True)
    ap.add_argument("--profiles", type=Path, default=Path(__file__).parent.parent / "profiles")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    profile = json.loads((args.profiles / "supply_profile.json").read_text())

    s0, eao = run_kpis(args.baseline, profile), run_kpis(args.eao, profile)
    for tag in ("measured", "declared"):
        for key in (f"peak_{tag}_w", f"peak_{tag}_contingency_w"):
            eao[f"{key}_reduction_vs_s0_pct"] = round(100 * (1 - eao[key] / s0[key]), 1) if s0[key] else None
        # Energy moved out of the contingency window and into the
        # high-availability windows (recovery + surplus), relative to S0.
        eao[f"shift_{tag}_out_of_contingency_wh"] = round(
            s0[f"energy_{tag}_contingency_wh"] - eao[f"energy_{tag}_contingency_wh"], 1)
        eao[f"shift_{tag}_into_high_availability_wh"] = round(
            (eao[f"energy_{tag}_recovery_wh"] + eao[f"energy_{tag}_surplus_wh"])
            - (s0[f"energy_{tag}_recovery_wh"] + s0[f"energy_{tag}_surplus_wh"]), 1)
        eao[f"shift_{tag}_into_surplus_wh"] = round(eao[f"energy_{tag}_surplus_wh"] - s0[f"energy_{tag}_surplus_wh"], 1)
        eao[f"peak_excess_{tag}_reduction_vs_s0_pct"] = (
            round(100 * (1 - eao[f"peak_excess_{tag}_w"] / s0[f"peak_excess_{tag}_w"]), 1) if s0[f"peak_excess_{tag}_w"] else None)
        eao[f"exceed_{tag}_wh_reduction_vs_s0_pct"] = (
            round(100 * (1 - eao[f"exceed_{tag}_wh"] / s0[f"exceed_{tag}_wh"]), 1) if s0[f"exceed_{tag}_wh"] else None)

    args.out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({"S0_baseline": s0, "S1-S3_eao": eao})
    df.index.name = "kpi"
    df.to_csv(args.out / "kpis.csv")
    print(df.to_string())


if __name__ == "__main__":
    main()
