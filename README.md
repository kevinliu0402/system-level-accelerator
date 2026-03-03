# DNN Accelerator Dataflows: MAESTRO and Timeloop

This repo implements **output-stationary** (ShiDianNao), **weight-stationary** (NVDLA), and **row-stationary** (Eyeriss) in MAESTRO and Timeloop and compares their predicted performance with scripts and plots.

## Repos

- **maestro** — [MAESTRO](https://github.com/maestro-project/maestro) (Georgia Tech): analytical cost model for DNN dataflows
- **timeloop** — [Timeloop](https://github.com/NVlabs/timeloop) (NVlabs): DNN accelerator evaluation
- **timeloop-accelergy-exercises** — [Timeloop/Accelergy exercises](https://github.com/Accelergy-Project/timeloop-accelergy-exercises) (Eyeriss, NVDLA-like examples)

## Usage

From the repository root:

```bash
./compare/run_all.sh
```

This runs MAESTRO and Timeloop for the three dataflows, parses their outputs, and generates summary tables and plots under `compare/results/`:

- `summary_table.csv`
- `comparison_latency_energy.png`
- `comparison_edp.png`

If MAESTRO is not built, only Timeloop results and plots are generated (using the pre-generated exercise stats).

## Documentation (reference notes)

- **[docs/Notes_Dataflows_OS_WS_RS.md](docs/Notes_Dataflows_OS_WS_RS.md)** — Three dataflows (OS, WS, RS), ShiDianNao/NVDLA/Eyeriss mappings in MAESTRO and Timeloop, and reproduction commands.
- **[docs/Notes_Implementation.md](docs/Notes_Implementation.md)** — Comparison pipeline: mapping files, scripts, parsers, and outputs.
- **[docs/Notes_Dataflows_Technical.md](docs/Notes_Dataflows_Technical.md)** — Technical overview of output-/weight-/row-stationary dataflows, loop structures, and MAESTRO/Timeloop expression.
