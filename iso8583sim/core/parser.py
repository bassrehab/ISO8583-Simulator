# iso8583sim/core/parser.py

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

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
    from .pool import MessagePool

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

    def __init__(self, version: ISO8583Version = ISO8583Version.V1987, pool: MessagePool | None = None):
        """
        Initialize the parser.

        Args:
            version: ISO8583 version to use
            pool: Optional MessagePool for object reuse in high-throughput scenarios
        """
        self.version = version
        self._pool = pool
        self._current_position = 0
        self._raw_message = ""
        self._detected_network = None
        self._secondary_bitmap = False
        self._network_fields = {}  # Cache for network-specific field definitions
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
                    field_def = get_field_definition(field_number, self._detected_network, self.version)

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
        """Get field definition considering network and version"""
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
            # Use cached network-specific field definition if available
            network_field_def = self._network_fields.get(field_number)
            if network_field_def is not None:
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

                if pan.startswith("4"):
                    return CardNetwork.VISA
                elif any(pan.startswith(prefix) for prefix in ["51", "52", "53", "54", "55"]):
                    return CardNetwork.MASTERCARD
                elif any(pan.startswith(prefix) for prefix in ["34", "37"]):
                    return CardNetwork.AMEX
                elif pan.startswith("62"):
                    return CardNetwork.UNIONPAY
                elif pan.startswith("35"):
                    return CardNetwork.JCB

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

    def _handle_network_specific(self, field_number: int, value: str) -> str:
        """Apply network-specific formatting rules"""
        if not self._detected_network:
            return value

        if self._detected_network == CardNetwork.VISA:
            # VISA-specific formatting
            if field_number == 44:  # Additional Response Data
                if not all(c in "0123456789ABCDEF" for c in value.upper()):
                    raise ParseError(f"Invalid VISA field 44 format: {value}")
                return value.upper()
            elif field_number == 48:  # Private Data
                if not value.startswith("VISA"):
                    return f"VISA{value}"
                return value
        elif self._detected_network == CardNetwork.MASTERCARD:
            # Mastercard-specific formatting
            if field_number == 48:  # Private Data
                if not value.startswith("MC"):
                    return f"MC{value}"
                return value
            elif field_number == 55:  # EMV Data
                value = self._parse_emv_data(value)
                if not value.startswith("9F"):
                    raise ParseError("Invalid MC EMV data format")
                return value

        return value

    def _validate_field_content(self, field_number: int, value: str, field_def: FieldDefinition) -> None:
        """Validate field content format"""
        # Validate field length
        if field_def.field_type not in [FieldType.LLVAR, FieldType.LLLVAR]:
            expected_length = field_def.max_length
            if field_def.field_type == FieldType.BINARY:
                expected_length *= 2  # Each byte is 2 hex chars
            if len(value) != expected_length:
                raise ParseError(
                    f"Field {field_number} has incorrect length: " f"got {len(value)}, expected {expected_length}"
                )

        # Validate content type
        if field_def.field_type == FieldType.NUMERIC:
            if not value.isdigit():
                raise ParseError(f"Field {field_number} must contain only digits")
        elif field_def.field_type == FieldType.BINARY:
            if not all(c in "0123456789ABCDEFabcdef" for c in value):
                raise ParseError(f"Field {field_number} must contain valid hexadecimal")
        elif field_def.field_type == FieldType.ALPHA:
            if not value.replace(" ", "").isalpha():
                raise ParseError(f"Field {field_number} must contain only letters")
        elif field_def.field_type == FieldType.ALPHANUMERIC:
            if not value.replace(" ", "").isalnum():
                raise ParseError(f"Field {field_number} must contain only letters and numbers")

    def _parse_length_indicator(self, field_number: int, indicator_size: int) -> int:
        """Parse and validate length indicator for variable length fields"""
        if self._current_position + indicator_size > len(self._raw_message):
            raise ParseError(f"Message too short for field {field_number} length indicator")

        length_str = self._raw_message[self._current_position : self._current_position + indicator_size]

        if not length_str.isdigit():
            raise ParseError(f"Invalid length indicator for field {field_number}: {length_str}")

        return int(length_str)

    def _calculate_field_length(self, field_number: int, base_length: int, field_def: FieldDefinition) -> int:
        """Calculate total field length including any special handling"""
        # For variable length fields, base_length is from length indicator
        if field_def.field_type in [FieldType.LLVAR, FieldType.LLLVAR]:
            if base_length > field_def.max_length:
                raise ParseError(
                    f"Field {field_number} length {base_length} " f"exceeds maximum {field_def.max_length}"
                )
            return base_length

        # For binary fields, each byte is represented by 2 hex characters
        if field_def.field_type == FieldType.BINARY:
            return field_def.max_length * 2

        # For fixed length fields, use max_length from definition
        return field_def.max_length

    def _process_emv_field(self, value: str) -> str:
        """Process EMV data field (field 55)"""
        try:
            return self._parse_emv_data(value)
        except Exception as e:
            self.logger.warning("EMV parsing error: %s", str(e))
            return value

    def _process_bitmap_fields(self, bitmap: str) -> list[tuple[int, int]]:
        """Process bitmap and return list of (field_number, field_position) tuples"""
        bitmap_bits = bin(int(bitmap, 16))[2:].zfill(len(bitmap) * 4)
        field_positions = []

        current_position = self._current_position
        for i, bit in enumerate(bitmap_bits):
            if bit == "1" and i + 1 not in [1, 65]:  # Skip bitmap indicators
                field_positions.append((i + 1, current_position))

        return field_positions

    def _handle_version_specific(self, field_def: FieldDefinition, field_number: int) -> FieldDefinition:
        """Apply version-specific field modifications"""
        if not field_def:
            return field_def

        # Handle version-specific field variations
        if self.version != ISO8583Version.V1987:
            version_fields = VERSION_SPECIFIC_FIELDS.get(self.version, {})
            if field_number in version_fields:
                return version_fields[field_number]

        return field_def

    def _handle_field_type(self, field_number: int, field_def: FieldDefinition) -> str:
        """Handle field based on its type"""
        if field_def.field_type in [FieldType.LLVAR, FieldType.LLLVAR]:
            return self._parse_variable_field(field_number, field_def)
        elif field_def.field_type == FieldType.BINARY:
            return self._parse_binary_field(field_number, field_def)
        else:
            return self._parse_fixed_field(field_number, field_def)
