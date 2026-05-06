#!/usr/bin/env python3
"""
Optimize layer-to-path assignment for two serial pipelines in parallel (4 accelerators).

Hardware (fixed):
  Path A: NVDLA_WS -> 2-slot ping-pong buffer -> Eyeriss_RS
  Path B: NVDLA_WS -> 2-slot ping-pong buffer -> ShiDianNao_OS

Workloads:
  - A window of consecutive ResNet-50 layers and a window of consecutive MobileNetV2 layers.
  - Each layer is assigned to path A or path B (binary choice per layer).
  - On each path, layers are ordered as: all assigned ResNet layers (in global ResNet order),
    then all assigned MobileNet layers (in global MobileNet order).  (Use --merge interleave
    for alternating merge by index; see --merge.)

Per path, layers are executed as a sequence of pipeline *batches*. Each batch uses:
  - Seg0 on Acc0: 1 or 2 consecutive layers (sum of MAESTRO runtimes on that path's Acc0 DF)
  - Seg1 on Acc1: 1 or 2 consecutive layers (same for Acc1 DF)

The model searches:
  1) All 2^(Lr+Lm) assignments (brute force; keep Lr+Lm modest, default 4+4=256 combos).
  2) For each path, all valid batchings of its layer list into (d0,d1) chunks.
  3) Repeats the per-forward batch schedule ``--micro-batches`` times (same schedule each time).

Objective: minimize wall time = max(sim_pathA, sim_pathB) using the event-accurate double-buffer
simulator with per-batch (T0,T1) lists (``pipeline_simulate_double_buffer_sequence``).

Note: This does not model DRAM/NoC contention between the two pipelines, only the local
double-buffer backpressure on each path.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import os
import sys
from typing import List, Sequence, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from compare.system_model.maestro_layer_metrics import layer_latency_and_bw_req, layer_output_l2_write_elems
from compare.system_model.noc_dram import bytes_to_cycles_transfer
from compare.system_model.run_two_group_serial_pipeline import (
    SimResult,
    _layer_order,
    pipeline_simulate_double_buffer_sequence,
)


def _seg_latency_mixed(seg: List[Tuple[str, str]], dataflow: str) -> float:
    return sum(layer_latency_and_bw_req(n, lyr, dataflow)[0] for n, lyr in seg)


def enumerate_batch_shapes(n: int) -> List[List[Tuple[int, int]]]:
    """Ways to partition n consecutive layers into batches (d0,d1) with 1<=d0,d1<=2, 2<=d0+d1<=4."""
    if n < 2:
        return []
    res: List[List[Tuple[int, int]]] = []

    def dfs(pos: int, acc: List[Tuple[int, int]]) -> None:
        if pos == n:
            res.append(list(acc))
            return
        for d0 in (1, 2):
            for d1 in (1, 2):
                tot = d0 + d1
                if tot < 2 or tot > 4 or pos + tot > n:
                    continue
                acc.append((d0, d1))
                dfs(pos + tot, acc)
                acc.pop()

    dfs(0, [])
    return res


def merge_layers_for_path(
    r_layers: List[str],
    m_layers: List[str],
    assign_r: Sequence[int],
    assign_m: Sequence[int],
    *,
    mode: str,
) -> List[Tuple[str, str]]:
    """assign_* are 0/1 for path A (1) vs B (0) — caller passes only one path's mask."""
    r_pick = [lyr for lyr, a in zip(r_layers, assign_r) if a == 1]
    m_pick = [lyr for lyr, a in zip(m_layers, assign_m) if a == 1]
    if mode == "resnet_first":
        return [("resnet50", x) for x in r_pick] + [("mobilenet_v2", x) for x in m_pick]
    if mode == "interleave":
        out: List[Tuple[str, str]] = []
        i = j = 0
        while i < len(r_pick) or j < len(m_pick):
            if i < len(r_pick):
                out.append(("resnet50", r_pick[i]))
                i += 1
            if j < len(m_pick):
                out.append(("mobilenet_v2", m_pick[j]))
                j += 1
        return out
    raise ValueError(f"Unknown merge mode: {mode}")


def best_path_schedule(
    layers: List[Tuple[str, str]],
    acc0_df: str,
    acc1_df: str,
    T_comm: float,
    micro_batches: int,
) -> Tuple[float, SimResult, List[Tuple[int, int]], List[float], List[float]]:
    if not layers:
        return 0.0, SimResult(0, 0, 0, 0, 0), [], [], []
    shapes = enumerate_batch_shapes(len(layers))
    if not shapes:
        return float("inf"), SimResult(0, 0, 0, 0, 0), [], [], []

    best_ms = float("inf")
    best_sim = SimResult(0, 0, 0, 0, 0)
    best_shape: List[Tuple[int, int]] = []
    best_t0: List[float] = []
    best_t1: List[float] = []

    for shape in shapes:
        T0s: List[float] = []
        T1s: List[float] = []
        pos = 0
        ok = True
        for d0, d1 in shape:
            seg0 = layers[pos : pos + d0]
            seg1 = layers[pos + d0 : pos + d0 + d1]
            if len(seg0) != d0 or len(seg1) != d1:
                ok = False
                break
            T0s.append(_seg_latency_mixed(seg0, acc0_df))
            T1s.append(_seg_latency_mixed(seg1, acc1_df))
            pos += d0 + d1
        if not ok or pos != len(layers):
            continue

        T0_run = T0s * micro_batches
        T1_run = T1s * micro_batches
        sim = pipeline_simulate_double_buffer_sequence(T0_run, T1_run, T_comm)
        if sim.makespan < best_ms:
            best_ms = sim.makespan
            best_sim = sim
            best_shape = list(shape)
            best_t0 = T0s
            best_t1 = T1s

    return best_ms, best_sim, best_shape, best_t0, best_t1


def _bytes_for_activation(network: str, layer: str, *, element_bytes: int, dataflow: str) -> float:
    # Use MAESTRO output L2 write elements as a simple proxy for activation size.
    elems = layer_output_l2_write_elems(network, layer, dataflow)
    return float(elems) * float(element_bytes)


def _inter_path_comm_bytes(
    r_layers: List[str],
    m_layers: List[str],
    assign_a_r: Sequence[int],
    assign_a_m: Sequence[int],
    *,
    element_bytes: int,
    # activation is produced by the layer's stage0 in this abstraction (NVDLA_WS)
    producer_df: str = "NVDLA_WS",
) -> float:
    """
    Charge a communication when consecutive layers of the *same network* are assigned to different paths.
    Bytes are estimated from the producer layer's output activation size.
    """
    total = 0.0
    # ResNet in-order
    for prev, nxt, a_prev, a_nxt in zip(r_layers[:-1], r_layers[1:], assign_a_r[:-1], assign_a_r[1:]):
        if a_prev != a_nxt:
            total += _bytes_for_activation("resnet50", prev, element_bytes=element_bytes, dataflow=producer_df)
    # MobileNet in-order
    for prev, nxt, a_prev, a_nxt in zip(m_layers[:-1], m_layers[1:], assign_a_m[:-1], assign_a_m[1:]):
        if a_prev != a_nxt:
            total += _bytes_for_activation("mobilenet_v2", prev, element_bytes=element_bytes, dataflow=producer_df)
    return total


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start-r", type=int, default=0)
    p.add_argument("--start-m", type=int, default=0)
    p.add_argument("--count-r", type=int, default=4)
    p.add_argument("--count-m", type=int, default=4)
    p.add_argument("--micro-batches", type=int, default=8, help="Repeat the same forward schedule this many times.")
    p.add_argument("--merge", choices=["resnet_first", "interleave"], default="resnet_first")
    p.add_argument("--t-comm", type=float, default=0.0, help="Buffer transfer cycles (same both paths).")
    p.add_argument("--out-csv", default="")
    p.add_argument("--max-total-layers", type=int, default=16, help="Safety cap for brute-force 2^n.")
    p.add_argument("--shared-bw-gbps", type=float, default=0.0, help="Shared BW before the system (GB/s). If >0, adds comm cycles.")
    p.add_argument("--clock-hz", type=float, default=1e9, help="Clock used to convert GB/s+bytes into cycles.")
    p.add_argument("--element-bytes", type=int, default=2, help="Bytes per activation element (for comm size proxy).")
    args = p.parse_args()

    r_layers = _layer_order("resnet50")[args.start_r : args.start_r + args.count_r]
    m_layers = _layer_order("mobilenet_v2")[args.start_m : args.start_m + args.count_m]
    if len(r_layers) != args.count_r or len(m_layers) != args.count_m:
        raise SystemExit("Not enough layers for requested window.")

    Lr, Lm = len(r_layers), len(m_layers)
    if Lr + Lm > args.max_total_layers:
        raise SystemExit(f"Lr+Lm={Lr+Lm} exceeds --max-total-layers={args.max_total_layers}")

    acc0_a, acc1_a = "NVDLA_WS", "Eyeriss_RS"
    acc0_b, acc1_b = "NVDLA_WS", "ShiDianNao_OS"

    best_wall = float("inf")
    best: dict = {}
    best_comm_bytes = 0.0

    for bits_r in itertools.product((0, 1), repeat=Lr):
        for bits_m in itertools.product((0, 1), repeat=Lm):
            assign_a_r = list(bits_r)
            assign_a_m = list(bits_m)
            assign_b_r = [1 - x for x in assign_a_r]
            assign_b_m = [1 - x for x in assign_a_m]

            path_a = merge_layers_for_path(r_layers, m_layers, assign_a_r, assign_a_m, mode=args.merge)
            path_b = merge_layers_for_path(r_layers, m_layers, assign_b_r, assign_b_m, mode=args.merge)

            # Each path must be empty or have a valid packing (>=2 layers)
            if len(path_a) == 1 or len(path_b) == 1:
                continue

            ms_a, sim_a, shape_a, t0a, t1a = best_path_schedule(
                path_a, acc0_a, acc1_a, args.t_comm, args.micro_batches
            )
            ms_b, sim_b, shape_b, t0b, t1b = best_path_schedule(
                path_b, acc0_b, acc1_b, args.t_comm, args.micro_batches
            )
            if ms_a == float("inf") or ms_b == float("inf"):
                continue

            # inter-path communication penalty (if network alternates paths)
            comm_bytes = _inter_path_comm_bytes(
                r_layers,
                m_layers,
                assign_a_r,
                assign_a_m,
                element_bytes=args.element_bytes,
            ) * float(args.micro_batches)

            comm_cycles = bytes_to_cycles_transfer(comm_bytes, args.shared_bw_gbps, args.clock_hz)
            wall = max(ms_a, ms_b) + comm_cycles

            if wall < best_wall:
                best_wall = wall
                best_comm_bytes = comm_bytes
                best = {
                    "bits_r": assign_a_r,
                    "bits_m": assign_a_m,
                    "path_a": path_a,
                    "path_b": path_b,
                    "ms_a": ms_a,
                    "ms_b": ms_b,
                    "sim_a": sim_a,
                    "sim_b": sim_b,
                    "shape_a": shape_a,
                    "shape_b": shape_b,
                    "t0a": t0a,
                    "t1a": t1a,
                    "t0b": t0b,
                    "t1b": t1b,
                    "comm_bytes": comm_bytes,
                    "comm_cycles": comm_cycles,
                }

    if not best:
        raise SystemExit("No valid assignment found (try different --count-* or --merge).")

    def fmt_assign(names: List[str], bits: List[int]) -> str:
        return "|".join(f"{nm}:{'A' if b else 'B'}" for nm, b in zip(names, bits))

    print("=== Dual series: optimal layer -> path assignment (sim wall time) ===")
    print(f"ResNet window ({Lr}): {r_layers}")
    print(f"MobileNet window ({Lm}): {m_layers}")
    print(f"merge={args.merge}  micro_batches={args.micro_batches}  T_comm={args.t_comm}")
    print("")
    print("Per-layer assignment (1=A path, 0=B path):")
    print(f"  ResNet:    {fmt_assign(r_layers, best['bits_r'])}")
    print(f"  MobileNet: {fmt_assign(m_layers, best['bits_m'])}")
    print("")
    print(f"Path A layers ({len(best['path_a'])}): {[x[1] for x in best['path_a']]}")
    print(f"  best batching (d0,d1): {best['shape_a']}  per-forward T0s={best['t0a']}  T1s={best['t1a']}")
    print(f"  makespan (sim): {best['ms_a']:,.3f}")
    print(f"Path B layers ({len(best['path_b'])}): {[x[1] for x in best['path_b']]}")
    print(f"  best batching (d0,d1): {best['shape_b']}  per-forward T0s={best['t0b']}  T1s={best['t1b']}")
    print(f"  makespan (sim): {best['ms_b']:,.3f}")
    print("")
    print(f"Shared BW (before system): {args.shared_bw_gbps} GB/s, clock_hz={args.clock_hz}, element_bytes={args.element_bytes}")
    print(f"Inter-path comm bytes (all micro-batches): {best['comm_bytes']:,.0f}")
    print(f"Inter-path comm cycles (shared BW): {best['comm_cycles']:,.3f}")
    print(f"Wall time (max(paths) + comm): {best_wall:,.3f} cycles")

    if args.out_csv:
        os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
        row_a = {
            "row_kind": "path",
            "path": "A",
            "network": "mixed",
            "acc0": acc0_a,
            "acc1": acc1_a,
            "layers": "|".join(f"{n}:{ly}" for n, ly in best["path_a"]),
            "batching": str(best["shape_a"]),
            "micro_batches": args.micro_batches,
            "T_comm": args.t_comm,
            "makespan_closed": f"{best['ms_a']:.6f}",
            "makespan_sim": f"{best['ms_a']:.6f}",
            "shared_bw_gbps": f"{args.shared_bw_gbps:.6f}",
            "comm_bytes_total": f"{best['comm_bytes']:.6f}",
            "comm_cycles_total": f"{best['comm_cycles']:.6f}",
            "stall0_full": f"{best['sim_a'].acc0_stall_full:.6f}",
            "stall1_empty": f"{best['sim_a'].acc1_stall_empty:.6f}",
        }
        row_b = {
            "row_kind": "path",
            "path": "B",
            "network": "mixed",
            "acc0": acc0_b,
            "acc1": acc1_b,
            "layers": "|".join(f"{n}:{ly}" for n, ly in best["path_b"]),
            "batching": str(best["shape_b"]),
            "micro_batches": args.micro_batches,
            "T_comm": args.t_comm,
            "makespan_closed": f"{best['ms_b']:.6f}",
            "makespan_sim": f"{best['ms_b']:.6f}",
            "shared_bw_gbps": f"{args.shared_bw_gbps:.6f}",
            "comm_bytes_total": f"{best['comm_bytes']:.6f}",
            "comm_cycles_total": f"{best['comm_cycles']:.6f}",
            "stall0_full": f"{best['sim_b'].acc0_stall_full:.6f}",
            "stall1_empty": f"{best['sim_b'].acc1_stall_empty:.6f}",
        }
        row_w = {
            "row_kind": "wall",
            "path": "",
            "network": "wall",
            "acc0": "",
            "acc1": "",
            "layers": "",
            "batching": "",
            "micro_batches": args.micro_batches,
            "T_comm": args.t_comm,
            "makespan_closed": f"{best_wall:.6f}",
            "makespan_sim": f"{best_wall:.6f}",
            "shared_bw_gbps": f"{args.shared_bw_gbps:.6f}",
            "comm_bytes_total": f"{best['comm_bytes']:.6f}",
            "comm_cycles_total": f"{best['comm_cycles']:.6f}",
            "stall0_full": "",
            "stall1_empty": "",
        }
        fieldnames = list(row_a.keys())
        with open(args.out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in (row_a, row_b, row_w):
                w.writerow(r)
        print(f"Wrote {args.out_csv}")


if __name__ == "__main__":
    main()
