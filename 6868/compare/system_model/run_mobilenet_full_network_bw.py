#!/usr/bin/env python3
"""
Full MobileNetV2 sweep: same as run_bw_combos_full_network.py but for MobileNetV2.

Only ``MobileNetV2_kcp_ws_pe256.csv`` exists in-tree. In ``maestro_layer_metrics``,
ShiDianNao_OS and Eyeriss_RS for mobilenet_v2 both read that WS export (proxy). So
combos that pair two different dataflows may use **identical** (L, bw_req) on both
cores for a given layer—interpret results as a **WS-only trace** with placeholder
heterogeneous labels, or run ``RS_WS`` / ``WS_OS`` where one side is WS and the other
is the same file (still models two named cores for allocator bookkeeping).

Layers run serially; within each layer the two jobs run concurrently until done.
"""

from __future__ import annotations

import csv
import os
import sys
from typing import Dict, List, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from compare.system_model.maestro_layer_metrics import layer_latency_and_bw_req, list_mobilenet_v2_layer_order
from compare.system_model.magma_bw_allocator import bw_allocator, make_two_core_combo

COMBOS: Dict[str, Tuple[str, str]] = {
    "OS_RS": ("ShiDianNao_OS", "Eyeriss_RS"),
    "RS_WS": ("Eyeriss_RS", "NVDLA_WS"),
    "WS_OS": ("NVDLA_WS", "ShiDianNao_OS"),
}


def run_layer_combo(layer: str, pair: Tuple[str, str], total_bw: float):
    a, b = pair
    L0, bw0, _, _ = layer_latency_and_bw_req("mobilenet_v2", layer, a)
    L1, bw1, _, _ = layer_latency_and_bw_req("mobilenet_v2", layer, b)
    q = make_two_core_combo(a, L0, bw0, b, L1, bw1)
    return bw_allocator(q, total_bw)


def main() -> None:
    total_bw = float(os.environ.get("SYSTEM_BW", "100.0"))
    which = os.environ.get("FULLNET_COMBO", "ALL").upper()
    out_csv = os.environ.get("MOBILENET_FULLNET_OUT_CSV") or os.environ.get(
        "FULLNET_OUT_CSV"
    )

    pairs: List[Tuple[str, Tuple[str, str]]] = []
    if which == "ALL":
        for key, p in COMBOS.items():
            pairs.append((key, p))
    elif which in COMBOS:
        pairs.append((which, COMBOS[which]))
    else:
        print(f"Unknown FULLNET_COMBO={which!r}. Use OS_RS, RS_WS, WS_OS, or ALL.")
        sys.exit(1)

    layers = list_mobilenet_v2_layer_order()
    print(f"Layers: {len(layers)} (MobileNetV2 MAESTRO export, kcp_ws_pe256)")
    print(f"SYSTEM_BW={total_bw}")
    print(
        "Note: OS/RS metrics are proxied from the WS CSV (single mapping in-tree); "
        "some combos duplicate the same (L, bw_req) on both cores."
    )
    print("")

    rows_for_csv: List[dict] = []

    for combo_name, pair in pairs:
        acc = 0.0
        util_area = 0.0
        for layer in layers:
            res = run_layer_combo(layer, pair, total_bw)
            acc += res.makespan
            util_area += res.bw_util * res.makespan
            rows_for_csv.append(
                {
                    "combo": combo_name,
                    "layer": layer,
                    "makespan": res.makespan,
                    "bw_util": res.bw_util,
                }
            )
        avg_util = util_area / acc if acc > 0 else 0.0
        print(f"Combo {combo_name} ({pair[0]} + {pair[1]})")
        print(f"  serial_full_net_makespan_sum: {acc:,.0f}")
        print(f"  layer_count: {len(layers)}")
        print(f"  bw_util weighted by layer makespan: {avg_util*100:.2f}%")
        print("")

    if out_csv:
        parent = os.path.dirname(out_csv)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["combo", "layer", "makespan", "bw_util"])
            w.writeheader()
            w.writerows(rows_for_csv)
        print(f"Wrote {out_csv}")


if __name__ == "__main__":
    main()
