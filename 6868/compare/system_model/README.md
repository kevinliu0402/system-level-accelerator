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

**Which row?** Environment variable **`BW_LAYER`** picks the **layer name** (e.g. `CONV2_1_2`) so all three CSVs use the **same layer** for a fair comparison.

If `Resnet50_yxp_os_pe256.csv` is missing, OS temporarily reuses the RS CSV. 
Generate the OS CSV with MAESTRO using mapping `Resnet50_yxp_os.m` and your PE config.

**Shared cap:** **`SYSTEM_BW`** is the total bandwidth both cores may use together. It must be in the **same units** as MAESTRO’s `Avg BW Req` (see `run_bw_combos.py` docstring). Optional overrides: `REQ_BW_OS`, `REQ_BW_WS`, `REQ_BW_RS`.

**Latencies:** Default **`LATENCY_FRAMEWORK=MAESTRO`** selects rows in `summary_table.csv`; use **`LATENCY_FRAMEWORK=Timeloop`** if you generated Timeloop rows.

## Commands

**Default run** (layer `CONV2_1_2`, `SYSTEM_BW=100`):

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

## Related files

- `magma_bw_allocator.py` — allocator logic  
- `run_example.py` — smaller example of the API  
- `noc_dram.py` — NoC/DRAM helpers (if used by your workflow)
