# Setup and “pytimeloop not found”

## You do **not** need pytimeloop for the standard comparison

`compare/timeloop/run_timeloop.sh` **copies pre-generated stats** from  
`timeloop-accelergy-exercises/.../ref-output/`.  
If those ref-output files exist (they do in this repo), **pytimeloop is never run** and `pip install pytimeloop` is not required.

So you can ignore the pytimeloop error for the normal workflow.

---

## Next steps (standard comparison, no pytimeloop)

From the **repo root**:

```bash
# 1. Build MAESTRO (one time)
cd maestro && scons && cd ..

# 2. Run full comparison (MAESTRO + Timeloop ref-output + parse + plot)
chmod +x compare/run_all.sh
./compare/run_all.sh
```

Then open:

- `compare/results/summary_table.csv`
- `compare/results/comparison_latency_energy.png`
- `compare/results/comparison_edp.png`

---

## Run Timeloop on the same layer as MAESTRO (RS)

To get Timeloop **row-stationary** results for the **same** conv layer (K=C=64, R=S=3, 56×56):

**One command from repo root (needs Docker):**

```bash
chmod +x compare/timeloop/run_timeloop_same_layer_rs_docker.sh
./compare/timeloop/run_timeloop_same_layer_rs_docker.sh
```

Then update the comparison:

```bash
python3 compare/parse_timeloop.py && python3 compare/plot_results.py
```

On Apple M1/M2 use: `DOCKER_ARCH=arm64 ./compare/timeloop/run_timeloop_same_layer_rs_docker.sh`

Once you have run this once, `run_timeloop.sh` will **not** overwrite `timeloop_rs_eyeriss.stats.txt`, so your same-layer RS stats are kept when you run `./compare/run_all.sh` later.

**Install Docker with sudo (recommended):**
```bash
sudo apt-get update && sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
```
Then log out and back in (or run `newgrp docker`). Pull the image and run the script:
```bash
docker pull timeloopaccelergy/timeloop-accelergy-pytorch:latest-amd64
./compare/timeloop/run_timeloop_same_layer_rs_docker.sh
```

**No sudo:** Run the script on another machine that has Docker, then copy `compare/results/timeloop_rs_eyeriss.stats.txt` back and run `python3 compare/parse_timeloop.py && python3 compare/plot_results.py`.

---

## Summary

| Goal                         | Need pytimeloop? | What to run                    |
|-----------------------------|------------------|--------------------------------|
| Full MAESTRO vs Timeloop    | **No**           | `./compare/run_all.sh`         |
| Timeloop RS on same layer   | Yes (Docker or build) | `run_timeloop_same_layer_rs_via_exercise.sh` in Docker |
