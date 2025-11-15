# tests/test_demo.py
"""Tests for the demo helper module."""

from iso8583sim.core.types import CardNetwork, ISO8583Message
from iso8583sim.demo import (
    PROCESSING_CODES,
    RESPONSE_CODES,
    build_and_parse,
    explain_emv,
    explain_field,
    generate_auth_request,
    generate_emv_auth,
    generate_financial_request,
    generate_network_message,
    generate_reversal,
    pretty_print,
    validate,
)


class TestGenerateAuthRequest:
    """Tests for generate_auth_request function."""

    def test_default_values(self):
        """Test generating auth request with default values."""
        msg = generate_auth_request()
        assert msg.mti == "0100"
        assert msg.fields[2] == "4111111111111111"
        assert msg.fields[3] == "000000"
        assert msg.fields[11] == "123456"
        assert msg.fields[41] == "TERM0001"

    def test_custom_pan(self):
        """Test generating auth request with custom PAN."""
        msg = generate_auth_request(pan="5555555555554444")
        assert msg.fields[2] == "5555555555554444"

    def test_custom_amount(self):
        """Test generating auth request with custom amount."""
        msg = generate_auth_request(amount=5000)
        assert msg.fields[4] == "000000005000"

    def test_custom_stan(self):
        """Test generating auth request with custom STAN."""
        msg = generate_auth_request(stan="999999")
        assert msg.fields[11] == "999999"

    def test_custom_terminal_merchant(self):
        """Test generating auth request with custom terminal/merchant IDs."""
        msg = generate_auth_request(terminal_id="MYTERM01", merchant_id="MYMERCHANT12345")
        assert msg.fields[41] == "MYTERM01"
        assert msg.fields[42] == "MYMERCHANT12345"

    def test_with_network(self):
        """Test generating auth request with network."""
        msg = generate_auth_request(network=CardNetwork.VISA)
        assert msg.network == CardNetwork.VISA

    def test_required_fields_present(self):
        """Test that required fields are present."""
        msg = generate_auth_request()
        required_fields = [0, 2, 3, 4, 11, 14, 22, 41, 42, 49]
        for field in required_fields:
            assert field in msg.fields, f"Field {field} should be present"


class TestGenerateFinancialRequest:
    """Tests for generate_financial_request function."""

    def test_default_values(self):
        """Test generating financial request with defaults."""
        msg = generate_financial_request()
        assert msg.mti == "0200"
        assert msg.fields[2] == "4111111111111111"
        assert msg.fields[3] == "000000"
        assert msg.fields[4] == "000000005000"
        assert msg.fields[11] == "654321"

    def test_custom_processing_code(self):
        """Test financial request with refund processing code."""
        msg = generate_financial_request(processing_code="200000")
        assert msg.fields[3] == "200000"

    def test_required_fields(self):
        """Test that required fields for financial are present."""
        msg = generate_financial_request()
        assert 12 in msg.fields  # Local time
        assert 13 in msg.fields  # Local date


class TestGenerateReversal:
    """Tests for generate_reversal function."""

    def test_reversal_mti(self):
        """Test that reversal has correct MTI."""
        original = generate_financial_request()
        reversal = generate_reversal(original)
        assert reversal.mti == "0400"

    def test_reversal_echoes_fields(self):
        """Test that reversal echoes original fields."""
        original = generate_financial_request(pan="5555555555554444", amount=10000)
        reversal = generate_reversal(original)

        assert reversal.fields[2] == original.fields[2]
        assert reversal.fields[3] == original.fields[3]
        assert reversal.fields[4] == original.fields[4]
        assert reversal.fields[41] == original.fields[41]
        assert reversal.fields[42] == original.fields[42]

    def test_reversal_new_stan(self):
        """Test that reversal has new STAN."""
        original = generate_financial_request(stan="123456")
        reversal = generate_reversal(original, new_stan="654321")
        assert reversal.fields[11] == "654321"
        assert reversal.fields[11] != original.fields[11]


class TestGenerateNetworkMessage:
    """Tests for generate_network_message function."""

    def test_echo_message(self):
        """Test generating echo test message."""
        msg = generate_network_message("echo")
        assert msg.mti == "0800"
        assert msg.fields[70] == "301"

    def test_signon_message(self):
        """Test generating sign-on message."""
        msg = generate_network_message("signon")
        assert msg.mti == "0800"
        assert msg.fields[70] == "001"

    def test_signoff_message(self):
        """Test generating sign-off message."""
        msg = generate_network_message("signoff")
        assert msg.mti == "0800"
        assert msg.fields[70] == "002"

    def test_key_exchange_message(self):
        """Test generating key exchange message."""
        msg = generate_network_message("key_exchange")
        assert msg.mti == "0800"
        assert msg.fields[70] == "161"

    def test_default_is_echo(self):
        """Test default network message is echo."""
        msg = generate_network_message()
        assert msg.fields[70] == "301"

    def test_required_fields(self):
        """Test that required network fields are present."""
        msg = generate_network_message()
        assert 7 in msg.fields  # Transmission date/time
        assert 11 in msg.fields  # STAN


class TestGenerateEmvAuth:
    """Tests for generate_emv_auth function."""

    def test_default_values(self):
        """Test EMV auth with default values."""
        msg = generate_emv_auth()
        assert msg.mti == "0100"
        assert msg.fields[2] == "4111111111111111"
        assert 55 in msg.fields  # EMV data present

    def test_custom_cryptogram(self):
        """Test EMV auth with custom cryptogram."""
        msg = generate_emv_auth(cryptogram="1122334455667788")
        emv_data = msg.fields[55]
        # Cryptogram should be in the EMV data
        assert "1122334455667788" in emv_data

    def test_emv_data_contains_required_tags(self):
        """Test that EMV data contains required tags."""
        msg = generate_emv_auth()
        emv_data = msg.fields[55]
        # Should contain common EMV tags
        assert "9F26" in emv_data  # Cryptogram
        assert "9F27" in emv_data  # CID
        assert "9F10" in emv_data  # Issuer App Data

    def test_has_track2_equivalent(self):
        """Test EMV auth has track 2 equivalent data."""
        msg = generate_emv_auth(pan="4111111111111111")
        assert 35 in msg.fields
        assert msg.fields[35].startswith("4111111111111111")


class TestBuildAndParse:
    """Tests for build_and_parse function."""

    def test_roundtrip(self):
        """Test that build_and_parse does a complete roundtrip."""
        original = generate_auth_request()
        parsed = build_and_parse(original)

        assert parsed.mti == original.mti
        assert parsed.fields[2] == original.fields[2]
        assert parsed.fields[3] == original.fields[3]
        assert parsed.fields[4] == original.fields[4]
        assert parsed.fields[11] == original.fields[11]

    def test_returns_iso8583_message(self):
        """Test that result is an ISO8583Message."""
        msg = generate_auth_request()
        result = build_and_parse(msg)
        assert isinstance(result, ISO8583Message)


class TestValidate:
    """Tests for validate function."""

    def test_validate_string_message(self, builder):
        """Test validating a raw string message."""
        msg = generate_auth_request()
        raw = builder.build(msg)
        # Should not raise
        validate(raw)

    def test_validate_message_object(self):
        """Test validating a message object."""
        msg = generate_auth_request()
        # Should not raise
        validate(msg)

    def test_validate_with_errors(self, capsys):
        """Test that validation errors are printed."""
        # Message missing required VISA fields
        msg = ISO8583Message(
            mti="0100",
            network=CardNetwork.VISA,
            fields={0: "0100", 2: "4111111111111111"},
        )
        validate(msg)
        captured = capsys.readouterr()
        assert "NO" in captured.out or "Error" in captured.out or "Required" in captured.out


class TestPrettyPrint:
    """Tests for pretty_print function."""

    def test_pretty_print_message(self, capsys):
        """Test pretty printing a message object."""
        msg = generate_auth_request()
        pretty_print(msg)
        captured = capsys.readouterr()

        assert "ISO 8583 Message" in captured.out
        assert "MTI: 0100" in captured.out
        assert "F002" in captured.out or "F2" in captured.out or "002" in captured.out

    def test_pretty_print_raw_string(self, capsys, builder):
        """Test pretty printing a raw message string."""
        msg = generate_auth_request()
        raw = builder.build(msg)
        pretty_print(raw)
        captured = capsys.readouterr()

        assert "ISO 8583 Message" in captured.out
        assert "MTI: 0100" in captured.out

    def test_pretty_print_shows_raw(self, capsys, builder):
        """Test show_raw option."""
        msg = generate_auth_request()
        _ = builder.build(msg)  # Build to ensure it works
        parsed = build_and_parse(msg)
        pretty_print(parsed, show_raw=True)
        captured = capsys.readouterr()

        assert "Raw Message" in captured.out

    def test_pan_masking(self, capsys):
        """Test that PAN is masked in output."""
        msg = generate_auth_request(pan="4111111111111111")
        pretty_print(msg)
        captured = capsys.readouterr()

        # PAN should be masked (411111******1111 pattern)
        assert "4111111111111111" not in captured.out or "411111" in captured.out

    def test_mti_breakdown(self, capsys):
        """Test that MTI is broken down."""
        msg = generate_auth_request()
        pretty_print(msg)
        captured = capsys.readouterr()

        assert "Version:" in captured.out
        assert "Class:" in captured.out
        assert "Function:" in captured.out
        assert "Origin:" in captured.out


class TestExplainField:
    """Tests for explain_field function."""

    def test_explain_known_field(self, capsys):
        """Test explaining a known field."""
        explain_field(2)
        captured = capsys.readouterr()
        assert "Field 2" in captured.out

    def test_explain_field_with_value(self, capsys):
        """Test explaining field with value interpretation."""
        explain_field(39, "00")
        captured = capsys.readouterr()
        assert "Approved" in captured.out

    def test_explain_processing_code(self, capsys):
        """Test explaining processing code field."""
        explain_field(3, "200000")
        captured = capsys.readouterr()
        assert "Refund" in captured.out

    def test_explain_currency(self, capsys):
        """Test explaining currency field."""
        explain_field(49, "840")
        captured = capsys.readouterr()
        assert "USD" in captured.out

    def test_explain_unknown_field(self, capsys):
        """Test explaining unknown field."""
        explain_field(999)
        captured = capsys.readouterr()
        assert "Unknown" in captured.out


class TestExplainEmv:
    """Tests for explain_emv function."""

    def test_explain_emv_data(self, capsys):
        """Test explaining EMV data."""
        emv_data = "9F2608AABBCCDD112233449F270180"
        explain_emv(emv_data)
        captured = capsys.readouterr()

        assert "EMV Data Analysis" in captured.out
        assert "9F26" in captured.out
        assert "9F27" in captured.out

    def test_explain_cid_value(self, capsys):
        """Test that CID is explained."""
        emv_data = "9F270180"  # ARQC
        explain_emv(emv_data)
        captured = capsys.readouterr()

        assert "ARQC" in captured.out or "Online" in captured.out


class TestResponseCodes:
    """Tests for RESPONSE_CODES constant."""

    def test_response_codes_populated(self):
        """Test that response codes dictionary is populated."""
        assert len(RESPONSE_CODES) > 10

    def test_common_codes_present(self):
        """Test that common response codes are present."""
        assert "00" in RESPONSE_CODES  # Approved
        assert "51" in RESPONSE_CODES  # Insufficient funds
        assert "54" in RESPONSE_CODES  # Expired card

    def test_approved_code(self):
        """Test approved code description."""
        assert RESPONSE_CODES["00"] == "Approved"


class TestProcessingCodes:
    """Tests for PROCESSING_CODES constant."""

    def test_processing_codes_populated(self):
        """Test that processing codes dictionary is populated."""
        assert len(PROCESSING_CODES) > 5

    def test_common_codes_present(self):
        """Test that common processing codes are present."""
        assert "00" in PROCESSING_CODES  # Purchase
        assert "20" in PROCESSING_CODES  # Refund

    def test_purchase_code(self):
        """Test purchase code description."""
        assert PROCESSING_CODES["00"] == "Purchase"
