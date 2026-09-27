# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Core module for ISO 8583 message handling.

This module provides the fundamental building blocks for working with
ISO 8583 financial transaction messages:

- **Types**: Data types, enums, and field definitions
- **Parser**: Parse raw message strings into structured objects
- **Builder**: Build raw message strings from objects
- **Validator**: Validate message structure and content
- **EMV**: Handle Field 55 chip card data (TLV format)
- **Pool**: Object pooling for high-throughput scenarios
"""

from .builder import ISO8583Builder
from .codes import PROCESSING_CODES, RESPONSE_CODES, detect_network_from_pan
from .emv import build_emv_data, parse_emv_data
from .parser import ISO8583Parser
from .pool import MessagePool
from .types import (
    BuildError,
    CardNetwork,
    FieldDefinition,
    FieldType,
    ISO8583Message,
    ISO8583Version,
    MessageClass,
    MessageFunction,
    ParseError,
    get_field_definition,
)
from .validator import ISO8583Validator

__all__ = [
    # Parser
    "ISO8583Parser",
    # Builder
    "ISO8583Builder",
    # Validator
    "ISO8583Validator",
    # Types
    "ISO8583Message",
    "ISO8583Version",
    "FieldType",
    "FieldDefinition",
    "CardNetwork",
    "MessageClass",
    "MessageFunction",
    "ParseError",
    "BuildError",
    "get_field_definition",
    # Codes
    "RESPONSE_CODES",
    "PROCESSING_CODES",
    "detect_network_from_pan",
    # EMV
    "parse_emv_data",
    "build_emv_data",
    # Pool
    "MessagePool",
]
