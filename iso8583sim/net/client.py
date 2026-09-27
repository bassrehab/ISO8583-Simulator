# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Asyncio TCP client that sends ISO 8583 requests and waits for their responses."""

from __future__ import annotations

import asyncio
import logging
import ssl as ssl_module
from types import TracebackType

from ..core.builder import ISO8583Builder
from ..core.types import ISO8583Message, ISO8583Version, ParseError
from ..wire import WireFormat, decode_message, encode_message
from .framing import Framing

logger = logging.getLogger(__name__)


class ISO8583Client:
    """Send requests to an ISO 8583 host over TCP.

    Responses are matched to requests by STAN (field 11), so several requests can be in
    flight on one connection at once.

    Example:
        >>> async with ISO8583Client("127.0.0.1", 8583) as client:
        ...     response = await client.send(sample_message())
        ...     print(response.fields[39])
    """

    def __init__(
        self,
        host: str,
        port: int,
        wire_format: WireFormat | None = None,
        framing: Framing | None = None,
        timeout: float = 10.0,
        ssl: ssl_module.SSLContext | bool | None = None,
        version: ISO8583Version = ISO8583Version.V1987,
    ):
        """
        Args:
            host: Host name or address
            port: TCP port
            wire_format: Byte layout of messages (defaults to ASCII with a binary bitmap)
            framing: Length header and optional TPDU (defaults to a 2-byte binary header)
            timeout: Seconds to wait for a response
            ssl: True or an SSLContext to connect over TLS
            version: ISO 8583 version used to decode responses
        """
        self.host = host
        self.port = port
        self.wire_format = wire_format or WireFormat.ascii_binary()
        self.framing = framing or Framing()
        self.timeout = timeout
        self.ssl = ssl
        self.version = version
        self._builder = ISO8583Builder(version=version)
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._receiver: asyncio.Task[None] | None = None
        self._pending: dict[str, asyncio.Future[ISO8583Message]] = {}
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def connect(self) -> None:
        """Open the connection. send() also connects on demand."""
        if self.connected:
            return
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port, ssl=self.ssl), self.timeout
            )
        except asyncio.TimeoutError:
            # subhadipmitra@: On Python 3.10 asyncio.TimeoutError is a different class from the
            # built-in TimeoutError (they merged in 3.11), so convert it to keep the documented
            # contract. The built-in is also an OSError, which callers already handle.
            raise TimeoutError(f"Could not connect to {self.host}:{self.port} within {self.timeout}s") from None
        self._receiver = asyncio.create_task(self._receive())

    async def close(self) -> None:
        """Close the connection. Requests still waiting fail with ConnectionError."""
        if self._receiver:
            self._receiver.cancel()
            self._receiver = None
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except (ConnectionError, OSError):
                pass
            self._writer = None
        self._fail_pending(ConnectionError("Connection closed"))

    async def __aenter__(self) -> ISO8583Client:
        await self.connect()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        await self.close()

    async def send(self, message: ISO8583Message, timeout: float | None = None) -> ISO8583Message:
        """Send a request and return the matching response.

        Args:
            message: Request message. It must have a STAN (field 11).
            timeout: Seconds to wait for the response (defaults to the client timeout)

        Returns:
            The decoded response

        Raises:
            TimeoutError: No response arrived in time
            ConnectionError: The connection closed before the response arrived
        """
        stan = message.fields.get(11)
        if not stan:
            # subhadipmitra@: Without a STAN there is nothing to match the response on, and
            # with several requests in flight the wrong response could be returned.
            raise ValueError("The request needs a STAN (field 11) to match its response")
        stan = stan.zfill(6)

        # subhadipmitra@: The lock covers connect and the pending-table check, so two
        # concurrent sends can neither open two connections nor claim the same STAN.
        async with self._lock:
            if not self.connected:
                await self.connect()
            if stan in self._pending:
                raise ValueError(f"A request with STAN {stan} is already waiting for a response")
            future: asyncio.Future[ISO8583Message] = asyncio.get_running_loop().create_future()
            self._pending[stan] = future
            assert self._writer is not None
            self._writer.write(self.framing.frame(encode_message(message, self.wire_format, self._builder)))
        try:
            assert self._writer is not None
            await self._writer.drain()
            return await asyncio.wait_for(future, timeout or self.timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"No response to STAN {stan} within {timeout or self.timeout}s") from None
        finally:
            self._pending.pop(stan, None)

    async def _receive(self) -> None:
        """Background task: read responses and hand each to the request waiting for it."""
        assert self._reader is not None
        try:
            while True:
                _, data = await self.framing.read(self._reader)
                try:
                    response = decode_message(data, self.wire_format, version=self.version)
                except ParseError as e:
                    logger.warning("Dropping undecodable message from %s:%s: %s", self.host, self.port, e)
                    continue
                future = self._pending.get(response.fields.get(11, "").zfill(6))
                if future and not future.done():
                    future.set_result(response)
                else:
                    # subhadipmitra@: Late responses (after a timeout) and unsolicited messages
                    # are logged, not raised, so one stray message can't break the connection.
                    logger.warning("Unmatched message %s (STAN %s)", response.mti, response.fields.get(11))
        except (EOFError, asyncio.IncompleteReadError, ConnectionError, OSError, ParseError) as e:
            # subhadipmitra@: A frame that can't be read (a bad or oversized length header) ends the
            # connection like a close does, so waiting requests fail now instead of timing out.
            self._fail_pending(ConnectionError(f"Connection to {self.host}:{self.port} closed: {e}"))
            if self._writer:
                self._writer.close()
                self._writer = None

    def _fail_pending(self, error: Exception) -> None:
        for future in self._pending.values():
            if not future.done():
                future.set_exception(error)
