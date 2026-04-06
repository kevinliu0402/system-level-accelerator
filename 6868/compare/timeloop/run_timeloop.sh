#!/usr/bin/env bash
# Run Timeloop OS, WS, RS on the same layer (K=C=64, R=S=3, P=Q=56) via Docker, then parse and plot.
# Usage: from repo root: ./compare/timeloop/run_timeloop.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ARCH="${DOCKER_ARCH:-amd64}"
IMAGE="timeloopaccelergy/timeloop-accelergy-pytorch:latest-${ARCH}"

if command -v docker &>/dev/null; then
  DOCKER_CMD=docker
elif command -v podman &>/dev/null; then
  DOCKER_CMD=podman
else
  echo "Docker or Podman not found. Install Docker and run: docker pull $IMAGE" 1>&2
  exit 1
fi

echo "Running Timeloop OS, WS, RS (same layer) in Docker..."
$DOCKER_CMD run --rm \
  -v "$REPO_ROOT":/home/repo \
  -w /home/repo/compare/timeloop \
  "$IMAGE" \
  python3 run_same_layer_all.py

echo "Parsing and plotting..."
python3 "$REPO_ROOT/compare/parse_timeloop.py"
python3 "$REPO_ROOT/compare/plot_results.py"
echo "Done. Plots in $REPO_ROOT/compare/results/"
