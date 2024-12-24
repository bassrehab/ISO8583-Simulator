# tests/test_integration.py

import pytest
from iso8583sim.core.types import (
    ISO8583Message,
    ISO8583Version,
    CardNetwork,
    FieldType,
    FieldDefinition
)
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.validator import ISO8583Validator


@pytest.fixture
def parser():
    return ISO8583Parser()


@pytest.fixture
def builder():
    return ISO8583Builder()


@pytest.fixture
def validator():
    return ISO8583Validator()


@pytest.fixture
def sample_visa_fields():
    """Sample fields for VISA message"""
    return {
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
        42: "MERCHANT12345"
    }


def test_build_parse_cycle(builder, parser, validator, sample_visa_fields):
    """Test complete build-parse cycle"""
    # Create and build message
    original = ISO8583Message(
        mti="0100",
        fields=sample_visa_fields,
        network=CardNetwork.VISA
    )

    # Validate original message
    errors = validator.validate_message(original)
    assert len(errors) == 0, f"Validation errors: {errors}"

    # Build message
    built = builder.build(original)
    assert built is not None

    # Parse built message
    parsed = parser.parse(built)

    # Verify parsed message matches original
    assert parsed.mti == original.mti
    assert parsed.network == original.network
    for field_num, value in original.fields.items():
        if field_num != 0:  # Skip MTI which is both field 0 and mti
            assert parsed.fields[field_num] == value


def test_network_specific_processing(builder, parser, validator):
    """Test network-specific message processing"""
    # VISA message
    visa_msg = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",
            4: "000000001000",
            11: "123456",
            14: "2412",
            22: "021",
            24: "001",
            25: "00",
            44: "A5B7"
        },
        network=CardNetwork.VISA
    )

    # Build and parse VISA message
    built_visa = builder.build(visa_msg)
    parsed_visa = parser.parse(built_visa)
    assert parsed_visa.network == CardNetwork.VISA
    assert parsed_visa.fields[44] == "A5B7"

    # Mastercard message
    mc_msg = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "5111111111111111",
            3: "000000",
            4: "000000001000",
            11: "123456",
            22: "021",
            24: "001",
            25: "00",
            48: "MC01"
        },
        network=CardNetwork.MASTERCARD
    )

    # Build and parse Mastercard message
    built_mc = builder.build(mc_msg)
    parsed_mc = parser.parse(built_mc)
    assert parsed_mc.network == CardNetwork.MASTERCARD
    assert parsed_mc.fields[48] == "MC01"


def test_response_message_flow(builder, parser, validator):
    """Test complete request-response flow"""
    # Create request message
    request = ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: "4111111111111111",
            3: "000000",
            4: "000000001000",
            11: "123456",
            41: "TEST1234",
            42: "MERCHANT12345"
        }
    )

    # Create response
    response_fields = {
        39: "00",  # Approval code
        54: "000000001000"  # Additional amount
    }
    response = builder.create_response(request, response_fields)

    # Validate response
    errors = validator.validate_message(response)
    assert len(errors) == 0, f"Validation errors: {errors}"

    # Build and parse response
    built_response = builder.build(response)
    parsed_response = parser.parse(built_response)

    # Verify response
    assert parsed_response.mti == "0110"  # Changed from 0100 to 0110
    assert parsed_response.fields[39] == "00"  # Approval
    assert parsed_response.fields[11] == request.fields[11]  # Same STAN
