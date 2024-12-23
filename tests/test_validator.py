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
from iso8583sim.core.validator import ISO8583Validator


@pytest.fixture
def validator():
    """Fixture for validator instance"""
    return ISO8583Validator()

@pytest.fixture
def valid_message():
    """Fixture for a valid message"""
    return ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",
            4: "000000001000",
            7: "0701234567",
            11: "123456"
        }
    )


@pytest.fixture
def complete_visa_message():
    """Fixture for a complete VISA message"""
    return ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",
            4: "000000001000",
            11: "123456",
            14: "2412",
            22: "051",
            24: "200",
            25: "00",
            44: "A5B7"
        },
        network=CardNetwork.VISA
    )


@pytest.fixture
def visa_message():
    """Fixture for a VISA message"""
    return ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",
            4: "000000001000",
            7: "0701234567",
            11: "123456",
            44: "A5B7",  # VISA specific field
        },
        network=CardNetwork.VISA
    )


@pytest.fixture
def mastercard_message():
    """Fixture for a Mastercard message"""
    return ISO8583Message(
        mti="0200",
        fields={
            0: "0200",
            2: "5111111111111111",
            3: "000000",
            4: "000000001000",
            7: "0701234567",
            11: "123456",
            48: "MC123",  # Mastercard specific field
        },
        network=CardNetwork.MASTERCARD
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


def test_validate_network_specific_fields(validator):
    """Test network-specific field validation"""
    # VISA Additional Response Data (Field 44)
    field_def = NETWORK_SPECIFIC_FIELDS[CardNetwork.VISA][44]
    valid, error = validator.validate_field(44, "A5B7", field_def, CardNetwork.VISA)
    assert valid
    assert error is None

    # Mastercard Private Data (Field 48)
    field_def = NETWORK_SPECIFIC_FIELDS[CardNetwork.MASTERCARD][48]
    valid, error = validator.validate_field(48, "MC123", field_def, CardNetwork.MASTERCARD)
    assert valid
    assert error is None


def test_validate_message_network_compliance(validator, complete_visa_message):
    """Test network-specific message validation"""
    # Test incomplete message
    incomplete_message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111"
        },
        network=CardNetwork.VISA
    )

    errors = validator.validate_message(incomplete_message)
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

    # Test 2003 version field with longer length
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


def test_validate_emv_data(validator):
    """Test EMV data validation"""
    # Valid EMV data
    valid_emv = "9F0607A0000000031010"
    errors = validator.validate_emv_data(valid_emv)
    assert len(errors) == 0

    # Invalid EMV data
    invalid_emv = "9F06"  # Incomplete
    errors = validator.validate_emv_data(invalid_emv)
    assert len(errors) > 0
    assert "Incomplete EMV data" in errors[0]


def test_validate_network_compliance(validator, complete_visa_message):
    """Test network compliance validation"""
    # Test valid message
    errors = validator.validate_network_compliance(complete_visa_message)
    assert len(errors) == 0

    # Test with invalid field format
    complete_visa_message.fields[44] = "XYZ"  # Invalid format for VISA field 44
    errors = validator.validate_network_compliance(complete_visa_message)
    assert len(errors) > 0
    assert "Invalid format for VISA field 44" in errors


def test_validate_field_compatibility(validator):
    """Test field version compatibility"""
    errors = validator.validate_field_compatibility(
        43, "A" * 256, ISO8583Version.V2003
    )
    assert len(errors) == 0

    errors = validator.validate_field_compatibility(
        43, "A" * 256, ISO8583Version.V1987
    )
    assert len(errors) > 0  # Too long for 1987 version


def test_validate_message_field_padding(validator):
    """Test field padding validation"""
    message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            41: "TEST1234"  # 8 chars exactly, no padding needed
        }
    )
    errors = validator.validate_message(message)
    assert len(errors) == 0

    # Test with invalid padding
    message.fields[41] = "TEST"  # Too short
    errors = validator.validate_message(message)
    assert len(errors) > 0
    assert any("length must be" in error for error in errors)
