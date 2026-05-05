#!/usr/bin/env python3
"""
Plot results from run_two_group_serial_pipeline.py --out-csv.

Produces a bar chart per segmentation candidate:
  - closed-form makespan
  - simulated makespan
  - Acc0 stall(full) and Acc1 stall(empty) (optional overlay)
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import List


def _require_plt():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        print("pip install matplotlib", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--title", default="")
    args = p.parse_args()

    rows: List[dict] = []
    with open(args.csv, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    if not rows:
        raise SystemExit("Empty CSV")

    plt = _require_plt()

    labels = [f"{r['seg0_depth']}/{r['seg1_depth']}" for r in rows]
    closed = [float(r["makespan_closed"]) for r in rows]
    sim = [float(r["makespan_sim"]) for r in rows]
    stall0 = [float(r.get("acc0_stall_full", "0") or 0) for r in rows]
    stall1 = [float(r.get("acc1_stall_empty", "0") or 0) for r in rows]

    x = list(range(len(rows)))
    w = 0.38

    fig, ax = plt.subplots(1, 1, figsize=(12, 4.6))
    ax.bar([i - w / 2 for i in x], closed, width=w, label="closed-form", color="#5c7c99")
    ax.bar([i + w / 2 for i in x], sim, width=w, label="simulated", color="#aa5555", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Seg0_depth / Seg1_depth")
    ax.set_ylabel("makespan (cycles)")
    ax.grid(True, axis="y", alpha=0.25)

    subtitle = (
        f"{rows[0].get('network','')}  "
        f"Acc0={rows[0].get('acc0_df','')}  Acc1={rows[0].get('acc1_df','')}  "
        f"N={rows[0].get('batches','')}"
    )
    ax.set_title(args.title or f"Two-group serial pipeline — makespan by segmentation\n{subtitle}")
    ax.legend(loc="upper left", fontsize=8)

    # annotate stalls (small text)
    for i in x:
        ax.text(i, max(closed[i], sim[i]) * 0.02, f"stall0={stall0[i]:.0f}\nstall1={stall1[i]:.0f}", ha="center", va="bottom", fontsize=6, alpha=0.85)

    fig.tight_layout()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    fig.savefig(args.out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()

