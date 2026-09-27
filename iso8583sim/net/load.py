# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Load generator: send many requests concurrently and measure throughput and latency."""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from ..core.samples import sample_message
from ..core.types import CardNetwork, ISO8583Message
from .client import ISO8583Client


@dataclass
class LoadReport:
    """Results of a load run. Latencies are in milliseconds."""

    sent: int = 0
    responses: int = 0
    timeouts: int = 0
    errors: int = 0
    duration_s: float = 0.0
    latencies_ms: list[float] = field(default_factory=list)
    response_codes: Counter[str] = field(default_factory=Counter)

    @property
    def throughput(self) -> float:
        """Responses per second."""
        return self.responses / self.duration_s if self.duration_s else 0.0

    def percentile(self, p: float) -> float:
        """Latency percentile (nearest rank), e.g. percentile(95)."""
        if not self.latencies_ms:
            return 0.0
        ordered = sorted(self.latencies_ms)
        rank = max(1, round(p / 100 * len(ordered)))
        return ordered[min(rank, len(ordered)) - 1]


def _default_messages(network: CardNetwork | None) -> Callable[[int], ISO8583Message]:
    # subhadipmitra@: STAN is 6 digits, so it cycles after 999999. Unique STANs among the
    # requests in flight are what matters for matching, and concurrency is far below that.
    return lambda i: sample_message(network=network, stan=f"{i % 999999 + 1:06d}")


async def run_load(
    make_client: Callable[[], ISO8583Client],
    count: int,
    concurrency: int = 10,
    connections: int = 1,
    network: CardNetwork | None = None,
    make_message: Callable[[int], ISO8583Message] | None = None,
) -> LoadReport:
    """Send `count` requests with at most `concurrency` in flight, spread over `connections`.

    Args:
        make_client: Creates a (not yet connected) client
        count: Number of requests to send
        concurrency: Maximum requests waiting for a response at once
        connections: Number of TCP connections to spread requests over
        network: Card network for the generated sample messages
        make_message: Builds request i. Defaults to sample authorizations with unique STANs.

    Returns:
        LoadReport with counts, response codes and latencies
    """
    if count < 1 or concurrency < 1 or connections < 1:
        raise ValueError("count, concurrency and connections must be at least 1")
    build = make_message or _default_messages(network)
    clients = [make_client() for _ in range(connections)]
    report = LoadReport()
    indexes = iter(range(count))

    async def worker() -> None:
        # subhadipmitra@: A fixed pool of workers pulls request numbers from a shared iterator,
        # so memory stays flat however large `count` is. Each worker has one request in
        # flight at a time, so the pool size is the concurrency.
        for i in indexes:
            client = clients[i % connections]
            report.sent += 1
            start = time.perf_counter()
            try:
                response = await client.send(build(i))
            except TimeoutError:
                report.timeouts += 1
                continue
            except (ConnectionError, OSError, ValueError):
                report.errors += 1
                continue
            report.latencies_ms.append((time.perf_counter() - start) * 1000)
            report.responses += 1
            report.response_codes[response.fields.get(39, "??")] += 1

    try:
        await asyncio.gather(*(c.connect() for c in clients))
        started = time.perf_counter()
        await asyncio.gather(*(worker() for _ in range(min(concurrency, count))))
        report.duration_s = time.perf_counter() - started
    finally:
        await asyncio.gather(*(c.close() for c in clients), return_exceptions=True)
    return report
