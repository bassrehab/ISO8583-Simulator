# iso8583sim/core/parser.py

import logging
from typing import Dict, Optional, List

from .types import (
    ISO8583Message,
    FieldType,
    FieldDefinition,
    ParseError,
    ISO8583Version,
    CardNetwork,
    get_field_definition
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class ISO8583Parser:
    """Parser for ISO 8583 messages with network support"""

    def __init__(self, version: ISO8583Version = ISO8583Version.V1987):
        self.version = version
        self._current_position = 0
        self._raw_message = ""
        self._detected_network = None
        self._secondary_bitmap = False
        # Initialize logger with class-specific name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.debug("Initialized ISO8583Parser with version %s", version.value)

    def parse(self, message: str, network: Optional[CardNetwork] = None) -> ISO8583Message:
        """Parse an ISO 8583 message string into an ISO8583Message object"""
        try:
            self._raw_message = message
            self._current_position = 0
            self._detected_network = network or self._detect_network(message)

            # Log parsing attempt
            self.logger.info("Starting to parse message with network: %s",
                             self._detected_network.value if self._detected_network else "Unknown")
            self.logger.debug("Raw message: %s", message)

            # Parse MTI
            mti = self._parse_mti()
            self.logger.debug("Parsed MTI: %s", mti)

            # Parse bitmap
            bitmap = self._parse_bitmap()
            self.logger.debug("Parsed bitmap: %s", bitmap)
            present_fields = self._get_present_fields(bitmap)
            self.logger.debug("Present fields: %s", present_fields)

            # Parse data fields
            fields = {0: mti}  # MTI is field 0
            for field_number in present_fields:
                try:
                    field_def = get_field_definition(
                        field_number,
                        self._detected_network,
                        self.version
                    )

                    if field_def is None:
                        self.logger.warning("No definition found for field %d", field_number)
                        continue

                    value = self._parse_field(field_number, field_def)
                    if value is not None:
                        fields[field_number] = value
                        self.logger.debug("Parsed field %d: %s", field_number, value)

                except Exception as e:
                    self.logger.error("Error parsing field %d: %s", field_number, str(e))
                    raise

            message = ISO8583Message(
                mti=mti,
                fields=fields,
                version=self.version,
                network=self._detected_network,
                raw_message=message,
                bitmap=bitmap
            )

            self.logger.info("Successfully parsed message")
            return message

        except Exception as e:
            self.logger.error("Failed to parse message: %s", str(e))
            raise ParseError(f"Failed to parse message: {str(e)}")

    def _parse_mti(self) -> str:
        """
        Parse Message Type Indicator (4 digits)

        Returns:
            str: 4-digit MTI

        Raises:
            ParseError: If MTI is invalid or message is too short
        """
        try:
            if len(self._raw_message) < self._current_position + 4:
                raise ParseError("Message too short for MTI")

            mti = self._raw_message[self._current_position:self._current_position + 4]

            if not mti.isdigit():
                raise ParseError("Invalid MTI format - must be numeric")

            self._current_position += 4
            return mti

        except Exception as e:
            raise ParseError(f"Failed to parse MTI: {str(e)}")

    def _parse_bitmap(self) -> str:
        """
        Parse primary and secondary bitmaps
        Returns bitmap as hexadecimal string
        """
        try:
            if len(self._raw_message) < self._current_position + 16:
                raise ParseError("Message too short for bitmap")

            # Get primary bitmap
            primary_bitmap = self._raw_message[self._current_position:self._current_position + 16]
            self._current_position += 16

            # Check if secondary bitmap is present (bit 1)
            bitmap_value = int(primary_bitmap, 16)
            self._secondary_bitmap = bool(bitmap_value & 0x8000000000000000)

            if self._secondary_bitmap:
                if len(self._raw_message) < self._current_position + 16:
                    raise ParseError("Message too short for secondary bitmap")

                # Get secondary bitmap
                secondary_bitmap = self._raw_message[self._current_position:self._current_position + 16]
                self._current_position += 16
                return primary_bitmap + secondary_bitmap

            return primary_bitmap

        except ValueError as e:
            raise ParseError(f"Invalid bitmap format: {str(e)}")
        except Exception as e:
            raise ParseError(f"Failed to parse bitmap: {str(e)}")

    def _get_present_fields(self, bitmap: str) -> List[int]:
        """
        Determine which fields are present based on bitmap

        Args:
            bitmap: Hexadecimal bitmap string

        Returns:
            List of field numbers present in message
        """
        try:
            # Convert hex string to binary string
            binary = bin(int(bitmap, 16))[2:].zfill(len(bitmap) * 4)

            # Check each bit
            present_fields = []
            for i in range(len(binary)):
                if binary[i] == '1':
                    field_number = i + 1  # Bitmap positions start at 1
                    if field_number != 1 or len(bitmap) == 32:  # Include field 1 only for secondary bitmap
                        present_fields.append(field_number)

            # Sort fields for consistent order
            return sorted(present_fields)

        except Exception as e:
            self.logger.error("Failed to process bitmap: %s", str(e))
            raise ParseError(f"Failed to process bitmap: {str(e)}")

    def _validate_emv_format(self, value: str) -> bool:
        """Validate basic EMV data format"""
        try:
            if not value or len(value) < 4:  # Minimum: 2 chars tag + 2 chars length
                return False

            position = 0
            while position < len(value):
                # Check if enough characters remain for tag and length
                if position + 4 > len(value):
                    return False

                # Check tag format (2 characters)
                tag = value[position:position + 2]
                if not all(c in '0123456789ABCDEFabcdef' for c in tag):
                    return False

                position += 2

                # Check length format (2 characters)
                length_str = value[position:position + 2]
                if not all(c in '0123456789ABCDEFabcdef' for c in length_str):
                    return False

                # Convert length from hex to int
                length = int(length_str, 16) * 2  # Each byte is 2 hex chars
                position += 2

                # Check if enough data remains
                if position + length > len(value):
                    return False

                position += length

            return position == len(value)

        except Exception:
            return False

    def _parse_field(self, field_number: int, field_def: FieldDefinition) -> Optional[str]:
        """
        Parse individual field based on its definition

        Args:
            field_number: Field number to parse
            field_def: Field definition

        Returns:
            Parsed field value or None if field should be skipped
        """
        try:
            if field_def.field_type in [FieldType.LLVAR, FieldType.LLLVAR]:
                # Variable length field
                length_indicator_size = 2 if field_def.field_type == FieldType.LLVAR else 3

                if len(self._raw_message) < self._current_position + length_indicator_size:
                    raise ParseError(f"Message too short for field {field_number} length indicator")

                length = int(self._raw_message[
                             self._current_position:self._current_position + length_indicator_size
                             ])
                self._current_position += length_indicator_size

                if len(self._raw_message) < self._current_position + length:
                    raise ParseError(f"Message too short for field {field_number} data")

                value = self._raw_message[self._current_position:self._current_position + length]
                self._current_position += length

            else:
                # Fixed length field
                if len(self._raw_message) < self._current_position + field_def.max_length:
                    raise ParseError(f"Message too short for field {field_number}")

                value = self._raw_message[
                        self._current_position:self._current_position + field_def.max_length
                        ]
                self._current_position += field_def.max_length

                # Handle padding
                if field_def.padding_char:
                    if field_def.padding_direction == 'left':
                        value = value.lstrip(field_def.padding_char)
                    else:
                        value = value.rstrip(field_def.padding_char)

            # Special field formatting
            if field_def.field_type == FieldType.BINARY:
                # Ensure proper hex format
                if not all(c in '0123456789ABCDEFabcdef' for c in value):
                    raise ParseError(f"Invalid binary data format in field {field_number}")
                value = value.upper()

            elif field_number == 55:  # EMV data
                # Validate basic EMV format
                if not self._validate_emv_format(value):
                    raise ParseError(f"Invalid EMV data format in field {field_number}")

            return value

        except Exception as e:
            raise ParseError(f"Failed to parse field {field_number}: {str(e)}")


    def _format_field_value(self, field_number: int, value: str, field_def: FieldDefinition) -> str:
        """Format field value based on type and rules"""
        try:
            # Handle binary fields
            if field_def.field_type == FieldType.BINARY:
                # Ensure valid hex format
                try:
                    int(value, 16)
                    return value.upper()
                except ValueError:
                    raise ParseError(f"Invalid binary format for field {field_number}")

            # Handle network-specific formatting
            if self._detected_network:
                value = self._apply_network_formatting(field_number, value)

            # Remove padding if specified
            if field_def.padding_char:
                if field_def.padding_direction == 'left':
                    value = value.lstrip(field_def.padding_char)
                else:
                    value = value.rstrip(field_def.padding_char)

            return value

        except Exception as e:
            raise ParseError(f"Failed to format field {field_number}: {str(e)}")

    def _apply_network_formatting(self, field_number: int, value: str) -> str:
        """Apply network-specific field formatting"""
        if not self._detected_network:
            return value

        # VISA specific formatting
        if self._detected_network == CardNetwork.VISA:
            if field_number == 44:  # Additional Response Data
                return value.upper()
            elif field_number == 54:  # Amounts, Additional
                return value.zfill(12)

        # Mastercard specific formatting
        elif self._detected_network == CardNetwork.MASTERCARD:
            if field_number == 48:  # Additional Data
                return value.strip()
            elif field_number == 55:  # ICC Data
                return value.upper()

        return value

    def _detect_network(self, message: str) -> Optional[CardNetwork]:
        """
        Attempt to detect card network from message contents

        Args:
            message: Full message string

        Returns:
            Detected CardNetwork or None
        """
        try:
            # Check if network was explicitly provided
            if self._detected_network:
                return self._detected_network

            # Extract PAN if present (after MTI and bitmap)
            if len(message) > 36:  # Minimum length for message with PAN
                potential_pan_start = 20  # After MTI(4) + Primary Bitmap(16)
                potential_pan = message[potential_pan_start:potential_pan_start + 19]

                # Check PAN patterns
                if potential_pan.startswith('4'):
                    return CardNetwork.VISA
                elif any(potential_pan.startswith(prefix) for prefix in ['51', '52', '53', '54', '55']):
                    return CardNetwork.MASTERCARD
                elif any(potential_pan.startswith(prefix) for prefix in ['34', '37']):
                    return CardNetwork.AMEX
                elif potential_pan.startswith('62'):
                    return CardNetwork.UNIONPAY
                elif potential_pan.startswith('35'):
                    return CardNetwork.JCB

            return None

        except Exception as e:
            self.logger.warning("Failed to detect network: %s", str(e))
            return None

    def parse_file(self, filename: str) -> List[ISO8583Message]:
        """Parse multiple messages from a file"""
        self.logger.info("Starting to parse messages from file: %s", filename)
        messages = []

        try:
            with open(filename, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            self.logger.debug("Parsing message from line %d", line_num)
                            message = self.parse(line)
                            messages.append(message)
                        except ParseError as e:
                            self.logger.error("Failed to parse message at line %d: %s",
                                              line_num, str(e))
                            # Continue parsing other messages
                            continue

            self.logger.info("Successfully parsed %d messages from file", len(messages))
            return messages

        except Exception as e:
            self.logger.error("Error reading file %s: %s", filename, str(e))
            raise

    def parse_emv_data(self, emv_data: str) -> Dict[str, str]:
        """
        Parse EMV data field (field 55)

        Args:
            emv_data: EMV data string

        Returns:
            Dictionary of EMV tags and values
        """
        if not emv_data:
            return {}

        result = {}
        position = 0

        while position < len(emv_data):
            # Parse tag
            if position + 2 > len(emv_data):
                break

            tag = emv_data[position:position + 2]
            position += 2

            # Parse length
            if position + 2 > len(emv_data):
                break

            try:
                length = int(emv_data[position:position + 2], 16)
                position += 2

                # Parse value
                if position + (length * 2) > len(emv_data):
                    break

                value = emv_data[position:position + (length * 2)]
                position += length * 2

                result[tag] = value

            except ValueError:
                break

        return result
