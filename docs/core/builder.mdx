# Builder

The `ISO8583Builder` class constructs raw ISO 8583 message strings from `ISO8583Message` objects.

## Quick Start

```python
from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.types import ISO8583Message

builder = ISO8583Builder()

# Define a message
message = ISO8583Message(
    mti="0100",
    fields={
        0: "0100",
        2: "4111111111111111",  # PAN
        3: "000000",            # Processing Code
        4: "000000001000",      # Amount ($10.00)
        11: "123456",           # STAN
        41: "TERM0001",         # Terminal ID
        42: "MERCHANT123456 ",  # Merchant ID
    }
)

# Build the raw message
raw_message = builder.build(message)
print(raw_message)
```

## Features

### Automatic Validation

The builder validates messages before building:

```python
from iso8583sim.core.types import BuildError

try:
    raw = builder.build(message)
except BuildError as e:
    print(f"Build error: {e}")
```

### Field Formatting

Fields are automatically formatted based on their definitions:

- **Numeric fields**: Left-padded with zeros
- **Alphanumeric fields**: Right-padded with spaces (where required)
- **Terminal ID (41)**: Right-padded to 8 characters
- **Merchant ID (42)**: Right-padded to 15 characters

```python
# Input
message.fields[41] = "TERM1"
message.fields[42] = "MERCHANT"

# Output (after build)
# Field 41: "TERM1   " (8 chars)
# Field 42: "MERCHANT       " (15 chars)
```

### Variable-Length Fields

LLVAR and LLLVAR fields get automatic length prefixes:

```python
# Field 2 (PAN) is LLVAR
message.fields[2] = "4111111111111111"

# In raw message: "164111111111111111"
#                  ^^ length prefix (16 chars)
```

### Bitmap Generation

The bitmap is automatically generated from present fields:

```python
message = ISO8583Message(
    mti="0100",
    fields={
        0: "0100",
        2: "4111111111111111",  # Bit 2
        3: "000000",            # Bit 3
        4: "000000001000",      # Bit 4
    }
)

# Bitmap: bits 2, 3, 4 set
# Binary: 0111 0000 0000 0000 ...
# Hex: 7000000000000000
```

### Network-Aware Building

Specify network for network-specific field formatting:

```python
from iso8583sim.core.types import CardNetwork

message = ISO8583Message(
    mti="0100",
    network=CardNetwork.VISA,
    fields={...}
)

raw = builder.build(message)
```

## Building Process

1. **Field Processing**: Format each field value based on definition
2. **Validation**: Validate message structure and field content
3. **MTI**: Append 4-character MTI
4. **Bitmap**: Generate and append bitmap from present fields
5. **Fields**: Append each field with length prefix (if variable)

## Common Field Examples

### Authorization Request (0100)

```python
auth_request = ISO8583Message(
    mti="0100",
    fields={
        0: "0100",
        2: "4111111111111111",      # PAN
        3: "000000",                # Processing Code (purchase)
        4: "000000001000",          # Amount
        7: "1225120000",            # Date/Time
        11: "123456",               # STAN
        14: "2512",                 # Expiry (YYMM)
        22: "051",                  # POS Entry Mode
        24: "100",                  # NII
        25: "00",                   # POS Condition Code
        41: "TERM0001",             # Terminal ID
        42: "MERCHANT123456 ",      # Merchant ID
    }
)
```

### Financial Request (0200)

```python
financial_request = ISO8583Message(
    mti="0200",
    fields={
        0: "0200",
        2: "4111111111111111",
        3: "000000",
        4: "000000001000",
        11: "123457",
        41: "TERM0001",
        42: "MERCHANT123456 ",
    }
)
```

### Reversal (0400)

```python
reversal = ISO8583Message(
    mti="0400",
    fields={
        0: "0400",
        2: "4111111111111111",
        3: "000000",
        4: "000000001000",
        11: "123456",       # Original STAN
        37: "123456789012", # Original retrieval reference
        41: "TERM0001",
        42: "MERCHANT123456 ",
    }
)
```

## Error Handling

```python
from iso8583sim.core.types import BuildError

try:
    raw = builder.build(message)
except BuildError as e:
    print(f"Build failed: {e}")
```

Common errors:
- Missing required fields
- Invalid field format
- Field value exceeds maximum length

## API Reference

See [Core API Reference](../api/core.md#iso8583simcorebuilder) for complete API documentation.
