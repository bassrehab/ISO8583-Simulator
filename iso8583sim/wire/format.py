"""Wire formats: how an ISO 8583 message is laid out as bytes on the network."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Encoding(Enum):
    """How characters and digits are represented on the wire."""

    ASCII = "ascii"
    EBCDIC = "ebcdic"
    # subhadipmitra@: Packed BCD stores two decimal digits per byte. Common for MTIs,
    # numeric fields and length prefixes on POS and many card network links.
    BCD = "bcd"
    # subhadipmitra@: Plain unsigned binary. Only meaningful for length prefixes.
    BINARY = "binary"


@dataclass(frozen=True)
class WireFormat:
    """Byte layout of a message. Each part of the message can be encoded independently.

    Attributes:
        mti: MTI encoding: ASCII, EBCDIC or BCD
        bitmap: "binary" for 8 raw bytes per bitmap, or "hex" for 16 hex characters in
            the text encoding
        length_prefix: Encoding of LLVAR / LLLVAR length indicators: ASCII, EBCDIC, BCD or BINARY
        numeric: Encoding of numeric field content: ASCII, EBCDIC or BCD
        text: Encoding of alphanumeric content: ASCII or EBCDIC
        binary_fields: "raw" to send binary fields (PIN block, MAC, EMV) as bytes, or "hex"
            to send them as hex characters in the text encoding
        ebcdic_codec: Python codec used for EBCDIC (cp037 is US/Canada, cp500 international)
        bcd_odd_padding: Filler nibble position for odd-length variable BCD fields
    """

    mti: Encoding = Encoding.ASCII
    bitmap: str = "binary"
    length_prefix: Encoding = Encoding.ASCII
    numeric: Encoding = Encoding.ASCII
    text: Encoding = Encoding.ASCII
    binary_fields: str = "raw"
    ebcdic_codec: str = "cp037"
    # subhadipmitra@: Where the filler nibble goes when a variable BCD field has an odd number
    # of digits: "left" (leading 0, right aligned) or "right" (trailing F, left aligned).
    # Networks differ, so this is configurable.
    bcd_odd_padding: str = "left"

    def __post_init__(self) -> None:
        if self.mti not in (Encoding.ASCII, Encoding.EBCDIC, Encoding.BCD):
            raise ValueError("MTI encoding must be ASCII, EBCDIC or BCD")
        if self.numeric not in (Encoding.ASCII, Encoding.EBCDIC, Encoding.BCD):
            raise ValueError("Numeric encoding must be ASCII, EBCDIC or BCD")
        if self.text not in (Encoding.ASCII, Encoding.EBCDIC):
            raise ValueError("Text encoding must be ASCII or EBCDIC")
        if self.bitmap not in ("binary", "hex"):
            raise ValueError('Bitmap must be "binary" or "hex"')
        if self.binary_fields not in ("raw", "hex"):
            raise ValueError('Binary fields must be "raw" or "hex"')
        if self.bcd_odd_padding not in ("left", "right"):
            raise ValueError('BCD odd padding must be "left" or "right"')

    @classmethod
    def ascii_hex(cls) -> WireFormat:
        """Everything as ASCII text with a hex bitmap: the byte form of this library's string messages."""
        # subhadipmitra@: This is exactly what ISO8583Builder.build() produces, encoded as
        # ASCII, so existing string messages and this format convert losslessly.
        return cls(bitmap="hex", binary_fields="hex")

    @classmethod
    def ascii_binary(cls) -> WireFormat:
        """ASCII text and numbers with a binary bitmap and raw binary fields. A common host format."""
        return cls()

    @classmethod
    def bcd(cls) -> WireFormat:
        """BCD MTI, numbers and lengths, binary bitmap, ASCII text. Typical of POS terminal links."""
        return cls(mti=Encoding.BCD, length_prefix=Encoding.BCD, numeric=Encoding.BCD)

    @classmethod
    def ebcdic(cls) -> WireFormat:
        """EBCDIC text and numbers with a binary bitmap. Used by IBM mainframe hosts."""
        return cls(mti=Encoding.EBCDIC, length_prefix=Encoding.EBCDIC, numeric=Encoding.EBCDIC, text=Encoding.EBCDIC)

    @classmethod
    def preset(cls, name: str) -> WireFormat:
        """Look up a preset by name: ascii-hex, ascii-binary, bcd or ebcdic."""
        presets = {
            "ascii-hex": cls.ascii_hex,
            "ascii-binary": cls.ascii_binary,
            "bcd": cls.bcd,
            "ebcdic": cls.ebcdic,
        }
        try:
            return presets[name.lower()]()
        except KeyError:
            raise ValueError(f"Unknown wire format {name!r}. Use one of: {', '.join(presets)}") from None


# subhadipmitra@: Field definitions describe length handling (fixed, LLVAR, LLLVAR) but not
# what a variable field contains. Binary wire formats need that: a PAN packs as BCD digits,
# EMV data travels as raw bytes, and everything else is text.
NUMERIC_VARIABLE_FIELDS = frozenset({2, 32, 33, 99, 100})
TRACK_FIELDS = frozenset({35, 36})
BINARY_VARIABLE_FIELDS = frozenset({55})
