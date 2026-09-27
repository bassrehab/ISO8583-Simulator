# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""ISO 9564-1 PIN blocks (formats 0, 1, 3 and 4).

For testing and simulation only. Real PIN handling happens inside an HSM, and clear PINs
and keys must never pass through application code like this.
"""

from __future__ import annotations

import secrets

from ._cipher import SecurityError, aes, parse_key, tdes, xor

SUPPORTED_FORMATS = (0, 1, 3, 4)


def _check_pin(pin: str) -> None:
    # subhadipmitra@: ISO 9564 allows 4 to 12 PIN digits. The length is stored in one hex
    # nibble, so the limit is also what the block can represent.
    if not pin.isdigit() or not 4 <= len(pin) <= 12:
        raise SecurityError("PIN must be 4 to 12 digits")


def _check_pan(pan: str) -> None:
    if not pan.isdigit() or len(pan) < 13:
        raise SecurityError("PAN must be at least 13 digits")


def _random_nibbles(count: int, alphabet: str) -> str:
    return "".join(secrets.choice(alphabet) for _ in range(count))


def _pan_field_8(pan: str) -> bytes:
    """PAN field for formats 0 and 3: four zeros, then the 12 rightmost PAN digits excluding the check digit."""
    _check_pan(pan)
    return bytes.fromhex("0000" + pan[:-1][-12:])


def _pin_field_8(pin: str, fmt: int) -> bytes:
    _check_pin(pin)
    head = f"{fmt}{len(pin):X}{pin}"
    # subhadipmitra@: Each format fills the unused nibbles differently. Format 0 uses F.
    # Format 3 uses random A to F, and format 1 random 0 to F, so repeated PINs don't
    # produce repeated blocks.
    fill = 16 - len(head)
    if fmt == 0:
        return bytes.fromhex(head + "F" * fill)
    if fmt == 1:
        return bytes.fromhex(head + _random_nibbles(fill, "0123456789ABCDEF"))
    return bytes.fromhex(head + _random_nibbles(fill, "ABCDEF"))


def _pin_field_16(pin: str) -> bytes:
    """Format 4 plain text PIN field: 4, length, PIN, A fill to 16 nibbles, then 16 random nibbles."""
    _check_pin(pin)
    head = f"4{len(pin):X}{pin}"
    return bytes.fromhex(head + "A" * (16 - len(head)) + _random_nibbles(16, "0123456789ABCDEF"))


def _pan_field_16(pan: str) -> bytes:
    """Format 4 plain text PAN field: PAN length minus 12, the PAN left aligned, 0 fill to 32 nibbles."""
    if not pan.isdigit() or not 1 <= len(pan) <= 19:
        raise SecurityError("PAN must be 1 to 19 digits")
    # subhadipmitra@: The first nibble says how many digits the PAN has beyond 12 (0 for 12
    # or fewer). Shorter PANs are left-padded with zeros to 12 digits.
    extra = max(len(pan) - 12, 0)
    return bytes.fromhex(f"{extra:X}{pan.rjust(12, '0')}".ljust(32, "0"))


def encode_pin_block(pin: str, pan: str | None = None, fmt: int = 0) -> bytes:
    """Build a clear (unencrypted) 8-byte PIN block in format 0, 1 or 3.

    Args:
        pin: 4 to 12 digit PIN
        pan: Primary Account Number (required for formats 0 and 3)
        fmt: PIN block format: 0, 1 or 3

    Returns:
        The 8-byte clear PIN block
    """
    if fmt == 1:
        return _pin_field_8(pin, 1)
    if fmt in (0, 3):
        if pan is None:
            raise SecurityError(f"Format {fmt} needs the PAN")
        return xor(_pin_field_8(pin, fmt), _pan_field_8(pan))
    raise SecurityError("Clear PIN blocks are defined for formats 0, 1 and 3. Format 4 is always AES encrypted.")


def decode_pin_block(block: bytes, pan: str | None = None, fmt: int = 0) -> str:
    """Recover the PIN from a clear 8-byte PIN block in format 0, 1 or 3."""
    if len(block) != 8:
        raise SecurityError("A format 0, 1 or 3 PIN block is 8 bytes")
    if fmt in (0, 3):
        if pan is None:
            raise SecurityError(f"Format {fmt} needs the PAN")
        block = xor(block, _pan_field_8(pan))
    elif fmt != 1:
        raise SecurityError("Clear PIN blocks are defined for formats 0, 1 and 3")

    digits = block.hex().upper()
    if digits[0] != str(fmt):
        raise SecurityError(f"Not a format {fmt} PIN block (control nibble is {digits[0]})")
    length = int(digits[1], 16)
    pin = digits[2 : 2 + length]
    # subhadipmitra@: A wrong key or PAN still XORs to "something", so check the result is
    # a plausible PIN instead of returning garbage.
    if not 4 <= length <= 12 or not pin.isdigit():
        raise SecurityError("PIN block does not decode to a valid PIN (wrong key, PAN or format?)")
    if fmt == 0 and set(digits[2 + length :]) != {"F"}:
        raise SecurityError("Format 0 PIN block has invalid fill (wrong key, PAN or format?)")
    # subhadipmitra@: Format 3 fill is random but always A to F. Checking it rejects almost all
    # blocks decrypted with the wrong key or PAN, which would otherwise sometimes pass.
    if fmt == 3 and not set(digits[2 + length :]) <= set("ABCDEF"):
        raise SecurityError("Format 3 PIN block has invalid fill (wrong key, PAN or format?)")
    return pin


def encrypt_pin_block(pin: str, pan: str | None, key: str | bytes, fmt: int = 0) -> str:
    """Build an encrypted PIN block as it appears in field 52.

    Formats 0, 1 and 3 use a double or triple length TDES key and give 8 bytes. Format 4
    uses an AES key and gives 16 bytes, which fits field 52 in the 1993 and 2003 versions.

    Args:
        pin: 4 to 12 digit PIN
        pan: Primary Account Number (not used by format 1)
        key: PIN encryption key as bytes or hex
        fmt: PIN block format: 0, 1, 3 or 4

    Returns:
        The encrypted PIN block as uppercase hex
    """
    if fmt == 4:
        if pan is None:
            raise SecurityError("Format 4 needs the PAN")
        k = parse_key(key, (16, 24, 32))
        # subhadipmitra@: Format 4 encrypts twice: the PIN field, then that result XORed with
        # the PAN field. This binds the PIN to the card without leaking PAN structure.
        return aes(k, xor(aes(k, _pin_field_16(pin)), _pan_field_16(pan))).hex().upper()
    k = parse_key(key, (16, 24))
    return tdes(k, encode_pin_block(pin, pan, fmt)).hex().upper()


def decrypt_pin_block(block: str | bytes, pan: str | None, key: str | bytes, fmt: int = 0) -> str:
    """Recover the PIN from an encrypted PIN block (formats 0, 1, 3 and 4).

    A wrong key is detected in every format, because it scrambles the whole block. A wrong
    PAN is always detected in format 4, but only sometimes in formats 0 and 3: there the PAN
    is applied with a single XOR, so a different PAN can still decode to a well-formed block
    with a different PIN. This is a property of those formats, not of this implementation.

    Raises:
        SecurityError: The block doesn't decode to a valid PIN block
    """
    data = bytes.fromhex(block) if isinstance(block, str) else block
    if fmt == 4:
        if pan is None:
            raise SecurityError("Format 4 needs the PAN")
        if len(data) != 16:
            raise SecurityError("A format 4 PIN block is 16 bytes")
        k = parse_key(key, (16, 24, 32))
        pin_field = aes(k, xor(aes(k, data, decrypt=True), _pan_field_16(pan)), decrypt=True).hex().upper()
        length = int(pin_field[1], 16)
        pin = pin_field[2 : 2 + length]
        # subhadipmitra@: Check the A fill too. With a wrong key or PAN the result is random,
        # and the control nibble, length and digits alone let about 1 in 1,000 through,
        # returning a wrong PIN instead of an error. The fill check makes that negligible.
        fill = pin_field[2 + length : 16]
        if pin_field[0] != "4" or not 4 <= length <= 12 or not pin.isdigit() or set(fill) != {"A"}:
            raise SecurityError("PIN block does not decode to a valid PIN (wrong key, PAN or format?)")
        return pin
    k = parse_key(key, (16, 24))
    return decode_pin_block(tdes(k, data, decrypt=True), pan, fmt)
