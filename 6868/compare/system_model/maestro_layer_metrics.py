"""
Load per-layer MAESTRO CSV metrics (Avg BW Req, Runtime cycles) for multi-model runs.

Used by run_scar_multi_model_bw.py so each concurrent job can use a different
network + layer + dataflow, instead of a single global latency from summary_table.csv.
"""

from __future__ import annotations

import csv
import os
import re
from typing import Dict, List, Tuple

# Project root = parent of compare/
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MAESTRO_DATA = os.path.join(_REPO, "maestro", "tools", "jupyter_notebook", "data")

# Dataflow names must match magma_bw_allocator / summary_table conventions.
MODEL_CSVS: Dict[str, Dict[str, str]] = {
    "resnet50": {
        "Eyeriss_RS": "Resnet50_rs_pe256.csv",
        "NVDLA_WS": "Resnet50_kcp_ws_pe256.csv",
        # Prefer real OS mapping; file may be absent (handled in layer_latency_and_bw_req).
        "ShiDianNao_OS": "Resnet50_yxp_os_pe256.csv",
    },
    "mobilenet_v2": {
        # Only kcp_ws export is in-tree; OS/RS fall back to this file (documented).
        "NVDLA_WS": "MobileNetV2_kcp_ws_pe256.csv",
        "Eyeriss_RS": "MobileNetV2_kcp_ws_pe256.csv",
        "ShiDianNao_OS": "MobileNetV2_kcp_ws_pe256.csv",
    },
    # In-tree stub: layer names from MAESTRO mapping squeezenet1_0_kcp_ws.m; numeric rows
    # cycled from MobileNetV2 WS export (NOT a real MAESTRO run for SqueezeNet).
    "squeezenet1_0": {
        "NVDLA_WS": "SqueezeNet1_0_kcp_ws_pe256.csv",
        "Eyeriss_RS": "SqueezeNet1_0_kcp_ws_pe256.csv",
        "ShiDianNao_OS": "SqueezeNet1_0_kcp_ws_pe256.csv",
    },
}


def _row_field(row: dict, *candidates: str) -> str:
    for c in candidates:
        v = row.get(c)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""


def _load_layer_row(csv_path: str, layer_name: str) -> dict:
    with open(csv_path, "r") as f:
        for r in csv.DictReader(f):
            layer = _row_field(r, " Layer Number", "Layer Number")
            if layer != layer_name:
                continue
            return r
    raise ValueError(f"Layer {layer_name!r} not found in {csv_path}")


def layer_latency_and_bw_req(
    network: str,
    layer: str,
    dataflow: str,
) -> Tuple[float, float, str, bool]:
    """
    Return (runtime_cycles, avg_bw_req, csv_path_used, proxied).

    ``proxied`` is True when OS/RS used the WS MobileNet CSV (only one mapping shipped).
    """
    net = network.lower().strip()
    df = dataflow.strip()
    if net not in MODEL_CSVS or df not in MODEL_CSVS[net]:
        raise KeyError(f"Unknown network {network!r} or dataflow {dataflow!r}")

    fname = MODEL_CSVS[net][df]
    full = os.path.join(_MAESTRO_DATA, fname)
    if net == "resnet50" and df == "ShiDianNao_OS" and not os.path.isfile(full):
        full = resolve_os_csv_path()
    elif not os.path.isfile(full):
        raise FileNotFoundError(f"Missing MAESTRO CSV: {full}")

    proxied = (net == "mobilenet_v2" and df != "NVDLA_WS") or (
        net == "squeezenet1_0" and df != "NVDLA_WS"
    )
    r = _load_layer_row(full, layer)

    rt_raw = _row_field(r, "Runtime (Cycles)", " Runtime (Cycles)")
    bw_raw = _row_field(r, "Avg BW Req", " Avg BW Req")
    if not rt_raw or not bw_raw:
        raise ValueError(f"Missing Runtime or Avg BW Req for {layer} in {full}")

    return float(rt_raw), float(bw_raw), full, proxied


def resolve_os_csv_path() -> str:
    """ResNet OS CSV, or RS proxy if OS file missing (same as run_bw_combos)."""
    os_csv = os.path.join(_MAESTRO_DATA, "Resnet50_yxp_os_pe256.csv")
    rs_csv = os.path.join(_MAESTRO_DATA, "Resnet50_rs_pe256.csv")
    return os_csv if os.path.isfile(os_csv) else rs_csv


def list_resnet50_layer_order() -> List[str]:
    """Layer names in row order from Resnet50_rs_pe256.csv (full network list)."""
    path = os.path.join(_MAESTRO_DATA, "Resnet50_rs_pe256.csv")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    out: List[str] = []
    with open(path, "r") as f:
        for r in csv.DictReader(f):
            layer = _row_field(r, " Layer Number", "Layer Number")
            if layer:
                out.append(layer)
    return out


def _squeezenet_layer_names_from_mapping() -> List[str]:
    mpath = os.path.join(_REPO, "maestro", "data", "mapping", "squeezenet1_0_kcp_ws.m")
    if not os.path.isfile(mpath):
        raise FileNotFoundError(mpath)
    names: List[str] = []
    with open(mpath, "r") as f:
        for line in f:
            m = re.match(r"^\s*Layer\s+(\S+)\s*\{", line)
            if m:
                names.append(m.group(1))
    if not names:
        raise ValueError(f"No Layer entries parsed from {mpath}")
    return names


def ensure_squeezenet1_0_maestro_stub_csv() -> str:
    """
    Write SqueezeNet1_0_kcp_ws_pe256.csv if missing.

    Layer order and names match ``squeezenet1_0_kcp_ws.m``. Each row's numeric metrics
    are copied by cycling rows from ``MobileNetV2_kcp_ws_pe256.csv`` — useful only for
    pipeline / allocator experiments until real MAESTRO exports exist.
    """
    out_path = os.path.join(_MAESTRO_DATA, "SqueezeNet1_0_kcp_ws_pe256.csv")
    if os.path.isfile(out_path):
        return out_path

    mn_path = os.path.join(_MAESTRO_DATA, "MobileNetV2_kcp_ws_pe256.csv")
    if not os.path.isfile(mn_path):
        raise FileNotFoundError(f"Need {mn_path} to build SqueezeNet stub")

    sq_layers = _squeezenet_layer_names_from_mapping()
    with open(mn_path, newline="") as f:
        mn_reader = csv.DictReader(f)
        mn_fieldnames = mn_reader.fieldnames
        if not mn_fieldnames:
            raise ValueError("MobileNet CSV has no header")
        mn_rows = list(mn_reader)
    if not mn_rows:
        raise ValueError("MobileNet CSV has no rows")

    nn_key = "Neural Network Name" if "Neural Network Name" in mn_fieldnames else None
    lyr_key = " Layer Number" if " Layer Number" in mn_fieldnames else "Layer Number"
    if lyr_key not in mn_fieldnames:
        raise KeyError(f"Expected layer column in MobileNet CSV: {mn_fieldnames}")

    out_rows: List[dict] = []
    for i, lyr in enumerate(sq_layers):
        src = dict(mn_rows[i % len(mn_rows)])
        if nn_key:
            src[nn_key] = "SqueezeNet1_0"
        src[lyr_key] = lyr
        out_rows.append(src)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(mn_fieldnames), extrasaction="ignore")
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    return out_path


def list_squeezenet1_0_layer_order() -> List[str]:
    """Layer names for SqueezeNet1_0 (stub CSV created by ensure_squeezenet1_0_maestro_stub_csv)."""
    ensure_squeezenet1_0_maestro_stub_csv()
    path = os.path.join(_MAESTRO_DATA, "SqueezeNet1_0_kcp_ws_pe256.csv")
    out: List[str] = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            layer = _row_field(r, " Layer Number", "Layer Number")
            if layer:
                out.append(layer)
    return out


def list_mobilenet_v2_layer_order() -> List[str]:
    """Layer names in row order from MobileNetV2_kcp_ws_pe256.csv."""
    path = os.path.join(_MAESTRO_DATA, "MobileNetV2_kcp_ws_pe256.csv")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    out: List[str] = []
    with open(path, "r") as f:
        for r in csv.DictReader(f):
            layer = _row_field(r, " Layer Number", "Layer Number")
            if layer:
                out.append(layer)
    return out
