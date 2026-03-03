#!/usr/bin/env python3
"""
Merge MAESTRO and Timeloop results and plot latency, energy, EDP.
Reads compare/results/results_maestro.csv and results_timeloop.csv.
Writes compare/results/summary_table.csv and compare/results/*.png
"""
import os
import csv
import argparse

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
MAESTRO_CSV = os.path.join(RESULTS_DIR, "results_maestro.csv")
TIMELOOP_CSV = os.path.join(RESULTS_DIR, "results_timeloop.csv")
SUMMARY_CSV = os.path.join(RESULTS_DIR, "summary_table.csv")

def load_csv(path):
    if not os.path.isfile(path):
        return []
    with open(path, "r") as f:
        return list(csv.DictReader(f))

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    maestro = load_csv(MAESTRO_CSV)
    timeloop = load_csv(TIMELOOP_CSV)

    # Normalize: same columns for merge
    all_rows = []
    for r in maestro:
        all_rows.append({
            "dataflow": r.get("dataflow", ""),
            "framework": "MAESTRO",
            "latency_cycles": int(float(r.get("latency_cycles") or 0)),
            "energy": float(r.get("energy_mac_units") or 0),
            "energy_unit": "MAC_units",
            "utilization_pct": float(r.get("utilization_pct") or 0),
        })
    for r in timeloop:
        all_rows.append({
            "dataflow": r.get("dataflow", ""),
            "framework": "Timeloop",
            "latency_cycles": int(float(r.get("latency_cycles") or 0)),
            "energy": float(r.get("energy_uj") or 0),
            "energy_unit": "uJ",
            "utilization_pct": float(r.get("utilization_pct") or 0),
        })

    with open(SUMMARY_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dataflow", "framework", "latency_cycles", "energy", "energy_unit", "utilization_pct"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"Wrote {SUMMARY_CSV}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib not installed; skipping plots. Install with: pip install matplotlib")
        return

    if not all_rows:
        print("No data to plot. Run run_maestro.sh, run_timeloop.sh, then parse_maestro.py and parse_timeloop.py.")
        return

    # Bar plots: latency and energy by dataflow, grouped by framework
    # Fixed order: OS, WS, RS (only include dataflows that exist in data)
    all_dataflows = sorted(set(r["dataflow"] for r in all_rows))
    preferred_order = ["ShiDianNao_OS", "NVDLA_WS", "Eyeriss_RS"]
    dataflows = [d for d in preferred_order if d in all_dataflows]
    dataflows += [d for d in all_dataflows if d not in dataflows]
    frameworks = ["MAESTRO", "Timeloop"]
    x = np.arange(len(dataflows))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    for i, fw in enumerate(frameworks):
        vals = []
        for df in dataflows:
            r = next((x for x in all_rows if x["dataflow"] == df and x["framework"] == fw), None)
            vals.append(r["latency_cycles"] if r else 0)
        off = -width/2 + (i + 0.5) * width
        ax1.bar(x + off, vals, width, label=fw)
    ax1.set_ylabel("Latency (cycles)")
    ax1.set_title("Latency by dataflow")
    ax1.set_xticks(x)
    ax1.set_xticklabels([d.replace("_", "\n") for d in dataflows])
    ax1.legend()

    for i, fw in enumerate(frameworks):
        vals = []
        for df in dataflows:
            r = next((x for x in all_rows if x["dataflow"] == df and x["framework"] == fw), None)
            vals.append(r["energy"] if r else 0)
        off = -width/2 + (i + 0.5) * width
        ax2.bar(x + off, vals, width, label=fw)
    ax2.set_ylabel("Energy")
    ax2.set_title("Energy by dataflow (MAESTRO: MAC units, Timeloop: uJ)")
    ax2.set_xticks(x)
    ax2.set_xticklabels([d.replace("_", "\n") for d in dataflows])
    ax2.legend()

    plt.tight_layout()
    plot_path = os.path.join(RESULTS_DIR, "comparison_latency_energy.png")
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"Saved {plot_path}")

    # EDP (energy * delay)
    fig2, ax = plt.subplots(figsize=(6, 4))
    for i, fw in enumerate(frameworks):
        edps = []
        for df in dataflows:
            r = next((x for x in all_rows if x["dataflow"] == df and x["framework"] == fw), None)
            if r and r["latency_cycles"] and r["energy"]:
                edps.append(r["latency_cycles"] * r["energy"])
            else:
                edps.append(0)
        off = -width/2 + (i + 0.5) * width
        ax.bar(x + off, edps, width, label=fw)
    ax.set_ylabel("EDP (cycles × energy)")
    ax.set_title("Energy-Delay Product by dataflow")
    ax.set_xticks(x)
    ax.set_xticklabels([d.replace("_", "\n") for d in dataflows])
    ax.legend()
    plt.tight_layout()
    edp_path = os.path.join(RESULTS_DIR, "comparison_edp.png")
    plt.savefig(edp_path, dpi=150)
    plt.close()
    print(f"Saved {edp_path}")

if __name__ == "__main__":
    main()
