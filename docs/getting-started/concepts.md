# ISO 8583 Concepts

ISO 8583 is the international standard for financial transaction card-originated messages. This guide covers the fundamental concepts.

## Message Structure

An ISO 8583 message consists of three main parts:

```
┌─────────┬──────────┬────────────────┐
│   MTI   │  Bitmap  │  Data Fields   │
│ (4 hex) │ (16 hex) │  (variable)    │
└─────────┴──────────┴────────────────┘
```

### MTI (Message Type Indicator)

The MTI is a 4-digit code that identifies the message type:

| Position | Meaning | Values |
|----------|---------|--------|
| 1 | ISO Version | 0=1987, 1=1993, 2=2003 |
| 2 | Message Class | 1=Auth, 2=Financial, 4=Reversal |
| 3 | Message Function | 0=Request, 1=Response, 2=Advice |
| 4 | Message Origin | 0=Acquirer, 2=Issuer |

**Common MTIs:**

| MTI | Description |
|-----|-------------|
| 0100 | Authorization Request |
| 0110 | Authorization Response |
| 0200 | Financial Request |
| 0210 | Financial Response |
| 0400 | Reversal Request |
| 0410 | Reversal Response |

### Bitmap

The bitmap indicates which fields are present in the message. It's a 64-bit (8-byte) or 128-bit (16-byte) field:

- **Primary Bitmap**: Fields 1-64
- **Secondary Bitmap**: Fields 65-128 (if bit 1 is set)

```python
# Example: Bitmap 7024058020C09000
# Binary: 0111 0000 0010 0100 0000 0101 1000 0000 ...
# Fields present: 2, 3, 4, 7, 11, 14, 22, 24, 25, ...
```

### Data Fields

ISO 8583 defines 128 standard fields. Each field has:

- **Field Number**: 1-128
- **Data Type**: Numeric, Alpha, Alphanumeric, Binary
- **Length**: Fixed or Variable (LLVAR/LLLVAR)

## Field Types

### Fixed-Length Fields

```python
# Field 3: Processing Code - 6 numeric digits
processing_code = "000000"  # Purchase

# Field 4: Amount - 12 numeric digits
amount = "000000001000"  # $10.00 (in cents)
```

### Variable-Length Fields

Variable fields have a length prefix:

- **LLVAR**: 2-digit length prefix (max 99 characters)
- **LLLVAR**: 3-digit length prefix (max 999 characters)

```python
# Field 2: PAN (LLVAR)
# "16" prefix + 16-digit PAN
pan_field = "164111111111111111"

# Field 35: Track 2 Data (LLLVAR)
# "037" prefix + 37 characters
track2 = "037411111111111111=2512101123400001"
```

## Key Fields

| Field | Name | Type | Description |
|-------|------|------|-------------|
| 2 | PAN | LLVAR | Primary Account Number (card number) |
| 3 | Processing Code | n6 | Transaction type (000000=purchase) |
| 4 | Amount | n12 | Transaction amount in minor units |
| 7 | Transmission Date/Time | n10 | MMDDhhmmss |
| 11 | STAN | n6 | System Trace Audit Number |
| 22 | POS Entry Mode | n3 | How card was read |
| 35 | Track 2 Data | LLVAR | Magnetic stripe data |
| 38 | Authorization Code | an6 | Approval code |
| 39 | Response Code | an2 | 00=Approved, 05=Declined |
| 41 | Terminal ID | ans8 | Card acceptor terminal ID |
| 42 | Merchant ID | ans15 | Card acceptor ID |
| 55 | EMV Data | LLLVAR | Chip card ICC data (TLV format) |

## Response Codes (Field 39)

| Code | Meaning |
|------|---------|
| 00 | Approved |
| 01 | Refer to issuer |
| 05 | Do not honor |
| 12 | Invalid transaction |
| 13 | Invalid amount |
| 14 | Invalid card number |
| 51 | Insufficient funds |
| 54 | Expired card |
| 55 | Incorrect PIN |

## Processing Codes (Field 3)

The 6-digit processing code has three parts:

| Digits | Meaning |
|--------|---------|
| 1-2 | Transaction Type |
| 3-4 | Account Type (From) |
| 5-6 | Account Type (To) |

**Transaction Types:**

| Code | Type |
|------|------|
| 00 | Purchase/Goods & Services |
| 01 | Cash Withdrawal |
| 09 | Purchase with Cash Back |
| 20 | Return/Refund |
| 30 | Balance Inquiry |

## EMV Data (Field 55)

Field 55 contains chip card data in TLV (Tag-Length-Value) format:

```
┌───────┬────────┬───────────────┐
│  Tag  │ Length │     Value     │
│ (1-3) │  (1-3) │  (variable)   │
└───────┴────────┴───────────────┘
```

**Common EMV Tags:**

| Tag | Name |
|-----|------|
| 9F26 | Application Cryptogram |
| 9F27 | Cryptogram Information Data |
| 9F10 | Issuer Application Data |
| 9F37 | Unpredictable Number |
| 9F36 | Application Transaction Counter |
| 82 | Application Interchange Profile |
| 9C | Transaction Type |

## Card Networks

Different card networks have specific requirements:

- **VISA**: Field 62 (VISA private data), specific response codes
- **Mastercard**: Field 48 (additional data), DE127 subfields
- **AMEX**: Different field formats, 15-digit PANs
- **Discover**: Similar to VISA
- **JCB**: Japan-specific requirements
- **UnionPay**: China-specific requirements

See the [Networks Guide](../networks/index.md) for details.

## Next Steps

- [Parser Guide](../core/parser.md) - Parse ISO 8583 messages
- [Builder Guide](../core/builder.md) - Build messages
- [EMV Data Guide](../core/emv.md) - Work with chip card data
