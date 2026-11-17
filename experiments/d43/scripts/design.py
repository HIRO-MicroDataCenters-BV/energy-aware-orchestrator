"""
Generates the D4.3 workload set and synthetic supply profile.

Everything is expressed relative to run start (t = 0 s). The run that has
the EAO enabled is started 45 min before a 6 h UTC slot boundary, so the
"surplus" slot of the profile is a real EAO slot (see RESULTS.md, time
compression).

Sizes are in watts as Kepler attributes them to a busy-looping pod on this
testbed (--watts-per-core, from the calibration run), so declared demand
(spec.energyConsumption) and measured power share one scale.

Usage: python design.py --watts-per-core 7.5 --seed 42 --out ../profiles
"""

import argparse
import json
import random
from pathlib import Path

RUN_MIN = 65
BOUNDARY_MIN = 45  # minutes from run start to the next 6 h UTC slot boundary
JOB_DURATION_S = 480
CORES_PER_POD = 1

# (class, kind, pods, submit window in minutes [lo, hi])
WORKLOADS = [
    ("Critical", "Deployment", 1, (0, 0)),
    ("Critical", "Deployment", 1, (17, 30)),   # submitted during the contingency
    ("Preferred", "Job", 2, (1, 4)),
    ("Preferred", "Job", 2, (9, 13)),          # starts before the drop, runs into it
    ("Preferred", "Job", 2, (17, 24)),
    ("Preferred", "Job", 2, (25, 32)),
    ("Optional", "Job", 2, (2, 10)),
    ("Optional", "Job", 2, (17, 30)),
    ("Optional", "Job", 2, (36, 42)),
]

# Phases of the current (pre-boundary) slot, as multiples of one flexible
# job's requirement R (2 pods). Feed A alone (contingency) is 0.9 R, i.e.
# below every Preferred/Optional job's requirement but 45 % of normal supply.
PHASES = [
    # name, start_min, end_min, feed_a (x R), feed_b (x R)
    ("normal", 0, 15, 0.9, 1.1),
    ("contingency", 15, 35, 0.9, 0.0),
    ("recovery", 35, BOUNDARY_MIN, 0.9, 1.1),
]
# Forecast for the slots after the boundary (x R), feed_a + feed_b each.
FUTURE_SLOTS = [
    # name, slot index after boundary (0 = first 6 h slot), feed_a, feed_b
    ("surplus", 0, 2.0, 2.0),
    ("night", 1, 0.9, 0.6),
    ("morning", 2, 0.9, 1.1),
    ("next-afternoon", 3, 0.9, 1.1),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--watts-per-core", type=float, required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    w1 = args.watts_per_core
    counters = {"Critical": 0, "Preferred": 0, "Optional": 0}
    workloads = []
    for cls, kind, pods, (lo, hi) in WORKLOADS:
        counters[cls] += 1
        name = f"{cls[0].lower()}{counters[cls]}-{cls.lower()}"
        submit_s = round(rng.uniform(lo * 60, hi * 60))
        workloads.append({
            "name": name,
            "class": cls,
            "kind": kind,
            "pods": pods,
            "cores_per_pod": CORES_PER_POD,
            "duration_s": None if kind == "Deployment" else JOB_DURATION_S,
            "submit_s": submit_s,
            "energy_consumption_w": round(pods * CORES_PER_POD * w1),
        })
    workloads.sort(key=lambda w: w["submit_s"])

    r = round(2 * CORES_PER_POD * w1)  # requirement of one flexible job
    profile = {
        "description": "SYNTHETIC two-feed supply profile (Feed A / Feed B). Not measured data.",
        "seed": args.seed,
        "watts_per_core": w1,
        "flexible_job_requirement_w": r,
        "run_min": RUN_MIN,
        "boundary_min": BOUNDARY_MIN,
        "phases": [
            {"name": n, "start_s": a * 60, "end_s": b * 60,
             "feed_a_w": round(fa * r, 1), "feed_b_w": round(fb * r, 1)}
            for n, a, b, fa, fb in PHASES
        ],
        "future_slots": [
            {"name": n, "index": i, "feed_a_w": round(fa * r, 1), "feed_b_w": round(fb * r, 1)}
            for n, i, fa, fb in FUTURE_SLOTS
        ],
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "workloads.json").write_text(json.dumps(workloads, indent=2) + "\n")
    (args.out / "supply_profile.json").write_text(json.dumps(profile, indent=2) + "\n")
    for w in workloads:
        print(f"{w['submit_s']:>5}s  {w['name']:<16} {w['kind']:<10} pods={w['pods']} {w['energy_consumption_w']} W")
    for p in profile["phases"]:
        print(p)
    for p in profile["future_slots"]:
        print(p)


if __name__ == "__main__":
    main()
