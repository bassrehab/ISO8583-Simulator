# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""PIN blocks and MACs for testing and simulating ISO 8583 security fields.

Requires the optional dependency: pip install iso8583sim[security]

For test and simulation use only. Production systems keep keys and clear PINs inside an
HSM and never handle them in application code.
"""

from ._cipher import SecurityError
from .mac import generate_mac, mac_field, sign_message, verify_mac, verify_message
from .pinblock import decode_pin_block, decrypt_pin_block, encode_pin_block, encrypt_pin_block

__all__ = [
    "SecurityError",
    # PIN blocks (ISO 9564-1)
    "encode_pin_block",
    "decode_pin_block",
    "encrypt_pin_block",
    "decrypt_pin_block",
    # MACs (ISO 9797-1)
    "generate_mac",
    "verify_mac",
    "mac_field",
    "sign_message",
    "verify_message",
]
