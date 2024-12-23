# tests/test_parser.py
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
def visa_message():
    """Fixture for VISA message"""
    # VISA Authorization Request
    return ("0100" +  # MTI
            "7000000000000000" +  # Bitmap
            "4111111111111111" +  # Field 2 (PAN)
            "000000" +  # Field 3 (Processing Code)
            "000000001000" +  # Field 4 (Amount)
            "0701234567" +  # Field 7 (Date/Time)
            "123456")  # Field 11 (STAN)


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


def test_parse_mti(parser, visa_message):
    """Test MTI parsing"""
    parser._raw_message = visa_message
    parser._current_position = 0
    mti = parser._parse_mti()
    assert mti == "0100"
    assert parser._current_position == 4


def test_parse_bitmap(parser, visa_message):
    """Test bitmap parsing"""
    parser._raw_message = visa_message
    parser._current_position = 4
    bitmap = parser._parse_bitmap()
    assert bitmap == "7000000000000000"
    assert parser._current_position == 20


def test_get_present_fields(parser):
    """Test present fields detection from bitmap"""
    bitmap = "7000000000000000"
    fields = parser._get_present_fields(bitmap)
    assert fields == [2, 3, 4, 7, 11]


def test_network_detection(parser, visa_message, mastercard_message):
    """Test network detection from PAN"""
    # VISA detection
    visa_result = parser.parse(visa_message)
    assert visa_result.network == CardNetwork.VISA

    # Mastercard detection
    mc_result = parser.parse(mastercard_message)
    assert mc_result.network == CardNetwork.MASTERCARD


def test_parse_network_specific_fields(parser):
    """Test parsing network-specific fields"""
    # VISA specific field 44 (Additional Response Data)
    visa_message = ("0110" +  # MTI
                    "0000100000000000" +  # Bitmap (field 44 present)
                    "03123")  # Field 44 (LLVAR)

    message = parser.parse(visa_message, network=CardNetwork.VISA)
    assert message.fields[44] == "123"


def test_parse_variable_length_field(parser):
    """Test parsing LLVAR and LLLVAR fields"""
    # Test LLVAR (field 2 - PAN)
    message = ("0100" +  # MTI
               "4000000000000000" +  # Bitmap
               "164111111111111111")  # Field 2 (16 digits PAN with length indicator)

    parsed = parser.parse(message)
    assert parsed.fields[2] == "4111111111111111"


def test_parse_binary_fields(parser):
    """Test parsing binary fields"""
    # Message with binary field
    message = ("0100" +  # MTI
               "0000000001000000" +  # Bitmap (field 52 present)
               "0123456789ABCDEF")  # Binary data

    parsed = parser.parse(message)
    assert parsed.fields[52] == "0123456789ABCDEF"


def test_parse_emv_data(parser):
    """Test parsing EMV data (field 55)"""
    # Message with EMV data
    message = ("0100" +  # MTI
               "0000000000100000" +  # Bitmap (field 55 present)
               "0339F0607A0000000031010")  # EMV data with length

    parsed = parser.parse(message)
    emv_data = parser.parse_emv_data(parsed.fields[55])
    assert "9F06" in emv_data  # Check EMV tag presence


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


def test_parse_multiple_messages(parser, tmp_path):
    """Test parsing multiple messages from file"""
    # Create test file
    test_file = tmp_path / "test_messages.txt"
    messages = [
        "01008220000000000000411111111111111100000000000001000123456",
        "02008220000000000000511111111111111100000000000002000123457"
    ]
    test_file.write_text("\n".join(messages))

    # Parse messages
    parsed = parser.parse_file(str(test_file))
    assert len(parsed) == 2
    assert parsed[0].mti == "0100"
    assert parsed[1].mti == "0200"


def test_network_specific_formatting(parser):
    """Test network-specific field formatting"""
    # VISA format
    visa_msg = ("0100" +  # MTI
                "0000100000000000" +  # Bitmap (field 44)
                "04ABCD")  # Field 44

    visa_parsed = parser.parse(visa_msg, network=CardNetwork.VISA)
    assert visa_parsed.fields[44] == "ABCD"  # Should be uppercase

    # Mastercard format
    mc_msg = ("0200" +  # MTI
              "0001000000000000" +  # Bitmap (field 48)
              "006MC123")  # Field 48

    mc_parsed = parser.parse(mc_msg, network=CardNetwork.MASTERCARD)
    assert mc_parsed.fields[48] == "MC123"
