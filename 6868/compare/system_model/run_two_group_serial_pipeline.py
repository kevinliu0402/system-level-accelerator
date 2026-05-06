#!/usr/bin/env python3
"""
Two-Group Serial Pipeline with Double Buffer (2-slot ping-pong).

System:
  IN -> Acc0 -> (Buff0/Buff1 ping-pong) -> Acc1 -> OUT

Each accelerator group runs one *segment* per mini-batch:
  - Seg0 on Acc0: 1 or 2 consecutive DNN layers
  - Seg1 on Acc1: 1 or 2 consecutive DNN layers
  - Total layers modeled per run: 2 to 4 (segment depth <= 2, exactly 2 segments)

Timing model (per mini-batch):
  - T0: Acc0 compute time for Seg0
  - T1: Acc1 compute time for Seg1
  - T_comm: transfer time from Acc0 output buffer to Acc1 input (cycles)

We provide both:
  - Closed-form makespan (idealized, steady-state throughput)
  - Small event simulation (double-buffer stalls) for sanity checking

Layer times (T0/T1) come from MAESTRO per-layer Runtime (Cycles) for chosen dataflows.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from compare.system_model.maestro_layer_metrics import (
    layer_latency_and_bw_req,
    list_mobilenet_v2_layer_order,
    list_resnet50_layer_order,
    list_squeezenet1_0_layer_order,
)
from compare.system_model.noc_dram import bytes_to_cycles_transfer


def _layer_order(network: str) -> List[str]:
    n = network.lower().strip()
    if n == "resnet50":
        return list_resnet50_layer_order()
    if n == "mobilenet_v2":
        return list_mobilenet_v2_layer_order()
    if n == "squeezenet1_0":
        return list_squeezenet1_0_layer_order()
    raise KeyError(f"Unsupported network: {network}")


def _seg_latency_cycles(network: str, layers: List[str], dataflow: str) -> float:
    return sum(layer_latency_and_bw_req(network, lyr, dataflow)[0] for lyr in layers)


def pipeline_makespan_closed_form(T0: float, T1: float, T_comm: float, N: int) -> float:
    """
    Idealized 2-stage pipeline with a comm gap before stage1.

    Derivation (stage1 service includes comm):
      stage0 service time = T0
      stage1 service time = T_comm + T1
      first output at: T0 + T_comm + T1
      steady-state period: max(T0, T_comm + T1)

    Total makespan:
      (first output) + (N-1)*period
    """
    if N <= 0:
        return 0.0
    period = max(T0, T_comm + T1)
    return (T0 + T_comm + T1) + (N - 1) * period


@dataclass
class SimResult:
    makespan: float
    acc0_busy: float
    acc1_busy: float
    acc0_stall_full: float
    acc1_stall_empty: float


def pipeline_simulate_double_buffer(T0: float, T1: float, T_comm: float, N: int) -> SimResult:
    """
    Discrete-event simulation with a 2-slot buffer between stage0 and stage1.
    Acc0 produces one token per batch after T0.
    Acc1 consumes one token per batch; it must wait for token, then pay T_comm before T1.
    """
    if N <= 0:
        return SimResult(0.0, 0.0, 0.0, 0.0, 0.0)

    t = 0.0
    buf = 0  # 0..2 tokens currently stored (produced by Acc0, not yet consumed by Acc1)
    b0_started = 0
    b0_done = 0
    b1_started = 0
    b1_done = 0

    acc0_free = 0.0
    acc1_free = 0.0
    next_acc0_done: float = float("inf")
    next_acc1_done: float = float("inf")

    acc0_busy = 0.0
    acc1_busy = 0.0
    acc0_stall_full = 0.0
    acc1_stall_empty = 0.0

    def update_event_times() -> None:
        nonlocal next_acc0_done, next_acc1_done
        next_acc0_done = acc0_free if b0_started > b0_done else float("inf")
        next_acc1_done = acc1_free if b1_started > b1_done else float("inf")

    update_event_times()

    while b1_done < N:
        # advance to next completion event (Acc0 finishes seg0 or Acc1 finishes seg1)
        t_next = min(next_acc0_done, next_acc1_done)
        if t_next == float("inf"):
            # nothing in flight; try to start work below
            t_next = t
        t = max(t, t_next)

        # apply completions at time t
        if abs(t - next_acc0_done) <= 1e-12:
            buf = min(2, buf + 1)
            b0_done += 1
            update_event_times()
        if abs(t - next_acc1_done) <= 1e-12:
            b1_done += 1
            update_event_times()

        progressed = False

        # try to start Acc1 if idle and data available
        if t >= acc1_free - 1e-12 and b1_started < N:
            if buf > 0:
                buf -= 1
                b1_started += 1
                acc1_busy += (T_comm + T1)
                acc1_free = t + T_comm + T1
                update_event_times()
                progressed = True
            else:
                # stall until Acc0 produces a token (next_acc0_done)
                if next_acc0_done != float("inf") and next_acc0_done > t:
                    acc1_stall_empty += next_acc0_done - t
                    acc1_free = next_acc0_done
                    update_event_times()
                    progressed = True

        # try to start Acc0 if idle and buffer has space
        if t >= acc0_free - 1e-12 and b0_started < N:
            if buf < 2:
                b0_started += 1
                acc0_busy += T0
                acc0_free = t + T0
                update_event_times()
                progressed = True
            else:
                # stall until Acc1 consumes a token (next_acc1_done or Acc1 start)
                if next_acc1_done != float("inf") and next_acc1_done > t:
                    acc0_stall_full += next_acc1_done - t
                    acc0_free = next_acc1_done
                    update_event_times()
                    progressed = True

        if not progressed:
            # nudge time to avoid stalling on exact ties
            t += 1e-9

    return SimResult(
        makespan=max(acc0_free, acc1_free),
        acc0_busy=acc0_busy,
        acc1_busy=acc1_busy,
        acc0_stall_full=acc0_stall_full,
        acc1_stall_empty=acc1_stall_empty,
    )


def pipeline_simulate_double_buffer_sequence(
    T0s: Sequence[float],
    T1s: Sequence[float],
    T_comm: float,
) -> SimResult:
    """
    Same double-buffer semantics as ``pipeline_simulate_double_buffer``, but each pipeline
    batch k uses its own (T0s[k], T1s[k]) service times (e.g. different layer groupings).
    """
    N = len(T0s)
    if N == 0:
        return SimResult(0.0, 0.0, 0.0, 0.0, 0.0)
    if len(T1s) != N:
        raise ValueError("T0s and T1s must have the same length")

    t = 0.0
    buf = 0
    b0_started = 0
    b0_done = 0
    b1_started = 0
    b1_done = 0

    acc0_free = 0.0
    acc1_free = 0.0
    next_acc0_done: float = float("inf")
    next_acc1_done: float = float("inf")

    acc0_busy = 0.0
    acc1_busy = 0.0
    acc0_stall_full = 0.0
    acc1_stall_empty = 0.0

    def update_event_times() -> None:
        nonlocal next_acc0_done, next_acc1_done
        next_acc0_done = acc0_free if b0_started > b0_done else float("inf")
        next_acc1_done = acc1_free if b1_started > b1_done else float("inf")

    update_event_times()

    while b1_done < N:
        t_next = min(next_acc0_done, next_acc1_done)
        if t_next == float("inf"):
            t_next = t
        t = max(t, t_next)

        if abs(t - next_acc0_done) <= 1e-12:
            buf = min(2, buf + 1)
            b0_done += 1
            update_event_times()
        if abs(t - next_acc1_done) <= 1e-12:
            b1_done += 1
            update_event_times()

        progressed = False

        if t >= acc1_free - 1e-12 and b1_started < N:
            if buf > 0:
                buf -= 1
                idx = b1_started
                acc1_busy += T_comm + T1s[idx]
                acc1_free = t + T_comm + T1s[idx]
                b1_started += 1
                update_event_times()
                progressed = True
            else:
                if next_acc0_done != float("inf") and next_acc0_done > t:
                    acc1_stall_empty += next_acc0_done - t
                    acc1_free = next_acc0_done
                    update_event_times()
                    progressed = True

        if t >= acc0_free - 1e-12 and b0_started < N:
            if buf < 2:
                idx = b0_started
                acc0_busy += T0s[idx]
                acc0_free = t + T0s[idx]
                b0_started += 1
                update_event_times()
                progressed = True
            else:
                if next_acc1_done != float("inf") and next_acc1_done > t:
                    acc0_stall_full += next_acc1_done - t
                    acc0_free = next_acc1_done
                    update_event_times()
                    progressed = True

        if not progressed:
            t += 1e-9

    return SimResult(
        makespan=max(acc0_free, acc1_free),
        acc0_busy=acc0_busy,
        acc1_busy=acc1_busy,
        acc0_stall_full=acc0_stall_full,
        acc1_stall_empty=acc1_stall_empty,
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--network", default="resnet50", help="resnet50 | mobilenet_v2 | squeezenet1_0")
    p.add_argument("--acc0-df", default="NVDLA_WS", help="MAESTRO dataflow name for Acc0")
    p.add_argument("--acc1-df", default="Eyeriss_RS", help="MAESTRO dataflow name for Acc1")
    p.add_argument("--layers", default="", help="Comma-separated layer names (2..4). If empty, use --start/--count.")
    p.add_argument("--start", type=int, default=0, help="Start index into the network's layer list (used when --layers empty).")
    p.add_argument("--count", type=int, default=4, help="How many consecutive layers to model (2..4).")
    p.add_argument("--seg0-depth", type=int, default=2, choices=[1, 2])
    p.add_argument("--seg1-depth", type=int, default=2, choices=[1, 2])
    p.add_argument("--batches", type=int, default=8, help="Number of mini-batches N.")

    # Communication: either specify cycles directly, or derive from bytes + link BW + clock.
    p.add_argument("--t-comm-cycles", type=float, default=-1.0)
    p.add_argument("--comm-bytes", type=float, default=0.0)
    p.add_argument("--comm-bw-gbps", type=float, default=0.0)
    p.add_argument("--clock-hz", type=float, default=1e9)

    p.add_argument("--search", action="store_true", help="Search over valid (seg0-depth, seg1-depth) and report best.")
    p.add_argument("--out-csv", default="", help="Optional: write evaluated segmentations to CSV.")
    args = p.parse_args()

    if args.layers.strip():
        chosen_layers = [x.strip() for x in args.layers.split(",") if x.strip()]
    else:
        order = _layer_order(args.network)
        chosen_layers = order[args.start : args.start + args.count]

    if not (2 <= len(chosen_layers) <= 4):
        raise SystemExit(f"Need 2..4 layers, got {len(chosen_layers)}: {chosen_layers}")

    if args.t_comm_cycles >= 0:
        T_comm = float(args.t_comm_cycles)
    else:
        T_comm = bytes_to_cycles_transfer(args.comm_bytes, args.comm_bw_gbps, args.clock_hz)

    def eval_depths(d0: int, d1: int) -> Tuple[float, float, float, float, List[str], List[str]]:
        if d0 + d1 != len(chosen_layers):
            return float("inf"), 0.0, 0.0, 0.0, [], []
        seg0 = chosen_layers[:d0]
        seg1 = chosen_layers[d0:]
        T0 = _seg_latency_cycles(args.network, seg0, args.acc0_df)
        T1 = _seg_latency_cycles(args.network, seg1, args.acc1_df)
        mk = pipeline_makespan_closed_form(T0, T1, T_comm, args.batches)
        return mk, T0, T1, T_comm, seg0, seg1

    candidates = [(args.seg0_depth, args.seg1_depth)]
    if args.search:
        candidates = [(1, 1), (1, 2), (2, 1), (2, 2)]

    rows_out: List[dict] = []
    best = None
    for d0, d1 in candidates:
        mk, T0, T1, Tc, seg0, seg1 = eval_depths(d0, d1)
        if mk == float("inf"):
            continue
        sim = pipeline_simulate_double_buffer(T0, T1, Tc, args.batches)
        rows_out.append(
            {
                "network": args.network,
                "acc0_df": args.acc0_df,
                "acc1_df": args.acc1_df,
                "layers": "|".join(chosen_layers),
                "seg0_depth": d0,
                "seg1_depth": d1,
                "seg0_layers": "|".join(seg0),
                "seg1_layers": "|".join(seg1),
                "batches": args.batches,
                "T0": f"{T0:.6f}",
                "T1": f"{T1:.6f}",
                "T_comm": f"{Tc:.6f}",
                "makespan_closed": f"{mk:.6f}",
                "makespan_sim": f"{sim.makespan:.6f}",
                "acc0_stall_full": f"{sim.acc0_stall_full:.6f}",
                "acc1_stall_empty": f"{sim.acc1_stall_empty:.6f}",
            }
        )
        if best is None or mk < best[0]:
            best = (mk, T0, T1, Tc, d0, d1, seg0, seg1, sim)

    if best is None:
        raise SystemExit("No valid segmentation (segment depths must sum to number of layers).")

    mk, T0, T1, Tc, d0, d1, seg0, seg1, sim = best
    print("=== Two-Group Serial Pipeline (Double Buffer) ===")
    print(f"network: {args.network}")
    print(f"Acc0 dataflow: {args.acc0_df}")
    print(f"Acc1 dataflow: {args.acc1_df}")
    print(f"layers modeled ({len(chosen_layers)}): {chosen_layers}")
    print(f"Seg0 depth={d0}: {seg0}")
    print(f"Seg1 depth={d1}: {seg1}")
    print("")
    print(f"T0 (Acc0 seg0)   = {T0:,.3f} cycles")
    print(f"T1 (Acc1 seg1)   = {T1:,.3f} cycles")
    print(f"T_comm (buffer)  = {Tc:,.3f} cycles")
    print(f"N (mini-batches) = {args.batches}")
    print("")
    print(f"Closed-form makespan: {mk:,.3f} cycles")
    print(f"Simulated makespan:   {sim.makespan:,.3f} cycles")
    print(f"  Acc0 busy:          {sim.acc0_busy:,.3f} cycles")
    print(f"  Acc1 busy:          {sim.acc1_busy:,.3f} cycles")
    print(f"  Acc0 stall(full):   {sim.acc0_stall_full:,.3f} cycles")
    print(f"  Acc1 stall(empty):  {sim.acc1_stall_empty:,.3f} cycles")

    if args.out_csv and rows_out:
        os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
        fieldnames = list(rows_out[0].keys())
        with open(args.out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows_out:
                w.writerow(r)
        print(f"Wrote {args.out_csv}")


if __name__ == "__main__":
    main()

