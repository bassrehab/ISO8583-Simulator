# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Mock issuer host: an asyncio TCP server that answers ISO 8583 requests by rules."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.builder import ISO8583Builder
from ..core.types import ISO8583Message, ISO8583Version, ParseError
from ..wire import WireFormat, decode_message, encode_message
from .framing import Framing, swap_tpdu

logger = logging.getLogger(__name__)

ACTIONS = ("respond", "drop", "close")

# subhadipmitra@: Fields a response echoes from its request, so the acquirer can match and
# reconcile it: PAN, processing code, amounts, times, STAN, IDs, currency and, for network
# management, field 70.
ECHOED_FIELDS = (2, 3, 4, 7, 11, 12, 13, 32, 33, 37, 41, 42, 49, 70)


@dataclass
class Rule:
    """One response rule. The first rule whose conditions all match is used.

    Attributes:
        mti: Request MTIs this rule applies to (any when empty)
        pan_prefix: Only match cards whose PAN starts with one of these
        amount_gt: Only match when field 4 is greater than this (minor units)
        amount_lt: Only match when field 4 is less than this (minor units)
        network: Only match this card network (e.g. "VISA")
        fields: Only match when these fields have exactly these values
        respond: Response code for field 39
        action: "respond" (default), "drop" (never answer, to test timeouts) or
            "close" (close the connection)
        delay_ms: Wait this long before answering
    """

    mti: list[str] = field(default_factory=list)
    pan_prefix: list[str] = field(default_factory=list)
    amount_gt: int | None = None
    amount_lt: int | None = None
    network: str | None = None
    fields: dict[int, str] = field(default_factory=dict)
    respond: str = "00"
    action: str = "respond"
    delay_ms: int = 0

    def __post_init__(self) -> None:
        if self.action not in ACTIONS:
            raise ValueError(f"Rule action must be one of: {', '.join(ACTIONS)}")
        if not (len(self.respond) == 2 and self.respond.isalnum()):
            raise ValueError(f"Response code must be 2 characters, got {self.respond!r}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        """Build a rule from a rules-file entry: {"match": {...}, "respond": "51", ...}."""
        match = dict(data.get("match") or {})
        unknown = set(match) - {"mti", "pan_prefix", "amount_gt", "amount_lt", "network", "fields"}
        unknown |= set(data) - {"match", "respond", "action", "delay_ms"}
        if unknown:
            raise ValueError(f"Unknown rule keys: {', '.join(sorted(unknown))}")

        def as_list(value: Any) -> list[str]:
            if value is None:
                return []
            return [str(v) for v in (value if isinstance(value, list) else [value])]

        return cls(
            mti=as_list(match.get("mti")),
            pan_prefix=as_list(match.get("pan_prefix")),
            amount_gt=match.get("amount_gt"),
            amount_lt=match.get("amount_lt"),
            network=match.get("network"),
            fields={int(k): str(v) for k, v in (match.get("fields") or {}).items()},
            respond=str(data.get("respond", "00")),
            action=data.get("action", "respond"),
            delay_ms=int(data.get("delay_ms", 0)),
        )

    def matches(self, request: ISO8583Message) -> bool:
        fields = request.fields
        if self.mti and request.mti not in self.mti:
            return False
        if self.pan_prefix and not any(fields.get(2, "").startswith(p) for p in self.pan_prefix):
            return False
        amount = int(fields[4]) if fields.get(4, "").isdigit() else None
        if self.amount_gt is not None and (amount is None or amount <= self.amount_gt):
            return False
        if self.amount_lt is not None and (amount is None or amount >= self.amount_lt):
            return False
        if self.network and (request.network is None or request.network.value != self.network.upper()):
            return False
        return all(fields.get(n) == v for n, v in self.fields.items())


def load_rules(path: str | Path) -> list[Rule]:
    """Load rules from a JSON or YAML file with a top-level "rules" list."""
    text = Path(path).read_text()
    if str(path).endswith((".yaml", ".yml")):
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError:
            raise ValueError("YAML rules need PyYAML: pip install pyyaml (or use a .json file)") from None
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise ValueError('Rules file must contain a top-level "rules" list')
    return [Rule.from_dict(entry) for entry in data["rules"]]


# subhadipmitra@: Approve everything by default, so a bare mock host is immediately useful
# for happy-path tests. Declines, delays and timeouts are opt-in through rules.
DEFAULT_RULES = [Rule()]


def response_mti(mti: str) -> str:
    """0100 -> 0110, 0200 -> 0210, 0400 -> 0410, 0800 -> 0810, 0120 -> 0130."""
    function = int(mti[2])
    if function % 2:
        raise ValueError(f"MTI {mti} is already a response")
    return mti[:2] + str(function + 1) + mti[3]


@dataclass
class HostStats:
    """Counters for what the mock host has seen and done."""

    received: int = 0
    responded: int = 0
    dropped: int = 0
    errors: int = 0
    response_codes: Counter[str] = field(default_factory=Counter)


class MockHost:
    """A mock issuer host for testing acquirer and switch software.

    Example:
        >>> host = MockHost(rules=[Rule(amount_gt=100000, respond="51"), Rule()])
        >>> server = await host.start("127.0.0.1", 8583)
    """

    def __init__(
        self,
        rules: list[Rule] | None = None,
        wire_format: WireFormat | None = None,
        framing: Framing | None = None,
        version: ISO8583Version = ISO8583Version.V1987,
    ):
        self.rules = rules or DEFAULT_RULES
        self.wire_format = wire_format or WireFormat.ascii_binary()
        self.framing = framing or Framing()
        self.version = version
        self.stats = HostStats()
        self._builder = ISO8583Builder(version=version)
        self._server: asyncio.Server | None = None

    def rule_for(self, request: ISO8583Message) -> Rule:
        for rule in self.rules:
            if rule.matches(request):
                return rule
        return Rule()

    def build_response(self, request: ISO8583Message, code: str) -> ISO8583Message:
        """Build the response to a request with the given response code."""
        fields = {n: request.fields[n] for n in ECHOED_FIELDS if n in request.fields}
        fields[39] = code
        # subhadipmitra@: An approval code derived from the STAN keeps runs reproducible,
        # which matters more for a test host than looking random.
        if code == "00" and request.mti[1] in "12":
            fields[38] = "A" + request.fields.get(11, "0").zfill(6)[-5:]
        # subhadipmitra@: No network on the response: the network required-field lists
        # describe requests, and a response echoes only some request fields.
        return ISO8583Message(mti=response_mti(request.mti), fields=fields, version=self.version)

    async def start(self, host: str = "127.0.0.1", port: int = 8583) -> asyncio.Server:
        """Start listening. Returns the asyncio server (port 0 picks a free port)."""
        self._server = await asyncio.start_server(self._handle, host, port)
        return self._server

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    @property
    def port(self) -> int:
        """The port the host is listening on."""
        if not self._server or not self._server.sockets:
            raise RuntimeError("Host is not running")
        return int(self._server.sockets[0].getsockname()[1])

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        tasks: set[asyncio.Task[None]] = set()
        try:
            while True:
                try:
                    tpdu, data = await self.framing.read(reader)
                except (EOFError, asyncio.IncompleteReadError, ConnectionError):
                    break
                self.stats.received += 1
                # subhadipmitra@: Each request is answered in its own task, so a rule with a
                # delay (or a dropped request) doesn't hold up other requests on the same
                # connection. That is how real hosts behave and what the client expects.
                task = asyncio.create_task(self._answer(tpdu, data, writer))
                tasks.add(task)
                task.add_done_callback(tasks.discard)
        finally:
            for task in tasks:
                task.cancel()
            writer.close()
            logger.debug("Connection from %s closed", peer)

    async def _answer(self, tpdu: bytes | None, data: bytes, writer: asyncio.StreamWriter) -> None:
        try:
            request = decode_message(data, self.wire_format, version=self.version)
            rule = self.rule_for(request)
            if rule.delay_ms:
                await asyncio.sleep(rule.delay_ms / 1000)
            if rule.action == "drop":
                self.stats.dropped += 1
                return
            if rule.action == "close":
                self.stats.dropped += 1
                writer.close()
                return
            response = self.build_response(request, rule.respond)
            payload = encode_message(response, self.wire_format, self._builder)
            writer.write(self.framing.frame(payload, tpdu=swap_tpdu(tpdu)))
            await writer.drain()
            self.stats.responded += 1
            self.stats.response_codes[rule.respond] += 1
        except (ParseError, ValueError) as e:
            self.stats.errors += 1
            logger.warning("Could not answer request: %s", e)
        except (ConnectionError, OSError):
            pass
