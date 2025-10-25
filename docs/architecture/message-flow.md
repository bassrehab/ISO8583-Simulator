# Message Flow

This document describes how ISO 8583 messages flow through iso8583sim.

## Parsing Flow

```
Raw Message String
        │
        ▼
┌───────────────────┐
│   ISO8583Parser   │
│                   │
│  1. _parse_mti()  │──▶ Extract 4-character MTI
│                   │
│  2. _parse_bitmap()│──▶ Parse primary bitmap (8 bytes hex)
│                   │    Check bit 1 for secondary bitmap
│                   │
│  3. _get_present_ │──▶ Convert bitmap to list of
│     fields()      │    present field numbers
│                   │
│  4. _parse_fields()│──▶ For each present field:
│                   │    - Get field definition
│                   │    - Parse based on type (fixed/LLVAR/LLLVAR)
│                   │    - Detect network from PAN
│                   │
│  5. _parse_emv()  │──▶ If Field 55 present:
│     (optional)    │    Parse TLV tags
│                   │
└───────────────────┘
        │
        ▼
  ISO8583Message
```

### Parser Methods

| Method | Purpose |
|--------|---------|
| `parse()` | Main entry point, orchestrates parsing |
| `_parse_mti()` | Extract MTI (positions 0-3) |
| `_parse_bitmap()` | Parse 16-hex-char primary bitmap |
| `_get_present_fields()` | Convert bitmap bits to field numbers |
| `_parse_fields()` | Parse individual field values |
| `_parse_fixed_field()` | Parse fixed-length field |
| `_parse_variable_field()` | Parse LLVAR/LLLVAR field |
| `_detect_network()` | Identify card network from PAN |

## Building Flow

```
  ISO8583Message
        │
        ▼
┌───────────────────┐
│   ISO8583Builder  │
│                   │
│  1. Format fields │──▶ For each field:
│                   │    - Get field definition
│                   │    - Apply padding/formatting
│                   │
│  2. Validate      │──▶ ISO8583Validator.validate_message()
│                   │    - Check required fields
│                   │    - Validate field types
│                   │    - Network-specific rules
│                   │
│  3. Build MTI     │──▶ Append 4-character MTI
│                   │
│  4. Build bitmap  │──▶ Create bitmap from present fields
│                   │    - Primary: fields 1-64
│                   │    - Secondary: fields 65-128
│                   │
│  5. Build fields  │──▶ For each field in order:
│                   │    - Add length prefix (LLVAR/LLLVAR)
│                   │    - Append field value
│                   │
└───────────────────┘
        │
        ▼
Raw Message String
```

### Builder Methods

| Method | Purpose |
|--------|---------|
| `build()` | Main entry point, orchestrates building |
| `_format_field_value()` | Apply padding and formatting rules |
| `_build_bitmap()` | Generate bitmap from present fields |
| `_build_field()` | Build individual field with length prefix |

## Validation Flow

```
  ISO8583Message
        │
        ▼
┌────────────────────────┐
│   ISO8583Validator     │
│                        │
│  1. validate_mti()     │──▶ Check MTI format (4 digits)
│                        │    Validate message class/function
│                        │
│  2. validate_bitmap()  │──▶ Check bitmap format (16 hex)
│                        │    Verify field presence matches
│                        │
│  3. validate_fields()  │──▶ For each field:
│                        │    - Check type (n/a/an/b)
│                        │    - Validate length
│                        │    - Apply field-specific rules
│                        │
│  4. Network validation │──▶ Check required fields present
│     (if network set)   │    Apply network-specific rules
│                        │
└────────────────────────┘
        │
        ▼
  List[str] (errors)
```

## EMV Data Flow

Field 55 contains EMV chip card data in TLV (Tag-Length-Value) format:

```
Field 55 Raw Data
        │
        ▼
┌────────────────────────┐
│   parse_emv_data()     │
│                        │
│  While data remains:   │
│  1. Read tag (1-3 bytes)│
│  2. Read length (1-3 bytes)│
│  3. Read value (length bytes)│
│  4. Store in dictionary │
│                        │
└────────────────────────┘
        │
        ▼
  Dict[tag, value]
  e.g., {"9F26": "ABCD...", "9F27": "80"}
```

## Object Pooling (High-Throughput)

For high-throughput scenarios, `MessagePool` reduces object allocation:

```
┌──────────────────┐
│   MessagePool    │
│                  │
│  acquire()       │──▶ Get message from pool or create new
│                  │
│  release()       │──▶ Reset and return message to pool
│                  │
│  Parser uses:    │
│  pool.acquire()  │──▶ Get blank message
│  ... parse ...   │
│  return message  │
│                  │
│  User returns:   │
│  pool.release()  │──▶ Message reused next time
│                  │
└──────────────────┘
```

## Cython Acceleration

When Cython extensions are compiled, critical functions are replaced:

| Python Function | Cython Function | Speedup |
|-----------------|-----------------|---------|
| `_parse_mti()` | `parse_mti_fast()` | ~2x |
| `_parse_bitmap()` | `parse_bitmap_fast()` | ~2x |
| `_get_present_fields()` | `get_present_fields_fast()` | ~1.5x |
| `_validate_pan_luhn()` | `validate_pan_luhn_fast()` | ~3x |

Detection is automatic:

```python
try:
    from ._parser_fast import parse_bitmap_fast
    _USE_CYTHON = True
except ImportError:
    _USE_CYTHON = False
```
