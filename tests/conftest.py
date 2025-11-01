# tests/conftest.py

import json
from pathlib import Path

import pytest
import yaml

from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.types import CardNetwork, ISO8583Message
from iso8583sim.core.validator import ISO8583Validator

# Constants for test data
TEST_DATA_DIR = Path(__file__).parent / "test_data"


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "network: mark test as requiring network specifics")
    config.addinivalue_line("markers", "visa: mark test as VISA specific")
    config.addinivalue_line("markers", "mastercard: mark test as Mastercard specific")
    config.addinivalue_line("markers", "amex: mark test as AMEX specific")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "unit: mark test as unit test")


@pytest.fixture(scope="session")
def test_data_dir():
    """Fixture to provide test data directory"""
    TEST_DATA_DIR.mkdir(exist_ok=True)
    return TEST_DATA_DIR


@pytest.fixture
def test_messages():
    """Common ISO8583 test messages with correct field formatting"""
    return {
        "basic_auth": {
            "mti": "0100",
            "fields": {
                0: "0100",
                2: "4111111111111111",
                3: "000000",  # Processing Code (n6)
                4: "000000001000",  # Amount, Transaction (n12)
                11: "123456",  # STAN (n6)
                41: "TEST1234",  # Terminal ID (ans8)
                42: "MERCHANT12345  ",  # Card Acceptor ID (ans15) - exactly 15 chars with spaces
            },
        },
        "visa_auth": {
            "mti": "0100",
            "network": CardNetwork.VISA,
            "fields": {
                0: "0100",
                2: "4111111111111111",
                3: "000000",
                4: "000000001000",
                11: "123456",
                14: "2412",
                22: "021",
                24: "001",
                25: "00",
                41: "TEST1234",
                42: "MERCHANT12345  ",  # Exactly 15 chars with spaces
                44: "A5B7",
            },
        },
        "mastercard_auth": {
            "mti": "0200",
            "network": CardNetwork.MASTERCARD,
            "fields": {
                0: "0200",
                2: "5111111111111111",
                3: "000000",
                4: "000000001000",
                11: "123456",
                22: "021",
                24: "001",
                25: "00",
                41: "TEST1234",
                42: "MERCHANT12345  ",  # Exactly 15 chars with spaces
                48: "MC123",
            },
        },
        "emv_auth": {
            "mti": "0100",
            "fields": {
                0: "0100",
                2: "4111111111111111",
                3: "000000",
                4: "000000001000",
                11: "123456",
                41: "TEST1234",
                42: "MERCHANT12345  ",  # Exactly 15 chars with spaces
                55: "9F0607A0000000031010",  # EMV data
            },
        },
        "reversal": {
            "mti": "0400",
            "fields": {
                0: "0400",
                2: "4111111111111111",
                3: "000000",
                4: "000000001000",
                11: "123456",
                41: "TEST1234",
                42: "MERCHANT12345  ",  # Exactly 15 chars with spaces
                39: "400",  # Reversal response code
                90: "0100123456".ljust(42, "0"),  # Original elements (42 chars)
            },
        },
    }


@pytest.fixture
def create_raw_message():
    """Helper fixture to create raw ISO8583 message strings"""

    def _create_raw_message(mti: str, bitmap: str, data: str) -> str:
        return f"{mti}{bitmap}{data}"

    return _create_raw_message


@pytest.fixture
def create_message():
    """Factory fixture to create ISO8583Message objects"""

    def _create_message(msg_type: str, test_messages: dict) -> ISO8583Message:
        msg_data = test_messages[msg_type]
        return ISO8583Message(
            mti=msg_data["mti"],
            fields=msg_data["fields"].copy(),  # Create a copy to avoid modifying original
            network=msg_data.get("network"),
        )

    return _create_message


@pytest.fixture
def parser():
    """Fixture for parser instance"""
    return ISO8583Parser()


@pytest.fixture
def builder():
    """Fixture for builder instance"""
    return ISO8583Builder()


@pytest.fixture
def validator():
    """Fixture for validator instance"""
    return ISO8583Validator()


@pytest.fixture(scope="session")
def load_test_message():
    """Fixture to load test messages from JSON files"""

    def _load_message(filename: str) -> dict:
        file_path = TEST_DATA_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Test data file not found: {filename}")
        with open(file_path) as f:
            return json.load(f)

    return _load_message


@pytest.fixture(scope="session")
def load_test_config():
    """Fixture to load test configuration from YAML files"""

    def _load_config(filename: str) -> dict:
        file_path = TEST_DATA_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {filename}")
        with open(file_path) as f:
            return yaml.safe_load(f)

    return _load_config


@pytest.fixture
def valid_emv_data():
    """Valid EMV data samples"""
    return [
        "9F0607A0000000031010",  # Simple EMV data
        "9F0607A00000000310109F15020001",  # Multiple tags
        "9F33036028C89F3501229F40056000F0A0019F02060000000001009F03060000000000009F1A0208409F3501229F34034203009F3704C6B1A04F",  # Complex
    ]


@pytest.fixture
def invalid_emv_data():
    """Invalid EMV data samples"""
    return [
        "9F",  # Incomplete tag
        "XX0607A0000000031010",  # Invalid tag
        "9F06XX",  # Invalid length
        "9F0607A0000000",  # Incomplete value
        "9F0607A00000000310ZZ",  # Invalid value characters
    ]


@pytest.fixture
def test_message_file(tmp_path):
    """Fixture to create temporary message files"""

    def _create_message_file(content: str, filename: str = "test_message.txt"):
        file_path = tmp_path / filename
        file_path.write_text(content)
        return file_path

    return _create_message_file
