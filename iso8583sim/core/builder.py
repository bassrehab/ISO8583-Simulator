# iso8583sim/core/builder.py

from datetime import datetime

from .types import (
    BuildError,
    CardNetwork,
    FieldDefinition,
    FieldType,
    ISO8583Message,
    ISO8583Version,
    MessageFunction,
    get_field_definition,
)
from .validator import ISO8583Validator


class ISO8583Builder:
    """Builder for creating ISO 8583 messages with network support"""

    def __init__(self, version: ISO8583Version = ISO8583Version.V1987):
        self.version = version
        self.validator = ISO8583Validator()

    def build(self, message: ISO8583Message) -> str:
        """Build raw ISO 8583 message string from message object"""
        try:
            # Pre-process fields
            processed_fields = {}
            for field_number, value in message.fields.items():
                if field_number == 0:  # Skip MTI
                    continue

                field_def = get_field_definition(field_number, message.network, message.version)
                if not field_def:
                    raise BuildError(f"Unknown field definition: {field_number}")

                # Format field value
                processed_value = self._format_field_value(field_number, value, field_def)
                processed_fields[field_number] = processed_value

            # Update message with processed fields
            message.fields.update(processed_fields)

            # Validate message
            errors = self.validator.validate_message(message)
            if errors:
                raise BuildError(f"Validation failed: {'; '.join(errors)}")

            # Build message components
            result = message.mti
            bitmap = self._build_bitmap(message.fields)
            result += bitmap

            # Build data fields in order
            present_fields = sorted(f for f in message.fields.keys() if f != 0)
            for field_number in present_fields:
                field_def = get_field_definition(field_number, message.network, message.version)
                if field_def:
                    field_data = self._build_field(field_number, message.fields[field_number], field_def)
                    result += field_data

            return result

        except BuildError:
            raise
        except Exception as e:
            raise BuildError(f"Failed to build message: {str(e)}") from e

    def _format_field_value(self, field_number: int, value: str, field_def: FieldDefinition) -> str:
        """Format field value based on type and rules"""
        try:
            value = str(value).strip()

            # Handle specific fields first (override field definition rules)
            if field_number == 42:  # Card Acceptor ID Code
                return value.ljust(15, " ")  # Must be exactly 15 chars
            elif field_number == 41:  # Terminal ID
                return value.ljust(8, " ")  # Must be exactly 8 chars

            # Handle binary fields
            if field_def.field_type == FieldType.BINARY:
                if not all(c in "0123456789ABCDEF" for c in value.upper()):
                    raise BuildError(f"Field {field_number} must be valid hexadecimal")
                required_length = field_def.max_length * 2  # Each byte is 2 hex chars
                return value.upper().zfill(required_length)

            # Handle numeric fields
            if field_def.field_type == FieldType.NUMERIC:
                if not value.isdigit():
                    raise BuildError(f"Field {field_number} must contain only digits")
                return value.zfill(field_def.max_length)

            # Handle alpha fields
            if field_def.field_type == FieldType.ALPHA:
                if not value.replace(" ", "").isalpha():
                    raise BuildError(f"Field {field_number} must contain only letters")
                if field_def.padding_direction == "left":
                    return value.rjust(field_def.max_length, field_def.padding_char or " ")
                return value.ljust(field_def.max_length, field_def.padding_char or " ")

            # Handle alphanumeric fields
            if field_def.field_type == FieldType.ALPHANUMERIC:
                if not value.replace(" ", "").isalnum():
                    raise BuildError(f"Field {field_number} must contain only letters and numbers")
                if field_def.padding_direction == "left":
                    return value.rjust(field_def.max_length, field_def.padding_char or " ")
                return value.ljust(field_def.max_length, field_def.padding_char or " ")

            # Handle variable length fields
            if field_def.field_type in [FieldType.LLVAR, FieldType.LLLVAR]:
                if len(value) > field_def.max_length:
                    raise BuildError(f"Field {field_number} exceeds maximum length {field_def.max_length}")
                return value

            # Apply default padding if specified
            if field_def.padding_char:
                if field_def.padding_direction == "left":
                    return value.rjust(field_def.max_length, field_def.padding_char)
                return value.ljust(field_def.max_length, field_def.padding_char)

            return value

        except BuildError:
            raise
        except Exception as e:
            raise BuildError(f"Failed to format field {field_number}: {str(e)}") from e

    def _build_field(self, field_number: int, value: str, field_def: FieldDefinition) -> str:
        """Build individual field based on its definition"""
        try:
            # First format the value
            formatted_value = self._format_field_value(field_number, value, field_def)

            if field_def.field_type in [FieldType.LLVAR, FieldType.LLLVAR]:
                # Variable length field
                length = len(formatted_value)
                length_indicator_size = 2 if field_def.field_type == FieldType.LLVAR else 3

                if length > field_def.max_length:
                    raise BuildError(f"Value too long for field {field_number}: " f"{length} > {field_def.max_length}")

                length_str = str(length).zfill(length_indicator_size)
                return length_str + formatted_value

            # For fixed length fields, ensure proper formatting
            if field_def.field_type == FieldType.NUMERIC:
                return formatted_value.zfill(field_def.max_length)
            elif field_def.field_type == FieldType.ALPHA:
                if field_def.padding_direction == "left":
                    return formatted_value.rjust(field_def.max_length, field_def.padding_char or " ")
                return formatted_value.ljust(field_def.max_length, field_def.padding_char or " ")
            elif field_def.field_type == FieldType.ALPHANUMERIC:
                if field_def.padding_direction == "left":
                    return formatted_value.rjust(field_def.max_length, field_def.padding_char or " ")
                return formatted_value.ljust(field_def.max_length, field_def.padding_char or " ")
            elif field_def.field_type == FieldType.BINARY:
                # Binary fields should be padded to correct length * 2 (hex)
                required_length = field_def.max_length * 2
                return formatted_value.upper().zfill(required_length)

            # Apply default padding if specified
            if field_def.padding_char:
                if field_def.padding_direction == "left":
                    return formatted_value.rjust(field_def.max_length, field_def.padding_char)
                return formatted_value.ljust(field_def.max_length, field_def.padding_char)

            return formatted_value

        except BuildError:
            raise
        except Exception as e:
            raise BuildError(f"Failed to build field {field_number}: {str(e)}") from e

    def _build_bitmap(self, fields: dict[int, str]) -> str:
        """Build bitmap from present fields"""
        try:
            # Initialize bitmap arrays
            primary = ["0"] * 64
            secondary = ["0"] * 64

            # Mark present fields
            need_secondary = False
            for field_number in fields.keys():
                if field_number == 0:  # Skip MTI
                    continue

                if 1 <= field_number <= 64:
                    primary[field_number - 1] = "1"
                elif 65 <= field_number <= 128:
                    secondary[field_number - 65] = "1"
                    need_secondary = True

            if need_secondary:
                # Set first bit in primary bitmap
                primary[0] = "1"
                primary_hex = hex(int("".join(primary), 2))[2:].upper().zfill(16)
                secondary_hex = hex(int("".join(secondary), 2))[2:].upper().zfill(16)
                return primary_hex + secondary_hex
            else:
                return hex(int("".join(primary), 2))[2:].upper().zfill(16)

        except Exception as e:
            raise BuildError(f"Failed to build bitmap: {str(e)}") from e

    def create_message(self, mti: str, fields: dict[int, str]) -> ISO8583Message:
        """Create an ISO8583Message object with validation"""
        message = ISO8583Message(mti=mti, fields=fields, version=self.version)

        # Validate
        errors = self.validator.validate_message(message)
        if errors:
            raise BuildError(f"Message validation failed: {'; '.join(errors)}")

        # Build raw message
        raw_message = self.build(message)
        message.raw_message = raw_message

        return message

    def create_response(self, request: ISO8583Message, response_fields: dict[int, str]) -> ISO8583Message:
        """Create a response message based on a request message"""
        # Create response MTI
        req_mti = request.mti
        resp_mti = list(req_mti)
        resp_mti[2] = MessageFunction.RESPONSE.value
        response_mti = "".join(resp_mti)

        # Copy necessary fields and ensure proper formatting
        response_fields = response_fields.copy()
        copy_fields = [2, 3, 4, 11, 37, 41, 42]
        for field in copy_fields:
            if field in request.fields:
                if field == 3:
                    # Ensure processing code is properly formatted
                    response_fields[field] = request.fields[field].zfill(6)
                elif field == 42:
                    # Ensure merchant ID is properly formatted
                    response_fields[field] = request.fields[field].ljust(15, " ")
                else:
                    response_fields[field] = request.fields[field]

        return self.create_message(response_mti, response_fields)

    def create_reversal(
        self, original: ISO8583Message, additional_fields: dict[int, str] | None = None
    ) -> ISO8583Message:
        """Create a reversal message"""
        # Create reversal MTI
        orig_mti = original.mti
        rev_mti = f"04{orig_mti[2:]}"

        # Copy fields and ensure proper formatting
        reversal_fields = {}
        for field_num, value in original.fields.items():
            if field_num == 42:  # Merchant ID
                reversal_fields[field_num] = value.ljust(15, " ")
            elif field_num == 3:  # Processing Code
                reversal_fields[field_num] = value.zfill(6)
            else:
                reversal_fields[field_num] = value

        # Add reversal-specific fields
        now = datetime.now()
        reversal_fields.update(
            {
                7: now.strftime("%m%d%H%M%S"),  # Transmission date and time
                39: "00",  # Response code
                90: f"{orig_mti}{original.fields.get('11', '').zfill(6)}".ljust(42, "0"),  # Original elements
            }
        )

        # Add any additional fields
        if additional_fields:
            reversal_fields.update(additional_fields)

        return self.create_message(rev_mti, reversal_fields)

    def create_network_management_message(
        self, message_type: str, network: CardNetwork | None = None
    ) -> ISO8583Message:
        """Create a network management message"""
        fields = {
            70: message_type.zfill(3),  # Network management type
        }

        # Add network-specific fields
        if network == CardNetwork.VISA:
            fields.update(
                {
                    53: "0000000000000000",  # Security Info
                    96: "0123456789ABCDEF",  # Message Security Code (16 hex chars)
                }
            )
        elif network == CardNetwork.MASTERCARD:
            fields.update({48: "MC00".ljust(4), 53: "0000000000000000"})

        return self.create_message("0800", fields)

    def build_emv_data(self, emv_tags: dict[str, str]) -> str:
        """Build EMV data field (field 55) from tags"""
        result = []
        for tag, value in sorted(emv_tags.items()):
            # Validate tag format
            if not all(c in "0123456789ABCDEF" for c in tag.upper()):
                raise BuildError(f"Invalid EMV tag format: {tag}")

            # Validate value format
            if not all(c in "0123456789ABCDEF" for c in value.upper()):
                raise BuildError(f"Invalid EMV value format for tag {tag}")

            # Calculate length
            length = len(value) // 2  # Convert hex length to bytes
            length_hex = hex(length)[2:].upper().zfill(2)

            result.append(tag + length_hex + value)

        return "".join(result)
