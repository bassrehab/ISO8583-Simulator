# iso8583sim/core/builder.py

from typing import Dict, Optional, List
import binascii
from datetime import datetime
import re

from .types import (
    ISO8583Message,
    ISO8583_FIELDS,
    FieldType,
    BuildError,
    ISO8583Version,
    CardNetwork,
    MessageFunction,
    get_field_definition
)
from .validator import ISO8583Validator


class ISO8583Builder:
    """Builder for creating ISO 8583 messages with network support"""

    def __init__(self, version: ISO8583Version = ISO8583Version.V1987):
        self.version = version
        self.validator = ISO8583Validator()

    def build(self, message: ISO8583Message) -> str:
        """
        Build raw ISO 8583 message string from message object

        Args:
            message: ISO8583Message object to build

        Returns:
            Raw message string

        Raises:
            BuildError: If message cannot be built
        """
        try:
            # Validate message first
            errors = self.validator.validate_message(message)
            if errors:
                raise BuildError(f"Validation failed: {'; '.join(errors)}")

            # Build MTI
            result = message.mti

            # Build bitmap
            bitmap = self._build_bitmap(message.fields)
            result += bitmap

            # Build data fields in order
            present_fields = sorted(
                [f for f in message.fields.keys() if f != 0]  # Exclude MTI
            )

            for field_number in present_fields:
                field_def = get_field_definition(
                    field_number,
                    message.network,
                    message.version
                )
                if field_def:
                    field_data = self._build_field(
                        field_number,
                        message.fields[field_number],
                        field_def
                    )
                    result += field_data

            return result

        except Exception as e:
            raise BuildError(f"Failed to build message: {str(e)}")

    def _build_bitmap(self, fields: Dict[int, str]) -> str:
        """
        Build bitmap from present fields
        Returns bitmap as hexadecimal string
        """
        try:
            # Initialize bitmap arrays (primary and secondary)
            primary = ['0'] * 64
            secondary = ['0'] * 64

            # Mark present fields
            need_secondary = False
            for field_number in fields.keys():
                if field_number == 0:  # Skip MTI
                    continue

                if 1 <= field_number <= 64:
                    primary[field_number - 1] = '1'
                elif 65 <= field_number <= 128:
                    secondary[field_number - 65] = '1'
                    need_secondary = True

            if need_secondary:
                # Set first bit in primary bitmap
                primary[0] = '1'

                # Convert both bitmaps
                primary_hex = hex(int(''.join(primary), 2))[2:].upper().zfill(16)
                secondary_hex = hex(int(''.join(secondary), 2))[2:].upper().zfill(16)

                return primary_hex + secondary_hex
            else:
                # Convert only primary bitmap
                return hex(int(''.join(primary), 2))[2:].upper().zfill(16)

        except Exception as e:
            raise BuildError(f"Failed to build bitmap: {str(e)}")

    def _build_field(
            self,
            field_number: int,
            value: str,
            field_def: Optional[Dict] = None
    ) -> str:
        """
        Build individual field based on its definition

        Args:
            field_number: Field number to build
            value: Field value
            field_def: Optional field definition override

        Returns:
            Formatted field value
        """
        try:
            if not field_def:
                field_def = get_field_definition(field_number)
                if not field_def:
                    raise BuildError(f"No definition for field {field_number}")

            # Apply field-specific formatting
            formatted_value = self._format_field_value(field_number, value, field_def)

            if field_def.field_type in [FieldType.LLVAR, FieldType.LLLVAR]:
                # Variable length field
                length = len(formatted_value)
                length_indicator_size = 2 if field_def.field_type == FieldType.LLVAR else 3

                if length > field_def.max_length:
                    raise BuildError(
                        f"Value too long for field {field_number}: "
                        f"{length} > {field_def.max_length}"
                    )

                length_str = str(length).zfill(length_indicator_size)
                return length_str + formatted_value

            else:
                # Fixed length field
                if len(formatted_value) != field_def.max_length:
                    # Apply padding if defined
                    if field_def.padding_char:
                        if field_def.padding_direction == 'left':
                            formatted_value = formatted_value.rjust(
                                field_def.max_length,
                                field_def.padding_char
                            )
                        else:
                            formatted_value = formatted_value.ljust(
                                field_def.max_length,
                                field_def.padding_char
                            )
                    else:
                        raise BuildError(
                            f"Invalid length for field {field_number}: "
                            f"expected {field_def.max_length}, got {len(formatted_value)}"
                        )

                return formatted_value

        except Exception as e:
            raise BuildError(f"Failed to build field {field_number}: {str(e)}")

    def _format_field_value(
            self,
            field_number: int,
            value: str,
            field_def: Dict
    ) -> str:
        """Format field value based on type and rules"""
        try:
            # Handle binary fields
            if field_def.field_type == FieldType.BINARY:
                try:
                    # Ensure valid hex format
                    int(value, 16)
                    return value.upper()
                except ValueError:
                    raise BuildError(f"Invalid binary format for field {field_number}")

            # Apply basic type formatting
            if field_def.field_type == FieldType.NUMERIC:
                if not value.isdigit():
                    raise BuildError(f"Field {field_number} must contain only digits")

            elif field_def.field_type == FieldType.ALPHA:
                if not value.isalpha():
                    raise BuildError(f"Field {field_number} must contain only letters")

            # Special field formatting
            if field_number == 2:  # PAN
                return self._format_pan(value)
            elif field_number == 35:  # Track 2
                return self._format_track2(value)
            elif field_number == 55:  # ICC Data
                return self._format_icc_data(value)

            return value

        except Exception as e:
            raise BuildError(f"Failed to format field {field_number}: {str(e)}")

    def _format_pan(self, pan: str) -> str:
        """Format PAN field"""
        # Remove any spaces or separators
        return ''.join(filter(str.isdigit, pan))

    def _format_track2(self, track2: str) -> str:
        """Format Track 2 data"""
        # Ensure proper format (PAN=YYMMServiceCode...)
        if '=' not in track2:
            raise BuildError("Track 2 data must contain separator '='")
        return track2

    def _format_icc_data(self, icc_data: str) -> str:
        """Format ICC (EMV) data"""
        # Ensure hex format
        try:
            int(icc_data, 16)
            return icc_data.upper()
        except ValueError:
            raise BuildError("ICC data must be in hexadecimal format")

    def create_message(self, mti: str, fields: Dict[int, str]) -> ISO8583Message:
        """
        Create an ISO8583Message object with validation

        Args:
            mti: Message Type Indicator
            fields: Dictionary of field numbers and values

        Returns:
            Validated ISO8583Message object
        """
        # Create message object
        message = ISO8583Message(
            mti=mti,
            fields=fields,
            version=self.version
        )

        # Validate
        errors = self.validator.validate_message(message)
        if errors:
            raise BuildError(f"Message validation failed: {'; '.join(errors)}")

        # Build raw message
        raw_message = self.build(message)
        message.raw_message = raw_message

        return message

    def create_response(
            self,
            request: ISO8583Message,
            response_fields: Dict[int, str]
    ) -> ISO8583Message:
        """
        Create a response message based on a request message

        Args:
            request: Original request message
            response_fields: Fields specific to response

        Returns:
            Response message
        """
        # Create response MTI
        req_mti = request.mti
        resp_mti = list(req_mti)
        resp_mti[2] = MessageFunction.RESPONSE.value
        response_mti = ''.join(resp_mti)

        # Copy necessary fields from request
        response_fields = response_fields.copy()
        # Fields that should be copied from request to response
        copy_fields = [2, 3, 4, 11, 37, 41, 42]
        for field in copy_fields:
            if field in request.fields:
                response_fields[field] = request.fields[field]

        return self.create_message(response_mti, response_fields)

    def create_reversal(
            self,
            original: ISO8583Message,
            additional_fields: Optional[Dict[int, str]] = None
    ) -> ISO8583Message:
        """
        Create a reversal message based on original message

        Args:
            original: Original message to reverse
            additional_fields: Optional additional fields for reversal

        Returns:
            Reversal message
        """
        # Create reversal MTI (usually 0400/0420)
        orig_mti = original.mti
        rev_mti = f"04{orig_mti[2:]}"

        # Copy fields from original
        reversal_fields = original.fields.copy()

        # Add reversal-specific fields
        now = datetime.now()
        reversal_fields.update({
            7: now.strftime("%m%d%H%M%S"),  # Transmission date and time
            39: "400",  # Response code (reversal)
            90: f"{orig_mti}{original.fields.get(11, '')}",  # Original elements
        })

        # Add any additional fields
        if additional_fields:
            reversal_fields.update(additional_fields)

        return self.create_message(rev_mti, reversal_fields)

    def create_network_management_message(
            self,
            message_type: str,
            network: Optional[CardNetwork] = None
    ) -> ISO8583Message:
        """
        Create a network management message

        Args:
            message_type: Type of network management message
            network: Optional card network

        Returns:
            Network management message
        """
        # Network management messages use MTI 0800
        fields = {
            70: message_type,  # Network management type
        }

        # Add network-specific fields
        if network == CardNetwork.VISA:
            fields.update({
                53: "0000000000000000",  # Security Info
                96: "0000000000000000"  # Message Security Code
            })
        elif network == CardNetwork.MASTERCARD:
            fields.update({
                48: "MC00",  # Network specific data
                53: "0000000000000000"
            })

        return self.create_message("0800", fields)

    def build_emv_data(self, emv_tags: Dict[str, str]) -> str:
        """
        Build EMV data field (field 55) from tags

        Args:
            emv_tags: Dictionary of EMV tags and values

        Returns:
            Formatted EMV data string
        """
        result = ""
        for tag, value in sorted(emv_tags.items()):
            # Validate tag format
            if not re.match(r'^[0-9A-F]{2,4}$', tag):
                raise BuildError(f"Invalid EMV tag format: {tag}")

            # Validate value format
            if not re.match(r'^[0-9A-F]+$', value):
                raise BuildError(f"Invalid EMV value format for tag {tag}")

            # Calculate length
            length = len(value) // 2  # Hex string length in bytes
            length_hex = hex(length)[2:].upper().zfill(2)

            result += tag + length_hex + value

        return result
