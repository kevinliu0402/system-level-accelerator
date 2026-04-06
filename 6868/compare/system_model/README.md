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

**Not the full network:** Each run uses **a single layer’s** `Avg BW Req` triple. There is no built-in “run all layers / entire structure” mode—repeat with different `BW_LAYER` values (see the loop below) if you want a sweep.

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

## Related files

- `magma_bw_allocator.py` — allocator logic  
- `run_example.py` — smaller example of the API  
- `noc_dram.py` — NoC/DRAM helpers (if used by your workflow)  
- `scar_workloads.json`, `run_scar_multi_model_bw.py`, `maestro_layer_metrics.py` — SCAR-inspired multi-model runs
