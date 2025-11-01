# tests/test_builder.py

import pytest

from iso8583sim.core.types import (
    BuildError,
    CardNetwork,
    FieldDefinition,
    FieldType,
    ISO8583Message,
    ISO8583Version,
    get_field_definition,
)

# Using all common fixtures from conftest.py: builder, parser, validator, test_messages, create_message


@pytest.fixture
def binary_message():
    """Message with binary fields - specific to binary field testing"""
    return ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            52: "0123456789ABCDEF",  # 16 hex chars = 8 bytes
            96: "0123456789ABCDEF",  # 16 hex chars = 8 bytes
        },
    )


def test_build_numeric_fields(builder):
    """Test building numeric fields with proper formatting"""
    message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            3: "000000",  # Processing Code (n6)
            4: "000000001234",  # Amount (n12)
            11: "123456",  # STAN (n6)
            39: "00",  # Response Code (n2)
        },
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
            41: "TEST1234",  # Terminal ID (exactly 8 chars)
            42: "MERCHANT12345  ",  # Card Acceptor ID (exactly 15 chars)
        },
    )

    result = builder.build(message)
    assert "TEST1234" in result  # Field 41 exact length
    assert "MERCHANT12345  " in result  # Field 42 exact length


def test_build_bitmap(builder, test_messages, create_message):
    """Test bitmap building"""
    message = create_message("basic_auth", test_messages)
    bitmap = builder._build_bitmap(message.fields)
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
    field_def = FieldDefinition(field_type=FieldType.LLVAR, max_length=19, description="Test LLVAR")
    value = builder._build_field(2, "4111111111111111", field_def)
    assert value == "164111111111111111"  # 16 is length prefix

    # Test fixed-length numeric with padding
    field_def = FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Test numeric",
        padding_char="0",
        padding_direction="left",
    )
    value = builder._build_field(3, "123", field_def)
    assert value == "000123"


def test_build_binary_fields(builder, binary_message):
    """Test building binary fields with proper formatting"""
    result = builder.build(binary_message)
    assert "0123456789ABCDEF" in result  # Field 52
    assert "0123456789ABCDEF" in result  # Field 96


def test_build_with_secondary_bitmap(builder):
    """Test building message with secondary bitmap"""
    message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            65: "1234567890123456",  # Field in secondary bitmap
        },
    )

    result = builder.build(message)
    assert len(result) > 20
    binary = bin(int(result[4:20], 16))[2:].zfill(64)
    assert binary[0] == "1"  # Secondary bitmap indicator


def test_build_network_specific(builder, test_messages, create_message):
    """Test building network-specific messages"""
    visa_msg = create_message("visa_auth", test_messages)
    result = builder.build(visa_msg)
    assert result is not None
    assert "A5B7" in result  # VISA-specific field 44


def test_build_network_specific_fields(builder, test_messages, create_message):
    """Test building network-specific fields"""
    visa_msg = create_message("visa_auth", test_messages)
    result = builder.build(visa_msg)

    assert result is not None
    assert "4111111111111111" in result  # PAN
    assert "000000" in result  # Processing code
    assert "123456" in result  # STAN
    assert "MERCHANT12345  " in result  # Merchant ID with proper padding


def test_build_response_message(builder, test_messages, create_message):
    """Test building response message"""
    request = create_message("basic_auth", test_messages)
    response_fields = {
        39: "00",  # Approval code
        54: "000000001000",  # Additional amount
    }

    response = builder.create_response(request, response_fields)
    result = builder.build(response)

    assert response.mti == "0110"
    assert "00" in result
    assert "000000001000" in result


def test_build_reversal_message(builder, test_messages, create_message):
    """Test building reversal message"""
    original = create_message("basic_auth", test_messages)
    extra_fields = {
        39: "00",
        90: "0100123456".ljust(42, "0"),  # 42 chars
    }

    reversal = builder.create_reversal(original, extra_fields)
    builder.build(reversal)  # Verify build succeeds

    assert reversal.mti == "0400"
    assert len(reversal.fields[90]) == 42


def test_build_network_management_message(builder):
    """Test building network management message"""
    message = builder.create_network_management_message(message_type="301", network=CardNetwork.VISA)

    builder.build(message)  # Verify build succeeds
    assert message.mti == "0800"
    assert message.fields[70] == "301"
    assert len(message.fields[96]) == 16


def test_build_emv_data(builder):
    """Test building EMV data"""
    emv_tags = {"9F06": "A0000000031010", "9F1A": "840", "9F33": "E0F8C8"}

    emv_data = builder.build_emv_data(emv_tags)
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
                3: "12A34",  # Invalid: contains letter
            },
        )
        builder.build(message)
    assert "must contain only digits" in str(exc_info.value)


def test_build_error_handling(builder):
    """Test error handling during message building"""
    message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            3: "ABC",  # Must be numeric
        },
    )
    with pytest.raises(BuildError) as exc_info:
        builder.build(message)
    assert "must contain only digits" in str(exc_info.value)


def test_build_version_specific(builder):
    """Test building with different ISO versions"""
    message_93 = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            43: "A" * 99,  # 1993 version max length
        },
        version=ISO8583Version.V1993,
    )
    result_93 = builder.build(message_93)
    assert len(result_93) > 20

    message_03 = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            43: "A" * 256,  # 2003 version max length
        },
        version=ISO8583Version.V2003,
    )
    result_03 = builder.build(message_03)
    assert len(result_03) > 20


def test_message_recreation(builder, parser, test_messages, create_message):
    """Test complete building and parsing cycle"""
    # Using basic_auth message as base
    original = create_message("basic_auth", test_messages)

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
    for field_num, _value in original.fields.items():
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
            if field_def.field_type == FieldType.BINARY:
                # For binary fields, string length should be twice max_length
                assert (
                    len(parsed_value) == field_def.max_length * 2
                ), f"Field {field_num} length mismatch: {len(parsed_value)} != {field_def.max_length * 2}"
            else:
                assert (
                    len(parsed_value) == field_def.max_length
                ), f"Field {field_num} length mismatch: {len(parsed_value)} != {field_def.max_length}"

        # Check field type-specific validations
        if field_def.field_type == FieldType.NUMERIC:
            assert parsed_value.isdigit(), f"Field {field_num} should be numeric"
        elif field_def.field_type == FieldType.BINARY:
            assert all(
                c in "0123456789ABCDEF" for c in parsed_value.upper()
            ), f"Field {field_num} should be hexadecimal"
        elif field_def.field_type == FieldType.ALPHA:
            assert parsed_value.replace(" ", "").isalpha(), f"Field {field_num} should be alphabetic"

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
        padding_direction="right",
    )
    value = builder._build_field(41, "TEST", field_def)
    assert value == "TEST    "  # 4 spaces padding

    # Left-padded numeric field
    field_def = FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Test left pad",
        padding_char="0",
        padding_direction="left",
    )
    value = builder._build_field(3, "123", field_def)
    assert value == "000123"
