# tests/test_validator.py
from iso8583sim.core.types import CardNetwork, FieldDefinition, FieldType, ISO8583Message, ISO8583Version


def test_validate_field_numeric(validator):
    """Test numeric field validation"""
    field_def = FieldDefinition(field_type=FieldType.NUMERIC, max_length=6, description="Test numeric")

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
    field_def = FieldDefinition(field_type=FieldType.ALPHA, max_length=4, description="Test alpha")

    # Valid cases
    valid, error = validator.validate_field(1, "ABCD", field_def)
    assert valid
    assert error is None

    # Invalid cases
    valid, error = validator.validate_field(1, "ABC1", field_def)
    assert not valid  # contains number


def test_validate_field_alphanumeric(validator):
    """Test alphanumeric field validation"""
    field_def = FieldDefinition(field_type=FieldType.ALPHANUMERIC, max_length=6, description="Test alphanumeric")

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
    # Create test message with network-specific fields
    message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",
            4: "000000001000",
            11: "123456",
            14: "2412",
            22: "021",
            24: "001",
            25: "00",
            41: "TEST1234",
            42: "MERCHANT12345  ",
            44: "A5B7",
        },
        network=CardNetwork.VISA,
    )

    errors = validator.validate_message(message)
    assert len(errors) == 0


def test_validate_message_network_compliance(validator):
    """Test network-specific message validation"""
    # Test with valid message
    complete_message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",
            4: "000000001000",
            11: "123456",
            14: "2412",
            22: "021",
            24: "001",
            25: "00",
            41: "TEST1234",
            42: "MERCHANT12345  ",
            44: "A5B7",
        },
        network=CardNetwork.VISA,
    )
    errors = validator.validate_network_compliance(complete_message)
    assert len(errors) == 0

    # Test incomplete message
    incomplete_message = ISO8583Message(mti="0100", fields={0: "0100", 2: "4111111111111111"}, network=CardNetwork.VISA)
    errors = validator.validate_network_compliance(incomplete_message)
    assert len(errors) > 0
    assert any("Required field" in error for error in errors)


def test_validate_emv_data(validator):
    """Test EMV data validation"""
    # Valid EMV data
    valid_data = [
        ("9F0607A0000000031010", "Simple EMV tag"),
        ("9F0607A00000000310109F15020001", "Multiple EMV tags"),
        ("9F33036028C89F3501229F40056000F0A001", "Complex EMV data"),
    ]

    for data, desc in valid_data:
        errors = validator.validate_emv_data(data)
        assert len(errors) == 0, f"Should be valid ({desc}): {data}"

    # Invalid EMV data
    invalid_data = [
        ("9F", "Incomplete tag"),
        ("XX0607A0000000031010", "Invalid tag"),
        ("9F06XX", "Invalid length"),
        ("9F0607A0000000", "Incomplete value"),
    ]

    for data, desc in invalid_data:
        errors = validator.validate_emv_data(data)
        assert len(errors) > 0, f"Should be invalid ({desc}): {data}"


def test_validate_field_padding(validator):
    """Test field padding validation"""
    field_def = FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=15,
        description="Test right pad",
        padding_char=" ",
        padding_direction="right",
    )

    # Test exact length with padding
    valid, error = validator.validate_field(42, "MERCHANT12345  ", field_def)
    assert valid, "Field with correct padding should be valid"
    assert error is None

    # Test insufficient length
    valid, error = validator.validate_field(42, "MERCHANT123", field_def)
    assert not valid, "Field with insufficient length should be invalid"


def test_validate_field_length(validator):
    """Test field length validation"""
    field_def = FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Test fixed length",
        padding_char="0",
        padding_direction="left",
    )

    # Test exact length
    valid, error = validator.validate_field(3, "123456", field_def)
    assert valid
    assert error is None

    # Test too short
    valid, error = validator.validate_field(3, "12345", field_def)
    assert not valid

    # Test too long
    valid, error = validator.validate_field(3, "1234567", field_def)
    assert not valid


def test_validate_field_compatibility(validator):
    """Test field version compatibility"""
    # Test 2003 version field
    errors = validator.validate_field_compatibility(43, "A" * 256, ISO8583Version.V2003)
    assert len(errors) == 0

    # Test same field with 1987 version (too long)
    errors = validator.validate_field_compatibility(43, "A" * 256, ISO8583Version.V1987)
    assert len(errors) > 0
