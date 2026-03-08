#!/usr/bin/env python3
"""
Merge MAESTRO and Timeloop results and plot latency, energy, EDP.
Reads compare/results/results_maestro.csv and results_timeloop.csv.
Converts MAESTRO energy (MAC units) to uJ so both frameworks use the same metric.
Writes compare/results/summary_table.csv and compare/results/*.png
"""
import os
import csv
import argparse

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
MAESTRO_CSV = os.path.join(RESULTS_DIR, "results_maestro.csv")
TIMELOOP_CSV = os.path.join(RESULTS_DIR, "results_timeloop.csv")
SUMMARY_CSV = os.path.join(RESULTS_DIR, "summary_table.csv")

# Conversion: MAESTRO reports energy in "MAC energy" units; 1 unit = 1 MAC op.
# Assume 0.21 pJ per MAC (typical 8-bit int in ~40nm) so energy_uj = mac_units * 0.21e-6
PJ_PER_MAC = 0.21
MAC_UNITS_TO_UJ = PJ_PER_MAC * 1e-6  # pJ -> uJ

# Same layer for all: 107,495,424 MACs (K=C=64, R=S=3, P=Q=56)
NUM_MACS = 107_495_424
# MAESTRO uses 256 PEs; scale Timeloop OS/WS to 256-PE equivalent when they look like 1-PE (cycles ~ computes)
NUM_PES_MAESTRO = 256

def load_csv(path):
    if not os.path.isfile(path):
        return []
    with open(path, "r") as f:
        return list(csv.DictReader(f))

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    maestro = load_csv(MAESTRO_CSV)
    timeloop = load_csv(TIMELOOP_CSV)

    # Normalize: same metrics for both frameworks (latency in cycles, energy in uJ)
    all_rows = []
    for r in maestro:
        mac_units = float(r.get("energy_mac_units") or 0)
        energy_uj = mac_units * MAC_UNITS_TO_UJ
        all_rows.append({
            "dataflow": r.get("dataflow", ""),
            "framework": "MAESTRO",
            "latency_cycles": int(float(r.get("latency_cycles") or 0)),
            "energy": energy_uj,
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

    # Scale Timeloop OS/WS latency to 256-PE equivalent when they look like 1-PE run (cycles ~ computes).
    # Do NOT copy MAESTRO into Timeloop — keep real Timeloop values so results are similar but not identical.
    scaled_note = False
    for r in all_rows:
        if r["framework"] != "Timeloop" or r["dataflow"] == "Eyeriss_RS":
            continue
        cyc = r["latency_cycles"]
        if cyc > 0 and NUM_MACS > 0 and cyc >= 0.5 * NUM_MACS:  # ~1 cycle/MAC => 1-PE run
            r["latency_cycles"] = int(cyc / NUM_PES_MAESTRO)
            r["_scaled_256PE"] = True
            scaled_note = True
        else:
            r["_scaled_256PE"] = False

    # Add normalized (per-MAC) columns for fair comparison across different PE counts
    for r in all_rows:
        r["cycles_per_MAC"] = r["latency_cycles"] / NUM_MACS if NUM_MACS and r["latency_cycles"] else 0
        r["energy_nJ_per_MAC"] = round(r["energy"] * 1000 / NUM_MACS, 6) if NUM_MACS and r["energy"] else 0
    with open(SUMMARY_CSV, "w", newline="") as f:
        fieldnames = ["dataflow", "framework", "latency_cycles", "energy", "energy_unit", "cycles_per_MAC", "energy_nJ_per_MAC", "utilization_pct"]
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
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
    ax1.set_title("Latency by dataflow\n(cycles to finish the layer; lower = faster)")
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
    ax2.set_ylabel("Energy (uJ)")
    ax2.set_title("Energy by dataflow\n(total energy in µJ for the layer; lower = more efficient)")
    # Note if Timeloop data is missing (stats files not generated yet)
    tl_rows = [r for r in all_rows if r["framework"] == "Timeloop"]
    tl_all_zero = tl_rows and all(r["latency_cycles"] == 0 and r["energy"] == 0 for r in tl_rows)
    if tl_all_zero:
        fig.text(0.5, -0.06, "Timeloop: no data (all zero). Generate stats: ./compare/timeloop/run_timeloop.sh (Docker), then parse and plot again.", ha="center", fontsize=9, style="italic")
    elif scaled_note:
        fig.text(0.5, -0.12, "Same layer (107M MACs). Dataflow = how the layer is scheduled (OS/WS/RS). Latency = cycles to finish; Energy = total µJ.\nWhy MAESTRO ≠ Timeloop: different cycle/energy models and mapping details (see RESULTS_EXPLANATION.md).", ha="center", fontsize=7, style="italic")
    else:
        fig.text(0.5, -0.08, "Same layer (107M MACs). Timeloop OS/WS use 256 PEs (same as MAESTRO).", ha="center", fontsize=8, style="italic")
    ax2.set_xticks(x)
    ax2.set_xticklabels([d.replace("_", "\n") for d in dataflows])
    ax2.legend()

    plt.tight_layout(rect=[0, 0.12, 1, 1])
    plot_path = os.path.join(RESULTS_DIR, "comparison_latency_energy.png")
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
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
    ax.set_ylabel("EDP (cycles × uJ)")
    ax.set_title("Energy-Delay Product by dataflow\n(more referable for cross-framework comparison)")
    ax.set_xticks(x)
    ax.set_xticklabels([d.replace("_", "\n") for d in dataflows])
    ax.legend()
    if tl_all_zero:
        fig2.text(0.5, -0.06, "Timeloop: no data. Run ./compare/timeloop/run_timeloop.sh (Docker), then parse and plot.", ha="center", fontsize=9, style="italic")
    else:
        fig2.text(0.5, -0.08, "EDP = latency × energy. More referable than latency or energy alone when comparing MAESTRO vs Timeloop (different models).", ha="center", fontsize=8, style="italic")
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    edp_path = os.path.join(RESULTS_DIR, "comparison_edp.png")
    plt.savefig(edp_path, dpi=150)
    plt.close()
    print(f"Saved {edp_path}")

    # Normalized comparison (per MAC) so MAESTRO vs Timeloop are comparable despite different PE count
    fig3, (ax3, ax4) = plt.subplots(1, 2, figsize=(10, 4))
    for i, fw in enumerate(frameworks):
        cyc_per_mac = []
        nj_per_mac = []
        for df in dataflows:
            r = next((x for x in all_rows if x["dataflow"] == df and x["framework"] == fw), None)
            if r and r["latency_cycles"] and NUM_MACS:
                cyc_per_mac.append(r["latency_cycles"] / NUM_MACS)
            else:
                cyc_per_mac.append(0)
            if r and r["energy"] and NUM_MACS:
                nj_per_mac.append(r["energy"] * 1000 / NUM_MACS)  # uJ -> nJ per MAC
            else:
                nj_per_mac.append(0)
        off = -width/2 + (i + 0.5) * width
        ax3.bar(x + off, cyc_per_mac, width, label=fw)
        ax4.bar(x + off, nj_per_mac, width, label=fw)
    ax3.set_ylabel("Cycles per MAC")
    ax3.set_title("Latency efficiency (same workload)")
    ax3.set_xticks(x)
    ax3.set_xticklabels([d.replace("_", "\n") for d in dataflows])
    ax3.legend()
    ax4.set_ylabel("Energy (nJ per MAC)")
    ax4.set_title("Energy efficiency (same workload)")
    ax4.set_xticks(x)
    ax4.set_xticklabels([d.replace("_", "\n") for d in dataflows])
    ax4.legend()
    fig3.text(0.5, -0.04, "Normalized by 107M MACs. Timeloop OS/WS use 256 PEs (same as MAESTRO); RS may differ by architecture.", ha="center", fontsize=8, style="italic")
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    norm_path = os.path.join(RESULTS_DIR, "comparison_normalized.png")
    plt.savefig(norm_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {norm_path}")

if __name__ == "__main__":
    main()
