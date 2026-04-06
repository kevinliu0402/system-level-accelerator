#!/usr/bin/env python3
"""
Run Timeloop model for OS, WS, RS on the same layer (K=C=64, R=S=3, P=Q=56).
Uses arch_2level_2dconv.yaml, single_layer_problem.yaml, map_same_layer_*.yaml.
Writes out_os/, out_ws/, out_rs/ and copies stats to compare/results/.
"""
import os
import subprocess
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
RESULTS_DIR = os.path.join(REPO_ROOT, "compare", "results")

ARCH = os.path.join(SCRIPT_DIR, "arch_2level_2dconv.yaml")
PROB = os.path.join(SCRIPT_DIR, "single_layer_problem.yaml")
MAPS = [
    ("out_os", "map_same_layer_os.yaml", "timeloop_os_shidiannao.stats.txt"),
    ("out_ws", "map_same_layer_ws.yaml", "timeloop_ws_nvdla.stats.txt"),
    ("out_rs", "map_same_layer_rs.yaml", "timeloop_rs_eyeriss.stats.txt"),
]

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    for out_name, map_name, stats_name in MAPS:
        out_dir = os.path.join(SCRIPT_DIR, out_name)
        map_path = os.path.join(SCRIPT_DIR, map_name)
        os.makedirs(out_dir, exist_ok=True)
        cmd = [
            "timeloop", "model",
            ARCH, PROB, map_path,
            "-o", out_dir,
        ]
        print("Running:", " ".join(cmd))
        result = subprocess.run(cmd, cwd=SCRIPT_DIR)
        if result.returncode != 0:
            print(f"Warning: timeloop exited {result.returncode} for {out_name}")
            continue
        src = os.path.join(out_dir, "timeloop-model.stats.txt")
        dst = os.path.join(RESULTS_DIR, stats_name)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            print(f"Copied -> {dst}")
        else:
            print(f"Stats not found: {src}")
    print("Done. Run parse_timeloop.py and plot_results.py from repo root.")

if __name__ == "__main__":
    main()
