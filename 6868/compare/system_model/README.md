# System model: shared bandwidth allocator

`run_bw_combos.py` simulates **MAGMA-style** allocation for **two cores** sharing one **system bandwidth** cap. Each core runs a job with:

- **No-stall latency** `L` (cycles), from `compare/results/summary_table.csv`
- **Required bandwidth** `bw_req`, so the job stays compute-bound if it gets that much BW

The allocator (`magma_bw_allocator.py`) scales allocations when total demand exceeds the cap and reports **makespan**, **bandwidth utilization**, and **per-slice allocations**.

## Three bandwidth requirements

Instead of a constant bandwidth, the script uses **three numbers**—one per dataflow—read from MAESTRO exports:

| Dataflow (core type) | CSV under `maestro/tools/jupyter_notebook/data/` | Column used |
|----------------------|--------------------------------------------------|-------------|
| Eyeriss (RS)         | `Resnet50_rs_pe256.csv`                          | `Avg BW Req` |
| NVDLA (WS)           | `Resnet50_kcp_ws_pe256.csv`                      | `Avg BW Req` |
| ShiDianNao (OS)      | `Resnet50_yxp_os_pe256.csv`                      | `Avg BW Req` |

**Which row?** Environment variable **`BW_LAYER`** picks **one** ResNet-50 **layer name** (e.g. `CONV2_1_2`) so all three CSVs use the **same layer** for a fair comparison.

**Single-layer default:** Each run uses **one** layer’s `Avg BW Req` triple. For the **full ResNet-50 layer list** with **per-layer** MAESTRO `Runtime` + `Avg BW Req`, use **`run_bw_combos_full_network.py`** (sums makespans layer-by-layer for each combo; see that file’s docstring).

If `Resnet50_yxp_os_pe256.csv` is missing, OS temporarily reuses the RS CSV. 
Generate the OS CSV with MAESTRO using mapping `Resnet50_yxp_os.m` and your PE config.

**Shared cap:** **`SYSTEM_BW`** is the total bandwidth both cores may use together. It must be in the **same units** as MAESTRO’s `Avg BW Req` (see `run_bw_combos.py` docstring). Optional overrides: `REQ_BW_OS`, `REQ_BW_WS`, `REQ_BW_RS`.

**Latencies:** Default **`LATENCY_FRAMEWORK=MAESTRO`** selects rows in `summary_table.csv`; use **`LATENCY_FRAMEWORK=Timeloop`** if you generated Timeloop rows.

## Commands

**Default run** (`SYSTEM_BW=100`, **`BW_LAYER` unset → same as `BW_LAYER=CONV2_1_2`**—one layer only):

```bash
cd /path/to/6868
python3 compare/system_model/run_bw_combos.py
```

**Choose layer and system bandwidth** (e.g. narrow vs wide bus in consistent units):

```bash
cd /path/to/6868
BW_LAYER=CONV3_1_2 SYSTEM_BW=256 python3 compare/system_model/run_bw_combos.py
```

**Sweep a few layers** (bash):

```bash
cd /path/to/6868
for L in CONV2_1_2 CONV3_1_2 CONV4_1_2; do
  echo "=== BW_LAYER=$L ==="
  BW_LAYER=$L python3 compare/system_model/run_bw_combos.py
done
```

**Override one required bandwidth** (optional):

```bash
REQ_BW_OS=50 python3 compare/system_model/run_bw_combos.py
```

**Regenerate OS MAESTRO CSV** (from `6868/maestro` after building `./maestro`):

```bash
cd /path/to/6868/maestro
./maestro --HW_file='data/hw/accelerator_1.m' \
  --Mapping_file='data/mapping/Resnet50_yxp_os.m' \
  --print_res=false --print_res_csv_file=true --print_log_file=false
cp Resnet50_yxp_os.csv tools/jupyter_notebook/data/Resnet50_yxp_os_pe256.csv
```

## Full network (all ResNet-50 layers in MAESTRO CSV)

Uses **per-layer** metrics from MAESTRO (not `summary_table.csv` latencies). Assumes layers run **serially**: each layer runs the 2-core combo to completion, then the next layer starts.

```bash
cd /path/to/6868
python3 compare/system_model/run_bw_combos_full_network.py
```

**One combo only** (`OS_RS`, `RS_WS`, or `WS_OS`):

```bash
FULLNET_COMBO=RS_WS SYSTEM_BW=100 python3 compare/system_model/run_bw_combos_full_network.py
```

**Per-layer CSV:**

```bash
FULLNET_OUT_CSV=compare/results/full_net_bw_layers.csv \
  python3 compare/system_model/run_bw_combos_full_network.py
```

### Full MobileNetV2 (all layers in `MobileNetV2_kcp_ws_pe256.csv`)

Same serial full-network idea as ResNet-50. **Only the WS MAESTRO CSV exists** for MobileNetV2; OS/RS jobs reuse that file, so some two-core combos use **identical** `(L, bw_req)` on both cores—see the script banner.

```bash
cd /path/to/6868
python3 compare/system_model/run_mobilenet_full_network_bw.py
```

```bash
FULLNET_COMBO=RS_WS SYSTEM_BW=100 python3 compare/system_model/run_mobilenet_full_network_bw.py
```

```bash
MOBILENET_FULLNET_OUT_CSV=compare/results/mobilenet_full_net_bw_layers.csv \
  python3 compare/system_model/run_mobilenet_full_network_bw.py
```

(`FULLNET_OUT_CSV` is also accepted if `MOBILENET_FULLNET_OUT_CSV` is unset.)

**Plot makespan** (`pip install matplotlib`):

```bash
python3 compare/system_model/visualize_makespan.py \
  --csv compare/results/full_net_bw_layers.csv --out compare/results/makespan_resnet.png
python3 compare/system_model/visualize_makespan.py \
  --csv compare/results/full_net_bw_layers.csv --out compare/results/makespan_cum.png --cumulative
python3 compare/system_model/visualize_makespan.py \
  --csv compare/results/scar.csv --out compare/results/makespan_scar.png --mode scar
```

## Export ONNX (PyTorch / torchvision)

Standard **ImageNet** weights → ONNX for ResNet-50 and MobileNet-V2 (for tooling / graph inspection; MAESTRO still uses its own `.m` mappings).

```bash
pip install torch torchvision onnx
cd /path/to/6868
python3 compare/scripts/export_resnet_mobilenet_onnx.py
```

Optional: `OUT_DIR=/path/to/out ONNX_OPSET=17 python3 compare/scripts/export_resnet_mobilenet_onnx.py`

Default output: `compare/models/onnx/resnet50.onnx` and `mobilenet_v2.onnx`.

## SCAR-style multi-model CNN workloads (next step)

[SCAR](https://arxiv.org/abs/2405.00790) (MICRO 2024) studies **multi-model** scheduling on heterogeneous MCM accelerators; evaluation uses **ten** scenarios (roughly: MLPerf-style datacenter multi-tenancy + XRBench-style AR/VR). You do **not** need to invent many new DNNs from scratch: the paper draws suites from **industry traces and benchmarks** (MLPerf, XRBench) and uses CNNs such as **ResNet-50** alongside heavier models.

This repo adds a **small, runnable subset** in `scar_workloads.json`: five **two-job** scenarios mixing **ResNet-50** and **MobileNetV2** with MAESTRO exports. Each job uses **`Runtime (Cycles)`** and **`Avg BW Req`** from the correct CSV row (per network, layer, and dataflow). **MobileNetV2** only ships a **weight-stationary** CSV in-tree; OS/RS jobs on MobileNet reuse that file (noted in the script output).

**Run all scenarios:**

```bash
cd /path/to/6868
python3 compare/system_model/run_scar_multi_model_bw.py
```

**One scenario, optional CSV output:**

```bash
SCAR_SCENARIO=DC_A SCAR_OUT_CSV=compare/results/scar_multi_model_bw.csv \
  SYSTEM_BW=256 python3 compare/system_model/run_scar_multi_model_bw.py
```

## Greedy 4-chiplet schedule (SCAR-inspired, ResNet + MobileNet)

Heterogeneous **four chiplets** (two **WS**, one **OS**, one **RS**), **two** single-stream networks (**ResNet-50**, **MobileNetV2**). Each step greedily picks a legal chiplet pair (or one chiplet when a network is finished) to minimize **completion time** under the **2-core MAGMA `bw_allocator`** with shared **`SYSTEM_BW`**.

```bash
cd /path/to/6868
SYSTEM_BW=100 GREEDY4_OUT_CSV=compare/results/greedy_four_chiplet_schedule.csv \
  python3 compare/system_model/run_greedy_four_chiplet.py
python3 compare/system_model/visualize_greedy_four_chiplet.py \
  --csv compare/results/greedy_four_chiplet_schedule.csv \
  --out compare/results/greedy_four_chiplet.png
```

## Plot layer results (`visualize_layer_results.py`)

These commands expect your shell’s current directory to be the **`6868`** project root (paths to `--csv` / `--out` are relative to that directory):

```bash
cd /path/to/6868
python3 compare/system_model/visualize_layer_results.py --kind lookup \
  --csv compare/results/layer_accel_lookup_resnet50.csv \
  --out compare/results/plot_layer_lookup.png

python3 compare/system_model/visualize_layer_results.py --kind traffic --combo OS_RS \
  --csv compare/results/full_net_bw_layers.csv \
  --out compare/results/plot_fullnet_traffic_OS_RS.png
```

The **traffic** figure uses three stacked panels: **allocator `makespan` + `bw_util`** (same MAGMA model as `visualize_makespan.py`), **per-layer MAESTRO `total_traffic` bars**, and **cumulative makespan vs cumulative traffic** (dual *y*). The **lookup** figure adds a **cumulative serial-time** panel: MAESTRO runtime sum for the chosen mapping and, when the CSV includes `*_makespan_cycles`, cumulative MAGMA makespan for the same choices under shared BW.

**Lookup table (`build_layer_lookup.py`):** `LOOKUP_POLICY=min_latency` (default) picks the lowest MAESTRO runtime per layer with no bus contention. Use **`LOOKUP_POLICY=min_makespan`** with **`SYSTEM_BW`** and optional **`LOOKUP_PARTNER_DATAFLOW`** (default `Eyeriss_RS`) to score each core0 mapping by **MAGMA allocator makespan** for that layer versus a fixed partner on core1—so choices reflect slowdown when combined demand exceeds the shared cap. Regenerate the CSV, then point `visualize_layer_results.py --kind lookup` at it; plots auto-detect `*_makespan_cycles` columns and label axes accordingly.

```bash
cd /path/to/6868
LOOKUP_POLICY=min_makespan SYSTEM_BW=100 \
  LOOKUP_OUT_CSV=compare/results/layer_accel_lookup_resnet50_bw.csv \
  python3 compare/system_model/build_layer_lookup.py
```

## Related files

- `magma_bw_allocator.py` — allocator logic  
- `run_example.py` — smaller example of the API  
- `noc_dram.py` — NoC/DRAM helpers (if used by your workflow)  
- `scar_workloads.json`, `run_scar_multi_model_bw.py`, `maestro_layer_metrics.py` — SCAR-inspired multi-model runs  
- `run_bw_combos_full_network.py` — full ResNet-50 layer sweep  
- `run_mobilenet_full_network_bw.py` — full MobileNetV2 layer sweep (WS CSV proxy for OS/RS)  
- `compare/scripts/export_resnet_mobilenet_onnx.py` — ONNX export  
- `visualize_makespan.py` — plots from full-net or SCAR CSVs  
- `build_layer_lookup.py`, `visualize_layer_results.py` — per-layer best-accelerator table + plots (`lookup` / `traffic`)  
- `run_greedy_four_chiplet.py`, `visualize_greedy_four_chiplet.py` — greedy 4-chiplet (2×WS, OS, RS) schedule + plot
