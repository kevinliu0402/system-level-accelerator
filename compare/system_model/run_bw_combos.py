#!/usr/bin/env python3
"""
Run three 2-core combinations:
  - OS with RS
  - RS with WS
  - WS with OS

You must provide req_bw for each dataflow (units: same as total_bw).
Latency is taken from compare/results/summary_table.csv (Timeloop by default).
"""

from __future__ import annotations

import csv
import os
import sys
from typing import Dict, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from compare.system_model.magma_bw_allocator import bw_allocator, make_two_core_combo


SUMMARY = os.path.join(REPO, "compare", "results", "summary_table.csv")


def load_latencies(framework: str = "Timeloop") -> Dict[str, float]:
    """Return latency_cycles by dataflow for a given framework."""
    out: Dict[str, float] = {}
    with open(SUMMARY, "r") as f:
        for r in csv.DictReader(f):
            if r.get("framework") != framework:
                continue
            out[r["dataflow"]] = float(r["latency_cycles"])
    return out


def main():
    # Configure shared BW and per-dataflow required BW.
    total_bw = float(os.environ.get("SYSTEM_BW", "100.0"))
    req_bw = {
        # TODO: replace with your own estimates (GB/s or any consistent unit)
        "ShiDianNao_OS": float(os.environ.get("REQ_BW_OS", "120.0")),
        "NVDLA_WS": float(os.environ.get("REQ_BW_WS", "200.0")),
        "Eyeriss_RS": float(os.environ.get("REQ_BW_RS", "80.0")),
    }
    lat = load_latencies("Timeloop")
    combos = [
        ("ShiDianNao_OS", "Eyeriss_RS"),
        ("Eyeriss_RS", "NVDLA_WS"),
        ("NVDLA_WS", "ShiDianNao_OS"),
    ]

    print(f"Using {SUMMARY}")
    print(f"total_bw={total_bw}")
    print(f"req_bw={req_bw}")
    print("")

    for a, b in combos:
        if a not in lat or b not in lat:
            print(f"Missing latency for {a} or {b}. Run plot_results.py first.")
            continue
        q = make_two_core_combo(
            a, lat[a], req_bw[a],
            b, lat[b], req_bw[b],
        )
        res = bw_allocator(q, total_bw)
        print(f"Combo: {a} + {b}")
        print(f"  makespan: {res.makespan:,.0f} (time units of latency input)")
        print(f"  bw_util:  {res.bw_util*100:.2f}%")
        if res.slices:
            s0 = res.slices[0]
            print(f"  first slice alloc: core0={s0.bw_alloc[0]:.2f}, core1={s0.bw_alloc[1]:.2f}, duration={s0.duration:,.0f}")
        print("")


if __name__ == "__main__":
    main()

