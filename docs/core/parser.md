# Parser

The `ISO8583Parser` class converts raw ISO 8583 message strings into structured `ISO8583Message` objects.

## Quick Start

```python
from iso8583sim.core.parser import ISO8583Parser

parser = ISO8583Parser()

# Parse a raw message
message = parser.parse("0100702406C120E09000164111111111111111...")

print(f"MTI: {message.mti}")
print(f"PAN: {message.fields.get(2)}")
print(f"Amount: {message.fields.get(4)}")
print(f"Network: {message.network}")
```

## Features

### Auto Network Detection

The parser automatically detects the card network from the PAN (Field 2):

```python
message = parser.parse(raw_message)
print(message.network)  # CardNetwork.VISA, CardNetwork.MASTERCARD, etc.
```

Network detection is based on PAN prefixes:
- **VISA**: 4xxx
- **Mastercard**: 51-55, 2221-2720
- **AMEX**: 34, 37
- **Discover**: 6011, 644-649, 65
- **JCB**: 3528-3589
- **UnionPay**: 62

### Manual Network Specification

Override auto-detection by specifying the network:

```python
from iso8583sim.core.types import CardNetwork

message = parser.parse(raw_message, network=CardNetwork.MASTERCARD)
```

### Version Support

```python
from iso8583sim.core.types import ISO8583Version

# Use ISO 8583:1993
parser = ISO8583Parser(version=ISO8583Version.V1993)
```

### EMV Data Parsing

Field 55 (ICC Data) is automatically parsed into a dictionary:

```python
message = parser.parse(emv_message)

if message.emv_data:
    print(f"Cryptogram: {message.emv_data.get('9F26')}")
    print(f"CID: {message.emv_data.get('9F27')}")
```

### Object Pooling

For high-throughput scenarios:

```python
from iso8583sim.core.pool import MessagePool

pool = MessagePool(size=1000)
parser = ISO8583Parser(pool=pool)

# Messages are recycled
message = parser.parse(raw)
# ... use message ...
pool.release(message)
```

## Parsing Process

1. **MTI Extraction**: Read first 4 characters as Message Type Indicator
2. **Bitmap Parsing**: Parse 16-character hex bitmap (64 bits)
3. **Secondary Bitmap**: If bit 1 is set, parse additional 16 characters
4. **Field Parsing**: For each set bit, parse the corresponding field
5. **Network Detection**: Identify card network from PAN if present

## Error Handling

```python
from iso8583sim.core.types import ParseError

try:
    message = parser.parse(raw_message)
except ParseError as e:
    print(f"Parse error: {e}")
```

Common errors:
- Invalid MTI format
- Malformed bitmap
- Field length exceeds maximum
- Invalid hex characters

## API Reference

See [Core API Reference](../api/core.md#iso8583simcoreparser) for complete API documentation.
