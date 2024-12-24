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

            # Parse MTI
            mti = self._parse_mti()
            self.logger.debug("Parsed MTI: %s", mti)

            # Parse bitmap
            bitmap = self._parse_bitmap()
            self.logger.debug("Parsed bitmap: %s", bitmap)
            present_fields = self._get_present_fields(bitmap)
            self.logger.debug("Present fields: %s", present_fields)

            # Detect network if not provided
            self._detected_network = network or self._detect_network(message)
            self.logger.info("Processing message for network: %s",
                             self._detected_network.value if self._detected_network else "Unknown")

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
            try:
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

            except ValueError:
                raise ParseError("Invalid bitmap format - must be hexadecimal")

        except Exception as e:
            raise ParseError(f"Failed to parse bitmap: {str(e)}")

    def _get_present_fields(self, bitmap: str) -> List[int]:
        """
        Determine which fields are present based on bitmap
        Returns list of field numbers present in message
        """
        try:
            # Convert hex string to binary
            bitmap_int = int(bitmap, 16)
            bitmap_bin = format(bitmap_int, f'0{len(bitmap) * 4}b')

            # Check each bit
            present_fields = []
            for i in range(len(bitmap_bin)):
                if bitmap_bin[i] == '1':
                    field_number = i + 1  # Bitmap positions start at 1
                    present_fields.append(field_number)

            return sorted(present_fields)

        except ValueError:
            raise ParseError("Invalid bitmap format")
        except Exception as e:
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
        """Parse individual field"""
        try:
            # Get field value based on type
            value = None

            if field_def.field_type in [FieldType.LLVAR, FieldType.LLLVAR]:
                # Variable length field
                length_indicator_size = 2 if field_def.field_type == FieldType.LLVAR else 3
                if self._current_position + length_indicator_size > len(self._raw_message):
                    raise ParseError(f"Message too short for field {field_number} length indicator")

                length = int(self._raw_message[
                             self._current_position:self._current_position + length_indicator_size
                             ])
                self._current_position += length_indicator_size

                if self._current_position + length > len(self._raw_message):
                    raise ParseError(f"Message too short for field {field_number} data")

                value = self._raw_message[self._current_position:self._current_position + length]
                self._current_position += length
            else:
                # Fixed length field
                if self._current_position + field_def.max_length > len(self._raw_message):
                    raise ParseError(f"Message too short for field {field_number}")

                field_length = field_def.max_length
                if field_def.field_type == FieldType.BINARY:
                    field_length *= 2  # Double length for hex representation

                value = self._raw_message[
                        self._current_position:self._current_position + field_length
                        ]
                self._current_position += field_length

            # Preserve padding based on field definition
            if value is not None:
                if field_def.field_type == FieldType.NUMERIC:
                    # Always preserve numeric field padding
                    return value
                elif field_def.field_type == FieldType.BINARY:
                    # Always preserve binary field as is
                    return value
                elif field_def.padding_char:
                    if field_def.padding_direction == 'left':
                        return value.lstrip(field_def.padding_char)
                    else:
                        return value.rstrip(field_def.padding_char)

                # Handle specific fields
                if field_number == 41:  # Terminal ID
                    return value.rstrip()
                elif field_number == 42:  # Card Acceptor ID
                    return value.rstrip()
                elif field_number == 44:  # Additional Response Data
                    return value.strip()

            return value

        except Exception as e:
            raise ParseError(f"Failed to parse field {field_number}: {str(e)}")

    def _parse_emv_data(self, data: str) -> str:
        """Parse EMV data field"""
        if not data:
            return ""

        try:
            position = 0
            parsed_data = []

            while position < len(data):
                # Need at least 4 chars for tag and length
                if position + 4 > len(data):
                    raise ParseError("Incomplete EMV data")

                # Parse tag
                tag = data[position:position + 2]
                if not all(c in '0123456789ABCDEF' for c in tag):
                    raise ParseError(f"Invalid tag format: {tag}")
                position += 2

                # Parse length
                length_hex = data[position:position + 2]
                try:
                    length = int(length_hex, 16)
                except ValueError:
                    raise ParseError(f"Invalid length format for tag {tag}")
                position += 2

                # Parse value
                value_length = length * 2  # Each byte is 2 hex chars
                if position + value_length > len(data):
                    raise ParseError(f"Incomplete value for tag {tag}")

                value = data[position:position + value_length]
                position += value_length

                parsed_data.append(f"{tag}{length_hex}{value}")

            return "".join(parsed_data)

        except Exception as e:
            raise ParseError(f"Failed to parse EMV data: {str(e)}")


    def _format_field_value(self, field_number: int, value: str, field_def: FieldDefinition) -> str:
        """Format field value based on definition"""
        # Remove padding if specified
        if field_def.padding_char:
            if field_def.padding_direction == 'left':
                value = value.lstrip(field_def.padding_char)
            else:
                value = value.rstrip(field_def.padding_char)

        # Format based on field type
        if field_def.field_type == FieldType.BINARY:
            value = value.upper()
        elif field_def.field_type == FieldType.NUMERIC:
            if not value.isdigit():
                raise ParseError(f"Field {field_number} must contain only digits")
        elif field_def.field_type == FieldType.ALPHA:
            if not value.replace(' ', '').isalpha():
                raise ParseError(f"Field {field_number} must contain only letters")
        elif field_def.field_type == FieldType.ALPHANUMERIC:
            if not value.replace(' ', '').isalnum():
                raise ParseError(f"Field {field_number} must contain only letters and numbers")

        return value

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
        """Detect card network from message contents"""
        try:
            # First check for network-specific patterns
            for field_start in range(len(message)):
                if field_start + 2 >= len(message):
                    break

                # Look for PAN (starts with length indicator)
                if message[field_start:field_start + 2].isdigit():
                    length = int(message[field_start:field_start + 2])
                    if field_start + 2 + length <= len(message):
                        pan = message[field_start + 2:field_start + 2 + length]

                        # Check PAN prefixes
                        if pan.startswith('4'):
                            return CardNetwork.VISA
                        elif any(pan.startswith(prefix) for prefix in ['51', '52', '53', '54', '55']):
                            return CardNetwork.MASTERCARD
                        elif any(pan.startswith(prefix) for prefix in ['34', '37']):
                            return CardNetwork.AMEX
                        elif pan.startswith('62'):
                            return CardNetwork.UNIONPAY
                        elif pan.startswith('35'):
                            return CardNetwork.JCB

                # Check for network-specific fields
                if 'MC' in message[field_start:field_start + 4]:
                    return CardNetwork.MASTERCARD
                elif 'VISA' in message[field_start:field_start + 6]:
                    return CardNetwork.VISA

            return None

        except Exception as e:
            self.logger.warning(f"Failed to detect network: {str(e)}")
            return None

    def parse_file(self, filename: str) -> List[ISO8583Message]:
        """Parse multiple messages from file"""
        self.logger.info(f"Starting to parse messages from file: {filename}")
        messages = []

        try:
            with open(filename, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        self.logger.debug(f"Parsing message from line {line_num}")
                        # Reset parser state for each message
                        self._current_position = 0
                        self._raw_message = line
                        message = self.parse(line)
                        messages.append(message)
                        self.logger.info(f"Successfully parsed message {line_num}")
                    except Exception as e:
                        self.logger.error(f"Failed to parse message at line {line_num}: {str(e)}")
                        # Don't raise, continue with next message
                        continue

            self.logger.info(f"Successfully parsed {len(messages)} messages from file")
            return messages

        except Exception as e:
            self.logger.error(f"Error reading file: {str(e)}")
            raise ParseError(f"Failed to read messages file: {str(e)}")



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
