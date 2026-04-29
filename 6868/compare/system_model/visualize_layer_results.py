#!/usr/bin/env python3
"""
Plot MAESTRO-derived layer results.

Kinds:
  lookup  — from build_layer_lookup.py CSV (per-layer best accelerator + latencies/traffic);
            allocator-aware CSVs also get a cumulative serial-time panel (MAESTRO vs MAGMA makespan).
  traffic — from run_*_full_network*.py CSV: per-layer MAGMA allocator makespan + bw_util, MAESTRO
            total_traffic bars, and cumulative makespan (end-to-end under SYSTEM_BW used in the run).

Optional: --drop-last-n N omits the last N layers from the figure only (CSV unchanged); the footer notes this.

Install: pip install matplotlib

Example (run from the 6868/ project root):

  cd /path/to/6868
  python3 compare/system_model/visualize_layer_results.py --kind lookup \\
    --csv compare/results/layer_accel_lookup_resnet50.csv \\
    --out compare/results/plot_layer_lookup.png
  python3 compare/system_model/visualize_layer_results.py --kind traffic --combo OS_RS \\
    --csv compare/results/full_net_bw_layers.csv \\
    --out compare/results/plot_fullnet_traffic_OS_RS.png
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from typing import Dict, List


def _trim_rows(rows: List[dict], drop_last_n: int, label: str) -> List[dict]:
    if drop_last_n <= 0:
        return rows
    if len(rows) <= drop_last_n:
        print(
            f"{label}: drop_last_n={drop_last_n} but only {len(rows)} row(s); keeping all.",
            file=sys.stderr,
        )
        return rows
    return rows[:-drop_last_n]


def _require_matplotlib():
    try:
        import matplotlib.pyplot as plt  # noqa: F401
        return plt
    except ImportError:
        print("pip install matplotlib", file=sys.stderr)
        sys.exit(1)


def plot_lookup(csv_path: str, out_path: str, title: str, drop_last_n: int = 0) -> None:
    plt = _require_matplotlib()
    rows: List[dict] = []
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    rows = _trim_rows(rows, drop_last_n, "plot_lookup")

    layers = [r["layer"] for r in rows]
    n_layers = len(layers)
    x = list(range(n_layers))
    use_alloc = bool(rows) and ("ShiDianNao_OS_makespan_cycles" in rows[0])
    if use_alloc:
        L_os = [float(r["ShiDianNao_OS_makespan_cycles"]) for r in rows]
        L_ws = [float(r["NVDLA_WS_makespan_cycles"]) for r in rows]
        L_rs = [float(r["Eyeriss_RS_makespan_cycles"]) for r in rows]
        best_L = [float(r["best_makespan_cycles"]) for r in rows]
        y0 = "MAGMA BW makespan (cycles)\ncore0 candidate vs fixed core1 partner"
        t0 = title or "ResNet-50 per-layer shared-BW makespan (core0 mapping)"
        best_lbl = "best (min makespan)"
        choice_lbl = "chosen core0 mapping\n(min allocator makespan)"
    else:
        L_os = [float(r["ShiDianNao_OS_latency_cycles"]) for r in rows]
        L_ws = [float(r["NVDLA_WS_latency_cycles"]) for r in rows]
        L_rs = [float(r["Eyeriss_RS_latency_cycles"]) for r in rows]
        best_L = [float(r["best_latency_cycles"]) for r in rows]
        y0 = "MAESTRO runtime (cycles)"
        t0 = title or "ResNet-50 per-layer MAESTRO latency by dataflow"
        best_lbl = "best (min latency)"
        choice_lbl = "chosen accelerator\n(min latency)"
    best_tr = [float(r["best_traffic"]) for r in rows]
    best_df = [r["best_dataflow"] for r in rows]

    _raw_xt = os.environ.get("LOOKUP_PLOT_MAX_XTICKS", "").strip()
    try:
        _xt_cap = int(_raw_xt) if _raw_xt != "" else n_layers
    except ValueError:
        _xt_cap = n_layers
    want_all_xticks = _raw_xt == "" or _xt_cap >= n_layers
    fig_w = 22 if want_all_xticks else 14
    bottom_h = 1.2 if want_all_xticks else 0.95
    fig = plt.figure(figsize=(fig_w, 11), layout="constrained")
    gs = fig.add_gridspec(4, 1, height_ratios=[2.0, 1.2, 1.05, bottom_h])
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[1, 0], sharex=ax0)
    ax_cum = fig.add_subplot(gs[2, 0], sharex=ax0)
    ax2 = fig.add_subplot(gs[3, 0], sharex=ax0)

    ax0.plot(x, L_os, label="ShiDianNao OS", lw=1.2)
    ax0.plot(x, L_ws, label="NVDLA WS", lw=1.2)
    ax0.plot(x, L_rs, label="Eyeriss RS", lw=1.2)
    ax0.plot(x, best_L, color="black", lw=1.6, linestyle="--", label=best_lbl)
    ax0.set_ylabel(y0)
    ax0.set_title(t0)
    ax0.legend(loc="upper right", fontsize=8)
    ax0.grid(True, alpha=0.25)

    ax1.plot(x, best_tr, color="#2a6f97", lw=1.4)
    ax1.fill_between(x, best_tr, alpha=0.15, color="#2a6f97")
    ax1.set_ylabel("best traffic\n(AvgBWReq×Runtime)")
    ax1.grid(True, alpha=0.25)

    bl_maestro = [float(r["best_latency_cycles"]) for r in rows]
    s_m = 0.0
    cum_m = []
    for v in bl_maestro:
        s_m += v
        cum_m.append(s_m)
    ax_cum.plot(x, cum_m, color="#6a4c93", lw=1.5, label="cumulative MAESTRO runtime\n(same per-layer choices)")
    if use_alloc:
        bm = [float(r["best_makespan_cycles"]) for r in rows]
        s_a = 0.0
        cum_a = []
        for v in bm:
            s_a += v
            cum_a.append(s_a)
        ax_cum.plot(
            x,
            cum_a,
            color="#bc4b51",
            lw=1.6,
            linestyle="--",
            label="cumulative MAGMA makespan\n(shared BW, lookup partner)",
        )
    ax_cum.set_ylabel("cumulative cycles\n(serial layer stack)")
    ax_cum.legend(loc="upper left", fontsize=7)
    ax_cum.grid(True, alpha=0.25)
    # Shared x: only bottom axis shows layer names (avoids 4× repeated overlapping labels).
    ax0.tick_params(axis="x", labelbottom=False)
    ax1.tick_params(axis="x", labelbottom=False)
    ax_cum.tick_params(axis="x", labelbottom=False)

    # Encode best choice as numeric bands for readability
    code = {"ShiDianNao_OS": 0, "NVDLA_WS": 1, "Eyeriss_RS": 2}
    y = [code.get(b, -1) for b in best_df]
    ax2.scatter(x, y, s=10, c="tab:blue", alpha=0.85)
    ax2.set_yticks([0, 1, 2])
    ax2.set_yticklabels(["ShiDianNao OS", "NVDLA WS", "Eyeriss RS"], fontsize=8)
    ax2.set_ylabel(choice_lbl)
    ax2.set_xlabel("layer (CSV order)")
    ax2.grid(True, axis="x", alpha=0.2)

    if _raw_xt == "":
        max_xtick_labels = n_layers
    else:
        max_xtick_labels = max(4, min(n_layers, _xt_cap))
    step = max(1, (n_layers + max_xtick_labels - 1) // max_xtick_labels)
    ticks = list(range(0, n_layers, step))
    ax2.set_xticks(ticks)
    _fs = 3.8 if step == 1 else 5.0
    _rot = 90 if step == 1 else 80
    ax2.set_xticklabels(
        [layers[i] for i in ticks],
        rotation=_rot,
        ha="center",
        fontsize=_fs,
    )
    ax2.tick_params(axis="x", pad=2)
    try:
        fig.set_constrained_pads(h_pad=0.4, hspace=0.12)
    except AttributeError:
        pass

    cnt = Counter(best_df)
    foot = "Layer counts by choice: " + ", ".join(f"{k}={v}" for k, v in sorted(cnt.items()))
    if use_alloc and rows[0].get("lookup_partner_dataflow"):
        foot += (
            f"  |  partner={rows[0]['lookup_partner_dataflow']}"
            f"  SYSTEM_BW={rows[0].get('lookup_system_bw', '')}"
        )
    if drop_last_n:
        foot += f"  |  plot: last {drop_last_n} layer(s) omitted"
    fig.text(0.02, 0.01, foot, fontsize=8)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def plot_traffic(csv_path: str, out_path: str, combo: str, title: str, drop_last_n: int = 0) -> None:
    plt = _require_matplotlib()
    rows: List[dict] = []
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            if r.get("combo", "").strip() == combo:
                rows.append(r)
    if not rows:
        print(f"No rows for combo={combo!r} in {csv_path}", file=sys.stderr)
        sys.exit(1)
    rows = _trim_rows(rows, drop_last_n, "plot_traffic")

    layers = [r["layer"] for r in rows]
    x = list(range(len(layers)))
    tr = [float(r["total_traffic"]) for r in rows]
    cum_tr = []
    s_tr = 0.0
    for v in tr:
        s_tr += v
        cum_tr.append(s_tr)

    has_ms = "makespan" in rows[0] and "bw_util" in rows[0]
    ms = [float(r["makespan"]) for r in rows] if has_ms else []
    util = [float(r["bw_util"]) for r in rows] if has_ms else []
    cum_ms: List[float] = []
    if has_ms:
        s_ms = 0.0
        for v in ms:
            s_ms += v
            cum_ms.append(s_ms)

    fig = plt.figure(figsize=(14, 10), layout="constrained")
    gs = fig.add_gridspec(3, 1, height_ratios=[1.25, 1.35, 1.15])
    ax_ms = fig.add_subplot(gs[0, 0])
    ax_bar = fig.add_subplot(gs[1, 0], sharex=ax_ms)
    ax_c = fig.add_subplot(gs[2, 0], sharex=ax_ms)

    if has_ms:
        (ln_ms,) = ax_ms.plot(
            x, ms, color="#2c5aa0", lw=1.35, marker=".", ms=3, label="makespan (allocator)"
        )
        ax_u = ax_ms.twinx()
        (ln_u,) = ax_u.plot(
            x,
            [u * 100.0 for u in util],
            color="#888888",
            lw=1.0,
            alpha=0.88,
            label="bw_util %",
        )
        ax_ms.set_ylabel("makespan (cycles)\nMAGMA BW allocator", fontsize=9)
        ax_u.set_ylabel("bw_util (%)", fontsize=9, color="#555555")
        ax_u.tick_params(axis="y", labelcolor="#555555")
        ax_ms.legend(handles=[ln_ms, ln_u], loc="upper left", fontsize=7)
    else:
        ax_ms.text(0.5, 0.5, "CSV missing makespan/bw_util", ha="center", va="center", transform=ax_ms.transAxes)
    ax_ms.set_title((title or os.path.basename(csv_path)) + f" — combo {combo}")
    ax_ms.grid(True, alpha=0.25)
    plt.setp(ax_ms.get_xticklabels(), visible=False)

    ax_bar.bar(x, tr, width=0.85, color="#5c7c99", edgecolor="none", label="total_traffic")
    ax_bar.set_ylabel(
        "total_traffic per layer\n(MAESTRO: sum of core AvgBWReq×Runtime)",
        fontsize=9,
    )
    ax_bar.grid(True, axis="y", alpha=0.25)
    plt.setp(ax_bar.get_xticklabels(), visible=False)

    if has_ms:
        (ln_cms,) = ax_c.plot(
            x, cum_ms, color="#8c3b3b", lw=1.65, label="cumulative makespan (serial stack)"
        )
        ax_c.fill_between(x, cum_ms, alpha=0.1, color="#8c3b3b")
    ax_ct = ax_c.twinx()
    (ln_ctr,) = ax_ct.plot(
        x,
        cum_tr,
        color="#3d6e8c",
        lw=1.25,
        alpha=0.9,
        label="cumulative total_traffic",
    )
    ax_c.set_ylabel("cumulative makespan (cycles)", fontsize=9, color="#6b3030")
    ax_c.tick_params(axis="y", labelcolor="#6b3030")
    ax_ct.set_ylabel("cumulative total_traffic", fontsize=9, color="#2d4d63")
    ax_ct.tick_params(axis="y", labelcolor="#2d4d63")
    h_c = [ln_ctr]
    if has_ms:
        h_c.insert(0, ln_cms)
    ax_c.legend(handles=h_c, loc="upper left", fontsize=7)
    ax_c.set_xlabel("layer (CSV order)", fontsize=8)
    ax_c.grid(True, alpha=0.25)

    max_xtick_labels = int(os.environ.get("TRAFFIC_PLOT_MAX_XTICKS", "40"))
    max_xtick_labels = max(2, max_xtick_labels)
    step = max(1, (len(layers) + max_xtick_labels - 1) // max_xtick_labels)
    ticks = list(range(0, len(layers), step))
    ax_c.set_xticks(ticks)
    ax_c.set_xticklabels([layers[i] for i in ticks], rotation=70, ha="right", fontsize=6)

    tail_note = (
        f" Plot omitted last {drop_last_n} layer(s)." if drop_last_n else ""
    )
    fig.text(
        0.02,
        0.01,
        "makespan/bw_util: MAGMA allocator when two MAESTRO jobs share SYSTEM_BW from the generator run. "
        "total_traffic: per-layer demand (no allocator scaling)."
        + tail_note,
        fontsize=7,
    )
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


def main() -> None:
    p = argparse.ArgumentParser(
        epilog=(
            "Run from the 6868/ directory. Example: "
            "cd /path/to/6868 && python3 compare/system_model/visualize_layer_results.py "
            "--kind lookup --csv compare/results/layer_accel_lookup_resnet50.csv "
            "--out compare/results/plot_layer_lookup.png"
        ),
    )
    p.add_argument("--kind", choices=("lookup", "traffic"), required=True)
    p.add_argument("--csv", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--combo", default="OS_RS", help="traffic mode: combo name filter")
    p.add_argument("--title", default="")
    p.add_argument(
        "--drop-last-n",
        type=int,
        default=0,
        metavar="N",
        help="omit the last N layers from the plot (CSV unchanged)",
    )
    args = p.parse_args()

    if args.kind == "lookup":
        plot_lookup(args.csv, args.out, args.title, drop_last_n=args.drop_last_n)
    else:
        plot_traffic(
            args.csv,
            args.out,
            args.combo.strip(),
            args.title,
            drop_last_n=args.drop_last_n,
        )


if __name__ == "__main__":
    main()
