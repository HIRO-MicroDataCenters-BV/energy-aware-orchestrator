"""
Renders figures F1-F5 (PNG, 300 dpi, no titles; captions live in RESULTS.md)
from the per-run CSVs.

Usage: python plot_figures.py --baseline ../results/S0_baseline --eao ../results/S1-S3_eao --out ../results/figures
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch

# Reference palette (dataviz skill, categorical slots 1-3 validate all-pairs).
CLASS_COLOR = {"Critical": "#2a78d6", "Preferred": "#eb6834", "Optional": "#1baf7a"}
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8985"
S0_COLOR, EAO_COLOR = "#8a8985", "#6250d6"
# Context bands: pale red = Feed B lost, pale blue = surplus slot. Red vs blue
# stays distinct under red-green colour blindness; dashed edges add a second cue.
SHADE, SHADE2, BAND_EDGE = "#f6d6d1", "#d9e7f7", "#9a9893"
BOX_FILL = "#f4f3f0"  # neutral fill for harness-side boxes in F5
CLASSES = ["Critical", "Preferred", "Optional"]

plt.rcParams.update({
    "font.size": 8.5, "axes.labelsize": 8.5, "legend.fontsize": 7.5, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#ecebe8",
    "grid.linewidth": 0.6, "axes.axisbelow": True, "savefig.dpi": 300, "figure.dpi": 100,
    "legend.frameon": False,
})


def windows(profile):
    w = {p["name"]: (p["start_s"] / 60, p["end_s"] / 60) for p in profile["phases"]}
    w["surplus"] = (profile["boundary_min"], profile["run_min"])
    return w


def shade(ax, profile, label=True):
    w = windows(profile)
    lo, hi = w["contingency"]
    ax.axvspan(lo, hi, color=SHADE, lw=0, zorder=0)
    lo2, hi2 = w["surplus"]
    ax.axvspan(lo2, hi2, color=SHADE2, lw=0, zorder=0)
    for x in (lo, hi, lo2):
        ax.axvline(x, color=BAND_EDGE, lw=0.7, ls=(0, (3, 2)), zorder=0.5)
    if label:
        ymax = ax.get_ylim()[1]
        ax.text((lo + hi) / 2, ymax * 0.97, "Feed B lost\n(contingency)", ha="center", va="top", fontsize=7, color=INK2)
        ax.text((lo2 + hi2) / 2, ymax * 0.97, "surplus slot\n(next 6 h slot)", ha="center", va="top", fontsize=7, color=INK2)


def tag(ax, text):
    ax.text(0.0, 1.02, text, transform=ax.transAxes, ha="left", va="bottom", fontsize=8, color=INK, fontweight="bold")


def step_minutes(ts):
    return ts.t_s / 60


def f1(s0, eao, profile, out):
    fig, axes = plt.subplots(2, 1, figsize=(7.0, 5.0), sharex=True)
    for ax, col, label in ((axes[0], "declared_demand_running_w", "a  Declared demand of running workloads (spec.energyConsumption)"),
                           (axes[1], "kepler_total_w", "b  Kepler-estimated power of experiment pods")):
        ax.step(step_minutes(eao), eao.available_w_profile, where="post", color=INK, lw=1.6, label="Available power (synthetic profile)")
        ax.plot(step_minutes(s0), s0[col], color=S0_COLOR, lw=1.6, label="S0 baseline (no EAO)")
        ax.plot(step_minutes(eao), eao[col], color=EAO_COLOR, lw=1.6, label="S1-S3 with EAO")
        ax.set_ylabel("Power (W)")
        ax.set_ylim(0, max(s0[col].max(), eao[col].max(), eao.available_w_profile.max()) * 1.18)
        shade(ax, profile)
        tag(ax, label)
    axes[1].set_xlabel("Time since run start (min)")
    axes[1].set_xlim(0, profile["run_min"])
    axes[0].legend(loc="upper left", bbox_to_anchor=(0.0, 0.86), ncol=1)
    fig.tight_layout()
    fig.savefig(out / "F1_available_vs_demand.png")
    plt.close(fig)


def f2(s0, eao, profile, out):
    fig, axes = plt.subplots(2, 1, figsize=(7.0, 5.0), sharex=True, sharey=True)
    ymax = max(s0.kepler_total_w.max(), eao.kepler_total_w.max(), eao.available_w_profile.max()) * 1.18
    for ax, ts, label in ((axes[0], s0, "a  S0 baseline (default scheduler, no EAO)"), (axes[1], eao, "b  S1-S3 with EAO")):
        ax.stackplot(step_minutes(ts), *[ts[f"kepler_{c.lower()}_w"] for c in CLASSES],
                     colors=[CLASS_COLOR[c] for c in CLASSES], labels=CLASSES, edgecolor="white", linewidth=0.6, alpha=0.95)
        ax.step(step_minutes(eao), eao.available_w_profile, where="post", color=INK, lw=1.6, label="Available power (synthetic)")
        ax.set_ylim(0, ymax)
        ax.set_ylabel("Power (W)")
        shade(ax, profile)
        tag(ax, label)
    axes[1].set_xlabel("Time since run start (min)")
    axes[1].set_xlim(0, profile["run_min"])
    handles, labels = axes[0].get_legend_handles_labels()
    axes[0].legend(handles, labels, loc="upper left", bbox_to_anchor=(0.0, 0.86))
    fig.tight_layout()
    fig.savefig(out / "F2_power_by_class.png")
    plt.close(fig)


def gantt(ax, ev, profile, label):
    ev = ev.sort_values("submit_t_s").reset_index(drop=True)
    for i, e in ev.iterrows():
        y = len(ev) - 1 - i
        c = CLASS_COLOR[e["class"]]
        sub = e.submit_t_s / 60
        if pd.notna(e.start_t_s):
            start, end = e.start_t_s / 60, e.end_t_s / 60
            if start - sub > 0.25:
                ax.barh(y, start - sub, left=sub, height=0.55, color="white", edgecolor=c, hatch="////", linewidth=0.8)
            ax.barh(y, end - start, left=start, height=0.55, color=c, edgecolor="white", linewidth=0.6)
        else:
            ax.barh(y, profile["run_min"] - sub, left=sub, height=0.55, color="white", edgecolor=c, hatch="////", linewidth=0.8)
        ax.plot([sub, sub], [y - 0.38, y + 0.38], color=INK, lw=1.4)
        if isinstance(e.decision, str) and e.decision.startswith(("postponed", "deferred")):
            ax.text(sub - 0.4, y, e.decision.split(" ")[0], ha="right", va="center", fontsize=6.5, color=INK2)
    ax.set_yticks(range(len(ev)))
    ax.set_yticklabels(list(ev.workload)[::-1])
    ax.set_ylim(-0.7, len(ev) - 0.3)
    ax.grid(axis="y", visible=False)
    shade(ax, profile, label=False)
    tag(ax, label)


def f3(s0_ev, eao_ev, profile, out):
    fig, axes = plt.subplots(2, 1, figsize=(7.0, 5.6), sharex=True)
    gantt(axes[0], s0_ev, profile, "a  S0 baseline (default scheduler, no EAO)")
    gantt(axes[1], eao_ev, profile, "b  S1-S3 with EAO")
    axes[1].set_xlabel("Time since run start (min)")
    axes[1].set_xlim(0, profile["run_min"])
    handles = [Patch(color=CLASS_COLOR[c], label=f"{c} (running)") for c in CLASSES]
    handles += [Patch(facecolor="white", edgecolor=INK2, hatch="////", label="Submitted, waiting (postponed/deferred)"),
                Line2D([0], [0], color=INK, lw=1.4, label="Submit time"),
                Patch(color=SHADE, label="Contingency (Feed B lost)"), Patch(color=SHADE2, label="Surplus slot")]
    fig.legend(handles=handles, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(out / "F3_workload_timeline.png")
    plt.close(fig)


def f4(kpis, out):
    order = ["normal", "contingency", "recovery", "surplus"]
    names = {"normal": "Normal\n0-15 min", "contingency": "Contingency\n15-35 min",
             "recovery": "Recovery\n35-45 min", "surplus": "Surplus slot\n45-65 min"}
    # (a) declared energy (spec.energyConsumption x running time) and (b) Kepler
    # estimate side by side: Kepler's per-pod split depends on what else runs.
    fig, axes = plt.subplots(2, 1, figsize=(7.0, 5.6), sharey=True)
    width, gap = 0.36, 0.04
    for ax, tag_, label in ((axes[0], "declared", "a  Declared energy (spec.energyConsumption x running time)"),
                            (axes[1], "measured", "b  Kepler-estimated energy of experiment pods")):
        for wi, w in enumerate(order):
            for si, (scen, lab) in enumerate((("S0_baseline", "S0"), ("S1-S3_eao", "EAO"))):
                x = wi + (si - 0.5) * (width + gap)
                bottom = 0.0
                for c in CLASSES:
                    v = float(kpis.loc[f"energy_{tag_}_{w}_{c.lower()}_wh", scen])
                    ax.bar(x, v, width, bottom=bottom, color=CLASS_COLOR[c], edgecolor="white", linewidth=1.0)
                    bottom += v
                ax.text(x, bottom + 0.6, f"{bottom:.0f}", ha="center", va="bottom", fontsize=7, color=INK)
                ax.text(x, -0.02, lab, ha="center", va="top", fontsize=7, color=INK2, transform=ax.get_xaxis_transform())
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels([names[w] for w in order])
        ax.tick_params(axis="x", pad=14, length=0)
        ax.set_ylabel("Energy (Wh)")
        ax.grid(axis="x", visible=False)
        tag(ax, label)
    axes[0].set_ylim(0, axes[0].get_ylim()[1] * 1.08)
    axes[0].legend(handles=[Patch(color=CLASS_COLOR[c], label=c) for c in CLASSES], loc="upper left")
    fig.tight_layout()
    fig.savefig(out / "F4_energy_shift.png")
    plt.close(fig)


def f5(out):
    fig, ax = plt.subplots(figsize=(7.0, 4.1))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 62)
    ax.axis("off")

    def box(x, y, w, h, title, sub, fill="white"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2",
                                    facecolor=fill, edgecolor=INK2, linewidth=1.0))
        ax.text(x + w / 2, y + h - 2.0, title, ha="center", va="top", fontsize=7.2, color=INK, fontweight="bold")
        ax.text(x + w / 2, y + h - 5.8, sub, ha="center", va="top", fontsize=6.1, color=INK2, linespacing=1.3)

    def arrow(p, q, dashed=False):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=9, color=INK2, lw=0.9,
                                     linestyle=(0, (3, 2)) if dashed else "-"))

    def label(x, y, text, ha="center"):
        ax.text(x, y, text, ha=ha, va="center", fontsize=6, color=INK2,
                bbox=dict(facecolor="white", edgecolor="none", pad=0.6))

    # top row: supply path
    box(0.5, 40, 15, 16, "Synthetic profile", "Feed A + Feed B\nW per 6 h slot\n(JSON, harness)", fill=BOX_FILL)
    box(22, 40, 15, 16, "Grid stub (mock)", "HTTP /capacity;\nstands in for a real\ngrid / PDU source")
    box(43.5, 40, 21, 16, "Energy Metric Service", "polls stub every 15 s\nPostgreSQL\nenergy_availability")
    box(71.5, 40, 28, 16, "Energy-Aware Operator", "EnergyAwareOrchestration CRs,\nreconcile every 30 s:\nCritical / Preferred / Optional")
    arrow((16.1, 50), (21.4, 50))
    label(18.75, 53.5, "push")
    arrow((37.6, 50), (42.9, 50))
    label(40.25, 53.5, "poll")
    arrow((65.1, 51), (70.9, 51))
    label(68.0, 58.6, "supply forecast")
    arrow((70.9, 45), (65.1, 45), dashed=True)
    label(68.0, 37.6, "demand report")

    # bottom row: enforcement + measurement
    box(71.5, 14, 28, 16, "Scheduler-plugin energy gate", "holds a pod while its EAO\ndecision is Scheduled and\nthe slot has not started")
    box(38, 14, 26, 16, "kind cluster (3 nodes)", "experiment Jobs / Deployments\n(CPU busy loops)\nnamespace d43")
    box(0.5, 14, 30, 16, "Kepler + Prometheus", "per-pod power estimates\n(model-based, 60 s scrape)\n+ cAdvisor CPU")
    arrow((85.5, 39.4), (85.5, 30.6))
    label(85.5, 35.0, "CR status.decision")
    arrow((70.9, 22), (64.6, 22))
    label(67.75, 32.4, "admit / hold")
    arrow((37.4, 22), (31.1, 22))
    label(34.25, 32.4, "power")
    arrow((15.5, 30.6), (50, 39.4), dashed=True)
    label(27.5, 36.0, "measured demand")

    box(14, 0.5, 72, 9.5, "Experiment harness (run_scenario.py)",
        "pushes profile phases, submits workloads (EAO CR first, then the Job),\nsamples CR and pod state every 5 s, exports CSVs and figures", fill=BOX_FILL)
    fig.tight_layout()
    fig.savefig(out / "F5_architecture.png")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--eao", type=Path, required=True)
    ap.add_argument("--kpis", type=Path, required=True)
    ap.add_argument("--profiles", type=Path, default=Path(__file__).parent.parent / "profiles")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    profile = json.loads((args.profiles / "supply_profile.json").read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    s0 = pd.read_csv(args.baseline / "timeseries.csv")
    eao = pd.read_csv(args.eao / "timeseries.csv")
    f1(s0, eao, profile, args.out)
    f2(s0, eao, profile, args.out)
    f3(pd.read_csv(args.baseline / "events.csv"), pd.read_csv(args.eao / "events.csv"), profile, args.out)
    f4(pd.read_csv(args.kpis, index_col="kpi"), args.out)
    f5(args.out)
    print(f"figures written to {args.out}")


if __name__ == "__main__":
    main()
