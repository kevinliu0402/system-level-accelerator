# System-Level NoC and Shared DRAM Models

This document describes the **simple analytical models** added on top of per-accelerator results from MAESTRO/Timeloop.

## Goal

- **MAESTRO / Timeloop** give **isolated** accelerator latency (cycles) and energy for one tile and one layer.
- **System-level** modeling adds:
  - **Shared DRAM**: limited off-chip (or last-level) bandwidth shared by all tiles.
  - **NoC**: limited on-chip bandwidth for traffic between tiles and toward DRAM.

## Code location

- `compare/system_model/noc_dram.py` — Python API and two combination modes.
- You can import from `compare.system_model` after adding the parent to `PYTHONPATH` or running from repo root.

## Parameters

| Parameter | Meaning | Example |
|-----------|---------|---------|
| `clock_hz` | Clock for cycle conversion | `1e9` (1 GHz) |
| `dram_bandwidth_gbps` | Aggregate DRAM bandwidth (GB/s, simplified) | `25` |
| `noc_bandwidth_gbps` | Aggregate NoC bandwidth (GB/s) | `100` |

Per tile (`AcceleratorTile`):

- `latency_cycles` — from MAESTRO/Timeloop (isolated).
- `dram_bytes_read`, `dram_bytes_write` — estimated DRAM traffic for the workload on that tile.
- `noc_bytes_to_dram`, `noc_bytes_to_peer` — estimated bytes moved on NoC (to memory path / to other tiles).

**You must supply or estimate byte traffic** (from layer size, mapping, or a separate traffic model). The module does not compute bytes from MACs automatically yet.

## Combination modes

1. **`max_plus_overhead` (default, conservative)**  
   \[
   T_{\text{sys}} \approx \max_i T_i + T_{\text{DRAM,serial}} + T_{\text{NoC,serial}}
   \]
   where \(T_{\text{DRAM,serial}}\) is cycles to move \(\sum_i (\text{read}_i + \text{write}_i)\) at shared DRAM BW, and similarly for NoC.

2. **`max_of_three` (optimistic overlap)**  
   \[
   T_{\text{sys}} \approx \max\left(\max_i T_i,\; T_{\text{DRAM,serial}},\; T_{\text{NoC,serial}}\right)
   \]

These are **first-order** bounds for design-space exploration, not cycle-accurate simulation.

## Example

```python
from compare.system_model.noc_dram import (
    AcceleratorTile,
    SystemConfig,
    estimate_multi_accelerator_system,
)

tiles = [
    AcceleratorTile("A", latency_cycles=1e6, dram_bytes_read=1e8, dram_bytes_write=5e7),
    AcceleratorTile("B", latency_cycles=1.2e6, dram_bytes_read=1e8, dram_bytes_write=5e7),
]
cfg = SystemConfig(clock_hz=1e9, dram_bandwidth_gbps=25, noc_bandwidth_gbps=100)
est = estimate_multi_accelerator_system(tiles, cfg)
print(est.total_cycles, est.note)
```

## Next steps (project)

1. **Derive DRAM/NoC bytes** from your layer + mapping (or reuse MAESTRO buffer/DRAM stats as hints).
2. **Plug in** measured `latency_cycles` from `summary_table.csv` per dataflow.
3. **Sweep** `dram_bandwidth_gbps` / `noc_bandwidth_gbps` for sensitivity plots.
4. Compare **trends** with MAGMA/SCAR-style discussions (qualitative agreement is enough for the course).

## Limitations

- Single DRAM pipe; no detailed bank-level or row-buffer model.
- NoC is one aggregate bandwidth; no topology, no routing contention.
- No multi-workload scheduling in `noc_dram.py` (see SCAR for scheduling ideas).

**Update — SCAR-style multi-model CNN workloads:** Under `compare/system_model/`, see `scar_workloads.json` and `run_scar_multi_model_bw.py` for two concurrent jobs (different networks/layers/dataflows) on the shared MAGMA bandwidth allocator, with per-job `L` and `Avg BW Req` from MAESTRO CSV rows. This is a **small CNN subset** inspired by SCAR’s MLPerf + XRBench methodology, not a full reproduction of their ten scenarios.

These match the proposal’s scope: **early-stage exploration**, not RTL-accurate modeling.

## Strong scaling vs weak scaling (parallel performance)

These terms describe **how you grow the problem** when you add processors (or PEs/chiplets).

**Strong scaling:** The **total problem size is fixed** (e.g. one ResNet-50 inference). You increase hardware (more cores / chiplets). Ideal speedup: time drops in proportion to resources. In practice, **communication**, **Amdahl serial fraction**, and **load imbalance** limit speedup.

**Weak scaling:** The **work per processor stays roughly constant**; when you double processors, you **double the problem size** (e.g. double the batch or double concurrent models). Ideal outcome: **time per step stays flat** as you scale. Used to study whether the system **saturates** (memory bandwidth, NoC) when load grows with machine size.

For this project, **shared DRAM / NoC caps** often show up as **poor strong scaling** (fixed inference hits a bandwidth wall) or **weak scaling** curves that **bend upward** once traffic exceeds the pipe.
