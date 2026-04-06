#!/usr/bin/env python3
"""
Run SCAR-inspired multi-model scenarios on the 2-core MAGMA bandwidth allocator.

Each scenario places two concurrent jobs (two models / layers / dataflows).  Per-job
latency L and required bandwidth come from MAESTRO CSV rows (Runtime + Avg BW Req),
not from summary_table.csv.

Workload list: scar_workloads.json (see paper SCAR, arXiv:2405.00790).
"""

from __future__ import annotations

import csv
import json
import os
import sys
from typing import Any, Dict, List

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from compare.system_model.maestro_layer_metrics import layer_latency_and_bw_req
from compare.system_model.magma_bw_allocator import Job, bw_allocator


def _job_label(j: Dict[str, Any]) -> str:
    return f"{j['network']}/{j['layer']}/{j['dataflow']}"


def run_scenario(
    scenario: Dict[str, Any],
    total_bw: float,
) -> Dict[str, Any]:
    jobs_spec = scenario["jobs"]
    if len(jobs_spec) != 2:
        raise ValueError(f"Scenario {scenario['id']}: expected exactly 2 jobs")

    jobs: List[Job] = []
    meta: List[str] = []
    for j in jobs_spec:
        L, bw, path, proxied = layer_latency_and_bw_req(
            j["network"], j["layer"], j["dataflow"]
        )
        jobs.append(
            Job(job_id=_job_label(j), no_stall_latency=L, req_bw=bw),
        )
        note = f"csv={os.path.basename(path)}"
        if proxied:
            note += " [MobileNet: OS/RS metrics proxied from WS CSV]"
        meta.append(note)

    queues = [[jobs[0]], [jobs[1]]]
    res = bw_allocator(queues, total_bw)

    return {
        "scenario_id": scenario["id"],
        "domain": scenario.get("domain", ""),
        "makespan": res.makespan,
        "bw_util": res.bw_util,
        "job0": jobs[0].job_id,
        "job1": jobs[1].job_id,
        "meta0": meta[0],
        "meta1": meta[1],
    }


def main() -> None:
    total_bw = float(os.environ.get("SYSTEM_BW", "100.0"))
    wl_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "scar_workloads.json",
    )
    only = os.environ.get("SCAR_SCENARIO")

    with open(wl_path, "r") as f:
        doc = json.load(f)

    print(doc.get("description", "")[:200] + "…")
    print(f"Reference: {doc.get('reference', '')}")
    print(f"SYSTEM_BW={total_bw}")
    print("")

    rows_out: List[Dict[str, Any]] = []
    for sc in doc["scenarios"]:
        if only and sc["id"] != only:
            continue
        try:
            r = run_scenario(sc, total_bw)
        except Exception as e:
            print(f"FAIL {sc['id']}: {e}")
            continue
        rows_out.append(r)
        print(f"=== {r['scenario_id']} ({r['domain']}) ===")
        print(f"  {r['job0']}")
        print(f"    {r['meta0']}")
        print(f"  {r['job1']}")
        print(f"    {r['meta1']}")
        print(f"  makespan: {r['makespan']:,.0f}")
        print(f"  bw_util:  {r['bw_util']*100:.2f}%")
        print("")

    out_csv = os.environ.get("SCAR_OUT_CSV")
    if out_csv and rows_out:
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "scenario_id",
                    "domain",
                    "makespan",
                    "bw_util",
                    "job0",
                    "job1",
                ],
            )
            w.writeheader()
            for r in rows_out:
                w.writerow(
                    {
                        "scenario_id": r["scenario_id"],
                        "domain": r["domain"],
                        "makespan": f"{r['makespan']:.6f}",
                        "bw_util": f"{r['bw_util']:.6f}",
                        "job0": r["job0"],
                        "job1": r["job1"],
                    }
                )
        print(f"Wrote {out_csv}")


if __name__ == "__main__":
    main()
