#!/usr/bin/env python3
"""
Parse MAESTRO stdout for latency (cycles) and total energy (X MAC energy).
Writes compare/results/results_maestro.csv
"""
import re
import os
import csv

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CSV_OUT = os.path.join(RESULTS_DIR, "results_maestro.csv")

def parse_maestro_stdout(path: str) -> dict:
    out = {"latency_cycles": None, "energy_mac": None, "utilization_pct": None}
    if not os.path.isfile(path):
        return out
    with open(path, "r") as f:
        text = f.read()
    # Runtime: 12345 cycles (take last occurrence if multiple layers)
    m = re.findall(r"Runtime:\s*(\d+)\s*cycles", text)
    if m:
        out["latency_cycles"] = int(m[-1])
    # Total energy consumption: X X MAC energy
    m = re.findall(r"Total energy consumption:\s*([\d.eE+-]+)\s*X MAC energy", text)
    if m:
        out["energy_mac"] = float(m[-1])
    return out

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rows = []
    for name, dataflow in [
        ("os_shidiannao", "ShiDianNao_OS"),
        ("ws_nvdla", "NVDLA_WS"),
        ("rs_eyeriss", "Eyeriss_RS"),
    ]:
        path = os.path.join(RESULTS_DIR, f"maestro_{name}.stdout")
        parsed = parse_maestro_stdout(path)
        rows.append({
            "dataflow": dataflow,
            "framework": "MAESTRO",
            "latency_cycles": parsed["latency_cycles"] or 0,
            "energy_mac_units": parsed["energy_mac"] or 0,
            "utilization_pct": parsed["utilization_pct"] or 0,
        })
    with open(CSV_OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dataflow", "framework", "latency_cycles", "energy_mac_units", "utilization_pct"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {CSV_OUT}")

if __name__ == "__main__":
    main()
