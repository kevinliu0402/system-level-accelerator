#!/usr/bin/env python3
"""
Plot makespan from simulation CSVs.

Supports:
  - Full-network exports: combo, layer, makespan, bw_util
    (run_bw_combos_full_network.py / run_mobilenet_full_network_bw.py)
  - SCAR exports: scenario_id, domain, makespan, bw_util, job0, job1
    (run_scar_multi_model_bw.py with SCAR_OUT_CSV)

Install: pip install matplotlib

Example:
  FULLNET_OUT_CSV=compare/results/full_net_bw_layers.csv \\
    python3 compare/system_model/run_bw_combos_full_network.py
  python3 compare/system_model/visualize_makespan.py \\
    --csv compare/results/full_net_bw_layers.csv --out compare/results/makespan_resnet.png

  SCAR_OUT_CSV=compare/results/scar.csv python3 compare/system_model/run_scar_multi_model_bw.py
  python3 compare/system_model/visualize_makespan.py --csv compare/results/scar.csv --out scar.png
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple


def _detect_mode(fieldnames: List[str]) -> str:
    s = set(fieldnames)
    if "layer" in s and "combo" in s and "makespan" in s:
        return "fullnet"
    if "scenario_id" in s and "makespan" in s:
        return "scar"
    return "unknown"


def _load_fullnet(path: str) -> Dict[str, List[Tuple[str, float, float]]]:
    by_combo: Dict[str, List[Tuple[str, float, float]]] = defaultdict(list)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            by_combo[row["combo"]].append(
                (
                    row["layer"].strip(),
                    float(row["makespan"]),
                    float(row["bw_util"]),
                )
            )
    return dict(by_combo)


def _load_scar(path: str) -> List[dict]:
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "scenario_id": row["scenario_id"],
                    "domain": row.get("domain", ""),
                    "makespan": float(row["makespan"]),
                    "bw_util": float(row.get("bw_util", 0) or 0),
                    "job0": (row.get("job0") or "").strip(),
                    "job1": (row.get("job1") or "").strip(),
                }
            )
    return rows


def _scar_bar_label(job0: str, job1: str) -> str:
    """
    job* strings look like: resnet50/CONV3_1_2/Eyeriss_RS
    -> readable two-line label for the x axis.
    """
    net_pretty = {
        "resnet50": "ResNet-50",
        "mobilenet_v2": "MobileNetV2",
    }
    df_pretty = {
        "ShiDianNao_OS": "ShiDianNao OS",
        "NVDLA_WS": "NVDLA WS",
        "Eyeriss_RS": "Eyeriss RS",
    }

    def one(tok: str) -> str:
        parts = tok.strip().split("/")
        if len(parts) != 3:
            return tok or "?"
        net, lyr, df = parts
        n = net_pretty.get(net.lower(), net)
        d = df_pretty.get(df, df.replace("_", " "))
        return f"{n}, {lyr}, {d}"

    if not job0 and not job1:
        return ""
    return one(job0) + "\n+ " + one(job1)


def plot_fullnet(
    by_combo: Dict[str, List[Tuple[str, float, float]]],
    out_path: str,
    *,
    cumulative: bool,
    title: str,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("pip install matplotlib", file=sys.stderr)
        sys.exit(1)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True, height_ratios=[2, 1])
    ax0, ax1 = axes

    layer_labels: List[str] | None = None
    for combo in sorted(by_combo.keys()):
        rows = by_combo[combo]
        if layer_labels is None:
            layer_labels = [r[0] for r in rows]
        xs = list(range(len(rows)))
        ms = [r[1] for r in rows]
        us = [r[2] for r in rows]
        if cumulative:
            acc = []
            s = 0.0
            for m in ms:
                s += m
                acc.append(s)
            ms = acc
        ax0.plot(xs, ms, marker=".", ms=4, lw=1.2, label=combo)
        ax1.plot(xs, [u * 100.0 for u in us], marker=".", ms=3, lw=1.0, alpha=0.85, label=combo)

    assert layer_labels is not None
    n = len(layer_labels)
    step = max(1, n // 24)
    tick_pos = list(range(0, n, step))
    ax1.set_xticks(tick_pos)
    ax1.set_xticklabels(
        [layer_labels[i] for i in tick_pos], rotation=75, ha="right", fontsize=5.5
    )
    ax0.set_ylabel("makespan (MAESTRO time units)", fontsize=9)
    ax0.set_title(
        title + (" — cumulative" if cumulative else " — per layer"),
        fontsize=10,
    )
    ax0.legend(loc="upper left", fontsize=7)
    ax0.tick_params(axis="y", labelsize=8)
    ax0.grid(True, alpha=0.3)

    ax1.set_ylabel("bw_util (%)", fontsize=9)
    ax1.set_xlabel("layer", fontsize=8)
    ax1.legend(loc="upper left", fontsize=7)
    ax1.tick_params(axis="both", labelsize=8)
    ax1.grid(True, alpha=0.3)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def plot_scar(rows: List[dict], out_path: str, title: str) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("pip install matplotlib", file=sys.stderr)
        sys.exit(1)

    labels = []
    for r in rows:
        lbl = _scar_bar_label(r.get("job0", ""), r.get("job1", ""))
        if not lbl.strip():
            lbl = r["scenario_id"]
        labels.append(lbl)
    ms = [r["makespan"] for r in rows]
    colors = ["#4477aa" if "datacenter" in r["domain"] else "#cc8844" for r in rows]

    fig, ax = plt.subplots(figsize=(12, 5))
    xpos = range(len(labels))
    ax.bar(xpos, ms, color=colors, edgecolor="black", linewidth=0.4)
    ax.set_xticks(list(xpos))
    ax.set_xticklabels(labels, rotation=0, ha="center", fontsize=5.5)
    ax.set_ylabel("makespan", fontsize=9)
    ax.set_xlabel(
        "Two concurrent jobs (network, layer, dataflow); core 0 / core 1",
        fontsize=7,
    )
    ax.set_title(title, fontsize=10)
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def main() -> None:
    p = argparse.ArgumentParser(description="Plot makespan from simulation CSVs.")
    p.add_argument("--csv", required=True, help="Input CSV path")
    p.add_argument("--out", required=True, help="Output image (.png)")
    p.add_argument(
        "--mode",
        choices=("auto", "fullnet", "scar"),
        default="auto",
        help="CSV format (default: infer from header)",
    )
    p.add_argument(
        "--cumulative",
        action="store_true",
        help="Full-network mode: plot running sum of per-layer makespan per combo",
    )
    p.add_argument("--title", default="", help="Figure title (optional)")
    args = p.parse_args()

    with open(args.csv, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])

    mode = args.mode
    if mode == "auto":
        mode = _detect_mode(list(fieldnames))
    if mode == "unknown":
        print(
            f"Could not infer CSV type from columns: {fieldnames}",
            file=sys.stderr,
        )
        sys.exit(1)

    title = args.title or os.path.basename(args.csv)

    if mode == "fullnet":
        by_combo = _load_fullnet(args.csv)
        if not by_combo:
            print("No rows in CSV", file=sys.stderr)
            sys.exit(1)
        plot_fullnet(by_combo, args.out, cumulative=args.cumulative, title=title)
    else:
        scar_rows = _load_scar(args.csv)
        if not scar_rows:
            print("No rows in CSV", file=sys.stderr)
            sys.exit(1)
        plot_scar(scar_rows, args.out, title=title)


if __name__ == "__main__":
    main()
