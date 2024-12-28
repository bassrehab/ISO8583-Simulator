# tests/test_parser.py
from pathlib import Path
import pytest
from iso8583sim.core.types import (
    ISO8583Message,
    ISO8583Version,
    CardNetwork,
    ParseError,
    FieldType,
    FieldDefinition
)
from iso8583sim.core.parser import ISO8583Parser


def test_parse_mti(parser):
    """Test MTI parsing"""
    raw_message = "0100" + "4000000000000000" + "164111111111111111"
    parser._raw_message = raw_message
    parser._current_position = 0
    mti = parser._parse_mti()
    assert mti == "0100"
    assert parser._current_position == 4


def test_parse_bitmap(parser):
    """Test bitmap parsing"""
    raw_message = "0100" + "4000000000000000" + "164111111111111111"
    parser._raw_message = raw_message
    parser._current_position = 4

    bitmap = parser._parse_bitmap()
    assert bitmap == "4000000000000000"  # Basic bitmap
    assert parser._current_position == 20  # 4 + 16


def test_get_present_fields(parser):
    """Test present fields detection from bitmap"""
    bitmap = "7220000000000000"  # This sets bits for fields 2,3,4,7,11
    fields = parser._get_present_fields(bitmap)
    assert fields == [2, 3, 4, 7, 11]
    assert len(fields) == 5  # Exactly 5 fields should be present


def test_bitmap_with_secondary(parser):
    """Test bitmap parsing with secondary bitmap"""
    message = ("0100" +  # MTI
               "C000000000000000" +  # Primary bitmap
               "0000000000000000" +  # Secondary bitmap
               "164111111111111111")  # Some data

    parser._raw_message = message
    parser._current_position = 4  # After MTI

    bitmap = parser._parse_bitmap()
    assert len(bitmap) == 32  # Should have both primary and secondary
    assert parser._secondary_bitmap == True


def test_field_length_validation(parser):
    """Test field length validation during parsing"""
    message = ("0100" +  # MTI
               "8220000000000000" +  # Bitmap
               "1234")  # Truncated data

    with pytest.raises(ParseError) as exc_info:
        parser.parse(message)
    assert "Message too short" in str(exc_info.value)


def test_variable_length_field_parsing(parser):
    """Test parsing of LLVAR and LLLVAR fields"""
    message = ("0100" +  # MTI
               "4000000000000000" +  # Bitmap (only field 2 present)
               "164111111111111111")  # Field 2 (16 digits PAN with length indicator)

    parsed = parser.parse(message)
    assert parsed.fields[2] == "4111111111111111"
    assert len(parsed.fields[2]) == 16


def test_parse_with_padding(parser):
    """Test parsing fields with padding"""
    message = ("0100" +  # MTI
               "6000000000000000" +  # Bitmap (fields 41,42)
               "TEST1234" +  # Field 41 (8 chars)
               "MERCHANT12345  ")  # Field 42 (15 chars)

    parsed = parser.parse(message)
    assert parsed.fields[41] == "TEST1234"
    assert parsed.fields[42] == "MERCHANT12345  "


def test_network_detection(parser):
    """Test network detection from PAN"""
    message = ("0100" +  # MTI
               "4000000000000000" +  # Bitmap (only field 2 present)
               "164111111111111111")  # Field 2 (16 digits PAN with length indicator)

    parsed = parser.parse(message)
    assert parsed.network == CardNetwork.VISA  # Based on PAN prefix '4'


def test_parse_network_specific_fields(parser):
    """Test parsing network-specific fields"""
    message = ("0100" +  # MTI
               "0000100000000000" +  # Bitmap with field 44 set
               "03A5B")  # Field 44 (LLVAR) with length '03'

    parsed = parser.parse(message, network=CardNetwork.VISA)
    assert '44' in parsed.fields
    assert parsed.fields[44] == "A5B"


def test_parse_binary_fields(parser):
    """Test parsing binary fields"""
    message = ("0100" +  # MTI
               "0000000001000000" +  # Bitmap (field 52 present)
               "0123456789ABCDEF")  # Field 52 (binary data)

    parsed = parser.parse(message)
    assert '52' in parsed.fields
    assert parsed.fields[52] == "0123456789ABCDEF"


def test_parse_emv_data(parser):
    """Test EMV data parsing"""
    message = ("0100" +  # MTI
               "0000000000100000" +  # Bitmap (field 55)
               "209F0607A0000000031010")  # Field 55 (EMV data) with length prefix 20

    parsed = parser.parse(message)
    assert 55 in parsed.fields
    assert "9F06" in parsed.fields[55]
    assert len(parsed.fields[55]) == 20


def test_parse_with_different_versions(parser):
    """Test parsing with different ISO versions"""
    parser_93 = ISO8583Parser(version=ISO8583Version.V1993)
    message = ("0100" +  # MTI
               "0000000100000000" +  # Bitmap (field 43 set)
               "A" * 99)  # Field 43 can be 99 chars in 1993

    parsed = parser_93.parse(message)
    assert parsed.version == ISO8583Version.V1993


def test_parse_with_extended_bitmap(parser):
    """Test parsing message with secondary bitmap"""
    message = ("0100" +  # MTI
               "C000000000000000" +  # Primary bitmap (C indicates secondary bitmap)
               "0000000000000000" +  # Secondary bitmap
               "164111111111111111")  # Field 2 data

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
    """Test parsing multiple messages"""
    messages = [
        # Message 1: Authorization with EMV
        ("0100" +  # MTI
         "0000000000100000" +  # Bitmap (field 55)
         "209F0607A0000000031010"),  # Field 55 (EMV) with length prefix 20
        # Message 2: Financial with PAN
        ("0200" +  # MTI
         "4000000000000000" +  # Bitmap (field 2)
         "164111111111111111")  # Field 2 (PAN) with length prefix 16
    ]

    test_file = tmp_path / "test_messages.txt"
    test_file.write_text("\n".join(messages))

    parsed_messages = parser.parse_file(str(test_file))
    assert len(parsed_messages) == 2

    # Check EMV message
    assert parsed_messages[0].mti == "0100"
    assert 55 in parsed_messages[0].fields
    assert len(parsed_messages[0].fields[55]) == 20

    # Check PAN message
    assert parsed_messages[1].mti == "0200"
    assert parsed_messages[1].fields[2] == "4111111111111111"


def test_network_specific_formatting(parser):
    """Test network-specific field formatting"""
    message = ("0100" +  # MTI
               "0000100000000000" +  # Bitmap (field 44 present)
               "04ABCD")  # Field 44 (LLVAR) with length prefix

    parsed = parser.parse(message, network=CardNetwork.VISA)
    assert parsed.fields[44] == "ABCD"


def test_parse_field_padding_preservation(parser):
    """Test preservation of field padding"""
    message = ("0100" +  # MTI
               "6000000000000000" +  # Bitmap (fields 41,42)
               "TEST1234" +  # Field 41 (8 chars)
               "MERCHANT12345  ")  # Field 42 (15 chars)

    parsed = parser.parse(message)
    assert len(parsed.fields[41]) == 8
    assert parsed.fields[41] == "TEST1234"
    assert len(parsed.fields[42]) == 15
    assert parsed.fields[42] == "MERCHANT12345  "  # Preserves padding