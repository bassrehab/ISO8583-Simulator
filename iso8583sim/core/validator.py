# iso8583sim/core/validator.py

from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime
import re
from .types import (
    FieldType,
    FieldDefinition,
    ISO8583_FIELDS,
    ValidationError,
    ISO8583Message,
    ISO8583Version,
    CardNetwork,
    NETWORK_SPECIFIC_FIELDS,
    VERSION_SPECIFIC_FIELDS,
    get_field_definition
)


class ISO8583Validator:
    """Enhanced validator for ISO 8583 messages with network support"""

    def __init__(self):
        self._load_custom_validators()

    def _load_custom_validators(self):
        """Load network-specific validation rules"""
        self.network_validators = {
            CardNetwork.VISA: self._validate_visa_specific,
            CardNetwork.MASTERCARD: self._validate_mastercard_specific,
            CardNetwork.AMEX: self._validate_amex_specific,
            CardNetwork.DISCOVER: self._validate_discover_specific,
            CardNetwork.JCB: self._validate_jcb_specific,
            CardNetwork.UNIONPAY: self._validate_unionpay_specific
        }

    @staticmethod
    def validate_field(
            field_number: int,
            value: str,
            field_def: FieldDefinition,
            network: Optional[CardNetwork] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a single field value against its definition

        Args:
            field_number: Field number
            value: Field value
            field_def: Field definition
            network: Optional card network for specific validation

        Returns:
            (is_valid, error_message)
        """
        try:
            # Check length constraints
            if field_def.field_type not in [FieldType.LLVAR, FieldType.LLLVAR]:
                if len(value) != field_def.max_length:
                    return False, f"Field {field_number} length must be {field_def.max_length}"
            else:
                if len(value) > field_def.max_length:
                    return False, f"Field {field_number} length cannot exceed {field_def.max_length}"
                if field_def.min_length and len(value) < field_def.min_length:
                    return False, f"Field {field_number} length cannot be less than {field_def.min_length}"

            # Validate based on field type
            if field_def.field_type == FieldType.NUMERIC:
                if not value.isdigit():
                    return False, f"Field {field_number} must contain only digits"

            elif field_def.field_type == FieldType.ALPHA:
                if not value.isalpha():
                    return False, f"Field {field_number} must contain only letters"

            elif field_def.field_type == FieldType.ALPHANUMERIC:
                if not value.isalnum():
                    return False, f"Field {field_number} must contain only letters and numbers"

            elif field_def.field_type == FieldType.BINARY:
                try:
                    int(value, 16)
                except ValueError:
                    return False, f"Field {field_number} must be valid hexadecimal"

            elif field_def.field_type == FieldType.TRACK2:
                track2_pattern = r"^[0-9]{1,19}=[0-9]{4}[0-9]*$"
                if not re.match(track2_pattern, value):
                    return False, f"Field {field_number} invalid Track2 format"

            # Network-specific field validations
            if network:
                valid, error = ISO8583Validator._validate_network_field(field_number, value, network)
                if not valid:
                    return False, error

            return True, None

        except Exception as e:
            return False, f"Validation error for field {field_number}: {str(e)}"

    @staticmethod
    def _validate_network_field(field_number: int, value: str, network: CardNetwork) -> Tuple[bool, Optional[str]]:
        """Validate network-specific field formats"""
        try:
            if network == CardNetwork.VISA:
                if field_number == 44:  # VISA Additional Response Data
                    if not re.match(r'^[0-9A-F]+$', value):
                        return False, "Invalid VISA Additional Response Data format"
                elif field_number == 46:  # VISA Fee Amounts
                    if not re.match(r'^[0-9]{1,12}$', value):
                        return False, "Invalid VISA Fee Amount format"

            elif network == CardNetwork.MASTERCARD:
                if field_number == 48:  # MC Private Data
                    if not value.startswith('MC'):
                        return False, "Invalid MC Private Data format"
                elif field_number == 55:  # MC EMV Data
                    if not re.match(r'^[0-9A-F]+$', value):
                        return False, "Invalid MC EMV Data format"

            elif network == CardNetwork.AMEX:
                if field_number == 112:  # AMEX Additional Data
                    if not value.startswith('AX'):
                        return False, "Invalid AMEX Additional Data format"

            return True, None

        except Exception as e:
            return False, f"Network-specific validation error: {str(e)}"

    def validate_message(self, message: ISO8583Message) -> List[str]:
        """
        Validate complete ISO 8583 message including network-specific rules

        Args:
            message: ISO8583Message to validate

        Returns:
            List of error messages (empty if valid)
        """
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

        # Get network-specific validator if applicable
        network_validator = self.network_validators.get(message.network) if message.network else None

        # Validate each field
        for field_number, value in message.fields.items():
            if field_number == 0:  # MTI already validated
                continue

            # Get field definition considering network and version
            field_def = get_field_definition(field_number, message.network, message.version)
            if not field_def:
                errors.append(f"Unknown field number: {field_number}")
                continue

            # Validate field
            valid, error = self.validate_field(field_number, value, field_def, message.network)
            if not valid:
                errors.append(error)

            # Additional network-specific validations
            if network_validator:
                network_errors = network_validator(field_number, value)
                errors.extend(network_errors)

        return errors

    def _validate_visa_specific(self, field_number: int, value: str) -> List[str]:
        """VISA specific validation rules"""
        errors = []
        if field_number == 44:
            if len(value) % 2 != 0:
                errors.append("VISA field 44 must have even length")
        return errors

    def _validate_mastercard_specific(self, field_number: int, value: str) -> List[str]:
        """Mastercard specific validation rules"""
        errors = []
        if field_number == 55:
            if not value.startswith('9F'):
                errors.append("MC EMV data must start with '9F'")
        return errors

    def _validate_amex_specific(self, field_number: int, value: str) -> List[str]:
        """AMEX specific validation rules"""
        errors = []
        return errors

    def _validate_discover_specific(self, field_number: int, value: str) -> List[str]:
        """Discover specific validation rules"""
        errors = []
        return errors

    def _validate_jcb_specific(self, field_number: int, value: str) -> List[str]:
        """JCB specific validation rules"""
        errors = []
        return errors

    def _validate_unionpay_specific(self, field_number: int, value: str) -> List[str]:
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
    def validate_mti(cls, mti: str) -> Tuple[bool, Optional[str]]:
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
        if version not in ['0', '1']:
            return False, "MTI version must be 0 or 1"

        message_class = mti[1]
        if message_class not in ['1', '2', '3', '4', '5', '6', '8', '9']:
            return False, "Invalid MTI message class"

        return True, None

    @classmethod
    def validate_bitmap(cls, bitmap: str) -> Tuple[bool, Optional[str]]:
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

    def validate_network_compliance(self, message: ISO8583Message) -> List[str]:
        """
        Validate message compliance with network-specific rules

        Args:
            message: ISO8583Message to validate

        Returns:
            List of compliance errors
        """
        errors = []
        if not message.network:
            return errors

        # Network-specific field requirements
        required_fields = {
            CardNetwork.VISA: [0, 2, 3, 4, 11, 14, 22, 24, 25],
            CardNetwork.MASTERCARD: [0, 2, 3, 4, 11, 22, 24, 25, 35],
            CardNetwork.AMEX: [0, 2, 3, 4, 11, 22, 25],
            CardNetwork.DISCOVER: [0, 2, 3, 4, 11, 22],
            CardNetwork.JCB: [0, 2, 3, 4, 11, 22, 25],
            CardNetwork.UNIONPAY: [0, 2, 3, 4, 11, 22, 25, 49]
        }

        # Check required fields
        network_fields = required_fields.get(message.network, [])
        for field in network_fields:
            if field not in message.fields:
                errors.append(f"Required field {field} missing for {message.network.value}")

        # Network-specific validations
        if message.network == CardNetwork.VISA:
            errors.extend(self._validate_visa_compliance(message))
        elif message.network == CardNetwork.MASTERCARD:
            errors.extend(self._validate_mastercard_compliance(message))
        # ... Add other network validations

        return errors

    def _validate_visa_compliance(self, message: ISO8583Message) -> List[str]:
        """VISA specific compliance rules"""
        errors = []

        # Check VISA PIN block format
        if 52 in message.fields:
            pin_block = message.fields[52]
            if not re.match(r'^[0-9A-F]{16}$', pin_block):
                errors.append("Invalid VISA PIN block format")

        # Check VISA CVV2 format
        if 48 in message.fields:
            cvv2_data = message.fields[48]
            if len(cvv2_data) != 3 or not cvv2_data.isdigit():
                errors.append("Invalid VISA CVV2 format")

        return errors

    def _validate_mastercard_compliance(self, message: ISO8583Message) -> List[str]:
        """Mastercard specific compliance rules"""
        errors = []

        # Check Mastercard specific fields
        if 48 in message.fields:
            field_48 = message.fields[48]
            if not field_48.startswith('MC'):
                errors.append("Mastercard field 48 must start with 'MC'")

        # Check Mastercard POS Entry Mode
        if 22 in message.fields:
            pos_entry = message.fields[22]
            if pos_entry not in ['02', '05', '07', '80', '90']:
                errors.append("Invalid Mastercard POS Entry Mode")

        return errors

    def validate_emv_data(self, emv_data: str) -> List[str]:
        """
        Validate EMV data format and tags

        Args:
            emv_data: EMV data string

        Returns:
            List of validation errors
        """
        errors = []

        if not emv_data:
            return ["EMV data is empty"]

        # Basic format check
        if not re.match(r'^[0-9A-F]+$', emv_data):
            return ["Invalid EMV data format"]

        try:
            # Parse and validate EMV tags
            position = 0
            while position < len(emv_data):
                # Parse tag
                if position + 2 > len(emv_data):
                    errors.append("Incomplete EMV tag")
                    break

                tag = emv_data[position:position + 2]
                position += 2

                # Parse length
                if position + 2 > len(emv_data):
                    errors.append(f"Incomplete length for tag {tag}")
                    break

                length = int(emv_data[position:position + 2], 16)
                position += 2

                # Check value
                if position + (length * 2) > len(emv_data):
                    errors.append(f"Incomplete value for tag {tag}")
                    break

                position += length * 2

        except ValueError as e:
            errors.append(f"EMV parsing error: {str(e)}")

        return errors

    def validate_field_compatibility(self, field_number: int, value: str,
                                     version: ISO8583Version) -> List[str]:
        """
        Validate field compatibility with ISO version

        Args:
            field_number: Field number
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
        if field_def.field_type == FieldType.BINARY and not re.match(r'^[0-9A-F]+$', value):
            errors.append(
                f"Field {field_number} must be hexadecimal "
                f"in version {version.value}"
            )

        return errors
