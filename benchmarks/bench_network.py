"""Benchmarks for wire encoding and the TCP client / mock host.

Run with: python benchmarks/bench_network.py
"""

import asyncio
import copy
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.samples import sample_message
from iso8583sim.net import ISO8583Client, MockHost, run_load
from iso8583sim.wire import WireFormat, decode_message, encode_message

PRESETS = ["ascii-hex", "ascii-binary", "bcd", "ebcdic"]


def bench_wire(iterations: int = 20000) -> None:
    print(f"Wire encode/decode ({iterations:,} messages each)")
    print(f"{'format':14} {'bytes':>6} {'encode msg/s':>14} {'decode msg/s':>14}")
    builder = ISO8583Builder()
    message = sample_message()
    for preset in PRESETS:
        fmt = WireFormat.preset(preset)
        data = encode_message(copy.deepcopy(message), fmt, builder)

        start = time.perf_counter()
        for _ in range(iterations):
            encode_message(copy.deepcopy(message), fmt, builder)
        encode_rate = iterations / (time.perf_counter() - start)

        start = time.perf_counter()
        for _ in range(iterations):
            decode_message(data, fmt)
        decode_rate = iterations / (time.perf_counter() - start)
        print(f"{preset:14} {len(data):>6} {encode_rate:>14,.0f} {decode_rate:>14,.0f}")


async def bench_tcp(count: int = 20000) -> None:
    print(f"\nTCP round trips against a local mock host ({count:,} requests, BCD)")
    print(f"{'concurrency':>11} {'connections':>11} {'msg/s':>9} {'p50 ms':>8} {'p99 ms':>8}")
    fmt = WireFormat.bcd()
    host = MockHost(wire_format=fmt)
    await host.start("127.0.0.1", 0)
    try:
        for concurrency, connections in [(1, 1), (10, 1), (50, 1), (50, 4), (200, 4)]:
            report = await run_load(
                lambda: ISO8583Client("127.0.0.1", host.port, wire_format=fmt),
                count=count,
                concurrency=concurrency,
                connections=connections,
            )
            assert report.responses == count, report
            print(
                f"{concurrency:>11} {connections:>11} {report.throughput:>9,.0f} "
                f"{report.percentile(50):>8.2f} {report.percentile(99):>8.2f}"
            )
    finally:
        await host.stop()


if __name__ == "__main__":
    logging.disable(logging.INFO)
    bench_wire()
    # Client and host share one process and event loop here, so these numbers are a floor
    # for the library's overhead rather than a network measurement.
    asyncio.run(bench_tcp())
