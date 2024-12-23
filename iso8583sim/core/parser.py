# iso8583sim/core/parser.py

from typing import Dict, Optional, Tuple, List, Any
import binascii
from datetime import datetime
import re
from .types import (
    ISO8583Message,
    ISO8583_FIELDS,
    FieldType,
    FieldDefinition,
    ParseError,
    ISO8583Version,
    CardNetwork,
    NETWORK_SPECIFIC_FIELDS,
    VERSION_SPECIFIC_FIELDS,
    get_field_definition
)


class ISO8583Parser:
    """Parser for ISO 8583 messages with network support"""

    def __init__(self, version: ISO8583Version = ISO8583Version.V1987):
        self.version = version
        self._current_position = 0
        self._raw_message = ""
        self._detected_network = None
        self._secondary_bitmap = False

    def parse(self, message: str, network: Optional[CardNetwork] = None) -> ISO8583Message:
        """
        Parse an ISO 8583 message string into an ISO8583Message object

        Args:
            message: Raw ISO 8583 message string
            network: Optional card network for specific parsing rules

        Returns:
            ISO8583Message object

        Raises:
            ParseError: If message cannot be parsed
        """
        try:
            self._raw_message = message
            self._current_position = 0
            self._detected_network = network or self._detect_network(message)

            # Parse MTI
            mti = self._parse_mti()

            # Parse bitmap
            bitmap = self._parse_bitmap()
            present_fields = self._get_present_fields(bitmap)

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
                        self.logger.warning(f"No definition found for field {field_number}")
                        continue

                    value = self._parse_field(field_number, field_def)
                    if value is not None:
                        fields[field_number] = value

                except Exception as e:
                    self.logger.error(f"Error parsing field {field_number}: {str(e)}")
                    raise

            return ISO8583Message(
                mti=mti,
                fields=fields,
                version=self.version,
                network=self._detected_network,
                raw_message=message,
                bitmap=bitmap
            )

        except Exception as e:
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
        Returns combined bitmap as hexadecimal string
        """
        if len(self._raw_message) < self._current_position + 16:
            raise ParseError("Message too short for bitmap")

        # Get primary bitmap
        primary_bitmap = self._raw_message[self._current_position:self._current_position + 16]
        self._current_position += 16

        try:
            # Check if secondary bitmap is present (first bit)
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

    def _get_present_fields(self, bitmap: str) -> List[int]:
        """
        Determine which fields are present based on bitmap

        Args:
            bitmap: Hexadecimal bitmap string

        Returns:
            List of field numbers present in message
        """
        try:
            # Convert hex string to binary string, properly handling length
            binary = bin(int(bitmap, 16))[2:].zfill(len(bitmap) * 4)

            # Check each bit
            present_fields = []
            for i in range(len(binary)):
                if binary[i] == '1':
                    field_number = i + 1  # Bitmap positions start at 1
                    # Skip secondary bitmap indicator (bit 1)
                    if i != 0 or len(bitmap) == 32:  # Include field 1 only for secondary bitmap
                        present_fields.append(field_number)

            return sorted(present_fields)

        except Exception as e:
            raise ParseError(f"Failed to process bitmap: {str(e)}")

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

            # Special field handling
            if field_number == 52 and field_def.field_type == FieldType.BINARY:
                # Ensure proper hex format for binary data
                if not all(c in '0123456789ABCDEFabcdef' for c in value):
                    raise ParseError(f"Invalid binary data format in field {field_number}")
                value = value.upper()

            elif field_number == 55:  # EMV data
                # Validate basic EMV format
                if len(value) % 2 != 0:
                    raise ParseError("Invalid EMV data length")

            # Remove padding if specified
            if field_def.padding_char:
                if field_def.padding_direction == 'left':
                    value = value.lstrip(field_def.padding_char)
                else:
                    value = value.rstrip(field_def.padding_char)

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

    def _detect_network(self, mti: str) -> Optional[CardNetwork]:
        """
        Attempt to detect card network from message

        Args:
            mti: Message Type Indicator

        Returns:
            Detected CardNetwork or None
        """
        # Check PAN prefix if present
        if len(self._raw_message) > 20:  # Minimum length for message with PAN
            pan_data = self._raw_message[20:35]  # Approximate position after bitmap

            # VISA starts with 4
            if pan_data.startswith('4'):
                return CardNetwork.VISA
            # Mastercard starts with 51-55
            elif pan_data.startswith(('51', '52', '53', '54', '55')):
                return CardNetwork.MASTERCARD
            # AMEX starts with 34 or 37
            elif pan_data.startswith(('34', '37')):
                return CardNetwork.AMEX
            # Discover starts with 6011, 644-649, or 65
            elif pan_data.startswith(('6011', '644', '645', '646', '647', '648', '649', '65')):
                return CardNetwork.DISCOVER
            # JCB starts with 35
            elif pan_data.startswith('35'):
                return CardNetwork.JCB
            # UnionPay starts with 62
            elif pan_data.startswith('62'):
                return CardNetwork.UNIONPAY

        return None

    def parse_file(self, filename: str, network: Optional[CardNetwork] = None) -> List[ISO8583Message]:
        """
        Parse multiple messages from a file

        Args:
            filename: Path to file containing messages
            network: Optional card network for specific parsing rules

        Returns:
            List of parsed ISO8583Message objects
        """
        messages = []
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    try:
                        message = self.parse(line, network)
                        messages.append(message)
                    except ParseError as e:
                        # Log error but continue parsing
                        print(f"Failed to parse message: {str(e)}")

        return messages


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
