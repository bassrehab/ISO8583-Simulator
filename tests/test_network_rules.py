# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Tests for network-specific field rules."""

import pytest

from iso8583sim.core.network_rules import check_mastercard_de48, check_pos_entry_mode
from iso8583sim.core.samples import sample_message
from iso8583sim.core.types import CardNetwork
from iso8583sim.core.validator import ISO8583Validator

VISA, MC = CardNetwork.VISA, CardNetwork.MASTERCARD


class TestPosEntryMode:
    @pytest.mark.parametrize("value", ["051", "071", "902", "010", "812", "808", "053"])
    def test_valid(self, value):
        assert check_pos_entry_mode(value, VISA) == []
        assert check_pos_entry_mode(value, MC) == []

    def test_visa_only_code(self):
        assert check_pos_entry_mode("951", VISA) == []
        assert "Visa only" in check_pos_entry_mode("951", MC)[0]

    @pytest.mark.parametrize(
        "value,message",
        [("08", "3 digits"), ("0511", "3 digits"), ("5A1", "3 digits"), ("421", "PAN entry mode 42"), ("054", "PIN")],
    )
    def test_invalid(self, value, message):
        assert message in " ".join(check_pos_entry_mode(value, VISA))


class TestMastercardDe48:
    @pytest.mark.parametrize("value", ["R", "T", " ", "R0103ABC", "R0103ABC4202XY", "U0100"])
    def test_valid(self, value):
        assert check_mastercard_de48(value) == []

    @pytest.mark.parametrize(
        "value,message",
        [
            ("", "empty"),
            ("MC123", "subelement ID"),  # the old, made-up format
            ("R01", "subelement ID"),
            ("R0105AB", "field ends first"),
            ("*0103ABC", "transaction category code"),
        ],
    )
    def test_invalid(self, value, message):
        assert message in check_mastercard_de48(value)[0]


class TestValidatorIntegration:
    def test_previously_rejected_values_now_pass(self):
        """VISA field 44 and Mastercard field 48 values that the old rules wrongly rejected."""
        validator = ISO8583Validator()
        visa = sample_message(network=VISA)
        visa.fields[44] = "M"  # CVV2 match result
        mc = sample_message(network=MC)
        mc.fields[48] = "R0103ABC"
        assert validator.validate_message(visa) == []
        assert validator.validate_message(mc) == []

    def test_rules_are_enforced(self):
        validator = ISO8583Validator()
        mc = sample_message(network=MC)
        mc.fields[22] = "951"
        assert any("Visa only" in e for e in validator.validate_message(mc))

    def test_other_networks_have_no_format_rules(self):
        """AMEX, Discover, JCB and UnionPay use different field 22 schemes, so no codes are enforced."""
        validator = ISO8583Validator()
        for network in (CardNetwork.AMEX, CardNetwork.DISCOVER, CardNetwork.JCB, CardNetwork.UNIONPAY):
            message = sample_message(network=network)
            message.fields[22] = "421"
            assert not any("field 22" in e for e in validator.validate_message(message))

    @pytest.mark.parametrize("network", list(CardNetwork))
    def test_generated_samples_still_valid(self, network):
        assert ISO8583Validator().validate_message(sample_message(network=network)) == []
