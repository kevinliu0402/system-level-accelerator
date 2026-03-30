"""
MAGMA Algorithm 1: Bandwidth (BW) Allocator.

This is an implementation of the BW allocation logic used in the MAGMA codebase
(HPCA'22) for multi-core accelerators with shared system bandwidth.

Core idea
---------
At any time, each core runs at most one job. Each job has:
  - no-stall latency L (time units)
  - required bandwidth bw_req (bandwidth units) to be compute-bound

Define remaining "area-under-curve" (AUC) work for a job as:
  auc = L * bw_req

Given allocated bandwidth bw_alloc, remaining time is:
  t = auc / bw_alloc

BW allocator rule (per time slice):
  - If sum(bw_req) <= BW_total: give each job its bw_req (no stalls).
  - Else: scale all jobs proportionally so allocations sum to BW_total:
        bw_alloc_i = bw_req_i * BW_total / sum(bw_req)

Then advance time until the next job completes (minimum t), update AUC, and
repeat (pull next job from that core if available).

This module is intentionally generic so you can plug in any (L, bw_req) you
estimate from MAESTRO/Timeloop + your DRAM traffic model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Job:
    """A single job on a core."""

    job_id: str
    no_stall_latency: float
    req_bw: float

    def auc(self) -> float:
        return self.no_stall_latency * self.req_bw


@dataclass(frozen=True)
class Slice:
    """One allocation slice until a completion event."""

    start_time: float
    duration: float
    bw_alloc: List[float]   # per core
    running_job_ids: List[Optional[str]]  # per core


@dataclass(frozen=True)
class AllocationResult:
    makespan: float
    bw_util: float
    slices: List[Slice]


def _proportional_alloc(req_bws: Sequence[float], total_bw: float) -> List[float]:
    s = sum(req_bws)
    if total_bw <= 0:
        return [0.0 for _ in req_bws]
    if s <= 0:
        return [0.0 for _ in req_bws]
    if s <= total_bw:
        return list(req_bws)
    scale = total_bw / s
    return [bw * scale for bw in req_bws]


def bw_allocator(
    core_job_queues: Sequence[Sequence[Job]],
    total_bw: float,
    *,
    return_slices: bool = True,
    eps: float = 1e-12,
) -> AllocationResult:
    """
    Implement MAGMA Algorithm 1 BW allocator over multiple cores.

    Inputs:
      - core_job_queues: list of per-core job lists (already ordered).
      - total_bw: shared bandwidth budget (same unit as Job.req_bw).

    Outputs:
      - makespan: total time until all jobs finish.
      - bw_util: 1 - (wasted_bw_area / (total_bw * makespan))
      - slices: optional timeline of allocations.
    """
    num_cores = len(core_job_queues)
    queues = [list(q) for q in core_job_queues]

    # Current running job per core.
    running: List[Optional[Job]] = [None] * num_cores
    remaining_auc: List[float] = [float("inf")] * num_cores
    req_bw: List[float] = [0.0] * num_cores
    job_ids: List[Optional[str]] = [None] * num_cores

    def pop_next(i: int) -> None:
        if queues[i]:
            j = queues[i].pop(0)
            running[i] = j
            remaining_auc[i] = j.auc()
            req_bw[i] = j.req_bw
            job_ids[i] = j.job_id
        else:
            running[i] = None
            remaining_auc[i] = float("inf")
            req_bw[i] = 0.0
            job_ids[i] = None

    for i in range(num_cores):
        pop_next(i)

    t = 0.0
    wasted_bw_area = 0.0
    out_slices: List[Slice] = []

    def any_running() -> bool:
        return any(j is not None for j in running)

    while any_running():
        alloc = _proportional_alloc(req_bw, total_bw)
        used = sum(alloc)
        waste = max(0.0, total_bw - used)

        # time-to-finish for each running job given its allocated bw
        times: List[float] = []
        for i in range(num_cores):
            if running[i] is None:
                times.append(float("inf"))
                continue
            bw_i = alloc[i]
            if bw_i <= eps:
                times.append(float("inf"))
            else:
                times.append(remaining_auc[i] / bw_i)

        dt = min(times)
        if dt == float("inf"):
            # no progress possible (e.g., total_bw=0). avoid infinite loop.
            break

        if return_slices:
            out_slices.append(
                Slice(
                    start_time=t,
                    duration=dt,
                    bw_alloc=list(alloc),
                    running_job_ids=list(job_ids),
                )
            )

        wasted_bw_area += waste * dt
        t += dt

        # advance and complete jobs that hit zero
        for i in range(num_cores):
            if running[i] is None:
                continue
            remaining_auc[i] -= alloc[i] * dt
            if remaining_auc[i] <= eps:
                pop_next(i)

    if t <= eps or total_bw <= eps:
        util = 0.0
    else:
        util = 1.0 - wasted_bw_area / (total_bw * t)
        util = max(0.0, min(1.0, util))

    return AllocationResult(makespan=t, bw_util=util, slices=out_slices if return_slices else [])


def make_two_core_combo(
    a_name: str,
    a_latency: float,
    a_req_bw: float,
    b_name: str,
    b_latency: float,
    b_req_bw: float,
) -> List[List[Job]]:
    """Convenience: one job on core0 and one job on core1."""
    return [
        [Job(job_id=a_name, no_stall_latency=a_latency, req_bw=a_req_bw)],
        [Job(job_id=b_name, no_stall_latency=b_latency, req_bw=b_req_bw)],
    ]

