# tests/test_types.py
import pytest

from iso8583sim.core.types import (
    ISO8583_FIELDS,
    NETWORK_SPECIFIC_FIELDS,
    VERSION_SPECIFIC_FIELDS,
    BuildError,
    CardNetwork,
    FieldDefinition,
    FieldType,
    ISO8583Error,
    ISO8583Message,
    ISO8583Version,
    MessageClass,
    MessageFunction,
    MessageOrigin,
    ParseError,
    ValidationError,
    get_field_definition,
)


def test_field_definition_creation():
    """Test creating field definitions"""
    field = FieldDefinition(field_type=FieldType.NUMERIC, max_length=6, description="Test field")
    assert field.field_type == FieldType.NUMERIC
    assert field.max_length == 6
    assert field.description == "Test field"
    assert field.encoding == "ascii"  # default value
    assert field.min_length == 6  # should be set to max_length in post_init


def test_variable_length_field_definition():
    """Test variable length field definitions"""
    # LLVAR field
    llvar = FieldDefinition(field_type=FieldType.LLVAR, max_length=19, description="Test LLVAR", min_length=1)
    assert llvar.min_length == 1  # min_length should not be modified for LLVAR

    # LLLVAR field
    lllvar = FieldDefinition(field_type=FieldType.LLLVAR, max_length=999, description="Test LLLVAR", min_length=1)
    assert lllvar.min_length == 1  # min_length should not be modified for LLLVAR


def test_field_type_uniqueness():
    """Test that field types have unique values"""
    values = [ft.value for ft in FieldType]
    assert len(values) == len(set(values))  # All values should be unique


def test_field_type_string_representation():
    """Test field type string representation"""
    assert str(FieldType.NUMERIC) == "n"
    assert str(FieldType.ALPHA) == "a"
    assert str(FieldType.ALPHANUMERIC) == "an"
    assert str(FieldType.BINARY) == "b"


def test_message_creation():
    """Test creating ISO8583Message instances"""
    msg = ISO8583Message(mti="0100", fields={0: "0100", 2: "4111111111111111", 3: "000000"}, network=CardNetwork.VISA)
    assert msg.mti == "0100"
    assert msg.version == ISO8583Version.V1987  # default version
    assert msg.network == CardNetwork.VISA
    assert msg.fields[0] == msg.mti


def test_message_class_properties():
    """Test message class property accessors"""
    msg = ISO8583Message(mti="1200", fields={})
    assert msg.message_class == MessageClass.FINANCIAL
    assert msg.message_function == MessageFunction.REQUEST
    assert msg.message_origin == MessageOrigin.ACQUIRER


def test_message_class_enums():
    """Test message class enum values"""
    assert MessageClass.AUTHORIZATION.value == "1"
    assert MessageClass.FINANCIAL.value == "2"
    assert MessageClass.NETWORK_MANAGEMENT.value == "8"


def test_message_function_enums():
    """Test message function enum values"""
    assert MessageFunction.REQUEST.value == "0"
    assert MessageFunction.RESPONSE.value == "1"
    assert MessageFunction.ADVICE.value == "2"


def test_message_origin_enums():
    """Test message origin enum values"""
    assert MessageOrigin.ACQUIRER.value == "0"
    assert MessageOrigin.ISSUER.value == "2"
    assert MessageOrigin.OTHER.value == "4"


def test_network_specific_fields():
    """Test network-specific field definitions"""
    # Test VISA specific field
    visa_field = get_field_definition(44, network=CardNetwork.VISA)
    assert visa_field is not None
    assert visa_field.max_length == 99
    assert visa_field.field_type == FieldType.LLVAR

    # Test Mastercard specific field
    mc_field = get_field_definition(48, network=CardNetwork.MASTERCARD)
    assert mc_field is not None
    assert mc_field.max_length == 999
    assert mc_field.field_type == FieldType.LLLVAR


def test_version_specific_fields():
    """Test version-specific field definitions"""
    # Test field 43 in different versions
    field_1987 = get_field_definition(43, version=ISO8583Version.V1987)
    field_1993 = get_field_definition(43, version=ISO8583Version.V1993)
    field_2003 = get_field_definition(43, version=ISO8583Version.V2003)

    assert field_1987.max_length == 40
    assert field_1993.max_length == 99
    assert field_2003.max_length == 256


def test_field_type_properties():
    """Test field type properties and behavior"""
    for field_type in FieldType:
        # Test string representation
        assert str(field_type) == field_type.value
        # Test uniqueness of values
        assert list(FieldType).count(field_type) == 1


def test_field_definition_defaults():
    """Test field definition default values"""
    field = FieldDefinition(field_type=FieldType.NUMERIC, max_length=6, description="Test")

    assert field.encoding == "ascii"
    assert field.padding_direction == "left"
    assert field.min_length == 6  # Should be set to max_length in post_init
    assert field.padding_char is None


def test_card_network_properties():
    """Test card network properties"""
    assert len(CardNetwork) == 6  # Verify all networks are defined
    assert CardNetwork.VISA.value == "VISA"
    assert CardNetwork.MASTERCARD.value == "MASTERCARD"


def test_field_definition_validation():
    """Test field definition validation"""
    # Test invalid field type
    with pytest.raises(ValueError, match="Invalid field type"):
        FieldDefinition(
            field_type="invalid",  # Should be FieldType enum
            max_length=6,
            description="Test",
        )

    # Test invalid max length
    with pytest.raises(ValueError, match="Invalid max length"):
        FieldDefinition(field_type=FieldType.NUMERIC, max_length=-1, description="Test")

    # Test invalid min length
    with pytest.raises(ValueError, match="Invalid min length"):
        FieldDefinition(field_type=FieldType.NUMERIC, max_length=6, min_length=-1, description="Test")

    # Test min length greater than max length
    with pytest.raises(ValueError, match="min_length cannot be greater than max_length"):
        FieldDefinition(field_type=FieldType.NUMERIC, max_length=6, min_length=8, description="Test")

    # Test invalid padding direction
    with pytest.raises(ValueError, match="Invalid padding direction"):
        FieldDefinition(field_type=FieldType.NUMERIC, max_length=6, description="Test", padding_direction="invalid")

    # Test invalid padding char
    with pytest.raises(ValueError, match="padding_char must be a single character"):
        FieldDefinition(field_type=FieldType.NUMERIC, max_length=6, description="Test", padding_char="00")


def test_custom_exceptions():
    """Test custom exception classes"""
    with pytest.raises(ISO8583Error):
        raise ISO8583Error("General error")

    with pytest.raises(ParseError):
        raise ParseError("Parse error")

    with pytest.raises(ValidationError):
        raise ValidationError("Validation error")

    with pytest.raises(BuildError):
        raise BuildError("Build error")


def test_field_inheritance():
    """Test field definitions inheritance and overrides"""
    # Test that network-specific fields override base fields
    base_field = ISO8583_FIELDS[44]
    visa_field = NETWORK_SPECIFIC_FIELDS[CardNetwork.VISA][44]
    assert base_field != visa_field

    # Test that version-specific fields override base fields
    base_field_43 = ISO8583_FIELDS[43]
    version_2003_field = VERSION_SPECIFIC_FIELDS[ISO8583Version.V2003][43]
    assert base_field_43.max_length != version_2003_field.max_length
