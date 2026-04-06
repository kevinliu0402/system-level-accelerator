---
marp: true
theme: default
paginate: true
---

# Midterm Presentation
## System-Level Modeling of Multi-Accelerator Architectures via Analytical Cost Model Integration

**COMS E6868 – Embedded Scalable Platforms – Spring 2025**  
Kevin Liu

---
<!-- _class: lead -->

# 1. Project introduction (~1 min)

---
## Goal

- **Unify accelerator-level and system-level modeling**
- Use analytical cost models (**MAESTRO**, **Timeloop**) for individual accelerators
- Add explicit modeling of **NoC** and **shared DRAM** for multi-accelerator systems
- Enable **design-space exploration** without cycle-accurate simulation

---
## Why it matters

- Multi-accelerator platforms need **performance estimation** across tiles
- Single-accelerator tools (MAESTRO, Timeloop) don’t model **inter-accelerator communication** or **DRAM contention**
- Frameworks like **MAGMA**, **SCAR** use their own cost models; we want to **plug in** MAESTRO/Timeloop

---
## Midterm focus

**Study how each accelerator’s dataflow can be expressed in each framework:**

- **ShiDianNao** (output-stationary, OS)
- **NVDLA** (weight-stationary, WS)
- **Eyeriss** (row-stationary, RS)

Same layer, same PE count, in **both** MAESTRO and Timeloop → compare latency, energy, EDP.

---
<!-- _class: lead -->

# 2. Progress: What I did

---
## Progress overview

1. **Describe hardware** the way each tool expects  
2. **Convert MAC to µJ** for comparable energy  
3. **Physical meaning** of quantities (Timeloop vs MAESTRO)  
4. **Run Timeloop on Docker** (reproducible setup)  
5. **Same layer, three dataflows** in both MAESTRO and Timeloop  

---
## 1. Describe hardware the way each tool expects

**MAESTRO**
- **HW file** (`.m`): `num_pes`, L1/L2 size constraints, NoC/off-chip BW  
- **Mapping file** (`.m`): Dataflow (TemporalMap, SpatialMap, Cluster over K,C,R,S,Y,X)  

**Timeloop**
- **Architecture YAML**: hierarchy (MainMemory → PE array → Buffer → MACC), `technology`, `global_cycle_seconds`, spatial mesh  
- **Mapping YAML**: temporal/spatial factors and permutation per level  

|           | MAESTRO                    | Timeloop                               |
|-----------|----------------------------|----------------------------------------|
| PE count  | `num_pes: 256`             | `spatial: {meshX: 16, meshY: 16}` (in arch) |
| Memory    | L1/L2 constraints          | Explicit depth, width, class           |

---
## 2. Convert MAC to µJ

- **MAESTRO** reports energy in **"X MAC energy"** (abstract units)  
- **Timeloop** reports energy in **µJ** (from Accelergy/ERT)  
- To compare:  
  \[
  \text{energy}_\mu J = (\text{X MAC energy}) \times 0.21\ \text{pJ/MAC} \times 10^{-6}
  \]
- Use **0.21 pJ/MAC** so MAESTRO and Timeloop are on the same µJ scale

---
## 3. Physical meaning of the quantities

| Quantity    | MAESTRO                       | Timeloop                            |
|-------------|-------------------------------|--------------------------------------|
| **Latency** | `Runtime: N cycles`           | `Cycles: N` (cycle = e.g. 1 ns)      |
| **Energy**  | "X MAC energy" → convert to µJ| **µJ** (physical, Accelergy / ERT)   |
| **Utilization** | % (from avg. utilized PEs) | % of PEs busy                        |
| **EDP**     | cycles × energy               | Same; main metric for cross-framework |

Different cycle/energy models ⇒ raw latency and energy can differ; **EDP is more comparable**.

---
## 3 (cont.) Utilization: MAESTRO vs Timeloop

**MAESTRO utilization**  
- MAESTRO prints **"Average number of utilized PEs: N"** (e.g. 216).  
- We parse that and report **utilization % = 100 × N / 256**.  

**Timeloop utilization ("% of PEs busy")**  
- **Utilization** = fraction of **PEs × cycles** doing useful MACs (not idle).  
- **100%** = every PE is busy every cycle; **under 100%** = some PEs or cycles are idle (e.g. waiting on data or bandwidth).  
- Timeloop prints this as `Utilization: X.XX%` in the stats file.

---
## 4. Run Timeloop on Docker

- **Image:** `timeloopaccelergy/timeloop-accelergy-pytorch:latest-amd64`  
- **One command from repo root:**
  ```bash
  ./compare/timeloop/run_timeloop.sh
  ```
  - Runs Timeloop OS, WS, RS on the **same layer** (K=C=64, R=S=3, P=Q=56) via Docker  
  - Uses v0.4 configs (`arch_2level_2dconv.yaml`, `single_layer_problem.yaml`, `map_same_layer_*.yaml`)  
  - Writes `timeloop_*_*.stats.txt` into `compare/results/`  

- Then:
  ```bash
  python3 compare/parse_timeloop.py
  python3 compare/plot_results.py
  ```

---
## 5. Same layer, three accelerators (MAESTRO + Timeloop)

**Same layer (all runs):** K=C=64, R=S=3, P=Q=56 → **107M MACs**  
**Same accelerator size:** **256 PEs** (MAESTRO directly; Timeloop scaled from 1-PE runs)

| Dataflow | MAESTRO mapping              | Timeloop mapping / config             |
|----------|------------------------------|---------------------------------------|
| OS       | ShiDianNao (output-stationary) | `map_same_layer_os.yaml`              |
| WS       | NVDLA (weight-stationary)    | `map_same_layer_ws.yaml`              |
| RS       | Eyeriss (row-stationary)     | `map_same_layer_rs.yaml` (same layer) |

---
## Results (summary)

- **Latency (cycles, 256-PE equivalent):**
  - MAESTRO: ~1–2M cycles for OS/WS/RS  
  - Timeloop: ~452K cycles for OS/WS/RS (1-PE run scaled by ÷256)

- **Why Timeloop latency is lower:**  
  - MAESTRO models a 256-PE run directly (with stalls, bandwidth limits).  
  - Timeloop cycles are from a **1-PE** bandwidth-based model, then scaled by ideal 256× speedup → more optimistic.

- **Energy (µJ):**
  - MAESTRO: ~190–420 µJ (after MAC→µJ conversion)  
  - Timeloop: ~1280–1965 µJ (OS/WS/RS)

- **Why Timeloop energy is higher:**  
  - MAESTRO uses a single MAC-energy-based model.  
  - Timeloop + Accelergy count energy for each component (DRAM / SRAM / regfile / MAC), so more detailed (and higher) energy accounting.

---
## Why EDP for comparison?

- **EDP = latency × energy (cycles × µJ)**  
- MAESTRO and Timeloop have:
  - Different **cycle models**
  - Different **energy models** and hierarchies

- Raw latency and energy can each be higher or lower in one tool.  
- **EDP** captures the tradeoff and is **more stable** as a comparison metric across frameworks.  
- In the plots, EDPs are of the same order and show consistent ranking of dataflows.

---
<!-- _class: lead -->

# 3. Plan for the second part of the semester

---
## Next steps (from proposal)

- **Design the system-level modeling framework** (Mar)  
- **Integrate inter-accelerator communication and DRAM modeling**  
- **Simulate representative DNN workloads** on multi-accelerator systems (April)  
- **Explore system-level optimizations** (inspired by MAGMA, SCAR, etc.)  
- **Final report and presentation** (May)

---
## How midterm work feeds in

- **Accelerator-level cost models:**  
  - Treat MAESTRO/Timeloop as **black boxes** that return latency and energy for (layer, dataflow, PE count).

- **System-level layer:**  
  - Add NoC + DRAM models (contention, bandwidth sharing).  
  - Combine per-accelerator costs with communication time.

- **Dataflow semantics:**  
  - Understanding OS/WS/RS in both tools is essential for mapping multiple layers / DNNs onto multiple accelerator cores.

---
<!-- _class: lead -->

# Thank you — Q&A

---
## Backup: Repo layout

- **MAESTRO:**  
  - `compare/maestro/hw/accelerator_1.m`  
  - `compare/maestro/mapping/single_layer_*_*.m`  
  - `compare/maestro/run_maestro.sh`

- **Timeloop:**  
  - `compare/timeloop/single_layer_problem.yaml`  
  - `compare/timeloop/arch_2level_2dconv.yaml` (and `arch_256pe_2dconv.yaml`)  
  - `compare/timeloop/map_same_layer_os.yaml`, `map_same_layer_ws.yaml`, `map_same_layer_rs.yaml`  
  - `compare/timeloop/run_same_layer_all.py`, `compare/timeloop/run_timeloop.sh`

- **Results & plots:**  
  - `compare/results/results_maestro.csv`, `results_timeloop.csv`  
  - `compare/results/summary_table.csv`  
  - `compare/results/comparison_latency_energy.png`  
  - `compare/results/comparison_edp.png`  
  - `compare/results/comparison_normalized.png`
