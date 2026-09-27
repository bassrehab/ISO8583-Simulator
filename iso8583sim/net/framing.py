# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Message framing for TCP: length headers and TPDUs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ..core.types import ParseError

HEADERS = ("2b", "4b", "2a", "4a")


@dataclass(frozen=True)
class Framing:
    """How messages are delimited on a TCP stream.

    Attributes:
        header: Length header: "2b" / "4b" (2 or 4 byte big-endian binary) or "2a" / "4a"
            (2 or 4 ASCII digits). The length covers everything after the header.
        tpdu: Optional TPDU sent after the length header, e.g. bytes.fromhex("6000010000").
            On responses the destination and source addresses are swapped.
        header_includes_self: Some hosts count the header bytes in the length. Off by default.
        max_message: The longest frame body accepted when reading, in bytes. A longer one
            raises ParseError before anything is read, so a peer can't make the reader buffer
            what a 4-byte header can declare (up to 4 GiB). 1 MiB by default.
    """

    header: str = "2b"
    tpdu: bytes | None = None
    header_includes_self: bool = False
    max_message: int = 1_048_576

    def __post_init__(self) -> None:
        if self.header not in HEADERS:
            raise ValueError(f"Length header must be one of: {', '.join(HEADERS)}")
        if self.tpdu is not None and len(self.tpdu) != 5:
            raise ValueError("A TPDU is 5 bytes: ID (1), destination (2), source (2)")
        if self.max_message < 1:
            raise ValueError("max_message must be at least 1 byte")

    @property
    def header_size(self) -> int:
        return int(self.header[0])

    def _max_length(self) -> int:
        if self.header.endswith("b"):
            return 256**self.header_size - 1
        return 10**self.header_size - 1

    def frame(self, message: bytes, tpdu: bytes | None = None) -> bytes:
        """Add the TPDU (if configured) and the length header to an encoded message."""
        body = (tpdu or self.tpdu or b"") + message
        length = len(body) + (self.header_size if self.header_includes_self else 0)
        if length > self._max_length():
            raise ValueError(f"Message of {length} bytes is too long for a {self.header} header")
        if self.header.endswith("b"):
            prefix = length.to_bytes(self.header_size, "big")
        else:
            prefix = str(length).zfill(self.header_size).encode("ascii")
        return prefix + body

    def _body_length(self, prefix: bytes) -> int:
        if self.header.endswith("b"):
            length = int.from_bytes(prefix, "big")
        else:
            text = prefix.decode("ascii", errors="replace")
            if not text.isdigit():
                raise ParseError(f"Invalid ASCII length header {text!r}")
            length = int(text)
        if self.header_includes_self:
            length -= self.header_size
        if length < 0:
            raise ParseError("Length header is smaller than the header itself")
        if length > self.max_message:
            raise ParseError(f"Frame of {length} bytes is over the {self.max_message}-byte limit")
        return length

    def _split_tpdu(self, body: bytes) -> tuple[bytes | None, bytes]:
        if self.tpdu is None:
            return None, body
        if len(body) < 5:
            raise ParseError("Frame is too short for its TPDU")
        return body[:5], body[5:]

    async def read(self, reader: asyncio.StreamReader) -> tuple[bytes | None, bytes]:
        """Read one framed message. Returns (tpdu, message).

        Raises asyncio.IncompleteReadError if the connection closes mid-frame, and EOFError
        when it closes cleanly between frames.
        """
        try:
            prefix = await reader.readexactly(self.header_size)
        except asyncio.IncompleteReadError as e:
            if not e.partial:
                raise EOFError("Connection closed") from None
            raise
        body = await reader.readexactly(self._body_length(prefix))
        return self._split_tpdu(body)

    def split(self, buffer: bytes) -> tuple[list[tuple[bytes | None, bytes]], bytes]:
        """Split a byte buffer into complete frames. Returns (frames, leftover bytes)."""
        # subhadipmitra@: For non-asyncio callers and tests: TCP can deliver several frames in
        # one read, or part of one, so keep whatever doesn't form a full frame yet.
        frames = []
        pos = 0
        while len(buffer) - pos >= self.header_size:
            length = self._body_length(buffer[pos : pos + self.header_size])
            end = pos + self.header_size + length
            if end > len(buffer):
                break
            frames.append(self._split_tpdu(buffer[pos + self.header_size : end]))
            pos = end
        return frames, buffer[pos:]


def swap_tpdu(tpdu: bytes | None) -> bytes | None:
    """Swap a TPDU's destination and source addresses, as a response does."""
    if tpdu is None:
        return None
    return tpdu[:1] + tpdu[3:5] + tpdu[1:3]
