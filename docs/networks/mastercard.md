# Mastercard

Mastercard-specific field definitions and requirements for iso8583sim.

## Network Detection

Mastercard cards are detected by PAN prefix:
- 51-55 (traditional)
- 2221-2720 (2-series BINs)
- 16 digits

```python
from iso8583sim.core.types import detect_network, CardNetwork

network = detect_network("5500000000000004")
assert network == CardNetwork.MASTERCARD

network = detect_network("2221000000000009")
assert network == CardNetwork.MASTERCARD
```

## Required Fields

Mastercard authorization requests require:

| Field | Name | Format |
|-------|------|--------|
| 2 | PAN | LLVAR (16 digits) |
| 3 | Processing Code | n6 |
| 4 | Amount | n12 |
| 11 | STAN | n6 |
| 22 | POS Entry Mode | n3 |
| 24 | NII | n3 |
| 25 | POS Condition Code | n2 |

Note: Field 14 (Expiration) is optional but recommended.

## Mastercard-Specific Fields

### Field 48 - Additional Data

Mastercard uses Field 48 for additional private data:

| Sub-element | Description |
|-------------|-------------|
| 01 | Additional Response Data |
| 14 | Transaction Category Code |
| 26 | Wallet Program Data |

### Field 61 - POS Data Extended

Extended point-of-service data:

```python
# Format varies by transaction type
message.fields[61] = "0000000001"
```

### DE127 - Private Data

Mastercard's Data Element 127 contains subfields for network data.

## POS Entry Modes (Field 22)

| Value | Description |
|-------|-------------|
| 010 | Manual/Key Entry |
| 051 | ICC Read, CVV Reliable |
| 052 | ICC Read, CVV Unreliable |
| 071 | Contactless M/Chip |
| 072 | Contactless Magnetic Stripe |
| 801 | E-commerce Manual |
| 812 | E-commerce Secure |

## Response Codes (Field 39)

| Code | Description |
|------|-------------|
| 00 | Approved |
| 01 | Refer to Issuer |
| 04 | Pick Up Card |
| 05 | Do Not Honor |
| 12 | Invalid Transaction |
| 14 | Invalid Card Number |
| 41 | Lost Card |
| 43 | Stolen Card |
| 51 | Insufficient Funds |
| 54 | Expired Card |
| 55 | Incorrect PIN |
| 57 | Transaction Not Permitted |
| 58 | Transaction Not Permitted to Terminal |
| 61 | Exceeds Amount Limit |
| 65 | Exceeds Frequency Limit |
| 75 | PIN Tries Exceeded |
| 91 | Issuer System Error |

## Example: Mastercard Authorization Request

```python
from iso8583sim.core.types import ISO8583Message, CardNetwork
from iso8583sim.core.builder import ISO8583Builder

message = ISO8583Message(
    mti="0100",
    network=CardNetwork.MASTERCARD,
    fields={
        0: "0100",
        2: "5500000000000004",      # Mastercard PAN
        3: "000000",                # Purchase
        4: "000000010000",          # $100.00
        7: "1225120000",            # Dec 25, 12:00:00
        11: "123456",               # STAN
        14: "2512",                 # Exp Dec 2025
        22: "051",                  # Chip, CVV reliable
        24: "100",                  # NII
        25: "00",                   # Normal transaction
        41: "TERM0001",
        42: "MERCHANT123456 ",
    }
)

builder = ISO8583Builder()
raw = builder.build(message)
```

## Example: Mastercard EMV Authorization

```python
from iso8583sim.demo import generate_emv_auth

# Use a Mastercard PAN
emv_message = generate_emv_auth(
    pan="5500000000000004",
    amount=25000,
    cryptogram="ABCDEF1234567890",
)

print(f"Network: {emv_message.network}")  # CardNetwork.MASTERCARD
```

## MasterCard Payment Gateway (MPG)

Mastercard authorizations route through MasterCard Payment Gateway:

- Authorization timeouts: 30 seconds standard
- Reversal required for timeout scenarios
- Advice messages for offline approvals

## SecureCode / 3DS

For e-commerce transactions with 3D Secure:

```python
# Field 48 contains authentication data
# Field 22 = 812 for authenticated e-commerce
message.fields[22] = "812"
```

## Validation

Mastercard-specific validation:

```python
from iso8583sim.core.validator import ISO8583Validator
from iso8583sim.core.types import CardNetwork

validator = ISO8583Validator()
message.network = CardNetwork.MASTERCARD

errors = validator.validate_message(message)
# Validates:
# - All Mastercard required fields present
# - PAN passes Luhn check
# - PAN prefix matches Mastercard ranges
# - Field formats match Mastercard specs
```

## 2-Series BINs

Mastercard 2-series BINs (2221-2720) are supported:

```python
# Both are valid Mastercard PANs
"5500000000000004"  # Traditional
"2221000000000009"  # 2-series
```
