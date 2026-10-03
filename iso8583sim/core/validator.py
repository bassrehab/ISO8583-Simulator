# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

# iso8583sim/core/validator.py

import re
from dataclasses import replace

from .network_rules import check_network_fields
from .spec import Spec
from .types import (
    MTI_VERSION_DIGITS,
    CardNetwork,
    FieldDefinition,
    FieldType,
    ISO8583Message,
    ISO8583Version,
    get_field_definition,
)

# Pre-compiled regex patterns for performance
_HEX_2_PATTERN = re.compile(r"^[0-9A-F]{2}$", re.IGNORECASE)
_HEX_PATTERN = re.compile(r"^[0-9A-F]+$", re.IGNORECASE)

# Try to import Cython-optimized functions
try:
    from ._validator_fast import is_alpha as _is_alpha_fast
    from ._validator_fast import is_alphanumeric as _is_alphanumeric_fast
    from ._validator_fast import is_numeric as _is_numeric_fast
    from ._validator_fast import is_valid_hex as _is_valid_hex_fast
    from ._validator_fast import validate_pan_luhn as _validate_pan_luhn_fast

    _USE_CYTHON = True
except ImportError:
    _USE_CYTHON = False


def _as_sent(value: str, field_def: FieldDefinition) -> str:
    """A fixed field's value as it's sent: padded to its length when the field has a padding character.

    subhadipmitra@: The parser takes padding off fixed fields (a card acceptor's name in field 43,
    say), and the builder puts it back before validating. Checking a message's values as they
    stand failed every parsed message with such a field ("Field 43 length must be 40"), so a
    message is checked as it would be sent. validate_field itself still wants the sent form.
    """
    if (
        field_def.padding_char is None
        or field_def.field_type in (FieldType.LLVAR, FieldType.LLLVAR, FieldType.BINARY)
        or len(value) >= field_def.max_length
    ):
        return value
    if field_def.padding_direction == "left":
        return value.rjust(field_def.max_length, field_def.padding_char)
    return value.ljust(field_def.max_length, field_def.padding_char)


class ISO8583Validator:
    """Enhanced validator for ISO 8583 messages with network support"""

    def __init__(self, spec: Spec | None = None):
        # Custom field definitions (see Spec), used wherever the spec defines a field.
        self._spec = spec
        self.network_required_fields = {
            CardNetwork.VISA: [2, 3, 4, 11, 14, 22, 24, 25],
            CardNetwork.MASTERCARD: [2, 3, 4, 11, 22, 24, 25],
            CardNetwork.AMEX: [2, 3, 4, 11, 22, 25],
            CardNetwork.DISCOVER: [2, 3, 4, 11, 22],
            CardNetwork.JCB: [2, 3, 4, 11, 22, 25],
            CardNetwork.UNIONPAY: [2, 3, 4, 11, 22, 25, 49],
        }

    def validate_field(
        self, field_number: int, value: str, field_def: FieldDefinition, network: CardNetwork | None = None
    ) -> tuple[bool, str | None]:
        """Validate field value"""
        try:
            # Length validation for fixed-length fields
            if field_def.field_type == FieldType.BINARY:
                # For binary fields, length is in bytes but value is in hex
                required_length = field_def.max_length * 2  # Convert bytes to hex chars
                if len(value) != required_length:
                    return False, f"Field {field_number} length must be {field_def.max_length * 2} hex chars"
            elif field_def.field_type not in [FieldType.LLVAR, FieldType.LLLVAR]:
                if len(value) != field_def.max_length:
                    return False, f"Field {field_number} length must be {field_def.max_length}"
            else:
                # Variable length field validation
                if len(value) > field_def.max_length:
                    return False, f"Field {field_number} length cannot exceed {field_def.max_length}"
                if field_def.min_length and len(value) < field_def.min_length:
                    return False, f"Field {field_number} length cannot be less than {field_def.min_length}"

            # Type-specific validation (use Cython if available)
            if field_def.field_type == FieldType.NUMERIC:
                is_valid = _is_numeric_fast(value) if _USE_CYTHON else value.isdigit()
                if not is_valid:
                    return False, f"Field {field_number} must contain only digits"
            elif field_def.field_type == FieldType.BINARY:
                is_valid = (
                    _is_valid_hex_fast(value) if _USE_CYTHON else all(c in "0123456789ABCDEFabcdef" for c in value)
                )
                if not is_valid:
                    return False, f"Field {field_number} must be valid hexadecimal"
            elif field_def.field_type == FieldType.ALPHA:
                is_valid = _is_alpha_fast(value) if _USE_CYTHON else value.replace(" ", "").isalpha()
                if not is_valid:
                    return False, f"Field {field_number} must contain only letters"
            elif field_def.field_type == FieldType.ALPHANUMERIC:
                is_valid = _is_alphanumeric_fast(value) if _USE_CYTHON else value.replace(" ", "").isalnum()
                if not is_valid:
                    return False, f"Field {field_number} must contain only letters and numbers"

            # Field passed all validations
            return True, None

        except Exception as e:
            return False, f"Validation error for field {field_number}: {str(e)}"

    def validate_message(self, message: ISO8583Message) -> list[str]:
        """Validate complete ISO 8583 message"""
        errors: list[str] = []

        # Validate MTI
        mti_valid, mti_error = self.validate_mti(message.mti)
        if not mti_valid and mti_error:
            errors.append(mti_error)

        # Validate bitmap if present
        if message.bitmap:
            bitmap_valid, bitmap_error = self.validate_bitmap(message.bitmap)
            if not bitmap_valid and bitmap_error:
                errors.append(bitmap_error)

        # Validate fields
        for field_number, value in message.fields.items():
            if field_number == 0:  # MTI already validated
                continue

            # Get field definition considering the spec, network and version
            field_def = (
                self._spec.definition(field_number, message.network, message.version)
                if self._spec is not None
                else get_field_definition(field_number, message.network, message.version)
            )

            if not field_def:
                errors.append(f"Unknown field number: {field_number}")
                continue

            valid, error = self.validate_field(field_number, _as_sent(value, field_def), field_def)
            if not valid and error:
                errors.append(error)

        # Network-specific validation
        if message.network:
            network_errors = self.validate_network_compliance(message)
            errors.extend(network_errors)

        return errors

    @staticmethod
    def validate_processing_code(code: str) -> bool:
        """Validate processing code format"""
        if not code.isdigit() or len(code) != 6:
            return False

        tt = int(code[0:2])  # Transaction Type
        aa = int(code[2:4])  # Account Type (From)
        ss = int(code[4:6])  # Account Type (To)

        return all(0 <= x <= 99 for x in (tt, aa, ss))

    @classmethod
    def validate_mti(cls, mti: str) -> tuple[bool, str | None]:
        """
        Validate Message Type Indicator

        Args:
            mti: 4-digit MTI string

        Returns:
            (is_valid, error_message)
        """
        if not mti or len(mti) != 4:
            return False, "MTI must be 4 digits"

        if not mti.isdigit():
            return False, "MTI must contain only digits"

        version = mti[0]
        if version not in MTI_VERSION_DIGITS.values():
            return False, "MTI version must be 0 (1987), 1 (1993) or 2 (2003)"

        message_class = mti[1]
        if message_class not in ["1", "2", "3", "4", "5", "6", "8", "9"]:
            return False, "Invalid MTI message class"

        return True, None

    @classmethod
    def validate_bitmap(cls, bitmap: str) -> tuple[bool, str | None]:
        """
        Validate bitmap format and content

        Args:
            bitmap: Hexadecimal bitmap string

        Returns:
            (is_valid, error_message)
        """
        if not bitmap:
            return False, "Bitmap is required"

        if len(bitmap) not in [16, 32]:  # 16 bytes for primary, 32 for secondary
            return False, "Invalid bitmap length"

        try:
            # Validate hex format
            int(bitmap, 16)

            # Check if secondary bitmap is present (bit 1)
            has_secondary = len(bitmap) == 32 or (int(bitmap[0], 16) & 0x80)
            if has_secondary and len(bitmap) != 32:
                return False, "Secondary bitmap indicator set but bitmap not 32 bytes"

            return True, None
        except ValueError:
            return False, "Invalid bitmap format"

    @classmethod
    def validate_pan(cls, pan: str) -> bool:
        """
        Validate Primary Account Number using Luhn algorithm

        Args:
            pan: Card number string

        Returns:
            True if valid, False otherwise
        """
        # Use Cython-optimized version if available
        if _USE_CYTHON:
            return _validate_pan_luhn_fast(pan)

        # Pure Python fallback
        if not pan.isdigit():
            return False

        # Luhn algorithm
        digits = [int(d) for d in pan]
        checksum = 0
        odd_even = len(digits) % 2

        for i in range(len(digits) - 1, -1, -1):
            d = digits[i]
            if i % 2 == odd_even:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d

        return (checksum % 10) == 0

    def validate_for_network(self, message: ISO8583Message, network: CardNetwork) -> list[str]:
        """Validate a message as if it were sent on another network.

        The message is not changed. Useful to check whether a message built for one
        network also meets another network's required fields and formats.
        """
        # subhadipmitra@: Network rules key off message.network, so validate a copy with the
        # network swapped instead of mutating the caller's message.
        return self.validate_message(replace(message, fields=dict(message.fields), network=network))

    def validate_for_networks(
        self, message: ISO8583Message, networks: list[CardNetwork] | None = None
    ) -> dict[CardNetwork, list[str]]:
        """Validate a message against several networks at once (all networks by default)."""
        return {net: self.validate_for_network(message, net) for net in (networks or list(CardNetwork))}

    def verify_mac(self, raw_message: str, key: str | bytes, algorithm: int = 3, padding: int = 1) -> bool:
        """Check the MAC in field 64 or 128 of a raw message. Requires the security extra."""
        from ..security import verify_message

        return verify_message(raw_message, key, algorithm=algorithm, padding=padding)

    def validate_network_compliance(self, message: ISO8583Message) -> list[str]:
        """Validate network-specific requirements"""
        errors: list[str] = []

        if not message.network:
            return errors

        # Check required fields
        required_fields = self.network_required_fields.get(message.network, [])
        for field in required_fields:
            if field not in message.fields:
                errors.append(f"Required field {field} missing for {message.network.value}")

        # subhadipmitra@: Field format rules live in network_rules, where each rule cites its
        # source. The rules that used to be here (VISA field 44 as hex, Mastercard field 48
        # starting with "MC") rejected valid messages and have been replaced.
        errors.extend(check_network_fields(message.fields, message.network))
        return errors

    def validate_emv_data(self, emv_data: str) -> list[str]:
        """Validate EMV data format (TLV structure)"""
        if not emv_data:
            return ["Empty EMV data"]

        errors: list[str] = []
        position = 0

        try:
            while position < len(emv_data):
                # Need minimum 4 chars (2 for 1-byte tag, 2 for length)
                if position + 4 > len(emv_data):
                    errors.append("Incomplete EMV data")
                    break

                # Read first byte of tag
                tag_byte1 = emv_data[position : position + 2]
                if not _HEX_2_PATTERN.match(tag_byte1):
                    errors.append(f"Invalid tag format: {tag_byte1}")
                    break
                position += 2

                # Check if this is a multi-byte tag (bits 1-5 all set = 1F, 5F, 9F, DF)
                first_byte = int(tag_byte1, 16)
                if (first_byte & 0x1F) == 0x1F:
                    # Multi-byte tag - read second byte
                    if position + 2 > len(emv_data):
                        errors.append(f"Incomplete multi-byte tag starting with {tag_byte1}")
                        break
                    tag_byte2 = emv_data[position : position + 2]
                    if not _HEX_2_PATTERN.match(tag_byte2):
                        errors.append(f"Invalid second byte of tag: {tag_byte2}")
                        break
                    tag = tag_byte1 + tag_byte2
                    position += 2
                else:
                    tag = tag_byte1

                # Check length format (2 hex chars for 1-byte length)
                if position + 2 > len(emv_data):
                    errors.append(f"Missing length for tag {tag}")
                    break

                length_hex = emv_data[position : position + 2]
                try:
                    length = int(length_hex, 16)
                except ValueError:
                    errors.append(f"Invalid length format for tag {tag}")
                    break
                position += 2

                # Check value format (length * 2 hex chars)
                value_length = length * 2  # Each byte is 2 hex chars
                if position + value_length > len(emv_data):
                    errors.append(f"Incomplete value for tag {tag}")
                    break

                value = emv_data[position : position + value_length]
                if len(value) != value_length or not _HEX_PATTERN.match(value):
                    errors.append(f"Invalid value format for tag {tag}")
                    break

                position += value_length

            return errors

        except Exception as e:
            return [f"EMV validation error: {str(e)}"]

    def validate_field_compatibility(self, field_number: int, value: str, version: ISO8583Version) -> list[str]:
        """
        Validate field compatibility with ISO version

        Args:
            field_number: Field number to validate
            value: Field value
            version: ISO8583 version

        Returns:
            List of compatibility errors
        """
        errors: list[str] = []

        # Get version-specific field definition
        field_def = get_field_definition(field_number, version=version)
        if not field_def:
            return [f"Field {field_number} not defined in ISO8583:{version.value}"]

        # Check length compatibility
        if len(value) > field_def.max_length:
            errors.append(
                f"Field {field_number} length {len(value)} exceeds "
                f"maximum {field_def.max_length} for version {version.value}"
            )

        # Check type compatibility
        if field_def.field_type == FieldType.BINARY and not _HEX_PATTERN.match(value):
            errors.append(f"Field {field_number} must be hexadecimal in version {version.value}")

        # Version-specific validations
        if version == ISO8583Version.V1987:
            if field_number == 43 and len(value) > 40:
                errors.append("Field 43 maximum length is 40 in ISO8583:1987")
        elif version == ISO8583Version.V1993:
            if field_number == 43 and len(value) > 99:
                errors.append("Field 43 maximum length is 99 in ISO8583:1993")
        elif version == ISO8583Version.V2003:
            if field_number == 43 and len(value) > 256:
                errors.append("Field 43 maximum length is 256 in ISO8583:2003")

        return errors

    def _parse_emv_data(self, value: str) -> str:
        """Parse EMV data and validate format"""
        if not value:
            return ""

        # For field 55, treat entire data as EMV data
        if value and len(value) >= 4:
            # Validate basic EMV structure
            if self.validate_emv_data(value):
                return value

        return value
