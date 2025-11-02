# iso8583sim/core/validator.py

import re

from .types import CardNetwork, FieldDefinition, FieldType, ISO8583Message, ISO8583Version, get_field_definition

# Pre-compiled regex patterns for performance
_HEX_16_PATTERN = re.compile(r"^[0-9A-F]{16}$")
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


class ISO8583Validator:
    """Enhanced validator for ISO 8583 messages with network support"""

    def __init__(self):
        self.network_required_fields = {
            CardNetwork.VISA: [2, 3, 4, 11, 14, 22, 24, 25],
            CardNetwork.MASTERCARD: [2, 3, 4, 11, 22, 24, 25],
            CardNetwork.AMEX: [2, 3, 4, 11, 22, 25],
            CardNetwork.DISCOVER: [2, 3, 4, 11, 22],
            CardNetwork.JCB: [2, 3, 4, 11, 22, 25],
            CardNetwork.UNIONPAY: [2, 3, 4, 11, 22, 25, 49],
        }

    def _load_custom_validators(self):
        """Load network-specific validation rules"""
        self.network_validators = {
            CardNetwork.VISA: self._validate_visa_specific,
            CardNetwork.MASTERCARD: self._validate_mastercard_specific,
            CardNetwork.AMEX: self._validate_amex_specific,
            CardNetwork.DISCOVER: self._validate_discover_specific,
            CardNetwork.JCB: self._validate_jcb_specific,
            CardNetwork.UNIONPAY: self._validate_unionpay_specific,
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

    def _validate_network_field(self, field_number: int, value: str, network: CardNetwork) -> tuple[bool, str | None]:
        """Validate network-specific field format"""
        if network == CardNetwork.VISA:
            if field_number == 44:
                if not all(c in "0123456789ABCDEF" for c in value):
                    return False, "Invalid VISA field 44 format"

            elif field_number == 48:
                if not value.startswith("VISA"):
                    return False, "VISA field 48 must start with 'VISA'"

        elif network == CardNetwork.MASTERCARD:
            if field_number == 48:
                if not value.startswith("MC"):
                    return False, "Mastercard field 48 must start with 'MC'"

        return True, None

    def validate_message(self, message: ISO8583Message) -> list[str]:
        """Validate complete ISO 8583 message"""
        errors = []

        # Validate MTI
        mti_valid, mti_error = self.validate_mti(message.mti)
        if not mti_valid:
            errors.append(mti_error)

        # Validate bitmap if present
        if message.bitmap:
            bitmap_valid, bitmap_error = self.validate_bitmap(message.bitmap)
            if not bitmap_valid:
                errors.append(bitmap_error)

        # Validate fields
        for field_number, value in message.fields.items():
            if field_number == 0:  # MTI already validated
                continue

            # Get field definition considering network and version
            field_def = get_field_definition(field_number, message.network, message.version)

            if not field_def:
                errors.append(f"Unknown field number: {field_number}")
                continue

            valid, error = self.validate_field(field_number, value, field_def)
            if not valid:
                errors.append(error)

        # Network-specific validation
        if message.network:
            network_errors = self.validate_network_compliance(message)
            errors.extend(network_errors)

        return errors

    def _validate_visa_specific(self, field_number: int, value: str) -> list[str]:
        """VISA specific validation rules"""
        errors = []
        if field_number == 44:
            if len(value) % 2 != 0:
                errors.append("VISA field 44 must have even length")
        return errors

    def _validate_mastercard_specific(self, field_number: int, value: str) -> list[str]:
        """Mastercard specific validation rules"""
        errors = []
        if field_number == 55:
            if not value.startswith("9F"):
                errors.append("MC EMV data must start with '9F'")
        return errors

    def _validate_amex_specific(self, field_number: int, value: str) -> list[str]:
        """AMEX specific validation rules"""
        errors = []
        return errors

    def _validate_discover_specific(self, field_number: int, value: str) -> list[str]:
        """Discover specific validation rules"""
        errors = []
        return errors

    def _validate_jcb_specific(self, field_number: int, value: str) -> list[str]:
        """JCB specific validation rules"""
        errors = []
        return errors

    def _validate_unionpay_specific(self, field_number: int, value: str) -> list[str]:
        """UnionPay specific validation rules"""
        errors = []
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
        if version not in ["0", "1"]:
            return False, "MTI version must be 0 or 1"

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

    def _validate_visa_field_44(self, value: str) -> bool:
        """Validate VISA-specific field 44 format"""
        if _USE_CYTHON:
            return _is_valid_hex_fast(value)
        return all(c in "0123456789ABCDEFabcdef" for c in value)

    def validate_network_compliance(self, message: ISO8583Message) -> list[str]:
        """Validate network-specific requirements"""
        errors = []

        if not message.network:
            return errors

        # Check required fields
        required_fields = self.network_required_fields.get(message.network, [])
        for field in required_fields:
            if field not in message.fields:
                errors.append(f"Required field {field} missing for {message.network.value}")

        # Network-specific validations
        if message.network == CardNetwork.VISA:
            if 44 in message.fields:
                if not self._validate_visa_field_44(message.fields[44]):
                    errors.append("Invalid format for VISA field 44")

        elif message.network == CardNetwork.MASTERCARD:
            if 48 in message.fields:
                if not message.fields[48].startswith("MC"):
                    errors.append("Mastercard field 48 must start with 'MC'")

        return errors

    def _validate_visa_compliance(self, message: ISO8583Message) -> list[str]:
        """VISA specific compliance rules"""
        errors = []

        # Check VISA PIN block format
        if 52 in message.fields:
            pin_block = message.fields[52]
            if not _HEX_16_PATTERN.match(pin_block):
                errors.append("Invalid VISA PIN block format")

        # Check VISA CVV2 format
        if 48 in message.fields:
            cvv2_data = message.fields[48]
            if len(cvv2_data) != 3 or not cvv2_data.isdigit():
                errors.append("Invalid VISA CVV2 format")

        return errors

    def _validate_mastercard_compliance(self, message: ISO8583Message) -> list[str]:
        """Mastercard specific compliance rules"""
        errors = []

        # Check Mastercard specific fields
        if 48 in message.fields:
            field_48 = message.fields[48]
            if not field_48.startswith("MC"):
                errors.append("Mastercard field 48 must start with 'MC'")

        # Check Mastercard POS Entry Mode
        if 22 in message.fields:
            pos_entry = message.fields[22]
            if pos_entry not in ["02", "05", "07", "80", "90"]:
                errors.append("Invalid Mastercard POS Entry Mode")

        return errors

    def validate_emv_data(self, emv_data: str) -> list[str]:
        """Validate EMV data format (TLV structure)"""
        if not emv_data:
            return ["Empty EMV data"]

        errors = []
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
        errors = []

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
            errors.append(f"Field {field_number} must be hexadecimal " f"in version {version.value}")

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
