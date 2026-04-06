"""
Simple analytical NoC + shared DRAM models for multi-accelerator system-level estimation.

Use with per-accelerator latency/energy from MAESTRO or Timeloop (isolated tile).
This does NOT replace those tools; it adds system-level overhead on top.

Units: bandwidth in GB/s; bytes for traffic; clock_hz for cycle conversion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


def gbps_to_bytes_per_sec(gbps: float) -> float:
    return gbps * 1e9 / 8.0  # GB/s = 10^9 bytes/s (decimal); bits/8 = bytes


@dataclass
class AcceleratorTile:
    """One accelerator instance with isolated metrics and traffic estimates."""

    name: str
    latency_cycles: float
    dram_bytes_read: float = 0.0
    dram_bytes_write: float = 0.0
    noc_bytes_to_dram: float = 0.0  # traffic that uses NoC toward DRAM path
    noc_bytes_to_peer: float = 0.0  # inter-accelerator traffic


@dataclass
class SystemConfig:
    """Shared resources."""

    clock_hz: float = 1e9
    dram_bandwidth_gbps: float = 25.0  # shared DRAM read+write
    noc_bandwidth_gbps: float = 100.0  # aggregate NoC


def bytes_to_cycles_transfer(bytes_total: float, bandwidth_gbps: float, clock_hz: float) -> float:
    """Time to move bytes at given link bandwidth, returned in cycles."""
    if bandwidth_gbps <= 0 or bytes_total <= 0:
        return 0.0
    bps = gbps_to_bytes_per_sec(bandwidth_gbps)
    seconds = bytes_total / bps
    return seconds * clock_hz


def dram_serial_contention_cycles(
    tiles: List[AcceleratorTile],
    dram_bw_gbps: float,
    clock_hz: float,
) -> float:
    """
    Worst-case serial DRAM time: all DRAM traffic serialized on one pipe.
    Total bytes = sum(read + write) across tiles (overlapping in time would be lower).
    """
    total = sum(t.dram_bytes_read + t.dram_bytes_write for t in tiles)
    return bytes_to_cycles_transfer(total, dram_bw_gbps, clock_hz)


def noc_aggregate_contention_cycles(
    tiles: List[AcceleratorTile],
    noc_bw_gbps: float,
    clock_hz: float,
) -> float:
    """
    Time to move all NoC-related bytes if they share one aggregate NoC capacity.
    """
    total = sum(t.noc_bytes_to_dram + t.noc_bytes_to_peer for t in tiles)
    return bytes_to_cycles_transfer(total, noc_bw_gbps, clock_hz)


@dataclass
class SystemEstimate:
    max_isolated_cycles: float
    dram_extra_cycles: float
    noc_extra_cycles: float
    total_cycles: float
    note: str


def estimate_multi_accelerator_system(
    tiles: List[AcceleratorTile],
    cfg: SystemConfig,
    mode: str = "max_plus_overhead",
) -> SystemEstimate:
    """
    Combine isolated accelerator latencies with simple DRAM + NoC bounds.

    mode:
      - "max_plus_overhead": T_sys = max(T_i) + T_dram_serial + T_noc_serial
        (conservative; assumes compute and memory could overlap less than ideal)
      - "max_of_three": T_sys = max(max(T_i), T_dram_serial, T_noc_serial)
        (optimistic overlap)
    """
    if not tiles:
        return SystemEstimate(0, 0, 0, 0, "no tiles")

    max_iso = max(t.latency_cycles for t in tiles)
    dram_c = dram_serial_contention_cycles(tiles, cfg.dram_bandwidth_gbps, cfg.clock_hz)
    noc_c = noc_aggregate_contention_cycles(tiles, cfg.noc_bandwidth_gbps, cfg.clock_hz)

    if mode == "max_of_three":
        total = max(max_iso, dram_c, noc_c)
        note = "T_sys = max( max(T_i), T_DRAM_serial, T_NoC )"
    else:
        total = max_iso + dram_c + noc_c
        note = "T_sys = max(T_i) + T_DRAM_serial + T_NoC (conservative)"

    return SystemEstimate(
        max_isolated_cycles=max_iso,
        dram_extra_cycles=dram_c,
        noc_extra_cycles=noc_c,
        total_cycles=total,
        note=note,
    )


def example_from_summary_csv_row(latency_cycles: float, num_tiles: int = 4) -> SystemEstimate:
    """
    Placeholder traffic: scale DRAM bytes roughly with layer size (tune from your workload).
    Here we use a toy: each tile same latency; DRAM bytes proportional to 107M MACs layer.
    """
    # Toy: 256 MB read + 128 MB write per tile (replace with measured or modeled traffic)
    bytes_per_tile_read = 256 * 1024 * 1024
    bytes_per_tile_write = 128 * 1024 * 1024
    tiles = []
    for i in range(num_tiles):
        tiles.append(
            AcceleratorTile(
                name=f"tile_{i}",
                latency_cycles=latency_cycles,
                dram_bytes_read=bytes_per_tile_read,
                dram_bytes_write=bytes_per_tile_write,
                noc_bytes_to_dram=bytes_per_tile_read + bytes_per_tile_write,
                noc_bytes_to_peer=32 * 1024 * 1024 * (num_tiles - 1) if num_tiles > 1 else 0,
            )
        )
    cfg = SystemConfig()
    return estimate_multi_accelerator_system(tiles, cfg, mode="max_plus_overhead")
