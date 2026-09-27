# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Tests for converting messages between ISO 8583 versions."""

import pytest

from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.convert import convert_message, convert_mti
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.types import CardNetwork, ISO8583Message, ISO8583Version

V87, V93, V03 = ISO8583Version.V1987, ISO8583Version.V1993, ISO8583Version.V2003

REVERSAL_FIELDS = {
    2: "4111111111111111",
    3: "000000",
    4: "000000001000",
    11: "123456",
    14: "2612",
    22: "051",
    24: "001",
    25: "00",
    43: "ACME STORE             NEW YORK     US",
    90: "010012345612251030000000001234500000000000",
}


def parsed_1987(fields=None, mti="0400"):
    raw = ISO8583Builder().build(ISO8583Message(mti=mti, fields=dict(fields or REVERSAL_FIELDS)))
    return raw, ISO8583Parser().parse(raw)


@pytest.mark.parametrize(
    "mti,target,expected",
    [("0100", V93, "1100"), ("0100", V03, "2100"), ("1210", V87, "0210"), ("2400", V93, "1400")],
)
def test_convert_mti(mti, target, expected):
    assert convert_mti(mti, target) == expected


def test_convert_mti_rejects_unknown_version_digit():
    with pytest.raises(ValueError, match="version digit"):
        convert_mti("9100", V87)


@pytest.mark.parametrize("target", [V93, V03])
def test_round_trip_is_lossless(target):
    raw, parsed = parsed_1987()
    forward = convert_message(parsed, target)
    assert forward.lossless
    built = ISO8583Builder(version=target).build(forward.message)

    back = convert_message(ISO8583Parser(version=target).parse(built), V87)
    assert back.lossless
    # subhadipmitra@: The strongest check: 1987 -> target -> 1987 reproduces the original
    # message byte for byte.
    assert ISO8583Builder().build(back.message) == raw


def test_original_data_moves_to_field_56_in_2003():
    _, parsed = parsed_1987()
    result = convert_message(parsed, V03)
    assert 90 not in result.message.fields
    assert result.message.fields[56] == REVERSAL_FIELDS[90]
    assert any("field 90 to field 56" in note for note in result.notes)


def test_existing_field_56_is_not_overwritten():
    msg = ISO8583Message(mti="0400", fields={**REVERSAL_FIELDS, 56: "KEEP"})
    result = convert_message(msg, V03)
    assert result.message.fields[56] == "KEEP"


def test_pin_data_is_dropped_with_reason():
    _, parsed = parsed_1987({**REVERSAL_FIELDS, 52: "2A3D408A1977DDE9"})
    result = convert_message(parsed, V93)
    assert 52 not in result.message.fields
    assert "re-encrypted" in result.dropped[52]
    assert not result.lossless


def test_value_too_long_for_target_is_dropped():
    msg = ISO8583Message(mti="1200", version=V93, fields={**REVERSAL_FIELDS, 43: "X" * 60})
    result = convert_message(msg, V87)
    assert 43 not in result.message.fields
    assert 43 in result.dropped


def test_meaning_change_is_noted():
    _, parsed = parsed_1987({**REVERSAL_FIELDS, 57: "ABC"})
    result = convert_message(parsed, V03)
    assert any("Field 57" in note and "Authorization Life Cycle Code" in note for note in result.notes)


def test_same_version_is_a_no_op():
    _, parsed = parsed_1987()
    result = convert_message(parsed, V87)
    assert result.message.fields == parsed.fields
    assert result.lossless


def test_network_is_kept():
    msg = ISO8583Message(mti="0100", fields=dict(REVERSAL_FIELDS), network=CardNetwork.VISA)
    assert convert_message(msg, V93).message.network == CardNetwork.VISA
