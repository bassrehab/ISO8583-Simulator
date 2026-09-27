"""Tests for byte-level wire formats.

Expected byte strings were cross-checked against the independent pyiso8583 library
(https://github.com/knovichikhin/pyiso8583) configured with the same encodings.
"""

import copy

import pytest

from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.samples import sample_message
from iso8583sim.core.types import CardNetwork, ISO8583Message, ISO8583Version, ParseError
from iso8583sim.wire import Encoding, WireFormat, decode_message, encode_message

PRESETS = ["ascii-hex", "ascii-binary", "bcd", "ebcdic"]

ODD_PAN = ISO8583Message(mti="0100", fields={2: "378282246310005", 3: "000000", 4: "000000001000", 11: "123456"})

RICH = ISO8583Message(
    mti="0200",
    fields={
        2: "4111111111111111",
        3: "000000",
        4: "000000001000",
        7: "1225103000",
        11: "123456",
        22: "051",
        32: "12345",
        35: "4111111111111111=2612101",
        41: "TERM0001",
        42: "MERCHANT123456 ",
        43: "ACME STORE             NEW YORK     US",
        48: "ADDITIONAL DATA",
        49: "840",
        52: "2A3D408A1977DDE9",
        55: "9F2608AABBCCDDEEFF00119F27018095050000008000",
        64: "0123456789ABCDEF",
    },
)

SECONDARY = ISO8583Message(
    mti="0800", fields={7: "1215143022", 11: "000001", 70: "301", 100: "123", 128: "0011223344556677"}
)

MESSAGES = {
    "sample": sample_message(),
    "echo": sample_message("echo"),
    "rich": RICH,
    "secondary": SECONDARY,
    "odd_pan": ODD_PAN,
    "v1993": ISO8583Message(
        mti="1100", version=ISO8583Version.V1993, fields={2: "4111111111111111", 3: "000000", 4: "000000001000"}
    ),
}


def encode(message, fmt):
    # subhadipmitra@: encode_message normalizes the message in place (as build() does), so
    # tests work on copies to keep the shared fixtures untouched.
    return encode_message(copy.deepcopy(message), fmt)


class TestKnownEncodings:
    def test_bcd(self):
        assert encode(ODD_PAN, WireFormat.bcd()).hex().upper() == (
            "01007020000000000000150378282246310005000000000000001000123456"
        )

    def test_bcd_right_padding_only_affects_variable_fields(self):
        fmt = WireFormat(**{**WireFormat.bcd().__dict__, "bcd_odd_padding": "right"})
        assert encode(ODD_PAN, fmt).hex().upper() == ("0100702000000000000015378282246310005F000000000000001000123456")

    def test_bcd_secondary_bitmap(self):
        assert encode(SECONDARY, WireFormat.bcd()).hex().upper() == (
            "080082200000000000000400000010000001121514302200000103010301230011223344556677"
        )

    def test_ebcdic(self):
        assert encode(ODD_PAN, WireFormat.ebcdic()).hex().upper() == (
            "F0F1F0F07020000000000000F1F5F3F7F8F2F8F2F2F4F6F3F1F0F0F0F5F0F0F0F0F0F0F0F0F0F0F0F0F0F0F1F0F0F0F1F2F3F4F5F6"
        )

    def test_ascii_binary_has_raw_bitmap(self):
        data = encode(ODD_PAN, WireFormat.ascii_binary())
        assert data[:4] == b"0100"
        assert data[4:12] == bytes.fromhex("7020000000000000")
        assert data[12:14] == b"15"


class TestCompatibility:
    @pytest.mark.parametrize("name", MESSAGES)
    def test_ascii_hex_matches_string_builder(self, name):
        message = MESSAGES[name]
        text = ISO8583Builder(version=message.version).build(copy.deepcopy(message))
        assert encode(message, WireFormat.ascii_hex()) == text.encode("ascii")

    @pytest.mark.parametrize("name", MESSAGES)
    @pytest.mark.parametrize("preset", PRESETS)
    @pytest.mark.parametrize("padding", ["left", "right"])
    def test_round_trip_matches_string_parser(self, name, preset, padding):
        message = MESSAGES[name]
        fmt = WireFormat(**{**WireFormat.preset(preset).__dict__, "bcd_odd_padding": padding})
        text = ISO8583Builder(version=message.version).build(copy.deepcopy(message))
        expected = ISO8583Parser(version=message.version).parse(text)

        decoded = decode_message(encode(message, fmt), fmt, version=message.version)

        # subhadipmitra@: The decoded message must equal what the string parser gives, so
        # everything downstream (validator, explainer, converter) works unchanged.
        assert decoded.fields == expected.fields
        assert decoded.mti == expected.mti
        assert decoded.network == expected.network

    def test_binary_formats_are_smaller(self):
        sizes = {p: len(encode(RICH, WireFormat.preset(p))) for p in PRESETS}
        assert sizes["bcd"] < sizes["ascii-binary"] < sizes["ascii-hex"]


class TestDecoding:
    def test_detects_network(self):
        data = encode(sample_message(network=CardNetwork.DISCOVER), WireFormat.bcd())
        assert decode_message(data, WireFormat.bcd()).network == CardNetwork.DISCOVER

    def test_track_2_separator(self):
        decoded = decode_message(encode(RICH, WireFormat.bcd()), WireFormat.bcd())
        assert decoded.fields[35] == "4111111111111111=2612101"

    def test_truncated_message(self):
        data = encode(RICH, WireFormat.bcd())
        with pytest.raises(ParseError, match="too short"):
            decode_message(data[:-3], WireFormat.bcd())

    def test_trailing_bytes(self):
        data = encode(ODD_PAN, WireFormat.bcd())
        with pytest.raises(ParseError, match="unexpected bytes"):
            decode_message(data + b"\x00", WireFormat.bcd())

    def test_wrong_format_is_reported(self):
        data = encode(ODD_PAN, WireFormat.ebcdic())
        with pytest.raises(ParseError):
            decode_message(data, WireFormat.ascii_binary())

    def test_cp500_codec(self):
        fmt = WireFormat(**{**WireFormat.ebcdic().__dict__, "ebcdic_codec": "cp500"})
        assert decode_message(encode(RICH, fmt), fmt).fields[43] == RICH.fields[43]


class TestWireFormat:
    def test_presets(self):
        assert WireFormat.preset("BCD") == WireFormat.bcd()
        with pytest.raises(ValueError, match="Unknown wire format"):
            WireFormat.preset("json")

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"mti": Encoding.BINARY},
            {"text": Encoding.BCD},
            {"numeric": Encoding.BINARY},
            {"bitmap": "base64"},
            {"binary_fields": "b64"},
            {"bcd_odd_padding": "middle"},
        ],
    )
    def test_invalid_combinations(self, kwargs):
        with pytest.raises(ValueError):
            WireFormat(**kwargs)


def test_builder_and_parser_shortcuts():
    data = ISO8583Builder().build_bytes(copy.deepcopy(ODD_PAN), WireFormat.bcd())
    assert data == encode(ODD_PAN, WireFormat.bcd())
    assert ISO8583Parser().parse_bytes(data, WireFormat.bcd()).fields[2] == "378282246310005"
