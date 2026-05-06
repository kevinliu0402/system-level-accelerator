#!/usr/bin/env python3
"""
Two *independent* serial pipelines in parallel (4 accelerators total).

  Path A:  NVDLA_WS -> (2-slot ping-pong buffer) -> Eyeriss_RS   (default: ResNet-50)
  Path B:  NVDLA_WS -> (2-slot ping-pong buffer) -> ShiDianNao_OS (default: MobileNetV2)

Each path uses the same timing model as run_two_group_serial_pipeline.py:
  Seg0 on first accelerator: 1 or 2 consecutive layers
  Seg1 on second accelerator: 1 or 2 consecutive layers
  Total layers per path: 2..4 (segment depths sum to layer count)

System wall time (no shared-resource contention modeled):
  wall = max(makespan_pathA, makespan_pathB)

With --search and --optimize minmax, picks segment splits (d0,d1) on each path to
minimize the wall time. With --optimize independent, minimizes each path separately
(can be worse for wall time).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Dict, List, Optional, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from compare.system_model.noc_dram import bytes_to_cycles_transfer
from compare.system_model.run_two_group_serial_pipeline import (
    SimResult,
    _layer_order,
    _seg_latency_cycles,
    pipeline_makespan_closed_form,
    pipeline_simulate_double_buffer,
)


def _splits_for_count(count: int) -> List[Tuple[int, int]]:
    if count == 2:
        return [(1, 1)]
    if count == 3:
        return [(1, 2), (2, 1)]
    if count == 4:
        return [(2, 2)]
    raise ValueError(f"layer count must be 2..4, got {count}")


def _pick_layers(network: str, start: int, count: int) -> List[str]:
    order = _layer_order(network)
    chosen = order[start : start + count]
    if len(chosen) != count:
        raise SystemExit(f"Not enough layers for {network}: need {count}, have {len(order)} from start={start}")
    return chosen


def _eval_split(
    network: str,
    layers: List[str],
    acc0_df: str,
    acc1_df: str,
    d0: int,
    d1: int,
    T_comm: float,
    N: int,
) -> Optional[Dict[str, object]]:
    if d0 + d1 != len(layers):
        return None
    seg0 = layers[:d0]
    seg1 = layers[d0:]
    T0 = _seg_latency_cycles(network, seg0, acc0_df)
    T1 = _seg_latency_cycles(network, seg1, acc1_df)
    mk = pipeline_makespan_closed_form(T0, T1, T_comm, N)
    sim = pipeline_simulate_double_buffer(T0, T1, T_comm, N)
    return {
        "seg0_depth": d0,
        "seg1_depth": d1,
        "seg0_layers": seg0,
        "seg1_layers": seg1,
        "T0": T0,
        "T1": T1,
        "T_comm": T_comm,
        "makespan_closed": mk,
        "makespan_sim": sim.makespan,
        "sim": sim,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--network-a", default="resnet50")
    p.add_argument("--network-b", default="mobilenet_v2")
    p.add_argument("--acc0-a", default="NVDLA_WS", help="First accelerator on path A (NVDLA)")
    p.add_argument("--acc1-a", default="Eyeriss_RS", help="Second accelerator on path A")
    p.add_argument("--acc0-b", default="NVDLA_WS", help="First accelerator on path B (NVDLA)")
    p.add_argument("--acc1-b", default="ShiDianNao_OS", help="Second accelerator on path B")
    p.add_argument("--start-a", type=int, default=0)
    p.add_argument("--start-b", type=int, default=0)
    p.add_argument("--count-a", type=int, default=4)
    p.add_argument("--count-b", type=int, default=4)
    p.add_argument("--batches", type=int, default=8)

    p.add_argument("--t-comm-a", type=float, default=-1.0)
    p.add_argument("--t-comm-b", type=float, default=-1.0)
    p.add_argument("--comm-bytes-a", type=float, default=0.0)
    p.add_argument("--comm-bw-a-gbps", type=float, default=0.0)
    p.add_argument("--comm-bytes-b", type=float, default=0.0)
    p.add_argument("--comm-bw-b-gbps", type=float, default=0.0)
    p.add_argument("--clock-hz", type=float, default=1e9)

    p.add_argument("--search", action="store_true", help="Search segment splits per path.")
    p.add_argument(
        "--optimize",
        choices=["minmax", "independent"],
        default="minmax",
        help="minmax: minimize max(path makespans); independent: best per path, then report max.",
    )
    p.add_argument("--out-csv", default="", help="Write one row per path + wall summary.")
    args = p.parse_args()

    if not (2 <= args.count_a <= 4 and 2 <= args.count_b <= 4):
        raise SystemExit("count-a and count-b must be in 2..4")

    layers_a = _pick_layers(args.network_a, args.start_a, args.count_a)
    layers_b = _pick_layers(args.network_b, args.start_b, args.count_b)

    if args.t_comm_a >= 0:
        T_comm_a = float(args.t_comm_a)
    else:
        T_comm_a = bytes_to_cycles_transfer(args.comm_bytes_a, args.comm_bw_a_gbps, args.clock_hz)
    if args.t_comm_b >= 0:
        T_comm_b = float(args.t_comm_b)
    else:
        T_comm_b = bytes_to_cycles_transfer(args.comm_bytes_b, args.comm_bw_b_gbps, args.clock_hz)

    splits_a = _splits_for_count(args.count_a)
    splits_b = _splits_for_count(args.count_b)

    def best_independent() -> Tuple[Dict[str, object], Dict[str, object]]:
        best_a: Optional[Dict[str, object]] = None
        best_b: Optional[Dict[str, object]] = None
        for sa in splits_a:
            r = _eval_split(
                args.network_a, layers_a, args.acc0_a, args.acc1_a, sa[0], sa[1], T_comm_a, args.batches
            )
            if r and (best_a is None or r["makespan_closed"] < best_a["makespan_closed"]):
                best_a = r
        for sb in splits_b:
            r = _eval_split(
                args.network_b, layers_b, args.acc0_b, args.acc1_b, sb[0], sb[1], T_comm_b, args.batches
            )
            if r and (best_b is None or r["makespan_closed"] < best_b["makespan_closed"]):
                best_b = r
        assert best_a is not None and best_b is not None
        return best_a, best_b

    def best_minmax() -> Tuple[Dict[str, object], Dict[str, object]]:
        best_pair: Optional[Tuple[float, Dict[str, object], Dict[str, object]]] = None
        for sa in splits_a:
            ra = _eval_split(
                args.network_a, layers_a, args.acc0_a, args.acc1_a, sa[0], sa[1], T_comm_a, args.batches
            )
            if not ra:
                continue
            for sb in splits_b:
                rb = _eval_split(
                    args.network_b, layers_b, args.acc0_b, args.acc1_b, sb[0], sb[1], T_comm_b, args.batches
                )
                if not rb:
                    continue
                wall = max(float(ra["makespan_closed"]), float(rb["makespan_closed"]))
                if best_pair is None or wall < best_pair[0]:
                    best_pair = (wall, ra, rb)
        assert best_pair is not None
        return best_pair[1], best_pair[2]

    if args.search:
        if args.optimize == "independent":
            ra, rb = best_independent()
        else:
            ra, rb = best_minmax()
    else:
        # default split: try (2,2) if counts allow else first valid
        da, db = splits_a[0][0], splits_a[0][1]
        dbb0, dbb1 = splits_b[0][0], splits_b[0][1]
        ra = _eval_split(args.network_a, layers_a, args.acc0_a, args.acc1_a, da, db, T_comm_a, args.batches)
        rb = _eval_split(args.network_b, layers_b, args.acc0_b, args.acc1_b, dbb0, dbb1, T_comm_b, args.batches)
        if not ra or not rb:
            raise SystemExit("Default split invalid; use --search or fix counts.")

    sim_a: SimResult = ra["sim"]  # type: ignore[assignment]
    sim_b: SimResult = rb["sim"]  # type: ignore[assignment]

    wall_closed = max(float(ra["makespan_closed"]), float(rb["makespan_closed"]))
    wall_sim = max(float(ra["makespan_sim"]), float(rb["makespan_sim"]))

    print("=== Dual serial pipelines in parallel (4 accelerators) ===")
    print(f"Path A: {args.network_a}  {args.acc0_a} -> buffer -> {args.acc1_a}")
    print(f"  layers ({len(layers_a)}): {layers_a}")
    print(f"  seg0_depth={ra['seg0_depth']} seg1_depth={ra['seg1_depth']}")
    print(f"  T0={float(ra['T0']):,.3f}  T1={float(ra['T1']):,.3f}  T_comm={float(ra['T_comm']):,.3f}")
    print(f"  makespan closed={float(ra['makespan_closed']):,.3f}  sim={float(ra['makespan_sim']):,.3f}")
    print("")
    print(f"Path B: {args.network_b}  {args.acc0_b} -> buffer -> {args.acc1_b}")
    print(f"  layers ({len(layers_b)}): {layers_b}")
    print(f"  seg0_depth={rb['seg0_depth']} seg1_depth={rb['seg1_depth']}")
    print(f"  T0={float(rb['T0']):,.3f}  T1={float(rb['T1']):,.3f}  T_comm={float(rb['T_comm']):,.3f}")
    print(f"  makespan closed={float(rb['makespan_closed']):,.3f}  sim={float(rb['makespan_sim']):,.3f}")
    print("")
    print(f"Wall time (max of paths): closed={wall_closed:,.3f}  sim={wall_sim:,.3f}")
    print(f"N batches={args.batches}  optimize={args.optimize}  search={bool(args.search)}")

    if args.out_csv:
        os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
        rows_out = [
            {
                "row_kind": "path",
                "path": "A",
                "network": args.network_a,
                "acc0": args.acc0_a,
                "acc1": args.acc1_a,
                "layers": "|".join(layers_a),
                "seg0_depth": ra["seg0_depth"],
                "seg1_depth": ra["seg1_depth"],
                "seg0": "|".join(ra["seg0_layers"]),  # type: ignore[arg-type]
                "seg1": "|".join(ra["seg1_layers"]),  # type: ignore[arg-type]
                "batches": args.batches,
                "T0": f"{float(ra['T0']):.6f}",
                "T1": f"{float(ra['T1']):.6f}",
                "T_comm": f"{float(ra['T_comm']):.6f}",
                "makespan_closed": f"{float(ra['makespan_closed']):.6f}",
                "makespan_sim": f"{float(ra['makespan_sim']):.6f}",
                "stall0_full": f"{sim_a.acc0_stall_full:.6f}",
                "stall1_empty": f"{sim_a.acc1_stall_empty:.6f}",
            },
            {
                "row_kind": "path",
                "path": "B",
                "network": args.network_b,
                "acc0": args.acc0_b,
                "acc1": args.acc1_b,
                "layers": "|".join(layers_b),
                "seg0_depth": rb["seg0_depth"],
                "seg1_depth": rb["seg1_depth"],
                "seg0": "|".join(rb["seg0_layers"]),  # type: ignore[arg-type]
                "seg1": "|".join(rb["seg1_layers"]),  # type: ignore[arg-type]
                "batches": args.batches,
                "T0": f"{float(rb['T0']):.6f}",
                "T1": f"{float(rb['T1']):.6f}",
                "T_comm": f"{float(rb['T_comm']):.6f}",
                "makespan_closed": f"{float(rb['makespan_closed']):.6f}",
                "makespan_sim": f"{float(rb['makespan_sim']):.6f}",
                "stall0_full": f"{sim_b.acc0_stall_full:.6f}",
                "stall1_empty": f"{sim_b.acc1_stall_empty:.6f}",
            },
            {
                "row_kind": "wall",
                "path": "",
                "network": f"{args.network_a}+{args.network_b}",
                "acc0": "",
                "acc1": "",
                "layers": "",
                "seg0_depth": "",
                "seg1_depth": "",
                "seg0": "",
                "seg1": "",
                "batches": args.batches,
                "T0": "",
                "T1": "",
                "T_comm": "",
                "makespan_closed": f"{wall_closed:.6f}",
                "makespan_sim": f"{wall_sim:.6f}",
                "stall0_full": "",
                "stall1_empty": "",
            },
        ]
        fieldnames = list(rows_out[0].keys())
        with open(args.out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in rows_out:
                w.writerow(row)
        print(f"Wrote {args.out_csv}")


if __name__ == "__main__":
    main()
