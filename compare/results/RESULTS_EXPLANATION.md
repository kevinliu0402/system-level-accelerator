# Results Summary: What I Did and What the Numbers Mean

## What I Did

1. **Defined one convolution layer** and evaluated it under **three dataflow styles** (output-stationary, weight-stationary, row-stationary) using **two analytical tools** (MAESTRO and Timeloop).

2. **MAESTRO (Georgia Tech):**
   - Wrote **hardware description** (`compare/maestro/hw/accelerator_1.m`: 256 PEs, L1/L2 sizes, NoC/off-chip BW).
   - Wrote **three mapping files** that express the same layer with different dataflows:
     - **OS (ShiDianNao):** output-stationary — partial sums stay in PE; weights and inputs stream.
     - **WS (NVDLA):** weight-stationary — weights stay in PE; inputs and partial sums stream.
     **RS (Eyeriss):** row-stationary — row of filter × input reused; balanced reuse of all three tensors.
   - Ran MAESTRO for each mapping and captured **runtime (cycles)** and **total energy (in MAC energy units)**.

3. **Timeloop (NVlabs):**
   - Used existing **Timeloop/Accelergy exercises**: OS and WS from a small conv1d example; RS from the Eyeriss conv-layer example.
   - Parsed their **stats** (cycles, energy in µJ, utilization) into the same summary format.

4. **Comparison pipeline:**
   - **Parsers:** `parse_maestro.py` (Runtime, Total energy from stdout); `parse_timeloop.py` (Cycles, Energy, Utilization from stats.txt).
   - **Merge and plot:** `plot_results.py` produces `summary_table.csv`, `comparison_latency_energy.png`, and `comparison_edp.png`.

So: **same conceptual comparison (OS vs WS vs RS)** in two frameworks; MAESTRO uses one real layer for all three; Timeloop OS/WS use a different (tiny) workload.

---

## Workload (MAESTRO)

**One 2D convolution layer:** K=64, C=64, R=3, S=3, Y=56, X=56.

- **K** = 64 output channels  
- **C** = 64 input channels  
- **R, S** = 3×3 filter  
- **Y, X** = 56×56 output spatial size  

**Total MACs:** 107,495,424 (same for all three MAESTRO runs).

---

## MAESTRO Results (same layer, same HW, different dataflow)

| Dataflow        | Latency (cycles) | Energy (MAC units) | Throughput (MACs/cycle) |
|-----------------|------------------|---------------------|--------------------------|
| ShiDianNao (OS) | 1,089,536        | 1.79e9              | 98.66                    |
| NVDLA (WS)      | 2,146,176        | 0.91e9              | 50.09                    |
| Eyeriss (RS)    | 1,382,402        | 2.00e9              | 77.76                    |

**How to read this:**

- **OS is fastest** (lowest cycles) and has high throughput; it maximizes output reuse and uses 216 PEs on average.
- **WS has lowest energy** in MAC units (heavy weight reuse, 256 PEs, but more cycles).
- **RS is in between** on both latency and energy; it balances reuse of weights, inputs, and outputs (row-stationary).

So under this single layer and abstract HW: **OS wins on latency, WS wins on energy (in MAESTRO units), RS is a middle ground.**

---

## Timeloop Results (different sources)

| Dataflow        | Latency (cycles) | Energy (µJ) | Notes                          |
|-----------------|------------------|-------------|--------------------------------|
| ShiDianNao (OS) | 48               | 0.00        | Tiny conv1d exercise (48 MACs)|
| NVDLA (WS)      | 48               | 0.00        | Same tiny exercise             |
| Eyeriss (RS)    | 5,505,024        | 2764.38     | Real Eyeriss conv (924M MACs)  |

**Important:** Timeloop OS and WS numbers come from a **different, tiny workload** (48 MACs, 48 cycles, no energy in the ref output). Only **RS (Eyeriss)** is from a real conv layer. So:

- **Do not compare Timeloop OS/WS to MAESTRO** for latency/energy — different problems.
- **Timeloop RS** (5.5M cycles, 2764 µJ) is a valid point for “Eyeriss-style row-stationary on a conv” in Timeloop, but the layer shape is not the same as the MAESTRO layer above.

---

## The Two Plots

- **comparison_latency_energy.png:** Bar chart of latency (cycles) and energy by dataflow, MAESTRO vs Timeloop.  
  - MAESTRO: all three dataflows use the same 107M-MAC layer; you can compare OS vs WS vs RS fairly.  
  - Timeloop: OS/WS bars are from the small exercise (48 cycles, 0 µJ); RS is from the Eyeriss example.

- **comparison_edp.png:** Energy–delay product (EDP = cycles × energy).  
  - Again, MAESTRO is comparable across dataflows; Timeloop OS/WS are 0 (zero energy).

---

## One-Line Summary for an Interview

“I modeled one conv layer (64×64, 3×3, 56×56) under three dataflow styles—output-stationary (ShiDianNao), weight-stationary (NVDLA), and row-stationary (Eyeriss)—in MAESTRO and Timeloop, and built a pipeline to parse both tools’ outputs and plot latency, energy, and EDP. Under MAESTRO, OS was fastest, WS was most energy-efficient in their units, and RS was in between.”
