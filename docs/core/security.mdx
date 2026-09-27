# PIN Blocks and MACs

The `iso8583sim.security` module builds and checks the two security fields most test harnesses need: PIN blocks for field 52 and message authentication codes (MACs) for fields 64 and 128.

!!! warning "Test and simulation use only"
    Real payment systems keep clear PINs and keys inside a hardware security module (HSM). Use this module to generate test data and to check what your system under test produces, never to handle real cardholder PINs or production keys.

## Installation

```bash
pip install iso8583sim[security]
```

This installs the `cryptography` package.

## PIN Blocks (ISO 9564-1)

| Format | Cipher | Size | Uses PAN | Fill |
|--------|--------|------|----------|------|
| 0 | TDES | 8 bytes | Yes | `F` |
| 1 | TDES | 8 bytes | No | Random |
| 3 | TDES | 8 bytes | Yes | Random `A` to `F` |
| 4 | AES | 16 bytes | Yes | Random |

Formats 0, 1 and 3 fit field 52 in every version (8 bytes). Format 4 is 16 bytes, which fits field 52 in the 1993 and 2003 versions.

```python
from iso8583sim.security import decrypt_pin_block, encrypt_pin_block

key = "0123456789ABCDEFFEDCBA9876543210"  # Double length TDES key (test key)

block = encrypt_pin_block("1234", "4111111111111111", key, fmt=0)
print(block)  # 2A3D408A1977DDE9

pin = decrypt_pin_block(block, "4111111111111111", key, fmt=0)
print(pin)  # 1234
```

Format 4 needs an AES key (128, 192 or 256 bits):

```python
aes_key = "00112233445566778899AABBCCDDEEFF"
block = encrypt_pin_block("1234", "4111111111111111", aes_key, fmt=4)  # 32 hex characters
```

For clear (unencrypted) blocks in formats 0, 1 and 3, use `encode_pin_block` and `decode_pin_block`:

```python
from iso8583sim.security import encode_pin_block

encode_pin_block("1234", "4111111111111111", fmt=0).hex().upper()  # 041225EEEEEEEEEE
```

Decrypting with the wrong key, PAN or format raises `SecurityError`, because the result fails the block's structure checks.

## MACs (ISO 9797-1)

| Algorithm | Name | Key |
|-----------|------|-----|
| 1 | CBC-MAC | 8, 16 or 24 bytes |
| 3 | Retail MAC (ANSI X9.19), default | 16 bytes |

Padding method 1 (zeros, the default) and method 2 (`0x80` then zeros) are supported.

### Signing and verifying messages

`build_with_mac` builds a message and puts its MAC in the last field: field 64, or field 128 when the message has a secondary bitmap.

```python
from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.types import ISO8583Message
from iso8583sim.core.validator import ISO8583Validator

mac_key = "0123456789ABCDEFFEDCBA9876543210"
message = ISO8583Message(
    mti="0200",
    fields={2: "4111111111111111", 3: "000000", 4: "000000001000", 11: "123456"},
)

raw = ISO8583Builder().build_with_mac(message, mac_key)
ISO8583Validator().verify_mac(raw, mac_key)  # True
```

The MAC covers every character of the message before the MAC field, including the MTI and bitmap. Any change to the message makes verification fail.

### Raw data

```python
from iso8583sim.security import generate_mac, verify_mac

mac = generate_mac(b"data to authenticate", mac_key, algorithm=3, padding=1)
verify_mac(b"data to authenticate", mac, mac_key)  # True
```

Pass `length=4` to `generate_mac` for a 4-byte MAC. `verify_mac` takes the length from the MAC you give it.
