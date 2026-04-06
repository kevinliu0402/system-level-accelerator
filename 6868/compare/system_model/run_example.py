#!/usr/bin/env python3
"""Run from repo root: python3 compare/system_model/run_example.py"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from compare.system_model.noc_dram import (
    AcceleratorTile,
    SystemConfig,
    estimate_multi_accelerator_system,
    example_from_summary_csv_row,
)

def main():
    print("=== Two tiles, same isolated latency, toy DRAM traffic ===")
    tiles = [
        AcceleratorTile(
            "A",
            latency_cycles=1_000_000,
            dram_bytes_read=1e8,
            dram_bytes_write=5e7,
            noc_bytes_to_dram=1.5e8,
            noc_bytes_to_peer=1e7,
        ),
        AcceleratorTile(
            "B",
            latency_cycles=1_200_000,
            dram_bytes_read=1e8,
            dram_bytes_write=5e7,
            noc_bytes_to_dram=1.5e8,
            noc_bytes_to_peer=1e7,
        ),
    ]
    cfg = SystemConfig(clock_hz=1e9, dram_bandwidth_gbps=25, noc_bandwidth_gbps=100)
    for mode in ("max_plus_overhead", "max_of_three"):
        est = estimate_multi_accelerator_system(tiles, cfg, mode=mode)
        print(f"\nmode={mode}")
        print(f"  max isolated cycles: {est.max_isolated_cycles:,.0f}")
        print(f"  DRAM serial cycles:  {est.dram_extra_cycles:,.0f}")
        print(f"  NoC serial cycles:   {est.noc_extra_cycles:,.0f}")
        print(f"  total cycles:        {est.total_cycles:,.0f}")
        print(f"  ({est.note})")

    print("\n=== Placeholder multi-tile example (toy bytes) ===")
    est2 = example_from_summary_csv_row(latency_cycles=451_584, num_tiles=4)
    print(est2)

if __name__ == "__main__":
    main()
