#!/usr/bin/env python3
"""Plot CSV from run_dual_series_parallel_pipeline.py --out-csv."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Dict, List


def _require_plt():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        print("pip install matplotlib", file=sys.stderr)
        sys.exit(1)


def _networks_in_layers(layers: str) -> str:
    nets = []
    for tok in (layers or "").split("|"):
        tok = tok.strip()
        if not tok or ":" not in tok:
            continue
        n = tok.split(":", 1)[0].strip()
        if n and n not in nets:
            nets.append(n)
    return "+".join(nets) if nets else ""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--title", default="")
    args = p.parse_args()

    rows: List[Dict[str, str]] = []
    with open(args.csv, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    by_kind = {r.get("row_kind", ""): r for r in rows}
    path_rows = [r for r in rows if r.get("row_kind") == "path"]
    wall = by_kind.get("wall")
    if len(path_rows) != 2 or wall is None:
        raise SystemExit("CSV must contain two path rows and one wall row")

    plt = _require_plt()
    fig, ax = plt.subplots(1, 1, figsize=(10, 4.2))

    labels = []
    for r in path_rows:
        topo = f"{r.get('acc0','')}→{r.get('acc1','')}"
        nets = _networks_in_layers(r.get("layers", "")) or r.get("network", "")
        labels.append(f"{r['path']}\n{topo}\n{nets}")
    closed = [float(r["makespan_closed"]) for r in path_rows]
    sim = [float(r["makespan_sim"]) for r in path_rows]
    x = [0, 1]
    w = 0.35
    same = all(abs(a - b) <= 1e-9 for a, b in zip(closed, sim)) and (
        abs(float(wall["makespan_closed"]) - float(wall["makespan_sim"])) <= 1e-9
    )
    if same:
        ax.bar(x, sim, width=0.55, label="makespan (sim)", color="#aa5555", alpha=0.88)
        ws = float(wall["makespan_sim"])
        ax.axhline(y=ws, color="#884444", ls="--", lw=1.2, alpha=0.85, label=f"wall (max)={ws:,.0f}")
    else:
        ax.bar([i - w / 2 for i in x], closed, width=w, label="closed-form", color="#5c7c99")
        ax.bar([i + w / 2 for i in x], sim, width=w, label="simulated", color="#aa5555", alpha=0.88)
        wc = float(wall["makespan_closed"])
        ws = float(wall["makespan_sim"])
        ax.axhline(y=wc, color="#222222", ls="--", lw=1.0, alpha=0.7, label=f"wall (closed)={wc:,.0f}")
        ax.axhline(y=ws, color="#884444", ls=":", lw=1.2, alpha=0.8, label=f"wall (sim)={ws:,.0f}")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("makespan (cycles)")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(loc="upper right", fontsize=8)
    if args.title:
        ax.set_title(args.title)
    else:
        # Add a descriptive default title and keep the legend compact.
        ax.set_title("Dual serial pipelines in parallel (4 accelerators)\nTwo-series topology and per-path makespan")

    # If comm columns exist, annotate shared-BW penalty.
    if "comm_cycles_total" in wall and wall.get("comm_cycles_total"):
        try:
            comm_c = float(wall["comm_cycles_total"])
            bw = wall.get("shared_bw_gbps", "")
            ax.text(
                0.02,
                0.02,
                f"Shared-BW comm penalty: {comm_c:,.0f} cycles (shared_bw_gbps={bw})",
                transform=ax.transAxes,
                fontsize=8,
                alpha=0.85,
            )
        except ValueError:
            pass

    fig.tight_layout()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    fig.savefig(args.out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
