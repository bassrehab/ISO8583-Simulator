# tests/test_builder.py
import pytest
from datetime import datetime
from iso8583sim.core.types import (
    ISO8583Message,
    ISO8583Version,
    CardNetwork,
    FieldType,
    FieldDefinition,
    BuildError,
    MessageFunction
)
from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.parser import ISO8583Parser


@pytest.fixture
def builder():
    """Fixture for builder instance"""
    return ISO8583Builder()


@pytest.fixture
def parser():
    """Fixture for parser instance to verify built messages"""
    return ISO8583Parser()


@pytest.fixture
def sample_message():
    """Sample message with correctly padded fields"""
    return ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",
            4: "000000001000",
            11: "123456",
            41: "TEST1234".ljust(8),  # 8 characters
            42: "MERCHANT12345".ljust(15),  # 15 characters
            96: "0000000000000000"  # 16 hex digits
        }
    )


@pytest.fixture
def visa_message():
    """Sample VISA message with network-specific fields"""
    return ISO8583Message(
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
            44: "A5B7"
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
            11: "123456",
            48: "MC123",  # Mastercard specific field
            104: "MC TEST"
        },
        network=CardNetwork.MASTERCARD
    )


def test_build_bitmap(builder, sample_message):
    """Test bitmap building"""
    bitmap = builder._build_bitmap(sample_message.fields)

    # Convert hex bitmap to binary string for easier testing
    binary = bin(int(bitmap, 16))[2:].zfill(64)

    # Check specific bits for present fields
    assert binary[1] == "1"  # Field 2
    assert binary[2] == "1"  # Field 3
    assert binary[3] == "1"  # Field 4
    assert binary[10] == "1"  # Field 11
    assert binary[11] == "1"  # Field 12
    assert binary[12] == "1"  # Field 13
    assert binary[40] == "1"  # Field 41
    assert binary[41] == "1"  # Field 42


def test_build_field(builder):
    """Test building individual fields"""
    # Test LLVAR field
    field_def = FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=19,
        description="Test LLVAR"
    )
    value = builder._build_field(2, "4111111111111111", field_def)
    assert value == "164111111111111111"  # 16 is length prefix

    # Test fixed-length numeric with padding
    field_def = FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Test numeric",
        padding_char="0",
        padding_direction="left"
    )
    value = builder._build_field(3, "123", field_def)
    assert value == "000123"


def test_build_with_secondary_bitmap(builder):
    """Test building message with secondary bitmap"""
    message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            65: "0000000000000000",  # 16 hex chars for 8 bytes
            100: "TEST100"
        }
    )
    result = builder.build(message)
    assert len(result) > 20
    binary = bin(int(result[4:20], 16))[2:].zfill(64)
    assert binary[0] == "1"


def test_build_network_specific(builder):
    """Test building network-specific messages"""
    # VISA message
    visa_message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",  # Ensure numeric
            4: "000000001000",
            44: "A5B7"
        },
        network=CardNetwork.VISA
    )
    visa_result = builder.build(visa_message)
    assert "A5B7" in visa_result


def test_build_response_message(builder, sample_message):
    """Test building response message"""
    response_fields = {
        39: "00",  # 2-digit response code
        54: "000000001000"  # Additional amount
    }
    response = builder.create_response(sample_message, response_fields)
    assert response.mti == "0110"  # Changed from 0100 to 0110
    assert response.fields[39] == "00"
    assert response.fields[54] == "000000001000"


def test_build_reversal_message(builder, sample_message):
    """Test building reversal message"""
    # Add the correct field lengths for reversal message
    extra_fields = {
        39: "00",  # 2-digit response code
        90: "0" * 42,  # 42 digits for original data elements
    }
    reversal = builder.create_reversal(sample_message, extra_fields)
    assert reversal.mti == "0400"
    assert len(reversal.fields[90]) == 42


def test_build_network_management_message(builder):
    """Test building network management message"""
    message = builder.create_network_management_message(
        message_type="301",
        network=CardNetwork.VISA
    )
    assert message.mti == "0800"
    assert message.fields[70] == "301"
    assert len(message.fields[96]) == 16  # 8 bytes = 16 hex chars


def test_build_emv_data(builder):
    """Test building EMV data"""
    emv_tags = {
        "9F06": "A0000000031010",
        "9F1A": "840",
        "9F33": "E0F8C8"
    }

    emv_data = builder.build_emv_data(emv_tags)

    # Verify each tag is present
    assert "9F06" in emv_data
    assert "A0000000031010" in emv_data
    assert "9F1A" in emv_data
    assert "840" in emv_data


def test_build_error_handling(builder):
    """Test error handling during message building"""
    # Test invalid MTI
    invalid_message = ISO8583Message(
        mti="0A00",  # Non-numeric MTI
        fields={0: "0A00"}
    )
    with pytest.raises(BuildError):
        builder.build(invalid_message)

    # Test invalid field length
    invalid_message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            3: "12345"  # Should be 6 digits
        }
    )
    with pytest.raises(BuildError):
        builder.build(invalid_message)


def test_build_version_specific(builder):
    """Test building with different ISO versions"""
    # Test with 1993 version field lengths
    message_93 = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            43: "A" * 99  # 1993 version length
        },
        version=ISO8583Version.V1993
    )
    result_93 = builder.build(message_93)
    assert len(result_93) > 20

    # Test with 2003 version
    message_03 = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            43: "A" * 256  # 2003 version length
        },
        version=ISO8583Version.V2003
    )
    result_03 = builder.build(message_03)
    assert len(result_03) > 20


def test_message_recreation(builder, parser, sample_message):
    """Test building and parsing cycle"""
    # Build message
    built = builder.build(sample_message)
    # Parse the built message
    parsed = parser.parse(built)

    # Compare original and parsed
    assert parsed.mti == sample_message.mti
    for field_num, value in sample_message.fields.items():
        if field_num != 0:  # Skip MTI which is both field 0 and mti
            assert parsed.fields[field_num] == value


def test_field_padding_handling(builder):
    """Test field padding behavior"""
    # Right-padded alphanumeric field
    field_def = FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=8,
        description="Test right pad",
        padding_char=" ",
        padding_direction="right"
    )
    value = builder._build_field(41, "TEST", field_def)
    assert value == "TEST    "  # 4 spaces padding

    # Left-padded numeric field
    field_def = FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Test left pad",
        padding_char="0",
        padding_direction="left"
    )
    value = builder._build_field(3, "123", field_def)
    assert value == "000123"
