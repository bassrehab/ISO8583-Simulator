# tests/test_validator.py
import pytest
from datetime import datetime
from iso8583sim.core.types import (
    ISO8583Message,
    ISO8583Version,
    CardNetwork,
    FieldType,
    FieldDefinition,
    ValidationError,
    NETWORK_SPECIFIC_FIELDS,
    VERSION_SPECIFIC_FIELDS,
    ISO8583_FIELDS
)


def test_validate_field_numeric(validator):
    """Test numeric field validation"""
    field_def = FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Test numeric"
    )

    # Valid cases
    valid, error = validator.validate_field(3, "123456", field_def)
    assert valid
    assert error is None

    # Invalid cases
    valid, error = validator.validate_field(3, "12345", field_def)
    assert not valid  # wrong length

    valid, error = validator.validate_field(3, "12A456", field_def)
    assert not valid  # contains letter


def test_validate_field_alpha(validator):
    """Test alphabetic field validation"""
    field_def = FieldDefinition(
        field_type=FieldType.ALPHA,
        max_length=4,
        description="Test alpha"
    )

    # Valid cases
    valid, error = validator.validate_field(1, "ABCD", field_def)
    assert valid
    assert error is None

    # Invalid cases
    valid, error = validator.validate_field(1, "ABC1", field_def)
    assert not valid  # contains number


def test_validate_field_alphanumeric(validator):
    """Test alphanumeric field validation"""
    field_def = FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=6,
        description="Test alphanumeric"
    )

    # Valid cases
    valid, error = validator.validate_field(1, "ABC123", field_def)
    assert valid
    assert error is None

    # Invalid cases
    valid, error = validator.validate_field(1, "ABC@23", field_def)
    assert not valid  # contains special character


def test_validate_mti(validator):
    """Test MTI validation"""
    # Valid cases
    valid, error = validator.validate_mti("0100")
    assert valid
    assert error is None

    valid, error = validator.validate_mti("1200")
    assert valid
    assert error is None

    # Invalid cases
    valid, error = validator.validate_mti("2100")  # invalid version
    assert not valid

    valid, error = validator.validate_mti("0700")  # invalid message class
    assert not valid


def test_validate_bitmap(validator):
    """Test bitmap validation"""
    # Valid cases
    valid, error = validator.validate_bitmap("8000000000000000")
    assert valid
    assert error is None

    # Secondary bitmap
    valid, error = validator.validate_bitmap("C000000000000000" + "0" * 16)
    assert valid
    assert error is None

    # Invalid cases
    valid, error = validator.validate_bitmap("800000")  # too short
    assert not valid

    valid, error = validator.validate_bitmap("80000000000000GG")  # invalid hex
    assert not valid


def test_validate_pan(validator):
    """Test PAN validation"""
    # Valid PANs
    assert validator.validate_pan("4111111111111111")  # Valid VISA
    assert validator.validate_pan("5555555555554444")  # Valid Mastercard

    # Invalid PANs
    assert not validator.validate_pan("1234567890123456")  # Invalid Luhn
    assert not validator.validate_pan("411111")  # Too short
    assert not validator.validate_pan("4111111111111112")  # Invalid check digit


def test_validate_network_specific_fields(validator, test_messages, create_message):
    """Test network-specific field validation"""
    # Test VISA field validation
    visa_msg = create_message('visa_auth', test_messages)
    errors = validator.validate_message(visa_msg)
    assert len(errors) == 0

    # Test Mastercard field validation
    mc_msg = create_message('mastercard_auth', test_messages)
    errors = validator.validate_message(mc_msg)
    assert len(errors) == 0


def test_validate_message_network_compliance(validator, test_messages, create_message):
    """Test network-specific message validation"""
    # Test complete message
    complete_msg = create_message('visa_auth', test_messages)
    errors = validator.validate_message(complete_msg)
    assert len(errors) == 0

    # Test incomplete message
    incomplete_msg = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111"
        },
        network=CardNetwork.VISA
    )
    errors = validator.validate_message(incomplete_msg)
    assert len(errors) > 0
    assert any("Required field" in error for error in errors)


def test_validate_version_specific_fields(validator):
    """Test version-specific field validation"""
    # Test 1987 version field
    message_1987 = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            43: "A" * 40  # 1987 version max length
        },
        version=ISO8583Version.V1987
    )
    errors = validator.validate_message(message_1987)
    assert len(errors) == 0

    # Test 2003 version field
    message_2003 = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            43: "A" * 256  # 2003 version max length
        },
        version=ISO8583Version.V2003
    )
    errors = validator.validate_message(message_2003)
    assert len(errors) == 0


def test_validate_emv_data(validator, valid_emv_data, invalid_emv_data):
    """Test EMV data validation"""
    # Test valid EMV data
    for data in valid_emv_data:
        errors = validator.validate_emv_data(data)
        assert len(errors) == 0, f"Should be valid: {data}"

    # Test invalid EMV data
    for data in invalid_emv_data:
        errors = validator.validate_emv_data(data)
        assert len(errors) > 0, f"Should be invalid: {data}"


def test_validate_field_format(validator, test_messages, create_message):
    """Test field format validation"""
    message = create_message('basic_auth', test_messages)

    # Test numeric field
    valid, error = validator.validate_field(
        3, "000000",
        ISO8583_FIELDS[3]
    )
    assert valid
    assert error is None

    # Test alphanumeric field with padding
    valid, error = validator.validate_field(
        42, "MERCHANT12345  ",  # Exactly 15 chars
        ISO8583_FIELDS[42]
    )
    assert valid
    assert error is None


def test_validate_required_fields(validator, test_messages, create_message):
    """Test required fields validation"""
    # Test VISA required fields
    visa_msg = create_message('visa_auth', test_messages)
    errors = validator.validate_message(visa_msg)
    assert len(errors) == 0

    # Test Mastercard required fields
    mc_msg = create_message('mastercard_auth', test_messages)
    errors = validator.validate_message(mc_msg)
    assert len(errors) == 0


def test_validate_field_length(validator):
    """Test field length validation"""
    # Test fixed-length field
    field_def = FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Test fixed length"
    )
    valid, error = validator.validate_field(3, "123456", field_def)
    assert valid
    assert error is None

    # Test variable length field
    field_def = FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=19,
        description="Test variable length"
    )
    valid, error = validator.validate_field(2, "4111111111111111", field_def)
    assert valid
    assert error is None


def test_validate_binary_fields(validator):
    """Test binary field validation"""
    field_def = FieldDefinition(
        field_type=FieldType.BINARY,
        max_length=8,
        description="Test binary"
    )
    valid, error = validator.validate_field(52, "0123456789ABCDEF", field_def)
    assert valid
    assert error is None


def test_validate_network_field_format(validator):
    """Test network-specific field format validation"""
    # VISA field validation
    valid, error = validator._validate_network_field(
        44, "A5B7", CardNetwork.VISA
    )
    assert valid
    assert error is None

    # Invalid VISA field
    valid, error = validator._validate_network_field(
        44, "XYZ@", CardNetwork.VISA
    )
    assert not valid
    assert "Invalid VISA field 44 format" in error

    # Mastercard field validation
    valid, error = validator._validate_network_field(
        48, "MC01", CardNetwork.MASTERCARD
    )
    assert valid
    assert error is None


def test_validate_field_compatibility(validator):
    """Test field version compatibility"""
    # Test 2003 version compatibility
    errors = validator.validate_field_compatibility(
        43, "A" * 256, ISO8583Version.V2003
    )
    assert len(errors) == 0

    # Test 1987 version compatibility
    errors = validator.validate_field_compatibility(
        43, "A" * 256, ISO8583Version.V1987
    )
    assert len(errors) > 0  # Too long for 1987 version


def test_validate_message_field_padding(validator, test_messages, create_message):
    """Test field padding validation"""
    message = create_message('basic_auth', test_messages)
    errors = validator.validate_message(message)
    assert len(errors) == 0

    # Test with invalid padding
    message.fields[41] = "TEST"  # Too short
    errors = validator.validate_message(message)
    assert len(errors) > 0
    assert any("length must be" in error for error in errors)


def test_validate_message_completeness(validator, test_messages, create_message):
    """Test message completeness validation"""
    # Test complete message
    message = create_message('visa_auth', test_messages)
    errors = validator.validate_message(message)
    assert len(errors) == 0

    # Test incomplete message
    incomplete = ISO8583Message(
        mti="0100",
        fields={0: "0100"},  # Missing required fields
        network=CardNetwork.VISA
    )
    errors = validator.validate_message(incomplete)
    assert len(errors) > 0
