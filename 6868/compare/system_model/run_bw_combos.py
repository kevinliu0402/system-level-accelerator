#!/usr/bin/env python3
"""
Run three 2-core combinations:
  - OS with RS
  - RS with WS
  - WS with OS

Required bandwidth is loaded from MAESTRO per-layer CSV `Avg BW Req` values
instead of hardcoded constants.
Latency (no-stall L) is taken from compare/results/summary_table.csv.
Default framework is MAESTRO so L differs per dataflow; override with
LATENCY_FRAMEWORK=Timeloop if needed.

Units (important)
-----------------
`SYSTEM_BW` and every `req_bw` value must live in the **same numeric domain**.
MAESTRO CSVs label that quantity as average bandwidth requirement (column
`Avg BW Req`); related headers may say "Elements/cycle" depending on export
settings. The allocator is unit-agnostic: if you apply a linear scale factor
to map MAESTRO numbers into external bandwidth (e.g. DRAM GB/s), apply the
**same** factor to `SYSTEM_BW`.

MAGMA-style DRAM scenarios (e.g. 16 vs 256 GB/s) are therefore expressed here
as two `SYSTEM_BW` settings in the **same** units as `Avg BW Req`, or as two
values that preserve the 16:256 ratio after a shared calibration. Example:
`SYSTEM_BW=16` vs `SYSTEM_BW=256` compares a "narrow" vs "wide" shared bus in
abstract allocator units, not raw GB/s unless you calibrated the scale.
"""

from __future__ import annotations

import csv
import os
import sys
from typing import Dict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from compare.system_model.magma_bw_allocator import bw_allocator, make_two_core_combo


SUMMARY = os.path.join(REPO, "compare", "results", "summary_table.csv")
MAESTRO_NB_DATA = os.path.join(REPO, "maestro", "tools", "jupyter_notebook", "data")


def _load_layer_avg_bw_req(csv_path: str, layer_name: str) -> float:
    """
    Read MAESTRO notebook CSV and return 'Avg BW Req' for the target layer.

    The MAESTRO CSVs include per-layer rows (e.g., CONV2_1_2) with columns:
      - Layer Number
      - Avg BW Req
    """
    with open(csv_path, "r") as f:
        for r in csv.DictReader(f):
            layer = (r.get(" Layer Number") or r.get("Layer Number") or "").strip()
            if layer != layer_name:
                continue
            raw = (r.get("Avg BW Req") or r.get(" Avg BW Req") or "").strip()
            if not raw:
                raise ValueError(f"'Avg BW Req' missing for {layer_name} in {csv_path}")
            return float(raw)
    raise ValueError(f"Layer {layer_name} not found in {csv_path}")


def load_req_bw_from_maestro(layer_name: str) -> Dict[str, float]:
    """
    Build req_bw dict from MAESTRO average BW requirements.

    Dataflow->CSV mapping:
      - RS (Eyeriss): Resnet50_rs_pe256.csv
      - WS (NVDLA):   Resnet50_kcp_ws_pe256.csv
      - OS (ShiDianNao): use Resnet50_yxp_os_pe256.csv if present; otherwise
        fall back to RS CSV as a temporary proxy.
    """
    rs_csv = os.path.join(MAESTRO_NB_DATA, "Resnet50_rs_pe256.csv")
    ws_csv = os.path.join(MAESTRO_NB_DATA, "Resnet50_kcp_ws_pe256.csv")
    os_csv = os.path.join(MAESTRO_NB_DATA, "Resnet50_yxp_os_pe256.csv")

    if not os.path.isfile(os_csv):
        # Keep pipeline runnable even if OS CSV was not generated yet.
        os_csv = rs_csv
        print("Note: Resnet50_yxp_os_pe256.csv not found; using RS CSV as OS BW proxy.")

    return {
        "ShiDianNao_OS": _load_layer_avg_bw_req(os_csv, layer_name),
        "NVDLA_WS": _load_layer_avg_bw_req(ws_csv, layer_name),
        "Eyeriss_RS": _load_layer_avg_bw_req(rs_csv, layer_name),
    }


def load_latencies(framework: str = "MAESTRO") -> Dict[str, float]:
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
    bw_layer = os.environ.get("BW_LAYER", "CONV2_1_2")
    req_bw = load_req_bw_from_maestro(bw_layer)

    # Optional explicit overrides (if user wants to sweep values).
    if "REQ_BW_OS" in os.environ:
        req_bw["ShiDianNao_OS"] = float(os.environ["REQ_BW_OS"])
    if "REQ_BW_WS" in os.environ:
        req_bw["NVDLA_WS"] = float(os.environ["REQ_BW_WS"])
    if "REQ_BW_RS" in os.environ:
        req_bw["Eyeriss_RS"] = float(os.environ["REQ_BW_RS"])
    framework = os.environ.get("LATENCY_FRAMEWORK", "MAESTRO")
    lat = load_latencies(framework)
    combos = [
        ("ShiDianNao_OS", "Eyeriss_RS"),
        ("Eyeriss_RS", "NVDLA_WS"),
        ("NVDLA_WS", "ShiDianNao_OS"),
    ]

    print(f"Using {SUMMARY} (latency_rows={framework})")
    print(f"BW layer={bw_layer} from MAESTRO Avg BW Req")
    print(
        "Units: SYSTEM_BW and req_bw must match (MAESTRO Avg BW Req domain); "
        "see module docstring for DRAM/GB/s calibration."
    )
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

