# Wire Formats

The rest of iso8583sim works with messages as strings: an ASCII MTI, a hex bitmap, and binary fields as hex. Real hosts exchange bytes, often with a binary bitmap, packed BCD numbers or EBCDIC text. `iso8583sim.wire` converts between the two.

```python
from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.samples import sample_message
from iso8583sim.wire import WireFormat

data = ISO8583Builder().build_bytes(sample_message(), WireFormat.bcd())   # bytes, 63 long
message = ISO8583Parser().parse_bytes(data, WireFormat.bcd())             # ISO8583Message
```

Decoded messages have the same field values the string parser gives, so validation, explain, conversion and the rest work on them unchanged.

The same functions are available directly as `iso8583sim.wire.encode_message` and `decode_message`.

## Presets

| Preset | MTI | Bitmap | Lengths | Numbers | Text | Binary fields | Typical use |
|--------|-----|--------|---------|---------|------|---------------|-------------|
| `WireFormat.ascii_hex()` | ASCII | hex text | ASCII | ASCII | ASCII | hex text | Exactly `build()` output as bytes |
| `WireFormat.ascii_binary()` (default) | ASCII | binary | ASCII | ASCII | ASCII | raw | Many host links |
| `WireFormat.bcd()` | BCD | binary | BCD | BCD | ASCII | raw | POS terminal links |
| `WireFormat.ebcdic()` | EBCDIC | binary | EBCDIC | EBCDIC | EBCDIC | raw | IBM mainframe hosts |

`WireFormat.preset("bcd")` looks a preset up by name.

## Custom formats

Every part is configurable:

```python
from iso8583sim.wire import Encoding, WireFormat

fmt = WireFormat(
    mti=Encoding.BCD,
    bitmap="binary",               # or "hex"
    length_prefix=Encoding.BINARY, # ASCII, EBCDIC, BCD or BINARY
    numeric=Encoding.BCD,          # ASCII, EBCDIC or BCD
    text=Encoding.ASCII,           # ASCII or EBCDIC
    binary_fields="raw",           # or "hex"
    ebcdic_codec="cp037",          # cp037 (US/Canada) or cp500 (international)
    bcd_odd_padding="right",       # odd-length variable BCD: "left" (leading 0) or "right" (trailing F)
)
```

Rules worth knowing:

- **BCD packs two digits per byte.** An LLVAR BCD length is one byte, an LLLVAR length two bytes. The length counts digits, not bytes.
- **Odd digit counts** need a filler nibble. Fixed numeric fields always get a leading `0`. For variable fields, networks differ, so `bcd_odd_padding` chooses a leading `0` or a trailing `F`.
- **Track 2** (field 35) uses `=` as a separator, which BCD writes as the nibble `D`.
- **Content types.** Fields 2, 32, 33, 99 and 100 are numeric, fields 35 and 36 are track data, and field 55 (EMV) is binary. Other variable fields are text.

## Accuracy

The encodings are tested against the independent [pyiso8583](https://github.com/knovichikhin/pyiso8583) library configured the same way, and every preset round-trips every field type.

Length headers and TPDUs for sending over TCP are covered separately.
