#!/usr/bin/env python3
"""
Greedy placement of ResNet-50 + MobileNetV2 + SqueezeNet1_0 on 4 heterogeneous chiplets (SCAR-inspired).

SqueezeNet1_0 uses an in-tree **stub** MAESTRO CSV (see ``maestro_layer_metrics.ensure_squeezenet1_0_maestro_stub_csv``):
layer names from the MAESTRO mapping file; numeric rows cycled from MobileNetV2 WS until real exports exist.

Chiplet fabric (fixed):
  - Chiplet 0, 1: NVDLA_WS (two WS tiles)
  - Chiplet 2:    ShiDianNao_OS
  - Chiplet 3:    Eyeriss_RS

Each layer uses the MAESTRO (Runtime, Avg BW Req) for the chiplet's dataflow.

Scheduling model:
  - Each network executes layers in strict original CSV order.
  - At most one in-flight layer per network (classic single-stream per model).
  - When multiple networks have a next layer, enumerate injective chiplet assignments
    (1, 2, or 3 concurrent jobs on distinct chiplets) and pick the assignment that
    minimizes completion time ``start + makespan`` under ``bw_allocator`` (N cores).
  - ``makespan`` is the wall time for that concurrent slice under shared SYSTEM_BW.

Output CSV (GREEDY4_OUT_CSV): one row per scheduled step.
"""

from __future__ import annotations

import csv
import itertools
import os
import sys
from typing import Dict, List, Optional, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from compare.system_model.maestro_layer_metrics import (
    layer_latency_and_bw_req,
    list_mobilenet_v2_layer_order,
    list_resnet50_layer_order,
    list_squeezenet1_0_layer_order,
)
from compare.system_model.magma_bw_allocator import Job, bw_allocator

CHIPLET_DF: Dict[int, str] = {
    0: "NVDLA_WS",
    1: "NVDLA_WS",
    2: "ShiDianNao_OS",
    3: "Eyeriss_RS",
}

TAG_R, TAG_M, TAG_S = "R", "M", "S"


def _metrics(network: str, layer: str, chiplet_id: int) -> Tuple[float, float, str, bool]:
    df = CHIPLET_DF[chiplet_id]
    L, bw, path, proxied = layer_latency_and_bw_req(network, layer, df)
    return L, bw, path, proxied


def _alloc_queues(queues: List[List[Job]], total_bw: float) -> Tuple[float, float]:
    res = bw_allocator(queues, total_bw)
    return res.makespan, res.bw_util


def _chip_keys_for_best(best: dict) -> List[str]:
    keys = []
    if int(best.get("chiplet_resnet", -1)) >= 0:
        keys.append("chiplet_resnet")
    if int(best.get("chiplet_mobilenet", -1)) >= 0:
        keys.append("chiplet_mobilenet")
    if int(best.get("chiplet_squeeze", -1)) >= 0:
        keys.append("chiplet_squeeze")
    return keys


def main() -> None:
    total_bw = float(os.environ.get("SYSTEM_BW", "100.0"))
    out_csv = os.environ.get(
        "GREEDY4_OUT_CSV",
        os.path.join(REPO, "compare", "results", "greedy_four_chiplet_schedule.csv"),
    )
    max_steps = int(os.environ.get("GREEDY4_MAX_STEPS", "0"))

    layers_r = list_resnet50_layer_order()
    layers_m = list_mobilenet_v2_layer_order()
    layers_s = list_squeezenet1_0_layer_order()
    n_r, n_m, n_s = len(layers_r), len(layers_m), len(layers_s)

    chiplet_free = [0.0, 0.0, 0.0, 0.0]
    done_r: List[float] = []
    done_m: List[float] = []
    done_s: List[float] = []

    ir = im = is_ = 0
    rows: List[dict] = []
    step = 0

    def dep(tag: str, idx: int) -> float:
        if tag == TAG_R:
            return done_r[idx - 1] if idx > 0 else 0.0
        if tag == TAG_M:
            return done_m[idx - 1] if idx > 0 else 0.0
        return done_s[idx - 1] if idx > 0 else 0.0

    def active() -> List[Tuple[str, str, int, str]]:
        a: List[Tuple[str, str, int, str]] = []
        if ir < n_r:
            a.append(("resnet50", TAG_R, ir, layers_r[ir]))
        if im < n_m:
            a.append(("mobilenet_v2", TAG_M, im, layers_m[im]))
        if is_ < n_s:
            a.append(("squeezenet1_0", TAG_S, is_, layers_s[is_]))
        return a

    def empty_row() -> dict:
        return {
            "resnet_layer": "",
            "mobilenet_layer": "",
            "squeeze_layer": "",
            "chiplet_resnet": -1,
            "chiplet_mobilenet": -1,
            "chiplet_squeeze": -1,
            "L_resnet": "",
            "bw_resnet": "",
            "L_mobilenet": "",
            "bw_mobilenet": "",
            "L_squeeze": "",
            "bw_squeeze": "",
        }

    while ir < n_r or im < n_m or is_ < n_s:
        step += 1
        if max_steps and step > max_steps:
            break

        act = active()
        if not act:
            break

        k = len(act)
        mode = {1: "single", 2: "pair", 3: "triple"}[k]
        best: Optional[dict] = None

        for perm in itertools.permutations(range(4), k):
            chips = list(perm)
            start_deps = max(dep(tag, idx) for (_, tag, idx, _) in act)
            start_chips = max(chiplet_free[c] for c in chips)
            start = max(start_deps, start_chips)

            queues: List[List[Job]] = []
            Lvals: Dict[str, float] = {}
            bwvals: Dict[str, float] = {}
            for (net, tag, idx, lyr), c in zip(act, chips):
                L, bw, _, _ = _metrics(net, lyr, c)
                Lvals[tag] = L
                bwvals[tag] = bw
                jid = f"{tag}/{net}/{lyr}/{CHIPLET_DF[c]}"
                queues.append([Job(job_id=jid, no_stall_latency=L, req_bw=bw)])

            ms, util = _alloc_queues(queues, total_bw)
            end = start + ms

            base = empty_row()
            for (net, tag, idx, lyr), c in zip(act, chips):
                if tag == TAG_R:
                    base["resnet_layer"] = lyr
                    base["chiplet_resnet"] = c
                    base["L_resnet"] = Lvals[tag]
                    base["bw_resnet"] = bwvals[tag]
                elif tag == TAG_M:
                    base["mobilenet_layer"] = lyr
                    base["chiplet_mobilenet"] = c
                    base["L_mobilenet"] = Lvals[tag]
                    base["bw_mobilenet"] = bwvals[tag]
                else:
                    base["squeeze_layer"] = lyr
                    base["chiplet_squeeze"] = c
                    base["L_squeeze"] = Lvals[tag]
                    base["bw_squeeze"] = bwvals[tag]

            cand = {
                "step": step,
                "mode": mode,
                **base,
                "start": start,
                "makespan": ms,
                "end": end,
                "bw_util": util,
                "_chips": chips,
            }
            if best is None or end < float(best["end"]) - 1e-9:
                best = cand
            elif best is not None and abs(end - float(best["end"])) < 1e-9:
                old_chips = [chiplet_free[int(best[k])] for k in _chip_keys_for_best(best)]
                new_chips = [chiplet_free[c] for c in chips]
                old_key = max(old_chips) if old_chips else 0.0
                new_key = max(new_chips) if new_chips else 0.0
                if new_key < old_key:
                    best = cand

        assert best is not None
        chips_done = best.pop("_chips")
        rows.append(best)

        end = float(best["end"])
        for (_, tag, _, _), c in zip(act, chips_done):
            chiplet_free[c] = end
            if tag == TAG_R:
                done_r.append(end)
                ir += 1
            elif tag == TAG_M:
                done_m.append(end)
                im += 1
            else:
                done_s.append(end)
                is_ += 1

    wall = max(chiplet_free) if chiplet_free else 0.0
    print(
        f"Greedy 4-chiplet schedule: ResNet={n_r}, MobileNet={n_m}, SqueezeNet={n_s}, steps={len(rows)}"
    )
    print(f"SYSTEM_BW={total_bw}")
    print(f"Wall time (max chiplet finish): {wall:,.0f} cycles")

    fieldnames = [
        "step",
        "mode",
        "resnet_layer",
        "mobilenet_layer",
        "squeeze_layer",
        "chiplet_resnet",
        "chiplet_mobilenet",
        "chiplet_squeeze",
        "start",
        "makespan",
        "end",
        "bw_util",
        "L_resnet",
        "bw_resnet",
        "L_mobilenet",
        "bw_mobilenet",
        "L_squeeze",
        "bw_squeeze",
    ]
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    print(f"Wrote {out_csv}")


if __name__ == "__main__":
    main()
