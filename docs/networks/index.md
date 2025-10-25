# Card Networks

iso8583sim supports multiple card networks with network-specific field definitions and validation rules.

## Supported Networks

| Network | PAN Prefixes | Documentation |
|---------|--------------|---------------|
| VISA | 4xxx | [VISA Guide](visa.md) |
| Mastercard | 51-55, 2221-2720 | [Mastercard Guide](mastercard.md) |
| AMEX | 34, 37 | [Other Networks](others.md) |
| Discover | 6011, 644-649, 65 | [Other Networks](others.md) |
| JCB | 3528-3589 | [Other Networks](others.md) |
| UnionPay | 62 | [Other Networks](others.md) |

## Network Detection

Networks are automatically detected from the PAN (Primary Account Number):

```python
from iso8583sim.core.parser import ISO8583Parser

parser = ISO8583Parser()
message = parser.parse(raw_message)

print(message.network)  # CardNetwork.VISA
```

### Detection Rules

```python
from iso8583sim.core.types import detect_network

detect_network("4111111111111111")    # CardNetwork.VISA
detect_network("5500000000000004")    # CardNetwork.MASTERCARD
detect_network("378282246310005")     # CardNetwork.AMEX
detect_network("6011111111111117")    # CardNetwork.DISCOVER
detect_network("3530111333300000")    # CardNetwork.JCB
detect_network("6200000000000005")    # CardNetwork.UNIONPAY
```

## Manual Network Specification

Override auto-detection by specifying the network:

```python
from iso8583sim.core.types import CardNetwork

# During parsing
message = parser.parse(raw_message, network=CardNetwork.MASTERCARD)

# In message object
message = ISO8583Message(
    mti="0100",
    network=CardNetwork.VISA,
    fields={...}
)
```

## Network-Specific Fields

Each network has specific field format requirements:

```python
from iso8583sim.core.types import NETWORK_SPECIFIC_FIELDS

# Get VISA-specific field 62 definition
visa_field_62 = NETWORK_SPECIFIC_FIELDS[CardNetwork.VISA].get(62)
```

## Required Fields by Network

Different networks require different fields for authorization:

| Network | Required Fields |
|---------|-----------------|
| VISA | 2, 3, 4, 11, 14, 22, 24, 25 |
| Mastercard | 2, 3, 4, 11, 22, 24, 25 |
| AMEX | 2, 3, 4, 11, 22, 25 |
| Discover | 2, 3, 4, 11, 22 |
| JCB | 2, 3, 4, 11, 22, 25 |
| UnionPay | 2, 3, 4, 11, 22, 25, 49 |

## Network Validation

The validator checks network-specific requirements:

```python
from iso8583sim.core.validator import ISO8583Validator
from iso8583sim.core.types import CardNetwork

validator = ISO8583Validator()

message.network = CardNetwork.VISA
errors = validator.validate_message(message)

# Checks:
# - Required fields are present
# - Network-specific field formats
# - Network-specific business rules
```

## Common Field Differences

### Field 22 - POS Entry Mode

| Network | Values |
|---------|--------|
| VISA | 01x=Manual, 05x=Chip, 07x=Contactless |
| Mastercard | 01x=Manual, 05x=Chip, 07x=Contactless |

### Field 39 - Response Codes

| Code | VISA | Mastercard |
|------|------|------------|
| 00 | Approved | Approved |
| 05 | Do Not Honor | Do Not Honor |
| 51 | Insufficient Funds | Insufficient Funds |
| 14 | Invalid Card | Invalid Card Number |

### Field 55 - EMV Data

EMV (chip card) data format is consistent across networks, but specific tags may vary in interpretation.

## Next Steps

- [VISA Specifics](visa.md)
- [Mastercard Specifics](mastercard.md)
- [Other Networks](others.md)
