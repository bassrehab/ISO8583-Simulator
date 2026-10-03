# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

# iso8583sim/core/parser.py

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .codes import detect_network_from_pan
from .types import (
    ISO8583_FIELDS,
    NETWORK_SPECIFIC_FIELDS,
    VERSION_SPECIFIC_FIELDS,
    CardNetwork,
    FieldDefinition,
    FieldType,
    ISO8583Message,
    ISO8583Version,
    ParseError,
    get_field_definition,
)

if TYPE_CHECKING:
    from ..wire import WireFormat
    from .pool import MessagePool
    from .spec import Spec

# Try to import Cython-optimized functions
try:
    from ._bitmap import build_bitmap_fast, get_present_fields_fast  # noqa: F401
    from ._parser_fast import parse_bitmap_fast, parse_mti_fast  # noqa: F401

    _USE_CYTHON = True
except ImportError:
    _USE_CYTHON = False


@dataclass(slots=True)
class EMVTag:
    """EMV Tag data structure"""

    tag: str
    length: int
    value: str
    raw: str


class ISO8583Parser:
    """Parser for ISO 8583 messages with network support"""

    def __init__(
        self,
        version: ISO8583Version = ISO8583Version.V1987,
        pool: MessagePool | None = None,
        spec: Spec | None = None,
    ):
        """
        Initialize the parser.

        Args:
            version: ISO8583 version to use
            pool: Optional MessagePool for object reuse in high-throughput scenarios
            spec: Optional custom field definitions (see Spec). Its version is used, and its
                fields wherever it defines them.
        """
        # subhadipmitra@: A spec's fields come first, before network and version variations: it
        # describes the link being parsed, which those tables only approximate.
        self._spec = spec
        if spec is not None:
            version = spec.version
        self.version = version
        self._pool = pool
        self._current_position = 0
        self._raw_message = ""
        self._detected_network: CardNetwork | None = None
        self._secondary_bitmap = False
        self._network_fields: dict[int, FieldDefinition] = {}  # Cache for network-specific field definitions
        # Cache version-specific fields at init time (version doesn't change)
        self._version_fields = VERSION_SPECIFIC_FIELDS.get(version, {})
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.debug("Initialized ISO8583Parser with version %s", version.value)

    def parse(self, message: str, network: CardNetwork | None = None) -> ISO8583Message:
        """Parse an ISO 8583 message string into an ISO8583Message object"""
        try:
            self._raw_message = message
            self._current_position = 0
            self._detected_network = network
            # Cache network-specific fields for faster lookup
            self._network_fields = NETWORK_SPECIFIC_FIELDS.get(network, {}) if network else {}

            # Parse MTI
            mti = self._parse_mti()
            self.logger.debug("Parsed MTI: %s", mti)

            # Parse bitmap
            bitmap = self._parse_bitmap()
            self.logger.debug("Parsed bitmap: %s", bitmap)
            present_fields = self._get_present_fields(bitmap)
            self.logger.debug("Present fields: %s", present_fields)

            # Auto-detect network if not provided
            if not network:
                self._detected_network = self._detect_network(message)
                # Update cached network fields after detection
                self._network_fields = (
                    NETWORK_SPECIFIC_FIELDS.get(self._detected_network, {}) if self._detected_network else {}
                )

            self.logger.info(
                "Processing message for network: %s",
                self._detected_network.value if self._detected_network else "Unknown",
            )

            # Parse data fields
            fields = {0: mti}  # MTI is field 0
            for field_number in present_fields:
                try:
                    field_def = (
                        self._spec.definition(field_number, self._detected_network, self.version)
                        if self._spec is not None
                        else get_field_definition(field_number, self._detected_network, self.version)
                    )

                    if field_def is None:
                        self.logger.warning("No definition found for field %d", field_number)
                        continue

                    value = self._parse_field(field_number, field_def)
                    if value is not None:
                        fields[field_number] = self._format_field_value(field_number, value, field_def)
                        self.logger.debug("Parsed field %d: %s", field_number, fields[field_number])

                except Exception as e:
                    self.logger.error("Error parsing field %d: %s", field_number, str(e))
                    raise

            # Create message object (use pool if available for better performance)
            if self._pool is not None:
                msg = self._pool.acquire(
                    mti=mti,
                    fields=fields,
                    version=self.version,
                    network=self._detected_network,
                    raw_message=message,
                    bitmap=bitmap,
                )
            else:
                msg = ISO8583Message(
                    mti=mti,
                    fields=fields,
                    version=self.version,
                    network=self._detected_network,
                    raw_message=message,
                    bitmap=bitmap,
                )

            self.logger.info("Successfully parsed message")
            return msg

        except Exception as e:
            self.logger.error("Failed to parse message: %s", str(e))
            raise ParseError(f"Failed to parse message: {str(e)}") from e

    def parse_bytes(
        self, data: bytes, wire_format: WireFormat | None = None, network: CardNetwork | None = None
    ) -> ISO8583Message:
        """Parse a message received as bytes in a wire format (binary bitmap, BCD, EBCDIC...).

        Defaults to ASCII with a binary bitmap. See iso8583sim.wire.WireFormat for the presets.
        """
        from ..wire import decode_message

        return decode_message(data, wire_format, version=self.version, network=network)

    def parse_file(self, filename: str) -> list[ISO8583Message]:
        """Parse multiple messages from file"""
        self.logger.info("Starting to parse messages from file: %s", filename)
        messages = []

        try:
            with open(filename) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        self.logger.debug("Parsing message from line %d", line_num)
                        message = self.parse(line)
                        messages.append(message)
                        self.logger.info("Successfully parsed message %d", line_num)
                    except Exception as e:
                        self.logger.error("Failed to parse message at line %d: %s", line_num, str(e))
                        raise ParseError(f"Failed to parse message at line {line_num}: {str(e)}") from e

            self.logger.info("Successfully parsed %d messages from file", len(messages))
            return messages

        except Exception as e:
            self.logger.error("Error reading or parsing file: %s", str(e))
            raise ParseError(f"Failed to read or parse file: {str(e)}") from e

    def _parse_mti(self) -> str:
        """Parse Message Type Indicator"""
        if len(self._raw_message) < self._current_position + 4:
            raise ParseError("Message too short for MTI")

        mti = self._raw_message[self._current_position : self._current_position + 4]
        if not mti.isdigit():
            raise ParseError("Invalid MTI format - must be numeric")

        self._current_position += 4
        return mti

    def _parse_bitmap(self) -> str:
        """Parse primary and secondary bitmaps"""
        if len(self._raw_message) < self._current_position + 16:
            raise ParseError("Message too short for bitmap")

        # Parse primary bitmap
        primary_bitmap = self._raw_message[self._current_position : self._current_position + 16]
        self._current_position += 16

        # Check for secondary bitmap
        bitmap_int = int(primary_bitmap, 16)
        self._secondary_bitmap = bool(bitmap_int & 0x8000000000000000)

        if self._secondary_bitmap:
            if len(self._raw_message) < self._current_position + 16:
                raise ParseError("Message too short for secondary bitmap")
            secondary_bitmap = self._raw_message[self._current_position : self._current_position + 16]
            self._current_position += 16
            return primary_bitmap + secondary_bitmap

        return primary_bitmap

    def _get_present_fields(self, bitmap: str) -> list[int]:
        """Get list of present fields from bitmap using optimized bit manipulation"""
        try:
            # Use Cython-optimized version if available
            if _USE_CYTHON:
                raw_fields = get_present_fields_fast(bitmap)
                # Filter to only fields that have definitions
                return [f for f in raw_fields if self._get_field_definition(f)]

            # Pure Python fallback
            # Convert hex bitmap to integer directly
            bitmap_int = int(bitmap, 16)
            bitmap_len = len(bitmap) * 4  # Each hex char = 4 bits

            # Find all set bits using bit manipulation
            present_fields = []
            for bit_pos in range(bitmap_len):
                # Check if bit is set (MSB first)
                if bitmap_int & (1 << (bitmap_len - 1 - bit_pos)):
                    field_number = bit_pos + 1
                    # Skip bitmap indicators (field 1 for secondary, field 65 for tertiary)
                    if field_number not in (1, 65):
                        # Only add if field definition exists
                        if self._get_field_definition(field_number):
                            present_fields.append(field_number)

            return present_fields  # Already in order, no need to sort
        except ValueError:
            raise ParseError("Invalid bitmap format") from None

    def _get_field_definition(self, field_number: int) -> FieldDefinition | None:
        """Get field definition considering the spec, network and version"""
        if self._spec is not None and field_number in self._spec.fields:
            return self._spec.fields[field_number]
        # Check cached network-specific definitions first (avoids repeated dict.get())
        field_def = self._network_fields.get(field_number)
        if field_def is not None:
            return field_def

        # Check cached version-specific variations
        field_def = self._version_fields.get(field_number)
        if field_def is not None:
            return field_def

        # Default to standard ISO8583 fields
        return ISO8583_FIELDS.get(field_number)

    def _parse_field(self, field_number: int, field_def: FieldDefinition) -> str:
        """Parse field based on its definition"""
        try:
            # Use cached network-specific field definition if available, unless the spec has its own
            network_field_def = self._network_fields.get(field_number)
            if network_field_def is not None and (self._spec is None or field_number not in self._spec.fields):
                field_def = network_field_def

            value = self._handle_field_type(field_number, field_def)
            return self._handle_field_padding(field_number, value, field_def)

        except Exception as e:
            raise ParseError(f"Failed to parse field {field_number}: {str(e)}") from e

    def _parse_fixed_field(self, field_number: int, field_def: FieldDefinition) -> str:
        """Parse fixed length field"""
        field_length = field_def.max_length
        if field_def.field_type == FieldType.BINARY:
            field_length *= 2  # Double length for hex representation

        if self._current_position + field_length > len(self._raw_message):
            raise ParseError(f"Message too short for field {field_number}")

        value = self._raw_message[self._current_position : self._current_position + field_length]
        self._current_position += field_length

        # Handle numeric fields with left padding
        if field_def.field_type == FieldType.NUMERIC:
            if field_def.padding_char == "0":
                value = value.zfill(field_length)
            elif not value.isdigit():
                raise ParseError(f"Field {field_number} must contain only digits")

        # Handle special fixed-length fields
        if field_number in [41, 42]:
            return value  # Preserve padding for these fields

        # Remove padding if specified
        if field_def.padding_char:
            if field_def.padding_direction == "left":
                value = value.lstrip(field_def.padding_char)
                if field_def.field_type == FieldType.NUMERIC:
                    value = value.zfill(field_length)
            else:
                value = value.rstrip(field_def.padding_char)
                value = value.ljust(field_length, field_def.padding_char)

        return value

    def _parse_variable_field(self, field_number: int, field_def: FieldDefinition) -> str:
        """Parse variable length field"""
        try:
            # Handle fields that look like LLVAR but are fixed length
            if field_number in [41, 42]:
                return self._parse_fixed_field(field_number, field_def)

            # Get length indicator size
            length_indicator_size = 2 if field_def.field_type == FieldType.LLVAR else 3
            if self._current_position + length_indicator_size > len(self._raw_message):
                raise ParseError(f"Message too short for field {field_number} length indicator")

            # Get and validate length indicator
            length_str = self._raw_message[self._current_position : self._current_position + length_indicator_size]
            if not length_str.isdigit():
                if field_number in [41, 42]:  # Special handling for these fields
                    return self._parse_fixed_field(field_number, field_def)
                raise ParseError(f"Invalid length indicator format for field {field_number}: {length_str}")

            length = int(length_str)
            if length > field_def.max_length:
                raise ParseError(f"Length {length} exceeds maximum {field_def.max_length} for field {field_number}")

            self._current_position += length_indicator_size

            # Extract the value
            if self._current_position + length > len(self._raw_message):
                raise ParseError(f"Message too short for field {field_number} data")

            value = self._raw_message[self._current_position : self._current_position + length]
            self._current_position += length

            # Special field handling
            if field_number == 55:  # EMV data
                return value
            elif field_number in [44, 48, 55, 105]:  # Network-specific fields
                if self._detected_network:
                    return value

            return value

        except ValueError as e:
            raise ParseError(f"Invalid length value for field {field_number}: {str(e)}") from e
        except Exception as e:
            raise ParseError(f"Error parsing variable length field {field_number}: {str(e)}") from e

    def _parse_binary_field(self, field_number: int, field_def: FieldDefinition) -> str:
        """Parse binary field"""
        field_length = field_def.max_length * 2  # Each byte is 2 hex chars
        if self._current_position + field_length > len(self._raw_message):
            raise ParseError(f"Message too short for binary field {field_number}")

        value = self._raw_message[self._current_position : self._current_position + field_length]
        if not all(c in "0123456789ABCDEFabcdef" for c in value):
            raise ParseError(f"Invalid hex format in binary field {field_number}")

        self._current_position += field_length
        return value.upper()

    def _format_field_value(self, field_number: int, value: str, field_def: FieldDefinition) -> str:
        """Format field value based on type and rules"""
        try:
            # Handle specific fields first
            if field_number in [41, 42]:  # Terminal ID and Card Acceptor ID
                return value  # Preserve padding

            # Handle numeric fields with padding
            if field_def.field_type == FieldType.NUMERIC:
                if not value.isdigit():
                    raise ParseError(f"Field {field_number} must contain only digits")
                return value.zfill(field_def.max_length)

            # Handle binary fields
            if field_def.field_type == FieldType.BINARY:
                return value.upper()

            # Handle padding for fixed-length fields
            if field_def.field_type not in [FieldType.LLVAR, FieldType.LLLVAR]:
                if field_def.padding_char:
                    if field_def.padding_direction == "left":
                        return value.lstrip(field_def.padding_char)
                    return value.rstrip(field_def.padding_char)

            return value

        except Exception as e:
            raise ParseError(f"Failed to format field {field_number}: {str(e)}") from e

    def _parse_emv_data(self, value: str) -> str:
        """Parse EMV data"""
        # For field 55, return the raw EMV data
        return value

    def _detect_network(self, message: str) -> CardNetwork | None:
        """Detect card network from message contents"""
        try:
            # First look for LLVAR PAN (field 2)
            # Pattern: position after bitmap (20 or 36) + 2 digits length + 16-19 digits PAN
            bitmap_length = 36 if message[20:22].upper() == "C0" else 20
            pan_start = bitmap_length + 2  # Skip length indicator

            if len(message) > pan_start + 2:  # Ensure we have enough length
                pan_length = int(message[bitmap_length:pan_start])
                pan = message[pan_start : pan_start + pan_length]

                # subhadipmitra@: Share one PAN range table with the rest of the package so
                # detection rules (Discover, Mastercard 2-series) are defined in one place.
                network = detect_network_from_pan(pan)
                if network is not None:
                    return network

            # Look for network-specific patterns
            if "VISA" in message:
                return CardNetwork.VISA
            elif "MC" in message:
                return CardNetwork.MASTERCARD
            elif "AMEX" in message:
                return CardNetwork.AMEX

            return None

        except Exception as e:
            self.logger.warning("Network detection failed: %s", str(e))
            return None

    def _handle_field_padding(self, field_number: int, value: str, field_def: FieldDefinition) -> str:
        """Handle field padding based on field definition"""
        # Special handling for Terminal ID and Card Acceptor ID
        if field_number in [41, 42]:
            return value  # Preserve padding for these fields

        # Numeric fields are already handled in _parse_fixed_field - don't double-strip
        if field_def.field_type == FieldType.NUMERIC:
            return value

        # Handle fixed length fields
        if field_def.field_type not in [FieldType.LLVAR, FieldType.LLLVAR]:
            if field_def.padding_char:
                if field_def.padding_direction == "left":
                    value = value.lstrip(field_def.padding_char)
                else:
                    value = value.rstrip(field_def.padding_char)

        return value

    def _handle_field_type(self, field_number: int, field_def: FieldDefinition) -> str:
        """Handle field based on its type"""
        if field_def.field_type in [FieldType.LLVAR, FieldType.LLLVAR]:
            return self._parse_variable_field(field_number, field_def)
        elif field_def.field_type == FieldType.BINARY:
            return self._parse_binary_field(field_number, field_def)
        else:
            return self._parse_fixed_field(field_number, field_def)
