"""Tests for reference code tables and PAN network detection."""

import pytest

from iso8583sim.core.codes import RESPONSE_CODES, detect_network_from_pan
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.types import CardNetwork


@pytest.mark.parametrize(
    "pan,network",
    [
        ("4111111111111111", CardNetwork.VISA),
        ("5555555555554444", CardNetwork.MASTERCARD),
        ("2221000000000009", CardNetwork.MASTERCARD),
        ("2720999999999996", CardNetwork.MASTERCARD),
        ("378282246310005", CardNetwork.AMEX),
        ("341111111111111", CardNetwork.AMEX),
        ("6011111111111117", CardNetwork.DISCOVER),
        ("6445644564456445", CardNetwork.DISCOVER),
        ("6500000000000002", CardNetwork.DISCOVER),
        ("3530111333300000", CardNetwork.JCB),
        ("6200000000000005", CardNetwork.UNIONPAY),
    ],
)
def test_detect_network_from_pan(pan, network):
    assert detect_network_from_pan(pan) == network


@pytest.mark.parametrize("pan", ["", "1234", "9999999999999999", "2220999999999999", "41111111abcd1111"])
def test_detect_network_from_pan_unknown(pan):
    assert detect_network_from_pan(pan) is None


def test_parser_detects_discover(builder):
    from iso8583sim.core.types import ISO8583Message

    raw = builder.build(
        ISO8583Message(mti="0100", fields={2: "6011111111111117", 3: "000000", 4: "000000001000", 11: "123456"})
    )
    assert ISO8583Parser().parse(raw).network == CardNetwork.DISCOVER


def test_response_codes_include_common_values():
    assert RESPONSE_CODES["00"] == "Approved"
    assert RESPONSE_CODES["51"] == "Insufficient funds"
