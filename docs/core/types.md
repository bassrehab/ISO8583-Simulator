# Types & Fields

The `types` module defines all data types, enums, and field definitions used throughout iso8583sim.

## Enumerations

### ISO8583Version

Protocol version identifiers:

```python
from iso8583sim.core.types import ISO8583Version

ISO8583Version.V1987  # Original version
ISO8583Version.V1993  # First revision
ISO8583Version.V2003  # Second revision
```

### FieldType

Field data types:

```python
from iso8583sim.core.types import FieldType

FieldType.NUMERIC       # n - Digits only (0-9)
FieldType.ALPHA         # a - Letters only (A-Z, a-z)
FieldType.ALPHANUMERIC  # an - Letters and numbers
FieldType.BINARY        # b - Binary/hex data
FieldType.SPECIAL       # s - Special characters
FieldType.TRACK2        # z - Track 2 magnetic stripe
FieldType.LLVAR         # Variable length (max 99)
FieldType.LLLVAR        # Variable length (max 999)
```

### CardNetwork

Supported card networks:

```python
from iso8583sim.core.types import CardNetwork

CardNetwork.VISA
CardNetwork.MASTERCARD
CardNetwork.AMEX
CardNetwork.DISCOVER
CardNetwork.JCB
CardNetwork.UNIONPAY
```

### MessageClass

Message class identifiers (MTI position 2):

```python
from iso8583sim.core.types import MessageClass

MessageClass.AUTHORIZATION      # "1" - Authorization
MessageClass.FINANCIAL          # "2" - Financial
MessageClass.FILE_ACTIONS       # "3" - File action
MessageClass.REVERSAL           # "4" - Reversal
MessageClass.RECONCILIATION     # "5" - Reconciliation
MessageClass.ADMINISTRATIVE     # "6" - Administrative
MessageClass.FEE_COLLECTION     # "7" - Fee collection
MessageClass.NETWORK_MANAGEMENT # "8" - Network management
```

### MessageFunction

Message function identifiers (MTI position 3):

```python
from iso8583sim.core.types import MessageFunction

MessageFunction.REQUEST          # "0" - Request
MessageFunction.RESPONSE         # "1" - Response
MessageFunction.ADVICE           # "2" - Advice
MessageFunction.ADVICE_RESPONSE  # "3" - Response to advice
MessageFunction.NOTIFICATION     # "4" - Notification
```

## Data Classes

### FieldDefinition

Defines the structure of an ISO 8583 field:

```python
from iso8583sim.core.types import FieldDefinition, FieldType

field = FieldDefinition(
    field_type=FieldType.NUMERIC,
    max_length=12,
    description="Transaction Amount",
    field_number=4,
    encoding="ascii",
    min_length=None,
    padding_char="0",
    padding_direction="left",
)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `field_type` | FieldType | Data type |
| `max_length` | int | Maximum length |
| `description` | str | Human-readable description |
| `field_number` | int | Field number (1-128) |
| `encoding` | str | Character encoding (default: "ascii") |
| `min_length` | int | Minimum length (for variable fields) |
| `padding_char` | str | Padding character |
| `padding_direction` | str | "left" or "right" |

### ISO8583Message

Represents a parsed or constructed message:

```python
from iso8583sim.core.types import ISO8583Message, CardNetwork, ISO8583Version

message = ISO8583Message(
    mti="0100",
    fields={
        0: "0100",
        2: "4111111111111111",
        3: "000000",
        4: "000000001000",
    },
    bitmap="7000000000000000",
    secondary_bitmap=None,
    network=CardNetwork.VISA,
    version=ISO8583Version.V1987,
    raw="",
    emv_data=None,
)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `mti` | str | Message Type Indicator |
| `fields` | dict[int, str] | Field number to value mapping |
| `bitmap` | str | Primary bitmap (hex) |
| `secondary_bitmap` | str | Secondary bitmap (hex) |
| `network` | CardNetwork | Detected card network |
| `version` | ISO8583Version | Protocol version |
| `raw` | str | Original raw message |
| `emv_data` | dict | Parsed Field 55 EMV tags |

## Field Definitions

### Standard Fields (ISO8583_FIELDS)

The `ISO8583_FIELDS` dictionary contains definitions for all 128 standard fields:

```python
from iso8583sim.core.types import ISO8583_FIELDS

# Get field 2 definition
pan_field = ISO8583_FIELDS[2]
print(pan_field.description)  # "Primary Account Number"
print(pan_field.field_type)   # FieldType.LLVAR
print(pan_field.max_length)   # 19
```

### Key Fields

| Field | Name | Type | Length | Description |
|-------|------|------|--------|-------------|
| 2 | PAN | LLVAR | 19 | Primary Account Number |
| 3 | Processing Code | n | 6 | Transaction type |
| 4 | Amount | n | 12 | Transaction amount |
| 7 | Transmission Date/Time | n | 10 | MMDDhhmmss |
| 11 | STAN | n | 6 | System Trace Audit Number |
| 12 | Local Time | n | 6 | hhmmss |
| 13 | Local Date | n | 4 | MMDD |
| 14 | Expiration Date | n | 4 | YYMM |
| 22 | POS Entry Mode | n | 3 | How card was read |
| 23 | Card Sequence Number | n | 3 | For multi-card PANs |
| 24 | NII | n | 3 | Network Identifier |
| 25 | POS Condition Code | n | 2 | Transaction condition |
| 35 | Track 2 Data | LLVAR | 37 | Magnetic stripe |
| 37 | Retrieval Reference | an | 12 | Unique reference |
| 38 | Authorization Code | an | 6 | Approval code |
| 39 | Response Code | an | 2 | 00=Approved |
| 41 | Terminal ID | ans | 8 | Card acceptor terminal |
| 42 | Merchant ID | ans | 15 | Card acceptor ID |
| 55 | ICC Data | LLLVAR | 999 | EMV chip data |

## Helper Functions

### get_field_definition

Get field definition with network/version overrides:

```python
from iso8583sim.core.types import get_field_definition, CardNetwork

# Basic lookup
field_def = get_field_definition(2)

# With network-specific override
field_def = get_field_definition(62, network=CardNetwork.VISA)
```

### detect_network

Detect card network from PAN:

```python
from iso8583sim.core.types import detect_network

network = detect_network("4111111111111111")
print(network)  # CardNetwork.VISA

network = detect_network("5500000000000004")
print(network)  # CardNetwork.MASTERCARD
```

## Exceptions

### ParseError

Raised when parsing fails:

```python
from iso8583sim.core.types import ParseError

try:
    message = parser.parse(invalid_message)
except ParseError as e:
    print(f"Parse error: {e}")
```

### BuildError

Raised when building fails:

```python
from iso8583sim.core.types import BuildError

try:
    raw = builder.build(invalid_message)
except BuildError as e:
    print(f"Build error: {e}")
```

## API Reference

See [Core API Reference](../api/core.md#iso8583simcoretypes) for complete API documentation.
