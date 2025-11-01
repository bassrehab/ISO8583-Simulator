# tests/test_integration.py

from iso8583sim.core.types import CardNetwork


def test_build_parse_cycle(builder, parser, validator, test_messages, create_message):
    """Test complete build-parse cycle"""

    # Create message using centralized test data
    original = create_message("visa_auth", test_messages)

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


def test_network_specific_processing(builder, parser, validator, test_messages, create_message):
    """Test network-specific message processing"""
    # Create VISA message
    visa_msg = create_message("visa_auth", test_messages)

    # Build and parse VISA message
    built_visa = builder.build(visa_msg)
    parsed_visa = parser.parse(built_visa)
    assert parsed_visa.network == CardNetwork.VISA
    assert parsed_visa.fields[44] == "A5B7"

    # Create Mastercard message
    mc_msg = create_message("mastercard_auth", test_messages)

    # Build and parse Mastercard message
    built_mc = builder.build(mc_msg)
    parsed_mc = parser.parse(built_mc)
    assert parsed_mc.network == CardNetwork.MASTERCARD
    assert parsed_mc.fields[48] == "MC123"


def test_response_message_flow(builder, parser, validator, test_messages, create_message):
    """Test complete request-response flow"""
    # Create request message using centralized test data
    request = create_message("basic_auth", test_messages)

    # Create response
    response_fields = {
        39: "00",  # Approval code
        54: "000000001000",  # Additional amount
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
