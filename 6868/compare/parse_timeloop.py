#!/usr/bin/env python3
"""
Parse Timeloop stats files (OS, WS, RS) into compare/results/results_timeloop.csv.
Looks for: compare/results/timeloop_os_shidiannao.stats.txt, timeloop_ws_nvdla.stats.txt,
           timeloop_rs_eyeriss.stats.txt
"""
import os
import re
import csv

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CSV_OUT = os.path.join(RESULTS_DIR, "results_timeloop.csv")

FILES = [
    ("os_shidiannao", "ShiDianNao_OS"),
    ("ws_nvdla", "NVDLA_WS"),
    ("rs_eyeriss", "Eyeriss_RS"),
]

def parse_stats(path):
    out = {"latency_cycles": 0, "energy_uj": 0.0, "utilization_pct": 0.0}
    if not os.path.isfile(path):
        return out
    with open(path) as f:
        text = f.read()
    m = re.search(r"Cycles:\s*(\d+)", text)
    if m:
        out["latency_cycles"] = int(m.group(1))
    m = re.search(r"Energy:\s*([\d.]+)\s*uJ", text)
    if m:
        out["energy_uj"] = float(m.group(1))
    m = re.search(r"Utilization:\s*([\d.]+)%", text)
    if m:
        out["utilization_pct"] = float(m.group(1))
    return out

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rows = []
    for stem, dataflow in FILES:
        path = os.path.join(RESULTS_DIR, f"timeloop_{stem}.stats.txt")
        p = parse_stats(path)
        rows.append({
            "dataflow": dataflow,
            "framework": "Timeloop",
            "latency_cycles": p["latency_cycles"],
            "energy_uj": p["energy_uj"],
            "utilization_pct": p["utilization_pct"],
        })
    with open(CSV_OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dataflow", "framework", "latency_cycles", "energy_uj", "utilization_pct"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {CSV_OUT}")

if __name__ == "__main__":
    main()
