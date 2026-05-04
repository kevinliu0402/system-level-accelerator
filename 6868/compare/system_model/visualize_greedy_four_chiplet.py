#!/usr/bin/env python3
"""
Plot schedule from run_greedy_four_chiplet.py CSV.

Example:
  cd /path/to/6868
  GREEDY4_OUT_CSV=compare/results/greedy_four_chiplet_schedule.csv \\
    python3 compare/system_model/run_greedy_four_chiplet.py
  python3 compare/system_model/visualize_greedy_four_chiplet.py \\
    --csv compare/results/greedy_four_chiplet_schedule.csv \\
    --out compare/results/greedy_four_chiplet.png

Also supports the windowed+pipelined CSV from run_windowed_pipelined_four_chiplet.py.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Dict, List, Tuple


def _require_plt():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        print("pip install matplotlib", file=sys.stderr)
        sys.exit(1)


def _is_windowed_pipelined(rows: List[dict]) -> bool:
    if not rows:
        return False
    return "row_kind" in rows[0] and "network" in rows[0] and "phase" in rows[0]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--title", default="")
    args = p.parse_args()

    plt = _require_plt()
    rows: List[dict] = []
    with open(args.csv, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    if not rows:
        print("Empty CSV", file=sys.stderr)
        sys.exit(1)

    wp = _is_windowed_pipelined(rows)

    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=False, gridspec_kw={"height_ratios": [1.1, 1.4, 1.0]})
    ax0, ax1, ax2 = axes

    if wp:
        step_rows = [r for r in rows if r.get("row_kind") == "step"]
        phase_rows = [r for r in rows if r.get("row_kind") == "phase"]
        if not step_rows:
            print("No step rows found in CSV", file=sys.stderr)
            sys.exit(1)
    else:
        step_rows = rows
        phase_rows = []

    ends = [float(r["end"]) for r in step_rows]
    steps = [int(r["step"]) for r in step_rows]
    ax0.plot(steps, ends, "o-", color="#6a4c93", lw=1.2, ms=3)
    ax0.set_ylabel("completion time (cycles)")
    ax0.set_title(
        args.title
        or (
            "Windowed+pipelined 4-chiplet (2×WS, 1×OS, 1×RS) — ResNet-50 + MobileNetV2 + SqueezeNet1_0"
            if wp
            else "Greedy 4-chiplet (2×WS, 1×OS, 1×RS) — ResNet-50 + MobileNetV2 + SqueezeNet1_0"
        )
    )
    ax0.grid(True, alpha=0.3)

    # Gantt on chiplets 0..3 (one bar per active network; distinct chiplets per step)
    colors = {0: "#4477aa", 1: "#88aadd", 2: "#cc8844", 3: "#44aa77"}

    if wp:
        # per-phase segments: use alpha to distinguish MEM vs COMP, and per-network alpha tier for readability
        net_alpha = {"resnet50": 0.92, "mobilenet_v2": 0.62, "squeezenet1_0": 0.38}
        phase_alpha = {"mem": 0.95, "comp": 0.55}
        phase_edge = {"mem": "black", "comp": "none"}
        phase_lw = {"mem": 0.25, "comp": 0.0}

        for r in phase_rows:
            try:
                c = int(r["chiplet"])
                start = float(r["start"])
                end = float(r["end"])
            except (KeyError, TypeError, ValueError):
                continue
            if c < 0:
                continue
            dur = max(0.0, end - start)
            net = r.get("network", "")
            ph = r.get("phase", "")
            alpha = net_alpha.get(net, 0.7) * phase_alpha.get(ph, 0.8)
            ax1.broken_barh(
                [(start, dur)],
                (c - 0.35, 0.7),
                facecolors=colors.get(c, "#999999"),
                edgecolor=phase_edge.get(ph, "black"),
                linewidth=phase_lw.get(ph, 0.2),
                alpha=alpha,
            )

        # window boundaries
        epochs: Dict[int, float] = {}
        for r in step_rows:
            try:
                e = int(r.get("epoch", 0))
                te = float(r.get("t_epoch", 0.0))
            except (TypeError, ValueError):
                continue
            epochs[e] = te
        # Window boundaries are times in cycles (t_epoch). Only draw them on ax1 where x is time.
        # Drawing them on ax0 would use step indices as x — mixing cycles into that axis squashes the
        # completion curve and makes markers look clustered at x≈0.
        for te in sorted(set(epochs.values())):
            ax1.axvline(x=te, color="black", lw=0.8, alpha=0.18)
    else:
        # greedy CSV: one row per step; use alpha tiers per network column
        chip_alphas = [
            ("chiplet_resnet", 0.92),
            ("chiplet_mobilenet", 0.62),
            ("chiplet_squeeze", 0.38),
        ]

        def gantt_segments(row: dict) -> List[Tuple[int, float]]:
            """Return (chip_id, alpha) for each active job in this step."""
            mode = row.get("mode", "")
            if mode == "resnet_only":
                c = int(row["chiplet_resnet"])
                return [(c, 0.9)] if c >= 0 else []
            if mode == "mobilenet_only":
                c = int(row["chiplet_mobilenet"])
                return [(c, 0.9)] if c >= 0 else []
            segs: List[Tuple[int, float]] = []
            for col, alpha in chip_alphas:
                if col not in row:
                    continue
                try:
                    c = int(row[col])
                except (TypeError, ValueError):
                    continue
                if c >= 0:
                    segs.append((c, alpha))
            return segs

        for r in step_rows:
            start = float(r["start"])
            end = float(r["end"])
            dur = end - start
            for c, alpha in gantt_segments(r):
                ax1.broken_barh(
                    [(start, dur)],
                    (c - 0.35, 0.7),
                    facecolors=colors[c],
                    edgecolor="black",
                    linewidth=0.2,
                    alpha=alpha,
                )

    ax1.set_yticks([0, 1, 2, 3])
    ax1.set_yticklabels(["WS0", "WS1", "OS", "RS"])
    ax1.set_ylabel("chiplet")
    ax1.set_xlabel("time (cycles)")
    ax1.grid(True, axis="x", alpha=0.25)

    makespan_key = "slice_makespan" if wp else "makespan"
    ms = [float(r[makespan_key]) for r in step_rows]
    util = [float(r["bw_util"]) * 100.0 for r in step_rows]
    ax2.bar(steps, ms, color="#5c7c99", width=0.8, label="step makespan")
    ax2.set_ylabel("makespan (cycles)")
    ax2_t = ax2.twinx()
    ax2_t.plot(steps, util, color="#aa5555", marker=".", ms=4, lw=1, label="bw_util %")
    ax2_t.set_ylabel("bw_util (%)", color="#aa5555")
    ax2.set_xlabel("schedule step")
    ax2.grid(True, axis="y", alpha=0.25)
    h1, l1 = ax2.get_legend_handles_labels()
    h2, l2 = ax2_t.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=7)

    fig.text(
        0.02,
        0.02,
        (
            "Windowed+pipelined: receding-horizon dispatch with MEM/COMP phases; MEM uses MAGMA-style BW allocator, "
            "COMP is BW-free. Window boundaries shown as vertical lines. "
            "2×WS + 1×OS + 1×RS. SqueezeNet uses stub MAESTRO rows."
            if wp
            else "Greedy: each step minimizes slice end time (1–3 concurrent layers on distinct chiplets) under MAGMA allocator; "
            "2×WS + 1×OS + 1×RS. SqueezeNet uses stub MAESTRO rows."
        ),
        fontsize=7,
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
