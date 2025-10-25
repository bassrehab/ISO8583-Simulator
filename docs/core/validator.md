# Validator

The `ISO8583Validator` class validates ISO 8583 messages for structure and content correctness.

## Quick Start

```python
from iso8583sim.core.validator import ISO8583Validator
from iso8583sim.core.types import ISO8583Message

validator = ISO8583Validator()

message = ISO8583Message(
    mti="0100",
    fields={
        0: "0100",
        2: "4111111111111111",
        3: "000000",
        4: "000000001000",
    }
)

errors = validator.validate_message(message)

if errors:
    for error in errors:
        print(f"Error: {error}")
else:
    print("Message is valid!")
```

## Validation Rules

### MTI Validation

- Must be exactly 4 digits
- First digit: ISO version (0, 1, 2)
- Second digit: Message class (1-8)
- Third digit: Message function (0-4, 8, 9)
- Fourth digit: Message origin (0-5)

```python
# Valid MTIs
"0100"  # Authorization request (1987)
"0110"  # Authorization response
"0200"  # Financial request
"0400"  # Reversal request

# Invalid MTIs
"100"   # Too short
"01A0"  # Non-numeric
"0190"  # Invalid function digit
```

### Field Type Validation

| Type | Rule | Example |
|------|------|---------|
| Numeric (n) | Only digits 0-9 | `"123456"` |
| Alpha (a) | Only letters A-Z, a-z | `"APPROVED"` |
| Alphanumeric (an) | Letters and digits | `"ABC123"` |
| Binary (b) | Hex characters | `"9F2608"` |
| LLVAR | Max 99 chars | PAN field |
| LLLVAR | Max 999 chars | EMV data |

### Field Length Validation

```python
# Fixed-length fields must match exactly
# Field 3 (Processing Code): 6 digits
"000000"   # Valid
"00000"    # Invalid (too short)
"0000000"  # Invalid (too long)

# Variable-length fields checked against max
# Field 2 (PAN): LLVAR, max 19
"4111111111111111"     # Valid (16 chars)
"41111111111111111111" # Invalid (20 chars)
```

### Network-Specific Validation

When network is specified, validates required fields:

```python
from iso8583sim.core.types import CardNetwork

message.network = CardNetwork.VISA

# VISA requires: 2, 3, 4, 11, 14, 22, 24, 25
errors = validator.validate_message(message)
```

**Network Required Fields:**

| Network | Required Fields |
|---------|-----------------|
| VISA | 2, 3, 4, 11, 14, 22, 24, 25 |
| Mastercard | 2, 3, 4, 11, 22, 24, 25 |
| AMEX | 2, 3, 4, 11, 22, 25 |
| Discover | 2, 3, 4, 11, 22 |
| JCB | 2, 3, 4, 11, 22, 25 |
| UnionPay | 2, 3, 4, 11, 22, 25, 49 |

### PAN Validation

Luhn checksum validation for Field 2:

```python
"4111111111111111"  # Valid (passes Luhn)
"4111111111111112"  # Invalid (fails Luhn)
```

## Single Field Validation

```python
from iso8583sim.core.types import get_field_definition

field_def = get_field_definition(2)  # PAN field

is_valid, error = validator.validate_field(
    field_number=2,
    value="4111111111111111",
    field_def=field_def
)

if not is_valid:
    print(f"Field 2 error: {error}")
```

## Validation Examples

### Valid Authorization Request

```python
message = ISO8583Message(
    mti="0100",
    network=CardNetwork.VISA,
    fields={
        0: "0100",
        2: "4111111111111111",  # PAN
        3: "000000",            # Processing Code
        4: "000000001000",      # Amount
        11: "123456",           # STAN
        14: "2512",             # Expiry
        22: "051",              # POS Entry Mode
        24: "100",              # NII
        25: "00",               # POS Condition Code
    }
)

errors = validator.validate_message(message)
# errors = []  (valid)
```

### Invalid Message Examples

```python
# Missing required field
message.fields.pop(4)  # Remove amount
errors = validator.validate_message(message)
# ["Missing required field: 4"]

# Invalid field type
message.fields[4] = "ABCDEF"  # Amount should be numeric
errors = validator.validate_message(message)
# ["Field 4 must contain only digits"]

# Invalid PAN (Luhn)
message.fields[2] = "4111111111111112"
errors = validator.validate_message(message)
# ["Field 2 (PAN) failed Luhn check"]
```

## Cython Acceleration

Validation functions have Cython optimizations:

| Function | Speedup |
|----------|---------|
| `is_numeric()` | ~2x |
| `is_alphanumeric()` | ~2x |
| `is_valid_hex()` | ~2x |
| `validate_pan_luhn()` | ~3x |

Detection is automatic when Cython extensions are compiled.

## API Reference

See [Core API Reference](../api/core.md#iso8583simcorevalidator) for complete API documentation.
