#!/usr/bin/env python3
"""Benchmark ISO8583 message parsing performance."""

import statistics
import sys
import time
from pathlib import Path

from conftest import generate_emv_messages, generate_test_messages

sys.path.insert(0, str(Path(__file__).parent.parent))

from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.types import CardNetwork


def benchmark_parse(messages: list[str], iterations: int = 5, warmup: int = 1) -> tuple[float, float, float]:
    """Benchmark parsing performance.

    Args:
        messages: List of raw messages to parse
        iterations: Number of benchmark iterations
        warmup: Number of warmup iterations (not counted)

    Returns:
        Tuple of (mean_tps, min_tps, max_tps)
    """
    parser = ISO8583Parser()
    results = []

    # Warmup
    for _ in range(warmup):
        for msg in messages:
            parser.parse(msg)

    # Benchmark
    for _i in range(iterations):
        start = time.perf_counter()
        for msg in messages:
            parser.parse(msg)
        elapsed = time.perf_counter() - start
        tps = len(messages) / elapsed
        results.append(tps)

    return statistics.mean(results), min(results), max(results)


def run_benchmarks():
    """Run all parser benchmarks."""
    print("=" * 60)
    print("ISO8583 Parser Benchmarks")
    print("=" * 60)

    # Test different batch sizes
    batch_sizes = [100, 1000, 10000]

    for size in batch_sizes:
        print(f"\n--- Batch size: {size:,} messages ---")

        # Basic messages
        messages = generate_test_messages(size)
        mean, min_tps, max_tps = benchmark_parse(messages)
        print(f"Basic messages:  {mean:>10,.0f} TPS (min: {min_tps:,.0f}, max: {max_tps:,.0f})")

        # VISA network
        visa_messages = generate_test_messages(size, CardNetwork.VISA)
        mean, min_tps, max_tps = benchmark_parse(visa_messages)
        print(f"VISA messages:   {mean:>10,.0f} TPS (min: {min_tps:,.0f}, max: {max_tps:,.0f})")

        # EMV messages
        emv_messages = generate_emv_messages(size)
        mean, min_tps, max_tps = benchmark_parse(emv_messages)
        print(f"EMV messages:    {mean:>10,.0f} TPS (min: {min_tps:,.0f}, max: {max_tps:,.0f})")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_benchmarks()
