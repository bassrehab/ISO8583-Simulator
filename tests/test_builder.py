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
    MessageFunction,
    get_field_definition
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
    """Sample message with correctly formatted fields"""
    return ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",  # Fixed: properly formatted processing code
            4: "000000001000",
            11: "123456",
            41: "TEST1234",  # Fixed: 8 characters
            42: "MERCHANT12345 ",  # Fixed: 15 characters with space padding
            96: "0000000000000000"  # Fixed: 16 hex digits
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
            3: "000000",  # Fixed: properly formatted
            4: "000000001000",
            11: "123456",
            14: "2412",  # Required VISA field
            22: "021",  # Required VISA field
            24: "001",  # Required VISA field
            25: "00",  # Required VISA field
            41: "TEST1234",
            42: "MERCHANT12345 ",
            44: "A5B7"  # VISA specific field
        },
        network=CardNetwork.VISA
    )


@pytest.fixture
def mastercard_message():
    """Sample Mastercard message"""
    return ISO8583Message(
        mti="0200",
        fields={
            0: "0200",
            2: "5111111111111111",
            3: "000000",  # Fixed: properly formatted
            4: "000000001000",
            11: "123456",
            22: "021",
            24: "001",
            25: "00",
            48: "MC123",  # Mastercard specific field
            96: "0000000000000000"  # Fixed: proper length
        },
        network=CardNetwork.MASTERCARD
    )


@pytest.fixture
def binary_message():
    """Message with binary fields"""
    return ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            52: "0123456789ABCDEF",  # Fixed: proper hex format
            96: "0000000000000000"  # Fixed: proper length
        }
    )


@pytest.fixture
def emv_message():
    """Message with EMV data"""
    return ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            55: "9F0607A0000000031010"  # EMV data
        }
    )


def test_build_numeric_fields(builder):
    """Test building numeric fields with proper formatting"""
    message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            3: "000000",  # Properly formatted processing code
            4: "000000001234",  # Properly formatted amount
            11: "123456",  # STAN
            39: "00"  # Properly formatted response code
        }
    )

    result = builder.build(message)
    assert result is not None
    assert "000000" in result  # Field 3
    assert "000000001234" in result  # Field 4
    assert "123456" in result  # Field 11
    assert "00" in result  # Field 39


def test_build_alphanumeric_fields(builder):
    """Test building alphanumeric fields with proper formatting"""
    message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            41: "TEST1234",  # Terminal ID (8 chars)
            42: "MERCH123",  # Merchant ID (15 chars)
        }
    )

    result = builder.build(message)
    assert "TEST1234" in result  # Field 41 exact length
    assert "MERCH123       " in result  # Field 42 right-padded


def test_build_bitmap(builder):
    """Test bitmap building"""
    message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",
            4: "000000001000",
            11: "123456",
            41: "TEST1234",
            42: "MERCHANT12345 "
        }
    )

    bitmap = builder._build_bitmap(message.fields)
    # Convert hex bitmap to binary string for testing
    binary = bin(int(bitmap, 16))[2:].zfill(64)

    assert binary[1] == "1"  # Field 2
    assert binary[2] == "1"  # Field 3
    assert binary[3] == "1"  # Field 4
    assert binary[10] == "1"  # Field 11
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


def test_build_binary_fields(builder):
    """Test building binary fields with proper formatting"""
    message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            52: "0123456789ABCDEF",  # 8 bytes binary data
            96: "0123456789ABCDEF"  # 8 bytes message security code
        }
    )

    result = builder.build(message)
    assert "0123456789ABCDEF" in result  # Field 52
    assert "0123456789ABCDEF" in result  # Field 96


def test_build_with_secondary_bitmap(builder):
    """Test building message with secondary bitmap"""
    message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            65: "1234567890123456"  # 8 bytes field 65
        }
    )

    result = builder.build(message)
    assert len(result) > 20
    binary = bin(int(result[4:20], 16))[2:].zfill(64)
    assert binary[0] == "1"  # Secondary bitmap indicator


def test_build_network_specific(builder):
    """Test building network-specific messages"""
    visa_message = ISO8583Message(
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
            42: "MERCHANT12345 ",
            44: "A5B7"
        },
        network=CardNetwork.VISA
    )

    result = builder.build(visa_message)
    assert result is not None
    assert "A5B7" in result

def test_build_network_specific_fields(builder):
    """Test building network-specific fields"""
    # VISA message with required fields
    visa_message = ISO8583Message(
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
            42: "MERCHANT12345 "
        },
        network=CardNetwork.VISA
    )

    result = builder.build(visa_message)
    assert result is not None
    assert "4111111111111111" in result  # PAN
    assert "000000" in result  # Processing code
    assert "123456" in result  # STAN
    assert "MERCHANT12345 " in result  # Merchant ID


def test_build_response_message(builder):
    """Test building response message"""
    request = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",
            4: "000000001000",
            11: "123456",
            41: "TEST1234",
            42: "MERCHANT12345 "
        }
    )

    response_fields = {
        39: "00",  # Properly formatted response code
        54: "000000001000"  # Additional amount
    }

    response = builder.create_response(request, response_fields)
    result = builder.build(response)

    assert response.mti == "0110"
    assert "00" in result
    assert "000000001000" in result


def test_build_reversal_message(builder):
    """Test building reversal message"""
    original = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",
            4: "000000001000",
            11: "123456",
            41: "TEST1234",
            42: "MERCHANT12345 "
        }
    )

    extra_fields = {
        39: "00",
        90: "000000000000000000000000000000000000000000"  # 42 digits
    }

    reversal = builder.create_reversal(original, extra_fields)
    result = builder.build(reversal)

    assert reversal.mti == "0400"
    assert len(reversal.fields[90]) == 42


def test_build_network_management_message(builder):
    """Test building network management message"""
    message = builder.create_network_management_message(
        message_type="301",
        network=CardNetwork.VISA
    )

    result = builder.build(message)
    assert message.mti == "0800"
    assert message.fields[70] == "301"
    # Updated length check for field 96
    assert len(message.fields[96]) == 16

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


def test_build_field_validation_errors(builder):
    """Test field validation error handling"""
    with pytest.raises(BuildError) as exc_info:
        message = ISO8583Message(
            mti="0100",
            fields={
                0: "0100",
                3: "12A34"  # Invalid: contains letter
            }
        )
        builder.build(message)
    assert "must contain only digits" in str(exc_info.value)


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


def test_message_recreation(builder, parser):
    """Test complete building and parsing cycle"""
    # Create original message with all types of fields
    original = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",  # PAN (LLVAR)
            3: "000000",  # Processing Code (n6)
            4: "000000001000",  # Amount (n12)
            11: "123456",  # STAN (n6)
            12: "104234",  # Time (n6)
            13: "0125",  # Date (n4)
            22: "021",  # POS Entry Mode (n3)
            25: "00",  # POS Condition Code (n2)
            41: "TEST1234",  # Terminal ID (ans8)
            42: "MERCHANT12345 ",  # Merchant ID (ans15)
            49: "840",  # Currency Code (n3)
            96: "0123456789ABCDEF"  # Message Security Code (b8)
        },
        version=ISO8583Version.V1987
    )

    try:
        # Build message
        built = builder.build(original)
        assert built is not None
        assert isinstance(built, str)

        # Parse the built message
        parsed = parser.parse(built)
        assert parsed is not None

        # Validate message-level attributes
        assert parsed.mti == original.mti
        assert parsed.version == original.version
        assert parsed.bitmap is not None
        assert parsed.raw_message == built

        # Validate fields
        for field_num, value in original.fields.items():
            if field_num == 0:  # Skip MTI as it's also in fields[0]
                continue

            # Assert field presence
            assert field_num in parsed.fields, f"Field {field_num} missing in parsed message"

            # Get field definition
            field_def = get_field_definition(field_num, version=original.version)
            assert field_def is not None, f"No definition for field {field_num}"

            parsed_value = parsed.fields[field_num]

            # Check field length
            if field_def.field_type not in [FieldType.LLVAR, FieldType.LLLVAR]:
                assert len(parsed_value) == field_def.max_length, \
                    f"Field {field_num} length mismatch: {len(parsed_value)} != {field_def.max_length}"

            # Check padding for fixed-length fields
            if field_def.padding_char:
                if field_def.padding_direction == 'left':
                    assert parsed_value.lstrip(field_def.padding_char) == \
                           value.lstrip(field_def.padding_char), \
                        f"Field {field_num} left padding mismatch"
                else:
                    assert parsed_value.rstrip(field_def.padding_char) == \
                           value.rstrip(field_def.padding_char), \
                        f"Field {field_num} right padding mismatch"

            # Check specific field types
            if field_def.field_type == FieldType.NUMERIC:
                assert parsed_value.isdigit(), f"Field {field_num} should be numeric"
            elif field_def.field_type == FieldType.BINARY:
                assert all(c in '0123456789ABCDEF' for c in parsed_value.upper()), \
                    f"Field {field_num} should be hexadecimal"
            elif field_def.field_type == FieldType.ALPHA:
                assert parsed_value.replace(' ', '').isalpha(), \
                    f"Field {field_num} should be alphabetic"

            # Check network-specific field formats if network is specified
            if original.network:
                network_def = get_field_definition(field_num, network=original.network)
                if network_def and network_def != field_def:
                    # Additional network-specific validations could be added here
                    assert len(parsed_value) <= network_def.max_length, \
                        f"Network-specific length exceeded for field {field_num}"

    except Exception as e:
        pytest.fail(f"Message recreation test failed: {str(e)}")

    # Validate bitmap reconstruction
    original_bitmap = builder._build_bitmap(original.fields)
    parsed_bitmap = builder._build_bitmap(parsed.fields)
    assert original_bitmap == parsed_bitmap, "Bitmap mismatch between original and parsed message"


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
