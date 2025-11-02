#!/usr/bin/env python3
"""Benchmark ISO8583 message building performance."""

import statistics
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.types import ISO8583Message


def generate_message_data(count: int) -> list[dict[str, Any]]:
    """Generate message data for building.

    Args:
        count: Number of message data sets to generate

    Returns:
        List of dictionaries with mti and fields
    """
    data = []
    for i in range(count):
        data.append(
            {
                "mti": "0100",
                "fields": {
                    0: "0100",
                    2: f"411111111111{i:04d}",
                    3: "000000",
                    4: f"{(i % 100000):012d}",
                    11: f"{i % 1000000:06d}",
                    41: "TERM0001",
                    42: "MERCHANT12345  ",
                },
            }
        )
    return data


def benchmark_build(
    message_data: list[dict[str, Any]], iterations: int = 5, warmup: int = 1
) -> tuple[float, float, float]:
    """Benchmark building performance.

    Args:
        message_data: List of message data dicts
        iterations: Number of benchmark iterations
        warmup: Number of warmup iterations

    Returns:
        Tuple of (mean_tps, min_tps, max_tps)
    """
    builder = ISO8583Builder()
    results = []

    # Warmup
    for _ in range(warmup):
        for data in message_data:
            msg = ISO8583Message(mti=data["mti"], fields=data["fields"].copy())
            builder.build(msg)

    # Benchmark
    for _i in range(iterations):
        start = time.perf_counter()
        for data in message_data:
            msg = ISO8583Message(mti=data["mti"], fields=data["fields"].copy())
            builder.build(msg)
        elapsed = time.perf_counter() - start
        tps = len(message_data) / elapsed
        results.append(tps)

    return statistics.mean(results), min(results), max(results)


def benchmark_create_message(count: int, iterations: int = 5, warmup: int = 1) -> tuple[float, float, float]:
    """Benchmark create_message method (includes validation).

    Args:
        count: Number of messages to create per iteration
        iterations: Number of benchmark iterations
        warmup: Number of warmup iterations

    Returns:
        Tuple of (mean_tps, min_tps, max_tps)
    """
    builder = ISO8583Builder()
    results = []

    # Warmup
    for _ in range(warmup):
        for i in range(count):
            builder.create_message(
                "0100",
                {
                    2: f"411111111111{i:04d}",
                    3: "000000",
                    4: "000000001000",
                    11: f"{i:06d}",
                    41: "TERM0001",
                    42: "MERCHANT12345  ",
                },
            )

    # Benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        for i in range(count):
            builder.create_message(
                "0100",
                {
                    2: f"411111111111{i:04d}",
                    3: "000000",
                    4: "000000001000",
                    11: f"{i:06d}",
                    41: "TERM0001",
                    42: "MERCHANT12345  ",
                },
            )
        elapsed = time.perf_counter() - start
        tps = count / elapsed
        results.append(tps)

    return statistics.mean(results), min(results), max(results)


def run_benchmarks():
    """Run all builder benchmarks."""
    print("=" * 60)
    print("ISO8583 Builder Benchmarks")
    print("=" * 60)

    batch_sizes = [100, 1000, 10000]

    for size in batch_sizes:
        print(f"\n--- Batch size: {size:,} messages ---")

        # Build only (no validation)
        message_data = generate_message_data(size)
        mean, min_tps, max_tps = benchmark_build(message_data)
        print(f"build():          {mean:>10,.0f} TPS (min: {min_tps:,.0f}, max: {max_tps:,.0f})")

        # Create message (includes validation)
        mean, min_tps, max_tps = benchmark_create_message(size)
        print(f"create_message(): {mean:>10,.0f} TPS (min: {min_tps:,.0f}, max: {max_tps:,.0f})")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_benchmarks()
