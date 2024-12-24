# tests/test_parser.py
from pathlib import Path

import pytest
from datetime import datetime
from iso8583sim.core.types import (
    ISO8583Message,
    ISO8583Version,
    CardNetwork,
    ParseError,
    FieldType,
    FieldDefinition
)
from iso8583sim.core.parser import ISO8583Parser


@pytest.fixture
def parser():
    """Fixture for parser instance"""
    return ISO8583Parser()


@pytest.fixture
def network_message():
    """Message for testing network detection"""
    return ("0100" +  # MTI
            "4000000000000000" +  # Bitmap
            "164111111111111111")  # Field 2 (PAN)


@pytest.fixture
def test_messages(tmp_path) -> Path:
    """Create test file with valid messages"""
    messages = [
        # Message 1: Authorization with EMV
        ("0100" +  # MTI
         "0000000000100000" +  # Bitmap (field 55)
         "209F0607A0000000031010"  # Field 55 (EMV)
         ),
        # Message 2: Financial with PAN
        ("0200" +  # MTI
         "4000000000000000" +  # Bitmap (field 2)
         "164111111111111111"  # Field 2 (PAN)
         )
    ]

    test_file = tmp_path / "test_messages.txt"
    test_file.write_text("\n".join(messages))
    return test_file


@pytest.fixture
def binary_message():
    """Fixture for message with binary field"""
    return ("0100" +  # MTI
            "0000000001000000" +  # Bitmap (field 52 present)
            "0123456789ABCDEF")  # Field 52 (binary data)


@pytest.fixture
def emv_message():
    """Fixture for message with EMV data"""
    return ("0100" +  # MTI
            "0000000000100000" +  # Bitmap (field 55 present)
            "209F0607A0000000031010")  # Field 55 (EMV data) with length prefix


@pytest.fixture
def visa_message():
    """Fixture for VISA test message"""
    return ("0100" +  # MTI
            "0000100000000000" +  # Bitmap with field 44 set
            "03123")  # Field 44 (LLVAR) with length '03' and data '123'


@pytest.fixture
def visa_response():
    """VISA response message"""
    return ("0110" +  # MTI
            "0000100000000000" +  # Bitmap
            "03A5B")  # Field 44 (Additional Response Data)


@pytest.fixture
def mastercard_message():
    """Fixture for Mastercard message"""
    # Mastercard Financial Request
    return ("0200" +  # MTI
            "7000000000000000" +  # Bitmap
            "5111111111111111" +  # Field 2 (PAN)
            "000000" +  # Field 3
            "000000002000" +  # Field 4
            "0701234567" +  # Field 7
            "123456")  # Field 11


@pytest.fixture
def pan_message():
    """Fixture for PAN detection"""
    return ("0100" +  # MTI
            "4000000000000000" +  # Bitmap (only field 2 present)
            "164111111111111111")  # Field 2 (16 digits PAN) with length prefix


@pytest.fixture
def padded_message():
    """Message with padded fields"""
    return ("0100" +  # MTI
            "4200000000000000" +  # Bitmap (fields 41,42)
            "TEST1234" +  # Field 41 (8 chars)
            "MERCHANT12345     ")  # Field 42 (15 chars)


def test_parse_mti(parser, visa_message):
    """Test MTI parsing"""
    parser._raw_message = visa_message
    parser._current_position = 0
    mti = parser._parse_mti()
    assert mti == "0100"
    assert parser._current_position == 4


def test_parse_bitmap(parser):
    """Test bitmap parsing"""
    parser._raw_message = ("0100" + "7000000000000000")
    parser._current_position = 4

    bitmap = parser._parse_bitmap()
    assert bitmap == "7000000000000000"
    assert parser._current_position == 20  # 4 + 16


@pytest.fixture
def sample_bitmap():
    """Sample bitmap with fields 2, 3, 4, 7, and 11 set"""
    # Converting to binary: fields 2,3,4,7,11 are set
    return "7220000000000000"  # This sets bits for fields 2,3,4,7,11


def test_get_present_fields(parser, sample_bitmap):
    """Test present fields detection from bitmap"""
    fields = parser._get_present_fields(sample_bitmap)
    assert fields == [2, 3, 4, 7, 11]
    assert len(fields) == 5  # Exactly 5 fields should be present


def test_bitmap_with_secondary(parser):
    """Test bitmap parsing with secondary bitmap"""
    # Primary bitmap with first bit set (indicating secondary bitmap)
    message = ("0100" +  # MTI
               "C000000000000000" +  # Primary bitmap
               "0000000000000000" +  # Secondary bitmap
               "123456")  # Some data

    parser._raw_message = message
    parser._current_position = 4  # After MTI

    bitmap = parser._parse_bitmap()
    assert len(bitmap) == 32  # Should have both primary and secondary
    assert parser._secondary_bitmap == True


def test_field_length_validation(parser):
    """Test field length validation during parsing"""
    # Message with truncated field
    message = ("0100" +  # MTI
               "8220000000000000" +  # Bitmap
               "1234")  # Truncated data

    with pytest.raises(ParseError) as exc_info:
        parser.parse(message)
    assert "Message too short" in str(exc_info.value)


def test_variable_length_field_parsing(parser):
    """Test parsing of LLVAR and LLLVAR fields"""
    # LLVAR field (field 2 - PAN)
    message = ("0100" +  # MTI
               "4000000000000000" +  # Bitmap (only field 2 present)
               "164111111111111111")  # Field 2 (16 digits PAN with length indicator)

    parsed = parser.parse(message)
    assert parsed.fields[2] == "4111111111111111"
    assert len(parsed.fields[2]) == 16


def test_parse_with_padding(parser, padded_message):
    """Test parsing fields with padding"""
    parsed = parser.parse(padded_message)
    assert parsed.fields[41] == "TEST1234"


def test_network_detection(parser, pan_message):
    """Test network detection from PAN"""
    parsed = parser.parse(pan_message)
    assert parsed.network == CardNetwork.VISA


def test_parse_network_specific_fields(parser, visa_message):
    """Test parsing network-specific fields"""
    parsed = parser.parse(visa_message, network=CardNetwork.VISA)
    assert '44' in parsed.fields
    assert parsed.fields[44] == "123"


def test_parse_variable_length_field(parser):
    """Test parsing LLVAR and LLLVAR fields"""
    # Test LLVAR (field 2 - PAN)
    message = ("0100" +  # MTI
               "4000000000000000" +  # Bitmap
               "164111111111111111")  # Field 2 (16 digits PAN with length indicator)

    parsed = parser.parse(message)
    assert parsed.fields[2] == "4111111111111111"


def test_parse_binary_fields(parser, binary_message):
    """Test parsing binary fields"""
    parsed = parser.parse(binary_message)
    assert '52' in parsed.fields
    assert parsed.fields[52] == "0123456789ABCDEF"


def test_parse_emv_data(parser):
    """Test EMV data parsing"""
    message = ("0100" +  # MTI
               "0000000000100000" +  # Bitmap (field 55)
               "209F0607A0000000031010")  # Field 55 (EMV)

    parsed = parser.parse(message)
    assert 55 in parsed.fields
    assert "9F06" in parsed.fields[55]
    assert len(parsed.fields[55]) == 20


def test_validate_emv_data(validator, valid_emv_data, invalid_emv_data):
    """Test EMV data validation"""
    # Test valid data
    for data in valid_emv_data:
        errors = validator.validate_emv_data(data)
        assert len(errors) == 0, f"Should be valid: {data}"

    # Test invalid data
    for data in invalid_emv_data:
        errors = validator.validate_emv_data(data)
        assert len(errors) > 0, f"Should be invalid: {data}"


def test_parse_with_different_versions(parser):
    """Test parsing with different ISO versions"""
    # 1993 version message
    parser_93 = ISO8583Parser(version=ISO8583Version.V1993)
    message = ("0100" +  # MTI
               "4000000000000000" +  # Bitmap
               "164111111111111111")  # Field 2

    parsed = parser_93.parse(message)
    assert parsed.version == ISO8583Version.V1993


def test_parse_with_extended_bitmap(parser):
    """Test parsing message with secondary bitmap"""
    message = ("0100" +  # MTI
               "C000000000000000" +  # Primary bitmap (C indicates secondary bitmap)
               "0000000000000000" +  # Secondary bitmap
               "164111111111111111")  # Field 2

    parsed = parser.parse(message)
    assert len(parsed.bitmap) == 32  # 16 bytes primary + 16 bytes secondary


def test_parse_error_handling(parser):
    """Test error handling during parsing"""
    # Test invalid MTI
    with pytest.raises(ParseError):
        parser.parse("A10082200000000000")

    # Test truncated message
    with pytest.raises(ParseError):
        parser.parse("0100")

    # Test invalid field length
    with pytest.raises(ParseError):
        parser.parse("010082200000000000FF")  # Invalid PAN length


def test_parse_multiple_messages(parser, test_messages):
    """Test parsing multiple messages"""
    messages = parser.parse_file(str(test_messages))
    assert len(messages) == 2

    # Check first message (EMV)
    assert messages[0].mti == "0100"
    assert 55 in messages[0].fields
    assert "9F06" in messages[0].fields[55]

    # Check second message (PAN)
    assert messages[1].mti == "0200"
    assert messages[1].fields[2] == "4111111111111111"


def test_network_specific_formatting(parser):
    """Test network-specific field formatting"""
    visa_msg = ("0100" +  # MTI
                "0000100000000000" +  # Bitmap (field 44 present)
                "04ABCD")  # Field 44 with length prefix

    parsed = parser.parse(visa_msg, network=CardNetwork.VISA)
    assert parsed.fields[44] == "ABCD"
