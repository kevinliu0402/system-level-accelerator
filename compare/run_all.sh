#!/usr/bin/env bash
# Run MAESTRO and Timeloop for all three dataflows, parse results, and plot.
# Usage: from repo root: ./compare/run_all.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "=== 1. MAESTRO ==="
bash compare/maestro/run_maestro.sh
python3 compare/parse_maestro.py

echo "=== 2. Timeloop ==="
bash compare/timeloop/run_timeloop.sh
python3 compare/parse_timeloop.py

echo "=== 3. Merge and plot ==="
python3 compare/plot_results.py

echo "Done. Results and plots: compare/results/"
