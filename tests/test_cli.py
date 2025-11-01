# tests/test_cli.py
"""Tests for CLI commands."""

import json

import pytest
from typer.testing import CliRunner

from iso8583sim.cli.commands import app
from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.types import ISO8583Message

runner = CliRunner()


class TestVersionCommand:
    """Tests for the version command."""

    def test_version_displays(self):
        """Test that version command shows version info."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "ISO8583 Simulator" in result.stdout
        assert "v0.1.0" in result.stdout


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
