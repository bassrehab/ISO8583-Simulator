from typing import Dict, Optional, List, Tuple
import re
from datetime import datetime
from .types import (
    FieldType,
    FieldDefinition,
    ISO8583_FIELDS,
    ValidationError,
    ISO8583Message
)


class ISO8583Validator:
    """Validator for ISO 8583 messages and fields"""

    @staticmethod
    def validate_field(
            field_number: int,
            value: str,
            field_def: FieldDefinition
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a single field value against its definition
        Returns (is_valid, error_message)
        """
        try:
            # Check length constraints
            if field_def.field_type not in [FieldType.LLVAR, FieldType.LLLVAR]:
                if len(value) != field_def.max_length:
                    return False, f"Field {field_number} length must be {field_def.max_length}"
            else:
                if len(value) > field_def.max_length:
                    return False, f"Field {field_number} length cannot exceed {field_def.max_length}"

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
                    # Try to convert to bytes
                    int(value, 16)
                except ValueError:
                    return False, f"Field {field_number} must be valid hexadecimal"

            elif field_def.field_type == FieldType.TRACK2:
                # Track 2 format: PAN=YYMM[SVCS]
                track2_pattern = r"^[0-9]{1,19}=[0-9]{4}[0-9]*$"
                if not re.match(track2_pattern, value):
                    return False, f"Field {field_number} invalid Track2 format"

            return True, None

        except Exception as e:
            return False, f"Validation error for field {field_number}: {str(e)}"

    @classmethod
    def validate_mti(cls, mti: str) -> Tuple[bool, Optional[str]]:
        """Validate Message Type Indicator"""
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
        """Validate bitmap format"""
        if not bitmap:
            return False, "Bitmap is required"

        if len(bitmap) != 16:  # 16 bytes for primary bitmap
            return False, "Primary bitmap must be 16 bytes"

        try:
            # Try to convert hex to int
            int(bitmap, 16)
            return True, None
        except ValueError:
            return False, "Invalid bitmap format"

    @classmethod
    def validate_message(cls, message: ISO8583Message) -> List[str]:
        """
        Validate complete ISO 8583 message
        Returns list of error messages (empty if valid)
        """
        errors = []

        # Validate MTI
        mti_valid, mti_error = cls.validate_mti(message.mti)
        if not mti_valid:
            errors.append(mti_error)

        # Validate bitmap if present
        if message.bitmap:
            bitmap_valid, bitmap_error = cls.validate_bitmap(message.bitmap)
            if not bitmap_valid:
                errors.append(bitmap_error)

        # Validate each field
        for field_number, value in message.fields.items():
            if field_number == 0:  # MTI already validated
                continue

            if field_number not in ISO8583_FIELDS:
                errors.append(f"Unknown field number: {field_number}")
                continue

            field_def = ISO8583_FIELDS[field_number]
            valid, error = cls.validate_field(field_number, value, field_def)
            if not valid:
                errors.append(error)

        return errors

    @classmethod
    def validate_pan(cls, pan: str) -> bool:
        """
        Validate Primary Account Number using Luhn algorithm
        """
        if not pan.isdigit():
            return False

        digits = [int(d) for d in pan]
        checksum = 0
        for i in range(len(digits) - 2, -1, -1):
            d = digits[i]
            if i % 2 == len(digits) % 2:  # Alternate digits
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        return (checksum + digits[-1]) % 10 == 0

    @classmethod
    def validate_processing_code(cls, code: str) -> bool:
        """
        Validate processing code format (position 3)
        Format: TTAASS
        TT = Transaction Type
        AA = Account Type (From)
        SS = Account Type (To)
        """
        if not code.isdigit() or len(code) != 6:
            return False

        tt = int(code[0:2])
        aa = int(code[2:4])
        ss = int(code[4:6])

        # Validate ranges based on ISO 8583 specifications
        if not (0 <= tt <= 99 and 0 <= aa <= 99 and 0 <= ss <= 99):
            return False

        return True
