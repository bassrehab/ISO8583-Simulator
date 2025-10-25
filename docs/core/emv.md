# EMV Data

The EMV module handles Field 55 (ICC Data) which contains chip card data in TLV (Tag-Length-Value) format.

## Quick Start

```python
from iso8583sim.core.emv import parse_emv_data, build_emv_data

# Parse EMV data
emv_hex = "9F2608..."  # Raw TLV data
tags = parse_emv_data(emv_hex)

print(tags.get("9F26"))  # Application Cryptogram
print(tags.get("9F27"))  # Cryptogram Information Data

# Build EMV data
tags = {
    "9F26": "1234567890ABCDEF",
    "9F27": "80",
    "9F10": "0110A00003220000",
}
emv_hex = build_emv_data(tags)
```

## TLV Format

EMV data uses Tag-Length-Value encoding:

```
┌───────────────┬───────────────┬────────────────────────┐
│     Tag       │    Length     │         Value          │
│   (1-3 bytes) │   (1-3 bytes) │    (Length bytes)      │
└───────────────┴───────────────┴────────────────────────┘
```

### Tag Format

- **1-byte tags**: First byte doesn't have bits 1-5 set to 11111
- **2-byte tags**: First byte ends with 11111 (1F, 5F, 9F, DF)
- **3-byte tags**: Second byte has high bit set

Examples:
- `82` - Single byte (Application Interchange Profile)
- `9F26` - Two bytes (Application Cryptogram)
- `DF8101` - Three bytes (if encountered)

### Length Format

- **1-byte length**: 0x00-0x7F (0-127 bytes)
- **2-byte length**: 0x81 + 1 byte (128-255 bytes)
- **3-byte length**: 0x82 + 2 bytes (256-65535 bytes)

## Common EMV Tags

| Tag | Name | Description |
|-----|------|-------------|
| 9F26 | Application Cryptogram | Transaction cryptogram from chip |
| 9F27 | Cryptogram Information Data | Type of cryptogram |
| 9F10 | Issuer Application Data | Issuer-specific data |
| 9F37 | Unpredictable Number | Random number for cryptogram |
| 9F36 | Application Transaction Counter | Incremental counter |
| 82 | Application Interchange Profile | Supported functions |
| 84 | Dedicated File Name | Application identifier |
| 9F33 | Terminal Capabilities | Terminal features |
| 9F34 | CVM Results | Cardholder verification results |
| 9F35 | Terminal Type | Terminal category |
| 9F1A | Terminal Country Code | Country where terminal is |
| 5F2A | Transaction Currency Code | Currency of transaction |
| 9A | Transaction Date | YYMMDD |
| 9C | Transaction Type | 00=purchase, 01=cash, etc. |
| 9F02 | Amount Authorized | Transaction amount |

## Cryptogram Types (Tag 9F27)

| Value | Type | Description |
|-------|------|-------------|
| 00 | AAC | Application Authentication Cryptogram (decline) |
| 40 | TC | Transaction Certificate (offline approve) |
| 80 | ARQC | Authorization Request Cryptogram (online) |

## Parsing Examples

### Full EMV Data String

```python
emv_data = (
    "9F2608ABCDEF0123456789"  # Cryptogram
    "9F2701"                   # CID length
    "80"                       # CID value (ARQC)
    "9F100706010A03A40000"     # Issuer Application Data
)

tags = parse_emv_data(emv_data)

print(tags)
# {
#     "9F26": "ABCDEF0123456789",
#     "9F27": "80",
#     "9F10": "06010A03A40000"
# }
```

### From Parsed Message

```python
from iso8583sim.core.parser import ISO8583Parser

parser = ISO8583Parser()
message = parser.parse(raw_message)

if message.emv_data:
    cryptogram = message.emv_data.get("9F26")
    cid = message.emv_data.get("9F27")

    if cid == "80":
        print("Online authorization requested (ARQC)")
    elif cid == "40":
        print("Offline approved (TC)")
    elif cid == "00":
        print("Offline declined (AAC)")
```

## Building Examples

### Build Field 55

```python
from iso8583sim.core.emv import build_emv_data

tags = {
    "9F26": "1234567890ABCDEF",
    "9F27": "80",
    "9F10": "0110A00003220000",
    "9F37": "12345678",
    "9F36": "0001",
}

field_55 = build_emv_data(tags)
print(field_55)  # "9F26081234567890ABCDEF9F27018..."
```

### Add to Message

```python
from iso8583sim.core.types import ISO8583Message
from iso8583sim.core.emv import build_emv_data

emv_tags = {
    "9F26": "1234567890ABCDEF",
    "9F27": "80",
}

message = ISO8583Message(
    mti="0100",
    fields={
        0: "0100",
        2: "4111111111111111",
        3: "000000",
        4: "000000025000",
        55: build_emv_data(emv_tags),
    }
)
```

## Integration with Demo Module

```python
from iso8583sim.demo import generate_emv_auth

# Generate EMV authorization with demo data
message = generate_emv_auth(
    pan="4111111111111111",
    amount=25000,
    cryptogram="1234567890ABCDEF",
)

print(message.fields.get(55))  # Contains built EMV TLV data
```

## API Reference

See [Core API Reference](../api/core.md#iso8583simcoreemv) for complete API documentation.
