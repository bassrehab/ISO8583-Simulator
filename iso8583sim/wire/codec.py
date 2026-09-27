"""Encode messages to bytes and decode them back, in any WireFormat."""

from __future__ import annotations

from ..core.builder import ISO8583Builder
from ..core.codes import detect_network_from_pan
from ..core.parser import ISO8583Parser
from ..core.types import (
    BuildError,
    CardNetwork,
    FieldDefinition,
    FieldType,
    ISO8583Message,
    ISO8583Version,
    ParseError,
    get_field_definition,
)
from .format import BINARY_VARIABLE_FIELDS, NUMERIC_VARIABLE_FIELDS, TRACK_FIELDS, Encoding, WireFormat

# Low-level helpers


def _pack_bcd(digits: str, pad: str) -> bytes:
    """Pack decimal digits (and D for track separators) two per byte."""
    # subhadipmitra@: An odd digit count needs one filler nibble. Fixed numeric fields are
    # right aligned with a leading 0. Variable fields follow WireFormat.bcd_odd_padding.
    if len(digits) % 2:
        digits = "0" + digits if pad == "left" else digits + "F"
    return bytes.fromhex(digits)


def _unpack_bcd(data: bytes, count: int, pad: str) -> str:
    nibbles = data.hex().upper()
    if len(nibbles) > count:
        nibbles = nibbles[len(nibbles) - count :] if pad == "left" else nibbles[:count]
    return nibbles


def _text_codec(fmt: WireFormat, encoding: Encoding) -> str:
    return fmt.ebcdic_codec if encoding == Encoding.EBCDIC else "ascii"


def _encode_text(value: str, fmt: WireFormat, encoding: Encoding) -> bytes:
    try:
        return value.encode(_text_codec(fmt, encoding))
    except UnicodeEncodeError as e:
        raise BuildError(f"Value {value!r} can't be encoded as {encoding.value}: {e}") from None


def _decode_text(data: bytes, fmt: WireFormat, encoding: Encoding) -> str:
    try:
        return data.decode(_text_codec(fmt, encoding))
    except UnicodeDecodeError:
        # subhadipmitra@: Bytes that aren't valid in the expected encoding almost always mean
        # the wrong wire format, so report it as a parse error the caller can act on.
        raise ParseError(f"Bytes {data.hex().upper()} are not valid {encoding.value} (wrong wire format?)") from None


def _content_kind(field_number: int, field_def: FieldDefinition) -> str:
    if field_def.field_type == FieldType.NUMERIC:
        return "numeric"
    if field_def.field_type == FieldType.BINARY:
        return "binary"
    if field_def.field_type in (FieldType.LLVAR, FieldType.LLLVAR):
        if field_number in NUMERIC_VARIABLE_FIELDS:
            return "numeric"
        if field_number in TRACK_FIELDS:
            return "track"
        if field_number in BINARY_VARIABLE_FIELDS:
            return "binary"
    return "text"


def _odd_padding(fmt: WireFormat, variable: bool) -> str:
    # subhadipmitra@: Fixed numeric fields are always right aligned with a leading 0 nibble,
    # like their zero-padded text form. Only variable fields follow bcd_odd_padding. The
    # pyiso8583 cross-check caught an earlier version that padded fixed fields with F too.
    return fmt.bcd_odd_padding if variable else "left"


def _is_variable(field_def: FieldDefinition) -> bool:
    return field_def.field_type in (FieldType.LLVAR, FieldType.LLLVAR)


# Encoding


def _encode_content(field_number: int, value: str, kind: str, fmt: WireFormat, variable: bool) -> tuple[bytes, int]:
    """Encode field content. Returns the bytes and the length to put in a length prefix."""
    if kind == "binary":
        if fmt.binary_fields == "raw":
            raw = bytes.fromhex(value)
            return raw, len(raw)
        return _encode_text(value, fmt, fmt.text), len(value)
    if kind in ("numeric", "track") and fmt.numeric == Encoding.BCD:
        # subhadipmitra@: Track data uses "=" as its field separator, which BCD writes as
        # the nibble D. The length prefix counts digits, not bytes.
        digits = value.replace("=", "D") if kind == "track" else value
        return _pack_bcd(digits, _odd_padding(fmt, variable)), len(value)
    encoding = fmt.numeric if kind in ("numeric", "track") else fmt.text
    data = _encode_text(value, fmt, encoding)
    return data, len(data)


def _encode_length(length: int, digits: int, fmt: WireFormat) -> bytes:
    if length >= 10**digits:
        raise BuildError(f"Length {length} does not fit a {digits}-digit length prefix")
    if fmt.length_prefix == Encoding.BINARY:
        # subhadipmitra@: A binary LL prefix is one byte and LLL is two, the same widths the
        # BCD form uses, so either can replace the other on the same link.
        return length.to_bytes(1 if digits == 2 else 2, "big")
    if fmt.length_prefix == Encoding.BCD:
        return _pack_bcd(str(length).zfill(digits), "left")
    return _encode_text(str(length).zfill(digits), fmt, fmt.length_prefix)


def encode_message(
    message: ISO8583Message, fmt: WireFormat | None = None, builder: ISO8583Builder | None = None
) -> bytes:
    """Encode a message as bytes in the given wire format.

    The message is validated and normalized exactly as ISO8583Builder.build() does, so
    encoding with WireFormat.ascii_hex() gives the same characters as build().

    Args:
        message: Message to encode
        fmt: Wire format (defaults to ascii_binary)
        builder: Builder to use for validation (defaults to one for the message's version)

    Returns:
        The encoded message
    """
    fmt = fmt or WireFormat.ascii_binary()
    builder = builder or ISO8583Builder(version=message.version)
    # subhadipmitra@: Building first reuses every existing rule: validation, network required
    # fields, padding of fixed fields, and the bitmap. The wire layer only re-encodes.
    text = builder.build(message)
    bitmap_hex = text[4 : 4 + (32 if int(text[4], 16) & 0x8 else 16)]

    out = bytearray()
    if fmt.mti == Encoding.BCD:
        out += _pack_bcd(message.mti, "left")
    else:
        out += _encode_text(message.mti, fmt, fmt.mti)
    out += bytes.fromhex(bitmap_hex) if fmt.bitmap == "binary" else _encode_text(bitmap_hex, fmt, fmt.text)

    for number in sorted(n for n in message.fields if n != 0):
        field_def = get_field_definition(number, message.network, message.version)
        if field_def is None:  # pragma: no cover - build() already rejected unknown fields
            raise BuildError(f"Unknown field definition: {number}")
        kind = _content_kind(number, field_def)
        if _is_variable(field_def):
            value = builder._format_field_value(number, message.fields[number], field_def)
            content, length = _encode_content(number, value, kind, fmt, variable=True)
            out += _encode_length(length, 2 if field_def.field_type == FieldType.LLVAR else 3, fmt)
            out += content
        else:
            padded = builder._build_field(number, message.fields[number], field_def)
            out += _encode_content(number, padded, kind, fmt, variable=False)[0]
    return bytes(out)


# Decoding


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, count: int, what: str) -> bytes:
        if self.pos + count > len(self.data):
            raise ParseError(f"Message too short for {what}: need {count} bytes at offset {self.pos}")
        chunk = self.data[self.pos : self.pos + count]
        self.pos += count
        return chunk


def _decode_length(reader: _Reader, digits: int, fmt: WireFormat, number: int) -> int:
    what = f"field {number} length"
    if fmt.length_prefix == Encoding.BINARY:
        return int.from_bytes(reader.take(1 if digits == 2 else 2, what), "big")
    if fmt.length_prefix == Encoding.BCD:
        text = _unpack_bcd(reader.take(1 if digits == 2 else 2, what), digits, "left")
    else:
        text = _decode_text(reader.take(digits, what), fmt, fmt.length_prefix)
    if not text.isdigit():
        raise ParseError(f"Invalid length prefix for field {number}: {text!r}")
    return int(text)


def _decode_content(reader: _Reader, number: int, kind: str, count: int, fmt: WireFormat, variable: bool) -> str:
    """Read `count` units of field content (digits for BCD, bytes or characters otherwise)."""
    what = f"field {number}"
    if kind == "binary":
        if fmt.binary_fields == "raw":
            return reader.take(count, what).hex().upper()
        return _decode_text(reader.take(count, what), fmt, fmt.text).upper()
    if kind in ("numeric", "track") and fmt.numeric == Encoding.BCD:
        value = _unpack_bcd(reader.take((count + 1) // 2, what), count, _odd_padding(fmt, variable))
        return value.replace("D", "=") if kind == "track" else value
    encoding = fmt.numeric if kind in ("numeric", "track") else fmt.text
    return _decode_text(reader.take(count, what), fmt, encoding)


class _Padding:
    """Adapter over the string parser's padding rule for fixed-length fields."""

    def __init__(self) -> None:
        self._parser = ISO8583Parser()

    def handle(self, number: int, value: str, field_def: FieldDefinition) -> str:
        return self._parser._handle_field_padding(number, value, field_def)


def decode_message(
    data: bytes,
    fmt: WireFormat | None = None,
    version: ISO8583Version = ISO8583Version.V1987,
    network: CardNetwork | None = None,
) -> ISO8583Message:
    """Decode bytes in the given wire format into a message.

    Field values come back in this library's usual string form (binary fields as uppercase
    hex, numbers as digit strings), so the result works with the validator, explainer,
    converter and everything else.

    Args:
        data: Encoded message
        fmt: Wire format (defaults to ascii_binary)
        version: ISO 8583 version
        network: Card network. Detected from the PAN when omitted.

    Returns:
        The decoded message
    """
    fmt = fmt or WireFormat.ascii_binary()
    reader = _Reader(data)

    if fmt.mti == Encoding.BCD:
        mti = _unpack_bcd(reader.take(2, "MTI"), 4, "left")
    else:
        mti = _decode_text(reader.take(4, "MTI"), fmt, fmt.mti)
    if not mti.isdigit():
        raise ParseError(f"Invalid MTI {mti!r} (wrong wire format?)")

    if fmt.bitmap == "binary":
        bitmap = reader.take(8, "bitmap")
        if bitmap[0] & 0x80:
            bitmap += reader.take(8, "secondary bitmap")
        bitmap_hex = bitmap.hex().upper()
    else:
        bitmap_hex = _decode_text(reader.take(16, "bitmap"), fmt, fmt.text).upper()
        if int(bitmap_hex[0], 16) & 0x8:
            bitmap_hex += _decode_text(reader.take(16, "secondary bitmap"), fmt, fmt.text).upper()
    try:
        bits = int(bitmap_hex, 16)
    except ValueError:
        raise ParseError(f"Invalid bitmap {bitmap_hex!r}") from None
    width = len(bitmap_hex) * 4
    present = [i + 1 for i in range(width) if bits >> (width - 1 - i) & 1 and i != 0]

    detected = network
    padding = _Padding()
    fields: dict[int, str] = {0: mti}
    for number in present:
        field_def = get_field_definition(number, detected, version)
        if field_def is None:
            raise ParseError(f"Field {number} is present in the bitmap but not defined")
        kind = _content_kind(number, field_def)
        if _is_variable(field_def):
            length = _decode_length(reader, 2 if field_def.field_type == FieldType.LLVAR else 3, fmt, number)
            if length > field_def.max_length:
                raise ParseError(f"Field {number} length {length} exceeds maximum {field_def.max_length}")
            fields[number] = _decode_content(reader, number, kind, length, fmt, variable=True)
        else:
            count = field_def.max_length
            if kind == "binary" and fmt.binary_fields == "hex":
                count *= 2  # hex characters
            # subhadipmitra@: Strip fixed-field padding with the string parser's own rule, so
            # decoded values are identical to what ISO8583Parser returns for the same message.
            value = _decode_content(reader, number, kind, count, fmt, variable=False)
            fields[number] = padding.handle(number, value, field_def)
        # subhadipmitra@: Detect the network as soon as the PAN is known, because later fields
        # may use network-specific definitions. This mirrors the string parser.
        if number == 2 and detected is None:
            detected = detect_network_from_pan(fields[2])

    if reader.pos != len(data):
        raise ParseError(f"{len(data) - reader.pos} unexpected bytes after the last field (wrong wire format?)")
    return ISO8583Message(mti=mti, fields=fields, version=version, network=detected, bitmap=bitmap_hex)
