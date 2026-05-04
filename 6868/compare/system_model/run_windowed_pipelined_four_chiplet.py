#!/usr/bin/env python3
"""
Windowed (receding-horizon) scheduler + simple accelerator pipelining model on 4 heterogeneous chiplets.

Compared to run_greedy_four_chiplet.py:
  - Uses a sliding planning window (WINDOW_CYCLES) advanced by WINDOW_STRIDE.
  - Splits each layer into two phases:
      MEM: consumes shared bandwidth (req_bw) for MEM_FRAC * L
      COMP: consumes no shared bandwidth for (1-MEM_FRAC) * L
    This exposes overlap opportunities where compute phases can overlap with other jobs' MEM phases.

This model is intentionally lightweight: BW contention is only modeled among jobs launched at the same
dispatch instant (same "step") using a MAGMA-style proportional allocator. Later dispatches do not
contend with earlier dispatches' MEM phases (approximation).

Outputs a CSV with per-network phase rows (for Gantt) plus one summary row per step.
"""

from __future__ import annotations

import csv
import itertools
import os
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from compare.system_model.maestro_layer_metrics import (
    layer_latency_and_bw_req,
    list_mobilenet_v2_layer_order,
    list_resnet50_layer_order,
    list_squeezenet1_0_layer_order,
)


CHIPLET_DF: Dict[int, str] = {
    0: "NVDLA_WS",
    1: "NVDLA_WS",
    2: "ShiDianNao_OS",
    3: "Eyeriss_RS",
}

TAG_R, TAG_M, TAG_S = "resnet50", "mobilenet_v2", "squeezenet1_0"


@dataclass(frozen=True)
class PhaseJob:
    network: str
    layer: str
    chiplet: int
    L_total: float
    bw_req: float
    L_mem: float
    L_comp: float


@dataclass(frozen=True)
class MemAllocResult:
    mem_makespan: float
    mem_done: Dict[int, float]  # chiplet -> time since slice start when MEM completes
    bw_util_mem: float          # utilization over MEM portion only (same definition as MAGMA)
    wasted_bw_area_mem: float


def _metrics(network: str, layer: str, chiplet_id: int) -> Tuple[float, float]:
    df = CHIPLET_DF[chiplet_id]
    L, bw, _path, _proxied = layer_latency_and_bw_req(network, layer, df)
    return float(L), float(bw)


def _split_layer(L: float, bw: float, mem_frac: float) -> Tuple[float, float, float]:
    mem_frac = max(0.0, min(1.0, mem_frac))
    L_mem = mem_frac * L
    L_comp = (1.0 - mem_frac) * L
    return L_mem, L_comp, bw


def _proportional_alloc(req_bws: List[float], total_bw: float) -> List[float]:
    s = sum(req_bws)
    if total_bw <= 0 or s <= 0:
        return [0.0 for _ in req_bws]
    if s <= total_bw:
        return list(req_bws)
    scale = total_bw / s
    return [bw * scale for bw in req_bws]


def _alloc_mem_completion_times(
    jobs: List[PhaseJob],
    total_bw: float,
    *,
    eps: float = 1e-12,
) -> MemAllocResult:
    """
    MAGMA-style allocator for a *single* MEM phase per active chiplet.
    Returns per-chiplet MEM completion times (relative to slice start).
    """
    if not jobs:
        return MemAllocResult(
            mem_makespan=0.0,
            mem_done={},
            bw_util_mem=0.0,
            wasted_bw_area_mem=0.0,
        )

    # one MEM job per chiplet in this slice
    chiplets = [j.chiplet for j in jobs]
    req_bw = [j.bw_req for j in jobs]
    remaining_auc = [j.L_mem * j.bw_req for j in jobs]
    done = [False for _ in jobs]
    mem_done: Dict[int, float] = {}

    t = 0.0
    wasted = 0.0
    # run until all MEM phases complete (COMP handled separately)
    while not all(done):
        alloc = _proportional_alloc([0.0 if done[i] else req_bw[i] for i in range(len(jobs))], total_bw)
        used = sum(alloc)
        waste = max(0.0, total_bw - used)

        times: List[float] = []
        for i in range(len(jobs)):
            if done[i]:
                times.append(float("inf"))
                continue
            bw_i = alloc[i]
            if bw_i <= eps:
                times.append(float("inf"))
            else:
                times.append(remaining_auc[i] / bw_i)
        dt = min(times)
        if dt == float("inf"):
            # no progress possible (e.g., total_bw=0)
            break

        wasted += waste * dt
        t += dt

        for i in range(len(jobs)):
            if done[i]:
                continue
            remaining_auc[i] -= alloc[i] * dt
            if remaining_auc[i] <= eps:
                done[i] = True
                mem_done[chiplets[i]] = t

    mem_makespan = t
    if mem_makespan <= eps or total_bw <= eps:
        util = 0.0
    else:
        util = 1.0 - wasted / (total_bw * mem_makespan)
        util = max(0.0, min(1.0, util))
    return MemAllocResult(
        mem_makespan=mem_makespan,
        mem_done=mem_done,
        bw_util_mem=util,
        wasted_bw_area_mem=wasted,
    )


def _simulate_slice(
    jobs: List[PhaseJob],
    total_bw: float,
) -> Tuple[float, float, Dict[int, Tuple[float, float]]]:
    """
    Simulate a slice where all MEM phases start together at slice start.
    Returns:
      - makespan (until all COMP phases complete)
      - bw_util over full slice (MEM + COMP tail, where BW is idle)
      - per-chiplet (mem_end, comp_end) relative times
    """
    mem = _alloc_mem_completion_times(jobs, total_bw)
    per_chip: Dict[int, Tuple[float, float]] = {}
    makespan = 0.0
    for j in jobs:
        mem_end = mem.mem_done.get(j.chiplet, mem.mem_makespan)
        comp_end = mem_end + j.L_comp
        per_chip[j.chiplet] = (mem_end, comp_end)
        makespan = max(makespan, comp_end)

    # compute bw_util over full slice duration
    if makespan <= 1e-12 or total_bw <= 1e-12:
        util_full = 0.0
    else:
        wasted = mem.wasted_bw_area_mem + total_bw * max(0.0, makespan - mem.mem_makespan)
        util_full = 1.0 - wasted / (total_bw * makespan)
        util_full = max(0.0, min(1.0, util_full))
    return makespan, util_full, per_chip


def _available_chiplets(chiplet_free: List[float], t: float) -> List[int]:
    return [c for c in range(len(chiplet_free)) if chiplet_free[c] <= t + 1e-9]


def _ready_networks(
    next_idx: Dict[str, int],
    layers: Dict[str, List[str]],
    net_ready_t: Dict[str, float],
    t: float,
) -> List[Tuple[str, int, str]]:
    out: List[Tuple[str, int, str]] = []
    for net, idx in next_idx.items():
        if idx >= len(layers[net]):
            continue
        if net_ready_t[net] <= t + 1e-9:
            out.append((net, idx, layers[net][idx]))
    return out


def _dispatch_candidates(
    t: float,
    avail_chips: List[int],
    ready: List[Tuple[str, int, str]],
    total_bw: float,
    mem_frac: float,
) -> Iterable[Tuple[List[PhaseJob], float, float, Dict[int, Tuple[float, float]], List[Tuple[str, int, str]]]]:
    """
    Enumerate candidate dispatches: choose k ready networks (k<=len(avail_chips)) and assign to distinct chips.
    Yields (jobs, makespan, bw_util_full, per_chip_times, chosen_ready).
    """
    if not avail_chips or not ready:
        return []

    max_k = min(len(avail_chips), len(ready))
    out = []
    # prefer dispatching more jobs when possible (explore k=max_k down to 1)
    for k in range(max_k, 0, -1):
        for chosen in itertools.combinations(ready, k):
            for chips in itertools.permutations(avail_chips, k):
                jobs: List[PhaseJob] = []
                for (net, _idx, lyr), c in zip(chosen, chips):
                    L, bw = _metrics(net, lyr, c)
                    L_mem, L_comp, bw_req = _split_layer(L, bw, mem_frac)
                    jobs.append(
                        PhaseJob(
                            network=net,
                            layer=lyr,
                            chiplet=c,
                            L_total=L,
                            bw_req=bw_req,
                            L_mem=L_mem,
                            L_comp=L_comp,
                        )
                    )
                ms, util, per_chip = _simulate_slice(jobs, total_bw)
                out.append((jobs, ms, util, per_chip, list(chosen)))
    return out


def _score_state(
    chiplet_free: List[float],
    next_idx: Dict[str, int],
    layers: Dict[str, List[str]],
) -> float:
    # lower is better; approximate global completion as max chiplet time + remaining layers count penalty
    base = max(chiplet_free) if chiplet_free else 0.0
    rem = 0
    for net, idx in next_idx.items():
        rem += max(0, len(layers[net]) - idx)
    return base + 1e-6 * rem


def _lookahead_pick(
    t: float,
    avail_chips: List[int],
    ready: List[Tuple[str, int, str]],
    chiplet_free: List[float],
    net_ready_t: Dict[str, float],
    next_idx: Dict[str, int],
    layers: Dict[str, List[str]],
    total_bw: float,
    mem_frac: float,
    window_end: float,
    lookahead_steps: int,
    beam_width: int,
) -> Optional[Tuple[List[PhaseJob], float, float, Dict[int, Tuple[float, float]], List[Tuple[str, int, str]]]]:
    """
    Limited lookahead with beam search over dispatch actions within a window.
    Returns the first action of the best sequence (lowest predicted score at window end).
    """
    cands = list(_dispatch_candidates(t, avail_chips, ready, total_bw, mem_frac))
    if not cands:
        return None

    # state tuple: (score, first_action, chiplet_free, net_ready_t, next_idx, t_current)
    beam: List[Tuple[float, Tuple, List[float], Dict[str, float], Dict[str, int], float]] = []
    for a in cands:
        jobs, ms, util, per_chip, chosen = a
        cf = list(chiplet_free)
        nrt = dict(net_ready_t)
        nidx = dict(next_idx)
        # apply action
        for j in jobs:
            mem_end, comp_end = per_chip[j.chiplet]
            abs_comp_end = t + comp_end
            cf[j.chiplet] = abs_comp_end
            nrt[j.network] = abs_comp_end
            nidx[j.network] += 1
        t2 = min(cf) if cf else t + ms
        beam.append((_score_state(cf, nidx, layers), a, cf, nrt, nidx, t2))
    beam.sort(key=lambda x: x[0])
    beam = beam[: max(1, beam_width)]

    # expand
    for _depth in range(1, max(1, lookahead_steps)):
        new_beam: List[Tuple[float, Tuple, List[float], Dict[str, float], Dict[str, int], float]] = []
        for score0, first_a, cf, nrt, nidx, tcur in beam:
            if tcur > window_end + 1e-9:
                new_beam.append((score0, first_a, cf, nrt, nidx, tcur))
                continue
            avail2 = _available_chiplets(cf, tcur)
            ready2 = _ready_networks(nidx, layers, nrt, tcur)
            c2 = list(_dispatch_candidates(tcur, avail2, ready2, total_bw, mem_frac))
            if not c2:
                new_beam.append((score0, first_a, cf, nrt, nidx, tcur))
                continue
            for a2 in c2:
                jobs2, _ms2, _util2, per_chip2, _chosen2 = a2
                cf2 = list(cf)
                nrt2 = dict(nrt)
                nidx2 = dict(nidx)
                for j in jobs2:
                    _mem_end, comp_end = per_chip2[j.chiplet]
                    abs_comp_end = tcur + comp_end
                    cf2[j.chiplet] = abs_comp_end
                    nrt2[j.network] = abs_comp_end
                    nidx2[j.network] += 1
                tnext = min(cf2) if cf2 else tcur
                new_beam.append((_score_state(cf2, nidx2, layers), first_a, cf2, nrt2, nidx2, tnext))
        new_beam.sort(key=lambda x: x[0])
        beam = new_beam[: max(1, beam_width)]

    beam.sort(key=lambda x: x[0])
    return beam[0][1]  # first_action


def main() -> None:
    total_bw = float(os.environ.get("SYSTEM_BW", "100.0"))
    out_csv = os.environ.get(
        "WP4_OUT_CSV",
        os.path.join(REPO, "compare", "results", "windowed_pipelined_four_chiplet_schedule.csv"),
    )

    window_cycles = float(os.environ.get("WINDOW_CYCLES", "5000000"))
    window_stride = float(os.environ.get("WINDOW_STRIDE", str(window_cycles)))
    mem_frac = float(os.environ.get("MEM_FRAC", "0.30"))
    lookahead_steps = int(os.environ.get("LOOKAHEAD_STEPS", "2"))
    beam_width = int(os.environ.get("BEAM_WIDTH", "8"))
    max_steps = int(os.environ.get("WP4_MAX_STEPS", "0"))

    layers: Dict[str, List[str]] = {
        TAG_R: list_resnet50_layer_order(),
        TAG_M: list_mobilenet_v2_layer_order(),
        TAG_S: list_squeezenet1_0_layer_order(),
    }
    next_idx: Dict[str, int] = {TAG_R: 0, TAG_M: 0, TAG_S: 0}
    # next time this network may launch a new layer (single-stream dependency)
    net_ready_t: Dict[str, float] = {TAG_R: 0.0, TAG_M: 0.0, TAG_S: 0.0}
    chiplet_free = [0.0, 0.0, 0.0, 0.0]

    rows: List[dict] = []
    step = 0
    epoch = 0
    t_epoch = 0.0
    t = 0.0

    def any_left() -> bool:
        return any(next_idx[n] < len(layers[n]) for n in layers)

    while any_left():
        if max_steps and step >= max_steps:
            break

        # advance time to the next event where something can be dispatched
        t = min(chiplet_free) if chiplet_free else t
        # if nothing is ready at that time, jump to earliest net_ready_t that is >= t
        ready_now = _ready_networks(next_idx, layers, net_ready_t, t)
        if not ready_now:
            # Only consider networks that still have layers; finished nets keep old net_ready_t
            # and would otherwise pin min(...) in the past and cause a bogus early exit.
            unfinished = [n for n in layers if next_idx[n] < len(layers[n])]
            if not unfinished:
                break
            t2 = min(net_ready_t[n] for n in unfinished)
            t = max(t, t2)
            ready_now = _ready_networks(next_idx, layers, net_ready_t, t)
        if not ready_now:
            break

        # manage epochs/windows
        if t >= t_epoch + window_stride - 1e-9:
            epoch += 1
            t_epoch = t
        window_end = t_epoch + window_cycles

        avail = _available_chiplets(chiplet_free, t)
        if not avail:
            continue

        pick = _lookahead_pick(
            t=t,
            avail_chips=avail,
            ready=ready_now,
            chiplet_free=chiplet_free,
            net_ready_t=net_ready_t,
            next_idx=next_idx,
            layers=layers,
            total_bw=total_bw,
            mem_frac=mem_frac,
            window_end=window_end,
            lookahead_steps=lookahead_steps,
            beam_width=beam_width,
        )
        if pick is None:
            break

        jobs, ms, util, per_chip, chosen = pick
        step += 1

        # phase rows (per job) for the Gantt
        for j in jobs:
            mem_end, comp_end = per_chip[j.chiplet]
            rows.append(
                {
                    "row_kind": "phase",
                    "step": step,
                    "epoch": epoch,
                    "t_epoch": f"{t_epoch:.6f}",
                    "window_cycles": f"{window_cycles:.6f}",
                    "window_stride": f"{window_stride:.6f}",
                    "mode": {1: "single", 2: "pair", 3: "triple"}.get(len(jobs), "multi"),
                    "phase": "mem",
                    "network": j.network,
                    "layer": j.layer,
                    "chiplet": j.chiplet,
                    "start": f"{t:.6f}",
                    "end": f"{t + mem_end:.6f}",
                    "L_phase": f"{j.L_mem:.6f}",
                    "bw_phase": f"{j.bw_req:.6f}",
                    "slice_makespan": f"{ms:.6f}",
                    "bw_util": f"{util:.6f}",
                }
            )
            rows.append(
                {
                    "row_kind": "phase",
                    "step": step,
                    "epoch": epoch,
                    "t_epoch": f"{t_epoch:.6f}",
                    "window_cycles": f"{window_cycles:.6f}",
                    "window_stride": f"{window_stride:.6f}",
                    "mode": {1: "single", 2: "pair", 3: "triple"}.get(len(jobs), "multi"),
                    "phase": "comp",
                    "network": j.network,
                    "layer": j.layer,
                    "chiplet": j.chiplet,
                    "start": f"{t + mem_end:.6f}",
                    "end": f"{t + comp_end:.6f}",
                    "L_phase": f"{j.L_comp:.6f}",
                    "bw_phase": f"{0.0:.6f}",
                    "slice_makespan": f"{ms:.6f}",
                    "bw_util": f"{util:.6f}",
                }
            )

        # summary row for this dispatch step
        slice_end = max(t + per_chip[j.chiplet][1] for j in jobs) if jobs else t
        rows.append(
            {
                "row_kind": "step",
                "step": step,
                "epoch": epoch,
                "t_epoch": f"{t_epoch:.6f}",
                "window_cycles": f"{window_cycles:.6f}",
                "window_stride": f"{window_stride:.6f}",
                "mode": {1: "single", 2: "pair", 3: "triple"}.get(len(jobs), "multi"),
                "phase": "",
                "network": "",
                "layer": "",
                "chiplet": "",
                "start": f"{t:.6f}",
                "end": f"{slice_end:.6f}",
                "L_phase": "",
                "bw_phase": "",
                "slice_makespan": f"{ms:.6f}",
                "bw_util": f"{util:.6f}",
            }
        )

        # apply: each job frees its chiplet at its COMP end and advances its network
        for j in jobs:
            _mem_end, comp_end = per_chip[j.chiplet]
            abs_comp_end = t + comp_end
            chiplet_free[j.chiplet] = abs_comp_end
            net_ready_t[j.network] = abs_comp_end
            next_idx[j.network] += 1

    wall = max(chiplet_free) if chiplet_free else 0.0
    print(
        "Windowed+pipelined 4-chiplet schedule: "
        f"ResNet={len(layers[TAG_R])}, MobileNet={len(layers[TAG_M])}, "
        f"SqueezeNet={len(layers[TAG_S])}, steps={step}"
    )
    print(f"SYSTEM_BW={total_bw}")
    print(f"WINDOW_CYCLES={window_cycles}, WINDOW_STRIDE={window_stride}, MEM_FRAC={mem_frac}")
    print(f"LOOKAHEAD_STEPS={lookahead_steps}, BEAM_WIDTH={beam_width}")
    print(f"Wall time (max chiplet finish): {wall:,.0f} cycles")

    fieldnames = [
        "row_kind",
        "step",
        "epoch",
        "t_epoch",
        "window_cycles",
        "window_stride",
        "mode",
        "phase",
        "network",
        "layer",
        "chiplet",
        "start",
        "end",
        "L_phase",
        "bw_phase",
        "slice_makespan",
        "bw_util",
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