#!/usr/bin/env python3
"""
Full ResNet-50 sweep: run each 2-core MAGMA combo once per layer, then sum makespans.

Unlike run_bw_combos.py (one BW_LAYER, global L from summary_table.csv), this uses
per-layer Runtime (Cycles) and Avg BW Req from the MAESTRO CSVs for each dataflow,
so the stacked time matches the full exported network structure.

Model: layers run back-to-back in CSV order; each layer runs the chosen 2-job combo to
completion before the next layer starts (serial pipeline, two concurrent jobs per layer).
"""

from __future__ import annotations

import csv
import os
import sys
from typing import Dict, List, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from compare.system_model.maestro_layer_metrics import layer_latency_and_bw_req, list_resnet50_layer_order
from compare.system_model.magma_bw_allocator import bw_allocator, make_two_core_combo

COMBOS: Dict[str, Tuple[str, str]] = {
    "OS_RS": ("ShiDianNao_OS", "Eyeriss_RS"),
    "RS_WS": ("Eyeriss_RS", "NVDLA_WS"),
    "WS_OS": ("NVDLA_WS", "ShiDianNao_OS"),
}


def run_layer_combo(layer: str, pair: Tuple[str, str], total_bw: float):
    a, b = pair
    L0, bw0, _, _ = layer_latency_and_bw_req("resnet50", layer, a)
    L1, bw1, _, _ = layer_latency_and_bw_req("resnet50", layer, b)
    q = make_two_core_combo(a, L0, bw0, b, L1, bw1)
    res = bw_allocator(q, total_bw)
    # Approx traffic in MAESTRO BW units: AvgBWReq (elements/cycle) * Runtime (cycles)
    traffic0 = L0 * bw0
    traffic1 = L1 * bw1
    return res, L0, bw0, traffic0, L1, bw1, traffic1


def main() -> None:
    total_bw = float(os.environ.get("SYSTEM_BW", "100.0"))
    which = os.environ.get("FULLNET_COMBO", "ALL").upper()
    out_csv = os.environ.get("FULLNET_OUT_CSV")

    pairs: List[Tuple[str, Tuple[str, str]]] = []
    if which == "ALL":
        for key, p in COMBOS.items():
            pairs.append((key, p))
    elif which in COMBOS:
        pairs.append((which, COMBOS[which]))
    else:
        print(f"Unknown FULLNET_COMBO={which!r}. Use OS_RS, RS_WS, WS_OS, or ALL.")
        sys.exit(1)

    layers = list_resnet50_layer_order()
    print(f"Layers: {len(layers)} (ResNet-50 MAESTRO export)")
    print(f"SYSTEM_BW={total_bw}")
    print("Per-layer L and Avg BW Req from MAESTRO RS/WS/OS CSVs.")
    print("")

    rows_for_csv: List[dict] = []

    for combo_name, pair in pairs:
        acc = 0.0
        util_area = 0.0
        traffic_sum = 0.0
        for layer in layers:
            res, L0, bw0, tr0, L1, bw1, tr1 = run_layer_combo(layer, pair, total_bw)
            acc += res.makespan
            util_area += res.bw_util * res.makespan
            traffic_sum += (tr0 + tr1)
            rows_for_csv.append(
                {
                    "combo": combo_name,
                    "layer": layer,
                    "makespan": res.makespan,
                    "bw_util": res.bw_util,
                    "core0_latency_cycles": L0,
                    "core0_avg_bw_req": bw0,
                    "core0_traffic": tr0,
                    "core1_latency_cycles": L1,
                    "core1_avg_bw_req": bw1,
                    "core1_traffic": tr1,
                    "total_traffic": tr0 + tr1,
                }
            )
        avg_util = util_area / acc if acc > 0 else 0.0
        print(f"Combo {combo_name} ({pair[0]} + {pair[1]})")
        print(f"  serial_full_net_makespan_sum: {acc:,.0f}")
        print(f"  layer_count: {len(layers)}")
        print(f"  bw_util weighted by layer makespan: {avg_util*100:.2f}%")
        print(f"  total_traffic_sum (AvgBWReq*Runtime): {traffic_sum:,.3e}")
        print("")

    if out_csv:
        os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "combo",
                    "layer",
                    "makespan",
                    "bw_util",
                    "core0_latency_cycles",
                    "core0_avg_bw_req",
                    "core0_traffic",
                    "core1_latency_cycles",
                    "core1_avg_bw_req",
                    "core1_traffic",
                    "total_traffic",
                ],
            )
            w.writeheader()
            w.writerows(rows_for_csv)
        print(f"Wrote {out_csv}")


if __name__ == "__main__":
    main()
