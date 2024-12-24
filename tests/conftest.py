# tests/conftest.py
import pytest
from datetime import datetime
from pathlib import Path
import json
import yaml
from iso8583sim.core.types import (
    ISO8583Message,
    ISO8583Version,
    CardNetwork,
    FieldType,
    FieldDefinition
)

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
def sample_message_data():
    """Fixture providing sample message data"""
    return {
        "mti": "0100",
        "fields": {
            "0": "0100",
            "2": "4111111111111111",
            "3": "000000",  # Fixed: properly formatted
            "4": "000000001000",
            "11": "123456",
            "12": datetime.now().strftime("%H%M%S"),
            "13": datetime.now().strftime("%m%d"),
            "41": "TEST1234",  # Fixed: 8 characters
            "42": "MERCHANT12345 "  # Fixed: 15 characters
        }
    }


@pytest.fixture
def network_specific_data():
    """Fixture providing network-specific test data"""
    return {
        CardNetwork.VISA: {
            "mti": "0100",
            "fields": {
                "0": "0100",
                "2": "4111111111111111",
                "3": "000000",  # Fixed: properly formatted
                "4": "000000001000",
                "11": "123456",
                "14": "2412",
                "22": "021",
                "24": "001",
                "25": "00",
                "44": "A5B7"
            }
        },
        CardNetwork.MASTERCARD: {
            "mti": "0200",
            "fields": {
                "0": "0200",
                "2": "5111111111111111",
                "3": "000000",  # Fixed: properly formatted
                "4": "000000001000",
                "11": "123456",
                "22": "021",
                "24": "001",
                "25": "00",
                "48": "MC123"
            }
        }
    }


@pytest.fixture
def tmp_message_file(tmp_path):
    """Fixture to create temporary message files"""

    def _create_message_file(content: str, filename: str = "test_message.txt"):
        file_path = tmp_path / filename
        file_path.write_text(content)
        return file_path

    return _create_message_file
