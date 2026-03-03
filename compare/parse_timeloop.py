#!/usr/bin/env python3
"""
Parse Timeloop stats.txt for Cycles, Energy (uJ), Utilization.
Writes compare/results/results_timeloop.csv
"""
import re
import os
import csv

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CSV_OUT = os.path.join(RESULTS_DIR, "results_timeloop.csv")

def parse_stats(path: str) -> dict:
    out = {"latency_cycles": None, "energy_uj": None, "utilization_pct": None}
    if not os.path.isfile(path):
        return out
    with open(path, "r") as f:
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
    for name, dataflow in [
        ("os_shidiannao", "ShiDianNao_OS"),
        ("ws_nvdla", "NVDLA_WS"),
        ("rs_eyeriss", "Eyeriss_RS"),
    ]:
        path = os.path.join(RESULTS_DIR, f"timeloop_{name}.stats.txt")
        parsed = parse_stats(path)
        rows.append({
            "dataflow": dataflow,
            "framework": "Timeloop",
            "latency_cycles": parsed["latency_cycles"] or 0,
            "energy_uj": parsed["energy_uj"] or 0,
            "utilization_pct": parsed["utilization_pct"] or 0,
        })
    with open(CSV_OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dataflow", "framework", "latency_cycles", "energy_uj", "utilization_pct"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {CSV_OUT}")

if __name__ == "__main__":
    main()
