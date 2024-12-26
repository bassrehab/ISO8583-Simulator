# tests/test_parser.py
from pathlib import Path
import pytest

from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.types import (
    ISO8583Message,
    ISO8583Version,
    CardNetwork,
    ParseError,
    FieldType,
    FieldDefinition
)


def test_parse_mti(parser, test_messages, create_message):
    """Test MTI parsing"""
    visa_msg = create_message('visa_auth', test_messages)
    parser._raw_message = visa_msg.raw_message
    parser._current_position = 0
    mti = parser._parse_mti()
    assert mti == "0100"
    assert parser._current_position == 4


def test_parse_bitmap(parser, test_messages, create_message):
    """Test bitmap parsing"""
    message = create_message('basic_auth', test_messages)
    parser._raw_message = message.raw_message
    parser._current_position = 4

    bitmap = parser._parse_bitmap()
    assert bitmap == "4000000000000000"  # Basic bitmap
    assert parser._current_position == 20  # 4 + 16


def test_get_present_fields(parser):
    """Test present fields detection from bitmap"""
    # Sample bitmap with fields 2,3,4,7,11 set
    bitmap = "7220000000000000"  # This sets bits for fields 2,3,4,7,11
    fields = parser._get_present_fields(bitmap)
    assert fields == [2, 3, 4, 7, 11]
    assert len(fields) == 5


def test_bitmap_with_secondary(parser):
    """Test bitmap parsing with secondary bitmap"""
    message = ("0100" +  # MTI
               "C000000000000000" +  # Primary bitmap
               "0000000000000000" +  # Secondary bitmap
               "123456")  # Some data

    parser._raw_message = message
    parser._current_position = 4

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


def test_variable_length_field_parsing(parser, test_messages, create_message):
    """Test parsing of LLVAR and LLLVAR fields"""
    message = create_message('basic_auth', test_messages)
    parsed = parser.parse(message.raw_message)
    assert parsed.fields[2] == "4111111111111111"
    assert len(parsed.fields[2]) == 16


def test_parse_with_padding(parser, test_messages, create_message):
    """Test parsing fields with padding"""
    message = create_message('basic_auth', test_messages)
    parsed = parser.parse(message.raw_message)
    assert parsed.fields[41] == "TEST1234"  # Terminal ID
    assert parsed.fields[42] == "MERCHANT12345  "  # Card Acceptor ID with proper padding


def test_network_detection(parser, test_messages, create_message):
    """Test network detection from PAN"""
    message = create_message('basic_auth', test_messages)
    parsed = parser.parse(message.raw_message)
    assert parsed.network == CardNetwork.VISA  # Based on PAN prefix '4'


def test_parse_network_specific_fields(parser, test_messages, create_message):
    """Test parsing network-specific fields"""
    message = create_message('visa_auth', test_messages)
    parsed = parser.parse(message.raw_message, network=CardNetwork.VISA)
    assert '44' in parsed.fields
    assert parsed.fields[44] == "A5B7"


def test_parse_binary_fields(parser, test_messages, create_message):
    """Test parsing binary fields"""
    # Create message with binary field
    message = create_message('basic_auth', test_messages)
    message.fields[52] = "0123456789ABCDEF"  # Add binary field

    parsed = parser.parse(message.raw_message)
    assert '52' in parsed.fields
    assert parsed.fields[52] == "0123456789ABCDEF"


def test_parse_emv_data(parser, test_messages, create_message):
    """Test EMV data parsing"""
    message = create_message('emv_auth', test_messages)
    parsed = parser.parse(message.raw_message)
    assert 55 in parsed.fields
    assert "9F06" in parsed.fields[55]
    assert len(parsed.fields[55]) > 0


def test_parse_with_different_versions(parser, test_messages, create_message):
    """Test parsing with different ISO versions"""
    parser_93 = ISO8583Parser(version=ISO8583Version.V1993)
    message = create_message('basic_auth', test_messages)
    parsed = parser_93.parse(message.raw_message)
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
    """Test parsing multiple messages"""
    # Create test messages
    messages = [
        "0100" + "0000000000100000" + "209F0607A0000000031010",  # EMV message
        "0200" + "4000000000000000" + "164111111111111111"  # PAN message
    ]

    test_file = tmp_path / "test_messages.txt"
    test_file.write_text("\n".join(messages))

    parsed_messages = parser.parse_file(str(test_file))
    assert len(parsed_messages) == 2

    # Check first message (EMV)
    assert parsed_messages[0].mti == "0100"
    assert 55 in parsed_messages[0].fields
    assert "9F06" in parsed_messages[0].fields[55]

    # Check second message (PAN)
    assert parsed_messages[1].mti == "0200"
    assert parsed_messages[1].fields[2] == "4111111111111111"


def test_network_specific_formatting(parser, test_messages, create_message):
    """Test network-specific field formatting"""
    message = create_message('visa_auth', test_messages)
    parsed = parser.parse(message.raw_message, network=CardNetwork.VISA)
    assert parsed.fields[44] == "A5B7"


def test_parse_version_specific_fields(parser):
    """Test parsing of version-specific fields"""
    # Test 1993 version specific field lengths
    parser_93 = ISO8583Parser(version=ISO8583Version.V1993)
    message = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            43: "A" * 99  # Field 43 can be 99 chars in 1993
        },
        version=ISO8583Version.V1993
    ).raw_message

    parsed = parser_93.parse(message)
    assert len(parsed.fields[43]) == 99


def test_parse_network_detection_accuracy(parser, test_messages, create_message):
    """Test accuracy of network detection from PANs"""
    # Test VISA detection
    visa_msg = create_message('visa_auth', test_messages)
    visa_parsed = parser.parse(visa_msg.raw_message)
    assert visa_parsed.network == CardNetwork.VISA

    # Test Mastercard detection
    mc_msg = create_message('mastercard_auth', test_messages)
    mc_parsed = parser.parse(mc_msg.raw_message)
    assert mc_parsed.network == CardNetwork.MASTERCARD


def test_parse_field_padding_preservation(parser, test_messages, create_message):
    """Test preservation of field padding"""
    message = create_message('basic_auth', test_messages)
    parsed = parser.parse(message.raw_message)

    # Check Terminal ID (field 41) - should be exactly 8 chars
    assert len(parsed.fields[41]) == 8
    assert parsed.fields[41] == "TEST1234"

    # Check Card Acceptor ID (field 42) - should be exactly 15 chars
    assert len(parsed.fields[42]) == 15
    assert parsed.fields[42] == "MERCHANT12345  "  # Exactly 15 chars with proper padding
