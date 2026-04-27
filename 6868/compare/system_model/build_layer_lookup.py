#!/usr/bin/env python3
"""
Build a per-layer accelerator lookup table from MAESTRO CSV metrics.

Policies (LOOKUP_POLICY):
  min_latency  — pick dataflow with minimum MAESTRO Runtime (Cycles) on that layer
                 (no shared-bus contention).
  min_makespan — same layer on core0 under candidate dataflow vs a fixed partner on
                 core1; run MAGMA bw_allocator with SYSTEM_BW; pick core0 mapping
                 that minimizes allocator makespan (stalls when total demand > cap).

Env:
  SYSTEM_BW — shared bandwidth cap (same units as MAESTRO Avg BW Req), default 100
  LOOKUP_PARTNER_DATAFLOW — core1 dataflow for min_makespan (default Eyeriss_RS)

Output CSV includes per-accelerator latency + Avg BW Req + traffic; min_makespan
also adds *_makespan_cycles and best_makespan_cycles.
"""

from __future__ import annotations

import csv
import os
import sys
from typing import Dict, List, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from compare.system_model.maestro_layer_metrics import (
    layer_latency_and_bw_req,
    list_resnet50_layer_order,
)
from compare.system_model.magma_bw_allocator import bw_allocator, make_two_core_combo


DATAFLOWS = ["ShiDianNao_OS", "NVDLA_WS", "Eyeriss_RS"]


def main() -> None:
    out_csv = os.environ.get(
        "LOOKUP_OUT_CSV",
        os.path.join(REPO, "compare", "results", "layer_accel_lookup_resnet50.csv"),
    )
    policy = os.environ.get("LOOKUP_POLICY", "min_latency").strip().lower()
    if policy not in ("min_latency", "min_makespan"):
        print("LOOKUP_POLICY must be min_latency or min_makespan.")
        sys.exit(1)

    total_bw = float(os.environ.get("SYSTEM_BW", "100.0"))
    partner = os.environ.get("LOOKUP_PARTNER_DATAFLOW", "Eyeriss_RS").strip()
    if policy == "min_makespan" and partner not in DATAFLOWS:
        print(f"LOOKUP_PARTNER_DATAFLOW must be one of {DATAFLOWS}, got {partner!r}.")
        sys.exit(1)

    layers = list_resnet50_layer_order()
    rows: List[Dict[str, object]] = []

    for layer in layers:
        per: Dict[str, Tuple[float, float]] = {}
        for df in DATAFLOWS:
            L, bw, _, _ = layer_latency_and_bw_req("resnet50", layer, df)
            per[df] = (L, bw)

        per_ms: Dict[str, float] = {}
        if policy == "min_latency":
            best_df = min(DATAFLOWS, key=lambda d: per[d][0])
        else:
            Lp, bwp = per[partner]
            for df in DATAFLOWS:
                L0, bw0 = per[df]
                q = make_two_core_combo(df, L0, bw0, partner, Lp, bwp)
                per_ms[df] = bw_allocator(q, total_bw).makespan
            best_df = min(DATAFLOWS, key=lambda d: per_ms[d])

        best_L, best_bw = per[best_df]

        r: Dict[str, object] = {
            "layer": layer,
            "best_dataflow": best_df,
            "best_latency_cycles": best_L,
            "best_avg_bw_req": best_bw,
            "best_traffic": best_L * best_bw,
        }

        for df in DATAFLOWS:
            L, bw = per[df]
            r[f"{df}_latency_cycles"] = L
            r[f"{df}_avg_bw_req"] = bw
            r[f"{df}_traffic"] = L * bw

        if policy == "min_makespan":
            for df in DATAFLOWS:
                r[f"{df}_makespan_cycles"] = per_ms[df]
            r["best_makespan_cycles"] = per_ms[best_df]
            r["lookup_partner_dataflow"] = partner
            r["lookup_system_bw"] = total_bw

        rows.append(r)

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        fieldnames = [
            "layer",
            "best_dataflow",
            "best_latency_cycles",
            "best_avg_bw_req",
            "best_traffic",
        ]
        if policy == "min_makespan":
            fieldnames.extend(
                [
                    "best_makespan_cycles",
                    "lookup_partner_dataflow",
                    "lookup_system_bw",
                ]
            )
        for df in DATAFLOWS:
            fieldnames.extend(
                [
                    f"{df}_latency_cycles",
                    f"{df}_avg_bw_req",
                    f"{df}_traffic",
                ]
            )
        if policy == "min_makespan":
            for df in DATAFLOWS:
                fieldnames.append(f"{df}_makespan_cycles")
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    extra = ""
    if policy == "min_makespan":
        extra = f", partner={partner}, SYSTEM_BW={total_bw}"
    print(f"Wrote {out_csv} (layers={len(layers)}, policy={policy}{extra})")


if __name__ == "__main__":
    main()

