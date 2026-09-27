# Other Networks

Support for American Express, Discover, JCB, and UnionPay.

## American Express (AMEX)

### Detection

- PAN prefix: 34, 37
- 15 digits

```python
from iso8583sim.core.types import detect_network, CardNetwork

network = detect_network("378282246310005")
assert network == CardNetwork.AMEX
```

### Required Fields

| Field | Name | Format |
|-------|------|--------|
| 2 | PAN | LLVAR (15 digits) |
| 3 | Processing Code | n6 |
| 4 | Amount | n12 |
| 11 | STAN | n6 |
| 22 | POS Entry Mode | n3 |
| 25 | POS Condition Code | n2 |

### Example

```python
from iso8583sim.core.types import ISO8583Message, CardNetwork

message = ISO8583Message(
    mti="0100",
    network=CardNetwork.AMEX,
    fields={
        0: "0100",
        2: "378282246310005",       # AMEX PAN (15 digits)
        3: "000000",
        4: "000000010000",
        11: "123456",
        22: "051",
        25: "00",
        41: "TERM0001",
        42: "MERCHANT123456 ",
    }
)
```

### AMEX-Specific Notes

- Uses 15-digit PANs (not 16)
- Different response code meanings for some codes
- CVV location differs (4 digits on front)

---

## Discover

### Detection

- PAN prefix: 6011, 644-649, 65
- 16-19 digits

```python
network = detect_network("6011111111111117")
assert network == CardNetwork.DISCOVER
```

### Required Fields

| Field | Name | Format |
|-------|------|--------|
| 2 | PAN | LLVAR (16-19 digits) |
| 3 | Processing Code | n6 |
| 4 | Amount | n12 |
| 11 | STAN | n6 |
| 22 | POS Entry Mode | n3 |

### Example

```python
message = ISO8583Message(
    mti="0100",
    network=CardNetwork.DISCOVER,
    fields={
        0: "0100",
        2: "6011111111111117",      # Discover PAN
        3: "000000",
        4: "000000010000",
        11: "123456",
        22: "051",
        41: "TERM0001",
        42: "MERCHANT123456 ",
    }
)
```

### Discover-Specific Notes

- D-PAS for tokenization
- Similar authorization flow to VISA
- ProtectBuy for 3D Secure

---

## JCB

### Detection

- PAN prefix: 3528-3589
- 16-19 digits

```python
network = detect_network("3530111333300000")
assert network == CardNetwork.JCB
```

### Required Fields

| Field | Name | Format |
|-------|------|--------|
| 2 | PAN | LLVAR (16-19 digits) |
| 3 | Processing Code | n6 |
| 4 | Amount | n12 |
| 11 | STAN | n6 |
| 22 | POS Entry Mode | n3 |
| 25 | POS Condition Code | n2 |

### Example

```python
message = ISO8583Message(
    mti="0100",
    network=CardNetwork.JCB,
    fields={
        0: "0100",
        2: "3530111333300000",      # JCB PAN
        3: "000000",
        4: "000000010000",
        11: "123456",
        22: "051",
        25: "00",
        41: "TERM0001",
        42: "MERCHANT123456 ",
    }
)
```

### JCB-Specific Notes

- Japan-based network with global acceptance
- J/Secure for 3D Secure authentication
- Currency conversion considerations for international transactions

---

## UnionPay

### Detection

- PAN prefix: 62
- 16-19 digits

```python
network = detect_network("6200000000000005")
assert network == CardNetwork.UNIONPAY
```

### Required Fields

| Field | Name | Format |
|-------|------|--------|
| 2 | PAN | LLVAR (16-19 digits) |
| 3 | Processing Code | n6 |
| 4 | Amount | n12 |
| 11 | STAN | n6 |
| 22 | POS Entry Mode | n3 |
| 25 | POS Condition Code | n2 |
| 49 | Currency Code | n3 |

Note: UnionPay requires Field 49 (Currency Code).

### Example

```python
message = ISO8583Message(
    mti="0100",
    network=CardNetwork.UNIONPAY,
    fields={
        0: "0100",
        2: "6200000000000005",      # UnionPay PAN
        3: "000000",
        4: "000000010000",
        11: "123456",
        22: "051",
        25: "00",
        41: "TERM0001",
        42: "MERCHANT123456 ",
        49: "156",                  # CNY (Chinese Yuan)
    }
)
```

### UnionPay-Specific Notes

- China-based network
- Field 49 required for currency identification
- QuickPass for contactless payments
- Supports both debit and credit products

---

## Response Codes Comparison

| Code | AMEX | Discover | JCB | UnionPay |
|------|------|----------|-----|----------|
| 00 | Approved | Approved | Approved | Approved |
| 05 | Do Not Honor | Do Not Honor | Do Not Honor | Do Not Honor |
| 14 | Invalid Card | Invalid Card | Invalid Card | Invalid Card |
| 51 | Insufficient Funds | Insufficient Funds | Insufficient Funds | Insufficient Funds |
| 54 | Expired Card | Expired Card | Expired Card | Expired Card |

## Adding Custom Network Support

To add a new network:

```python
# 1. Add to CardNetwork enum
class CardNetwork(Enum):
    NEW_NETWORK = "NEW_NETWORK"

# 2. Add detection rule
def detect_network(pan: str) -> CardNetwork | None:
    if pan.startswith("999"):  # Example prefix
        return CardNetwork.NEW_NETWORK
    # ... existing rules

# 3. Add field definitions
NETWORK_SPECIFIC_FIELDS[CardNetwork.NEW_NETWORK] = {
    62: FieldDefinition(...),
}

# 4. Add required fields
NETWORK_REQUIRED_FIELDS[CardNetwork.NEW_NETWORK] = [2, 3, 4, 11]
```
