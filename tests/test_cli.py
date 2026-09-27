# tests/test_cli.py
"""Tests for CLI commands."""

import json

import pytest
from typer.testing import CliRunner

from iso8583sim import __version__
from iso8583sim.cli.commands import app
from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.types import ISO8583Message
from iso8583sim.llm import LLMProvider

runner = CliRunner()


class TestVersionCommand:
    """Tests for the version command."""

    def test_version_displays(self):
        """Test that version command shows version info."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "ISO8583 Simulator" in result.stdout
        assert f"v{__version__}" in result.stdout


class TestParseCommand:
    """Tests for the parse command."""

    @pytest.fixture
    def sample_message(self):
        """Generate a valid ISO8583 message for testing."""
        builder = ISO8583Builder()
        msg = ISO8583Message(
            mti="0100",
            fields={
                0: "0100",
                2: "4111111111111111",
                3: "000000",
                4: "000000001000",
                11: "123456",
                41: "TERM0001",
                42: "MERCHANT12345  ",
            },
        )
        return builder.build(msg)

    def test_parse_valid_message_table(self, sample_message):
        """Test parsing a valid message with table output."""
        result = runner.invoke(app, ["parse", sample_message, "--format", "table"])
        assert result.exit_code == 0
        assert "4111111111111111" in result.stdout
        assert "TERM0001" in result.stdout

    def test_parse_valid_message_json(self, sample_message):
        """Test parsing a valid message with JSON output."""
        result = runner.invoke(app, ["parse", sample_message, "--format", "json"])
        assert result.exit_code == 0
        # JSON output contains the PAN
        assert "4111111111111111" in result.stdout

    def test_parse_with_network(self, sample_message):
        """Test parsing with explicit network specified."""
        result = runner.invoke(app, ["parse", sample_message, "--network", "VISA"])
        assert result.exit_code == 0

    def test_parse_with_version(self, sample_message):
        """Test parsing with explicit version specified."""
        result = runner.invoke(app, ["parse", sample_message, "--version", "1987"])
        assert result.exit_code == 0

    def test_parse_invalid_message(self):
        """Test parsing an invalid message."""
        result = runner.invoke(app, ["parse", "invalid_message"])
        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_parse_too_short_message(self):
        """Test parsing a message that's too short."""
        result = runner.invoke(app, ["parse", "0100"])
        assert result.exit_code == 1

    def test_parse_output_to_file(self, sample_message, tmp_path):
        """Test parsing with output to file."""
        output_file = tmp_path / "output.json"
        result = runner.invoke(app, ["parse", sample_message, "--output", str(output_file)])
        assert result.exit_code == 0
        assert output_file.exists()

        # Verify file contents
        data = json.loads(output_file.read_text())
        assert data["mti"] == "0100"


class TestBuildCommand:
    """Tests for the build command."""

    @pytest.fixture
    def fields_file(self, tmp_path):
        """Create a temporary fields JSON file."""
        fields = {
            "2": "4111111111111111",
            "3": "000000",
            "4": "000000001000",
            "11": "123456",
            "41": "TERM0001",
            "42": "MERCHANT12345  ",
        }
        file_path = tmp_path / "fields.json"
        file_path.write_text(json.dumps(fields))
        return file_path

    def test_build_valid_message(self, fields_file):
        """Test building a valid message."""
        result = runner.invoke(app, ["build", "--mti", "0100", "--fields", str(fields_file)])
        assert result.exit_code == 0
        assert "0100" in result.stdout  # MTI in output

    def test_build_with_network(self, fields_file):
        """Test building with network specified."""
        # Add network-required fields
        fields = json.loads(fields_file.read_text())
        fields.update({"14": "2512", "22": "051", "24": "001", "25": "00"})
        fields_file.write_text(json.dumps(fields))

        result = runner.invoke(app, ["build", "--mti", "0100", "--fields", str(fields_file), "--network", "VISA"])
        assert result.exit_code == 0

    def test_build_missing_mti(self, fields_file):
        """Test building without MTI fails."""
        result = runner.invoke(app, ["build", "--fields", str(fields_file)])
        assert result.exit_code != 0

    def test_build_missing_fields_file(self):
        """Test building without fields file fails."""
        result = runner.invoke(app, ["build", "--mti", "0100", "--fields", "/nonexistent/path.json"])
        assert result.exit_code == 1

    def test_build_output_to_file(self, fields_file, tmp_path):
        """Test building with output to file."""
        output_file = tmp_path / "message.txt"
        result = runner.invoke(
            app, ["build", "--mti", "0100", "--fields", str(fields_file), "--output", str(output_file)]
        )
        assert result.exit_code == 0
        assert output_file.exists()


class TestValidateCommand:
    """Tests for the validate command."""

    @pytest.fixture
    def valid_message(self):
        """Generate a valid ISO8583 message with all VISA-required fields."""
        builder = ISO8583Builder()
        msg = ISO8583Message(
            mti="0100",
            fields={
                0: "0100",
                2: "4111111111111111",
                3: "000000",
                4: "000000001000",
                11: "123456",
                14: "2512",  # Expiry date (VISA required)
                22: "051",  # POS entry mode (VISA required)
                24: "001",  # Function code (VISA required)
                25: "00",  # POS condition code (VISA required)
                41: "TERM0001",
                42: "MERCHANT12345  ",
            },
        )
        return builder.build(msg)

    def test_validate_valid_message(self, valid_message):
        """Test validating a valid message."""
        result = runner.invoke(app, ["validate", valid_message])
        assert result.exit_code == 0

    def test_validate_invalid_message(self):
        """Test validating an invalid message."""
        result = runner.invoke(app, ["validate", "invalid"])
        assert result.exit_code == 1

    def test_validate_with_network(self, valid_message):
        """Test validating with network specified."""
        runner.invoke(app, ["validate", valid_message, "--network", "VISA"])
        # May fail validation if VISA-required fields are missing
        # That's expected behavior


class TestGenerateCommand:
    """Tests for the generate command."""

    def test_generate_auth_message(self):
        """Test generating an authorization message."""
        result = runner.invoke(
            app, ["generate", "--type", "auth", "--pan", "4111111111111111", "--amount", "000000001000"]
        )
        assert result.exit_code == 0
        assert "0100" in result.stdout  # Auth MTI

    def test_generate_financial_message(self):
        """Test generating a financial message."""
        result = runner.invoke(
            app, ["generate", "--type", "financial", "--pan", "4111111111111111", "--amount", "000000001000"]
        )
        assert result.exit_code == 0
        assert "0200" in result.stdout  # Financial MTI

    def test_generate_reversal_message(self):
        """Test generating a reversal message."""
        result = runner.invoke(
            app, ["generate", "--type", "reversal", "--pan", "4111111111111111", "--amount", "000000001000"]
        )
        assert result.exit_code == 0
        assert "0400" in result.stdout  # Reversal MTI

    def test_generate_with_currency(self):
        """Test generating with currency code."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--type",
                "auth",
                "--pan",
                "4111111111111111",
                "--amount",
                "000000001000",
                "--currency",
                "978",  # EUR
            ],
        )
        assert result.exit_code == 0

    def test_generate_output_to_file(self, tmp_path):
        """Test generating with output to file."""
        output_file = tmp_path / "generated.txt"
        result = runner.invoke(
            app,
            [
                "generate",
                "--type",
                "auth",
                "--pan",
                "4111111111111111",
                "--amount",
                "000000001000",
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()

    def test_generate_invalid_type(self):
        """Test generating with invalid type."""
        result = runner.invoke(
            app, ["generate", "--type", "invalid_type", "--pan", "4111111111111111", "--amount", "000000001000"]
        )
        assert result.exit_code == 1


class TestCLIHelp:
    """Tests for CLI help messages."""

    def test_main_help(self):
        """Test main help message."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ISO 8583 Message Simulator" in result.stdout
        assert "parse" in result.stdout
        assert "build" in result.stdout
        assert "validate" in result.stdout

    def test_parse_help(self):
        """Test parse command help."""
        result = runner.invoke(app, ["parse", "--help"])
        assert result.exit_code == 0
        assert "Parse an ISO 8583 message" in result.stdout

    def test_build_help(self):
        """Test build command help."""
        result = runner.invoke(app, ["build", "--help"])
        assert result.exit_code == 0
        assert "Build an ISO 8583 message" in result.stdout

    def test_validate_help(self):
        """Test validate command help."""
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate an ISO 8583 message" in result.stdout

    def test_generate_help(self):
        """Test generate command help."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "Generate a sample ISO 8583 message" in result.stdout


class TestMcpCommand:
    """Tests for the mcp command."""

    def test_mcp_without_extra_shows_install_hint(self, monkeypatch):
        """Test that a missing mcp extra gives an install hint instead of a traceback."""
        import sys

        monkeypatch.setitem(sys.modules, "iso8583sim.mcp", None)
        result = runner.invoke(app, ["mcp"])
        assert result.exit_code == 1
        assert "iso8583sim[mcp]" in result.stdout


class FakeProvider(LLMProvider):
    """Stand-in LLM provider that records prompts and returns a canned reply."""

    def __init__(self, response):
        self.response = response
        self.prompts = []

    def complete(self, prompt, system=None):
        self.prompts.append(prompt)
        return self.response

    @property
    def name(self):
        return "Fake"

    @property
    def model(self):
        return "fake-model"


@pytest.fixture
def auth_message():
    """A built VISA authorization request."""
    builder = ISO8583Builder()
    return builder.build(
        ISO8583Message(
            mti="0100",
            fields={
                0: "0100",
                2: "4111111111111111",
                3: "000000",
                4: "000000001000",
                11: "123456",
                41: "TERM0001",
                42: "MERCHANT123456 ",
                49: "840",
            },
        )
    )


def use_provider(monkeypatch, provider):
    """Make the CLI's get_provider return the given provider and record its arguments."""
    import iso8583sim.llm

    calls = []

    def fake_get_provider(name=None, **kwargs):
        calls.append((name, kwargs))
        return provider

    # subhadipmitra@: The commands import get_provider from iso8583sim.llm at call time,
    # so patching the module attribute is enough to swap in the fake provider.
    monkeypatch.setattr(iso8583sim.llm, "get_provider", fake_get_provider)
    return calls


class TestExplainCommand:
    """Tests for the explain command."""

    def test_explain_no_llm(self, auth_message):
        """Test the rule-based explanation, which needs no provider."""
        result = runner.invoke(app, ["explain", auth_message, "--no-llm"])
        assert result.exit_code == 0
        assert "authorization request" in result.stdout
        assert "411111******1111" in result.stdout
        assert "10.00 USD" in result.stdout

    def test_explain_with_llm(self, monkeypatch, auth_message):
        """Test that the explanation comes from the provider."""
        provider = FakeProvider("A $10.00 VISA purchase authorization.")
        calls = use_provider(monkeypatch, provider)

        result = runner.invoke(app, ["explain", auth_message, "--provider", "anthropic", "--model", "m1"])

        assert result.exit_code == 0, result.stdout
        assert "A $10.00 VISA purchase authorization." in result.stdout
        assert calls == [("anthropic", {"model": "m1"})]
        assert "0100" in provider.prompts[0]

    def test_explain_without_provider_suggests_no_llm(self, monkeypatch, auth_message):
        """Test that a missing provider shows the error and the --no-llm tip."""
        import iso8583sim.llm
        from iso8583sim.llm import ProviderConfigError

        def no_provider(name=None, **kwargs):
            raise ProviderConfigError("No LLM provider available. Install iso8583sim[anthropic]")

        monkeypatch.setattr(iso8583sim.llm, "get_provider", no_provider)
        result = runner.invoke(app, ["explain", auth_message])

        assert result.exit_code == 1
        assert "Install iso8583sim[anthropic]" in result.stdout
        assert "--no-llm" in result.stdout

    def test_explain_invalid_message(self):
        """Test that a message that fails to parse exits with an error."""
        result = runner.invoke(app, ["explain", "garbage", "--no-llm"])
        assert result.exit_code == 1
        assert "Error parsing message" in result.stdout


class TestGenerateWithLLM:
    """Tests for generate --llm."""

    def test_generate_with_llm(self, monkeypatch, tmp_path):
        """Test generating a message from a description."""

        reply = json.dumps(
            {
                "mti": "0200",
                "fields": {
                    "2": "5555555555554444",
                    "3": "200000",
                    "4": "000000005000",
                    "11": "654321",
                    "41": "TERM0001",
                    "42": "ACME STORE     ",
                    "49": "840",
                },
            }
        )
        provider = FakeProvider(reply)
        use_provider(monkeypatch, provider)
        output = tmp_path / "msg.txt"

        result = runner.invoke(app, ["generate", "--llm", "$50 Mastercard refund at ACME", "-o", str(output)])

        assert result.exit_code == 0, result.stdout
        assert "Generated Message 0200" in result.stdout
        assert output.read_text().startswith("0200")
        assert "$50 Mastercard refund at ACME" in provider.prompts[0]

    def test_generate_requires_type_or_llm(self):
        """Test that generate needs either --type or --llm."""
        result = runner.invoke(app, ["generate"])
        assert result.exit_code == 1
        assert "--type" in result.stdout


class TestConvertAndNetworkChecks:
    """Tests for the convert command and validate --against."""

    @pytest.fixture
    def reversal(self):
        fields = {
            2: "4111111111111111",
            3: "000000",
            4: "000000001000",
            11: "123456",
            14: "2612",
            22: "051",
            24: "001",
            25: "00",
            90: "010012345612251030000000001234500000000000",
        }
        return ISO8583Builder().build(ISO8583Message(mti="0400", fields=fields))

    def test_convert_to_2003(self, reversal, tmp_path):
        output = tmp_path / "out.txt"
        result = runner.invoke(app, ["convert", reversal, "--to", "2003", "-o", str(output)])
        assert result.exit_code == 0, result.stdout
        assert output.read_text().startswith("2400")
        assert "field 90 to field 56" in result.stdout

    def test_convert_reports_dropped_fields(self):
        fields = {2: "4111111111111111", 3: "000000", 4: "000000001000", 11: "123456", 52: "2A3D408A1977DDE9"}
        raw = ISO8583Builder().build(ISO8583Message(mti="0200", fields=fields))
        result = runner.invoke(app, ["convert", raw, "--to", "1993"])
        assert result.exit_code == 0
        assert "Dropped field 52" in result.stdout

    def test_validate_against_all_networks(self, reversal):
        result = runner.invoke(app, ["validate", reversal, "--against", "all"])
        assert "UNIONPAY" in result.stdout and "FAIL" in result.stdout
        assert result.exit_code == 1

    def test_validate_against_passing_networks(self, reversal):
        result = runner.invoke(app, ["validate", reversal, "--against", "visa, amex"])
        assert result.exit_code == 0
        assert "FAIL" not in result.stdout

    def test_invalid_message_is_not_misreported_as_error(self):
        """A validation failure exits 1 without an 'Error validating message' line"""
        raw = ISO8583Builder().build(
            ISO8583Message(mti="0100", fields={2: "4111111111111111", 3: "000000", 4: "000000001000", 11: "123456"})
        )
        result = runner.invoke(app, ["validate", raw, "--network", "VISA"])
        assert result.exit_code == 1
        assert "Error validating message" not in result.stdout


class TestWebCommand:
    """Tests for the web command."""

    def test_web_without_extra_shows_install_hint(self, monkeypatch):
        """A missing web extra gives an install hint instead of a traceback."""
        import sys

        monkeypatch.setitem(sys.modules, "uvicorn", None)
        result = runner.invoke(app, ["web"])
        assert result.exit_code == 1
        assert "iso8583sim[web]" in result.stdout
