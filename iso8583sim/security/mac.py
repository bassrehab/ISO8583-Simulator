# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""ISO 9797-1 message authentication codes for ISO 8583 fields 64 and 128.

For testing and simulation only. Production MACs are generated inside an HSM.
"""

from __future__ import annotations

import hmac
from typing import TYPE_CHECKING

from ._cipher import SecurityError, parse_key, tdes, xor

if TYPE_CHECKING:
    from ..core.builder import ISO8583Builder
    from ..core.types import ISO8583Message, ISO8583Version

ALGORITHMS = (1, 3)
PADDINGS = (1, 2)


def _pad(data: bytes, method: int) -> bytes:
    # subhadipmitra@: Method 1 appends zeros only when needed, so data that is already a
    # multiple of 8 bytes is left alone. Empty data still gets one block of zeros, because
    # the MAC needs at least one block. Method 2 always appends 0x80 first, which makes
    # the padding unambiguous.
    if method == 1:
        remainder = len(data) % 8
        return data + b"\x00" * ((8 - remainder) % 8 if data else 8)
    if method == 2:
        data += b"\x80"
        return data + b"\x00" * ((8 - len(data) % 8) % 8)
    raise SecurityError("Padding method must be 1 or 2")


def generate_mac(data: str | bytes, key: str | bytes, algorithm: int = 3, padding: int = 1, length: int = 8) -> str:
    """Generate an ISO 9797-1 MAC with DES based block ciphers.

    Algorithm 1 is a CBC-MAC with the whole key (single, double or triple length).
    Algorithm 3 is the retail MAC (ANSI X9.19): single DES CBC with the left key half,
    then decrypt with the right half and encrypt with the left half on the final block.

    Args:
        data: Data to authenticate. A str is encoded as ASCII, which is how this
            simulator carries ISO 8583 messages.
        key: MAC key as bytes or hex (8, 16 or 24 bytes for algorithm 1; 16 for algorithm 3)
        algorithm: ISO 9797-1 MAC algorithm: 1 or 3
        padding: ISO 9797-1 padding method: 1 or 2
        length: MAC length in bytes, 4 to 8. Truncation keeps the leftmost bytes.

    Returns:
        The MAC as uppercase hex
    """
    raw = data.encode("ascii") if isinstance(data, str) else data
    if not 4 <= length <= 8:
        raise SecurityError("MAC length must be 4 to 8 bytes")
    blocks = _pad(raw, padding)

    if algorithm == 1:
        k = parse_key(key, (8, 16, 24))
        chain_key = k
    elif algorithm == 3:
        k = parse_key(key, (16,))
        # subhadipmitra@: The retail MAC chains with cheap single DES under K1 and only
        # strengthens the last block with K2. That was the X9.19 trade-off for hardware
        # of the time, and it is still what most networks expect.
        chain_key = k[:8]
    else:
        raise SecurityError("MAC algorithm must be 1 or 3")

    state = bytes(8)
    for i in range(0, len(blocks), 8):
        state = tdes(chain_key, xor(state, blocks[i : i + 8]))

    if algorithm == 3:
        state = tdes(k[:8], tdes(k[8:], state, decrypt=True))
    return state[:length].hex().upper()


def verify_mac(data: str | bytes, mac: str, key: str | bytes, algorithm: int = 3, padding: int = 1) -> bool:
    """Check a MAC. The expected length is taken from the given MAC."""
    if len(mac) % 2 or not 8 <= len(mac) <= 16:
        raise SecurityError("MAC must be 4 to 8 bytes of hex")
    expected = generate_mac(data, key, algorithm, padding, length=len(mac) // 2)
    # subhadipmitra@: Constant-time comparison, so timing can't reveal how many leading
    # characters of a forged MAC were right.
    return hmac.compare_digest(expected, mac.upper())


def mac_field(fields: dict[int, str]) -> int:
    """Return which field carries the MAC: 128 when the message has a secondary bitmap, else 64."""
    # subhadipmitra@: The MAC is always the last field of the message. With a secondary
    # bitmap that is field 128, and field 64 must then be absent.
    return 128 if any(65 <= n <= 128 for n in fields if n not in (64, 128)) else 64


def sign_message(
    message: ISO8583Message,
    key: str | bytes,
    builder: ISO8583Builder | None = None,
    algorithm: int = 3,
    padding: int = 1,
) -> str:
    """Build a message with its MAC in field 64 (or 128 with a secondary bitmap).

    Args:
        message: Message to build. Any existing MAC field is replaced.
        key: MAC key as bytes or hex
        builder: Builder to use (defaults to one for the message's version)
        algorithm: ISO 9797-1 MAC algorithm: 1 or 3
        padding: ISO 9797-1 padding method: 1 or 2

    Returns:
        The raw message with the MAC filled in
    """
    from ..core.builder import ISO8583Builder

    builder = builder or ISO8583Builder(version=message.version)
    field = mac_field(message.fields)
    message.fields.pop(64 if field == 128 else 128, None)
    # subhadipmitra@: Build once with a zero placeholder so the bitmap already has the MAC
    # bit set. The MAC covers everything before the MAC field, and the bitmap is part of
    # that, so it must be final before the MAC is computed.
    message.fields[field] = "0" * 16
    raw = builder.build(message)
    mac = generate_mac(raw[:-16], key, algorithm, padding)
    message.fields[field] = mac
    return raw[:-16] + mac


def verify_message(
    raw: str, key: str | bytes, algorithm: int = 3, padding: int = 1, version: ISO8583Version | None = None
) -> bool:
    """Check the MAC in field 64 or 128 of a raw message built by this simulator."""
    from ..core.parser import ISO8583Parser
    from ..core.types import ISO8583Version

    parsed = ISO8583Parser(version=version or ISO8583Version.V1987).parse(raw)
    field = 128 if 128 in parsed.fields else 64 if 64 in parsed.fields else None
    if field is None:
        raise SecurityError("Message has no MAC field (64 or 128)")
    # subhadipmitra@: The MAC field is the last field and is fixed at 16 hex characters, so
    # the authenticated data is the raw message minus its last 16 characters.
    return verify_mac(raw[:-16], parsed.fields[field], key, algorithm, padding)
