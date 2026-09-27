"""Byte-level wire formats for sending ISO 8583 messages over a network.

The rest of the library works with messages as strings (ASCII MTI, hex bitmap, binary
fields as hex). This package converts those messages to and from the byte layouts real
hosts use: binary bitmaps, packed BCD, EBCDIC and raw binary fields.
"""

from .codec import decode_message, encode_message
from .format import Encoding, WireFormat

__all__ = ["Encoding", "WireFormat", "encode_message", "decode_message"]
