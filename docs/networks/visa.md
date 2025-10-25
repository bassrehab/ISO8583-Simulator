# VISA

VISA-specific field definitions and requirements for iso8583sim.

## Network Detection

VISA cards are detected by PAN prefix:
- Starts with `4`
- 13, 16, or 19 digits

```python
from iso8583sim.core.types import detect_network, CardNetwork

network = detect_network("4111111111111111")
assert network == CardNetwork.VISA
```

## Required Fields

VISA authorization requests require:

| Field | Name | Format |
|-------|------|--------|
| 2 | PAN | LLVAR (13-19 digits) |
| 3 | Processing Code | n6 |
| 4 | Amount | n12 |
| 11 | STAN | n6 |
| 14 | Expiration Date | n4 (YYMM) |
| 22 | POS Entry Mode | n3 |
| 24 | NII | n3 |
| 25 | POS Condition Code | n2 |

## VISA-Specific Fields

### Field 62 - VISA Private Data

Reserved for VISA-specific data elements:

```python
message.fields[62] = "01" + "0123456789"  # Example format
```

### Field 63 - VISA Additional Data

Additional transaction data:

| Sub-element | Description |
|-------------|-------------|
| 01 | Network ID |
| 02 | Settlement Basis |
| 03 | Transaction ID |

## POS Entry Modes (Field 22)

| Value | Description |
|-------|-------------|
| 010 | Manual/Key Entry (No PIN) |
| 011 | Manual/Key Entry (PIN Entry) |
| 051 | Chip Card (No PIN) |
| 052 | Chip Card (PIN Entry) |
| 071 | Contactless (No PIN) |
| 072 | Contactless (PIN Entry) |
| 901 | Magnetic Stripe (No PIN) |
| 902 | Magnetic Stripe (PIN Entry) |

## Response Codes (Field 39)

| Code | Description |
|------|-------------|
| 00 | Approved |
| 01 | Refer to Issuer |
| 05 | Do Not Honor |
| 12 | Invalid Transaction |
| 14 | Invalid Card Number |
| 41 | Lost Card - Pick Up |
| 43 | Stolen Card - Pick Up |
| 51 | Insufficient Funds |
| 54 | Expired Card |
| 55 | Incorrect PIN |
| 61 | Exceeds Withdrawal Limit |
| 65 | Activity Count Limit Exceeded |
| 75 | PIN Tries Exceeded |
| 91 | Issuer Unavailable |

## Example: VISA Authorization Request

```python
from iso8583sim.core.types import ISO8583Message, CardNetwork
from iso8583sim.core.builder import ISO8583Builder

message = ISO8583Message(
    mti="0100",
    network=CardNetwork.VISA,
    fields={
        0: "0100",
        2: "4111111111111111",      # VISA PAN
        3: "000000",                # Purchase
        4: "000000010000",          # $100.00
        7: "1225120000",            # Dec 25, 12:00:00
        11: "123456",               # STAN
        14: "2512",                 # Exp Dec 2025
        22: "051",                  # Chip, no PIN
        24: "100",                  # NII
        25: "00",                   # Normal transaction
        41: "TERM0001",
        42: "MERCHANT123456 ",
    }
)

builder = ISO8583Builder()
raw = builder.build(message)
```

## Example: VISA EMV Authorization

```python
from iso8583sim.demo import generate_emv_auth

emv_message = generate_emv_auth(
    pan="4111111111111111",
    amount=25000,
    cryptogram="1234567890ABCDEF",
)

# Field 55 contains EMV data
print(emv_message.fields.get(55))
```

## VISA Base I/II

VISA uses two processing environments:

- **Base I**: Authorization and clearing
- **Base II**: Settlement and reconciliation

iso8583sim focuses on Base I authorization messages.

## Validation

VISA-specific validation:

```python
from iso8583sim.core.validator import ISO8583Validator
from iso8583sim.core.types import CardNetwork

validator = ISO8583Validator()
message.network = CardNetwork.VISA

errors = validator.validate_message(message)
# Validates:
# - All VISA required fields present
# - PAN passes Luhn check
# - Field formats match VISA specs
```
