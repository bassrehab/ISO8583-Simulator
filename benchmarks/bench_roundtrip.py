#!/usr/bin/env python3
"""Benchmark full roundtrip: build -> parse -> validate."""

import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.pool import MessagePool
from iso8583sim.core.types import ISO8583Message
from iso8583sim.core.validator import ISO8583Validator


def benchmark_roundtrip(
    count: int, iterations: int = 5, warmup: int = 1, include_validation: bool = True
) -> tuple[float, float, float]:
    """Benchmark full roundtrip performance.

    Args:
        count: Number of messages per iteration
        iterations: Number of benchmark iterations
        warmup: Number of warmup iterations
        include_validation: Whether to include validation step

    Returns:
        Tuple of (mean_tps, min_tps, max_tps)
    """
    builder = ISO8583Builder()
    parser = ISO8583Parser()
    validator = ISO8583Validator()
    results = []

    def run_cycle(i: int):
        # Build
        msg = ISO8583Message(
            mti="0100",
            fields={
                0: "0100",
                2: f"411111111111{i:04d}",
                3: "000000",
                4: f"{(i % 100000):012d}",
                11: f"{i % 1000000:06d}",
                41: "TERM0001",
                42: "MERCHANT12345  ",
            },
        )
        raw = builder.build(msg)

        # Parse
        parsed = parser.parse(raw)

        # Validate (optional)
        if include_validation:
            validator.validate_message(parsed)

        return parsed

    # Warmup
    for _ in range(warmup):
        for i in range(min(count, 100)):  # Limit warmup
            run_cycle(i)

    # Benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        for i in range(count):
            run_cycle(i)
        elapsed = time.perf_counter() - start
        tps = count / elapsed
        results.append(tps)

    return statistics.mean(results), min(results), max(results)


def benchmark_response_flow(count: int, iterations: int = 5, warmup: int = 1) -> tuple[float, float, float]:
    """Benchmark request/response flow.

    Simulates: build request -> parse -> create response -> build response

    Args:
        count: Number of request/response pairs per iteration
        iterations: Number of benchmark iterations
        warmup: Number of warmup iterations

    Returns:
        Tuple of (mean_tps, min_tps, max_tps)
    """
    builder = ISO8583Builder()
    parser = ISO8583Parser()
    results = []

    def run_flow(i: int):
        # Build request
        request = ISO8583Message(
            mti="0100",
            fields={
                0: "0100",
                2: f"411111111111{i:04d}",
                3: "000000",
                4: "000000001000",
                11: f"{i % 1000000:06d}",
                41: "TERM0001",
                42: "MERCHANT12345  ",
            },
        )
        raw_request = builder.build(request)

        # Parse request
        parsed_request = parser.parse(raw_request)

        # Create response
        response = builder.create_response(parsed_request, {39: "00", 38: "ABC123"})

        # Build response
        raw_response = builder.build(response)

        return raw_response

    # Warmup
    for _ in range(warmup):
        for i in range(min(count, 100)):
            run_flow(i)

    # Benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        for i in range(count):
            run_flow(i)
        elapsed = time.perf_counter() - start
        tps = count / elapsed
        results.append(tps)

    return statistics.mean(results), min(results), max(results)


def benchmark_roundtrip_pooled(
    count: int, iterations: int = 5, warmup: int = 1, include_validation: bool = True
) -> tuple[float, float, float]:
    """Benchmark roundtrip with object pooling.

    Args:
        count: Number of messages per iteration
        iterations: Number of benchmark iterations
        warmup: Number of warmup iterations
        include_validation: Whether to include validation step

    Returns:
        Tuple of (mean_tps, min_tps, max_tps)
    """
    pool = MessagePool(size=100)
    builder = ISO8583Builder()
    parser = ISO8583Parser(pool=pool)
    validator = ISO8583Validator()
    results = []

    def run_cycle(i: int):
        # Build
        msg = ISO8583Message(
            mti="0100",
            fields={
                0: "0100",
                2: f"411111111111{i:04d}",
                3: "000000",
                4: f"{(i % 100000):012d}",
                11: f"{i % 1000000:06d}",
                41: "TERM0001",
                42: "MERCHANT12345  ",
            },
        )
        raw = builder.build(msg)

        # Parse (uses pool)
        parsed = parser.parse(raw)

        # Validate (optional)
        if include_validation:
            validator.validate_message(parsed)

        # Release back to pool
        pool.release(parsed)

        return parsed

    # Warmup
    for _ in range(warmup):
        for i in range(min(count, 100)):
            run_cycle(i)

    # Benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        for i in range(count):
            run_cycle(i)
        elapsed = time.perf_counter() - start
        tps = count / elapsed
        results.append(tps)

    return statistics.mean(results), min(results), max(results)


def run_benchmarks():
    """Run all roundtrip benchmarks."""
    print("=" * 60)
    print("ISO8583 Roundtrip Benchmarks")
    print("=" * 60)

    batch_sizes = [100, 1000, 10000]

    for size in batch_sizes:
        print(f"\n--- Batch size: {size:,} messages ---")

        # Full roundtrip with validation
        mean, min_tps, max_tps = benchmark_roundtrip(size, include_validation=True)
        print(f"Build->Parse->Validate: {mean:>8,.0f} TPS (min: {min_tps:,.0f}, max: {max_tps:,.0f})")

        # Roundtrip without validation
        mean, min_tps, max_tps = benchmark_roundtrip(size, include_validation=False)
        print(f"Build->Parse only:      {mean:>8,.0f} TPS (min: {min_tps:,.0f}, max: {max_tps:,.0f})")

        # Pooled roundtrip
        mean, min_tps, max_tps = benchmark_roundtrip_pooled(size, include_validation=True)
        print(f"Pooled (with validate): {mean:>8,.0f} TPS (min: {min_tps:,.0f}, max: {max_tps:,.0f})")

        # Request/Response flow
        mean, min_tps, max_tps = benchmark_response_flow(size)
        print(f"Request->Response flow: {mean:>8,.0f} TPS (min: {min_tps:,.0f}, max: {max_tps:,.0f})")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_benchmarks()
