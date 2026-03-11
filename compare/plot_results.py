#!/usr/bin/env python3
"""
Merge MAESTRO and Timeloop results and plot latency, energy, EDP.
Reads compare/results/results_maestro.csv and results_timeloop.csv.
Converts MAESTRO energy (MAC units) to uJ (0.21 pJ/MAC).
Writes compare/results/summary_table.csv and comparison_*.png
"""
import os
import csv

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
MAESTRO_CSV = os.path.join(RESULTS_DIR, "results_maestro.csv")
TIMELOOP_CSV = os.path.join(RESULTS_DIR, "results_timeloop.csv")
SUMMARY_CSV = os.path.join(RESULTS_DIR, "summary_table.csv")

PJ_PER_MAC = 0.21
MAC_UNITS_TO_UJ = PJ_PER_MAC * 1e-6
NUM_MACS = 107_495_424
NUM_PES_MAESTRO = 256

def load_csv(path):
    if not os.path.isfile(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    maestro = load_csv(MAESTRO_CSV)
    timeloop = load_csv(TIMELOOP_CSV)

    all_rows = []
    for r in maestro:
        mac_units = float(r.get("energy_mac_units") or 0)
        all_rows.append({
            "dataflow": r.get("dataflow", ""),
            "framework": "MAESTRO",
            "latency_cycles": int(float(r.get("latency_cycles") or 0)),
            "energy": mac_units * MAC_UNITS_TO_UJ,
            "energy_unit": "uJ",
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

    for r in all_rows:
        if r["framework"] != "Timeloop":
            continue
        cyc = r["latency_cycles"]
        if cyc > 0 and NUM_MACS > 0 and cyc >= 0.5 * NUM_MACS:
            r["latency_cycles"] = int(cyc / NUM_PES_MAESTRO)

    for r in all_rows:
        r["cycles_per_MAC"] = r["latency_cycles"] / NUM_MACS if NUM_MACS and r["latency_cycles"] else 0
        r["energy_nJ_per_MAC"] = round(r["energy"] * 1000 / NUM_MACS, 6) if NUM_MACS and r["energy"] else 0

    with open(SUMMARY_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dataflow", "framework", "latency_cycles", "energy", "energy_unit", "cycles_per_MAC", "energy_nJ_per_MAC", "utilization_pct"], extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)
    print(f"Wrote {SUMMARY_CSV}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib not installed; skipping plots.")
        return

    if not all_rows:
        return

    preferred_order = ["ShiDianNao_OS", "NVDLA_WS", "Eyeriss_RS"]
    dataflows = [d for d in preferred_order if d in {r["dataflow"] for r in all_rows}]
    dataflows += [d for d in sorted({r["dataflow"] for r in all_rows}) if d not in dataflows]
    frameworks = ["MAESTRO", "Timeloop"]
    x = np.arange(len(dataflows))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    for i, fw in enumerate(frameworks):
        vals = [next((r["latency_cycles"] for r in all_rows if r["dataflow"] == df and r["framework"] == fw), 0) for df in dataflows]
        ax1.bar(x + (-width/2 + (i + 0.5) * width), vals, width, label=fw)
    ax1.set_ylabel("Latency (cycles)")
    ax1.set_title("Latency by dataflow")
    ax1.set_xticks(x)
    ax1.set_xticklabels([d.replace("_", "\n") for d in dataflows])
    ax1.legend()
    ax1.set_ylim(0, 2.5e6)

    for i, fw in enumerate(frameworks):
        vals = [next((r["energy"] for r in all_rows if r["dataflow"] == df and r["framework"] == fw), 0) for df in dataflows]
        ax2.bar(x + (-width/2 + (i + 0.5) * width), vals, width, label=fw)
    ax2.set_ylabel("Energy (uJ)")
    ax2.set_title("Energy by dataflow")
    ax2.set_ylim(0, 2250)
    ax2.set_xticks(x)
    ax2.set_xticklabels([d.replace("_", "\n") for d in dataflows])
    ax2.legend()
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    plt.savefig(os.path.join(RESULTS_DIR, "comparison_latency_energy.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {RESULTS_DIR}/comparison_latency_energy.png")

    fig2, ax = plt.subplots(figsize=(6, 4))
    for i, fw in enumerate(frameworks):
        edps = [next((r["latency_cycles"] * r["energy"] for r in all_rows if r["dataflow"] == df and r["framework"] == fw), 0) or 0 for df in dataflows]
        ax.bar(x + (-width/2 + (i + 0.5) * width), edps, width, label=fw)
    ax.set_ylabel("EDP (cycles × uJ)")
    ax.set_title("Energy-Delay Product by dataflow")
    ax.set_xticks(x)
    ax.set_xticklabels([d.replace("_", "\n") for d in dataflows])
    ax.legend()
    ax.set_ylim(0, 10e8)
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(os.path.join(RESULTS_DIR, "comparison_edp.png"), dpi=150)
    plt.close()
    print(f"Saved {RESULTS_DIR}/comparison_edp.png")

    fig3, (ax3, ax4) = plt.subplots(1, 2, figsize=(10, 4))
    for i, fw in enumerate(frameworks):
        cyc_per_mac = [next((r["cycles_per_MAC"] for r in all_rows if r["dataflow"] == df and r["framework"] == fw), 0) for df in dataflows]
        nj_per_mac = [next((r["energy_nJ_per_MAC"] for r in all_rows if r["dataflow"] == df and r["framework"] == fw), 0) for df in dataflows]
        ax3.bar(x + (-width/2 + (i + 0.5) * width), cyc_per_mac, width, label=fw)
        ax4.bar(x + (-width/2 + (i + 0.5) * width), nj_per_mac, width, label=fw)
    ax3.set_ylabel("Cycles per MAC")
    ax3.set_title("Latency efficiency")
    ax3.set_xticks(x)
    ax3.set_xticklabels([d.replace("_", "\n") for d in dataflows])
    ax3.legend()
    ax4.set_ylabel("Energy (nJ per MAC)")
    ax4.set_title("Energy efficiency")
    ax4.set_xticks(x)
    ax4.set_xticklabels([d.replace("_", "\n") for d in dataflows])
    ax4.legend()
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    plt.savefig(os.path.join(RESULTS_DIR, "comparison_normalized.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {RESULTS_DIR}/comparison_normalized.png")

if __name__ == "__main__":
    main()
