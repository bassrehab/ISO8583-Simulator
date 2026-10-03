# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Custom field definitions from a file (iso8583sim.core.spec)."""

import json

import pytest
from typer.testing import CliRunner

from iso8583sim.cli.commands import app
from iso8583sim.core import (
    FieldType,
    ISO8583Builder,
    ISO8583Message,
    ISO8583Parser,
    ISO8583Validator,
    ISO8583Version,
    Spec,
    SpecError,
)

ACME = {
    "name": "Acme network",
    "version": "1987",
    "fields": {
        # Standard 62 is LLLVAR up to 999; Acme sends 12 fixed characters, space padded.
        "62": {"type": "an", "max_length": 12, "padding_char": " ", "padding_direction": "right"},
        48: {"type": "LLLVAR", "max_length": 20, "description": "Acme additional data"},
    },
}

FIELDS = {2: "4111111111111111", 3: "000000", 4: "000000001000", 11: "000123", 41: "TERM0001", 62: "ACME1"}


def test_a_spec_s_fields_replace_the_standard_ones_and_the_rest_stay():
    spec = Spec.from_dict(ACME)
    assert spec.name == "Acme network" and spec.version is ISO8583Version.V1987
    assert spec.definition(62).field_type is FieldType.ALPHANUMERIC and spec.definition(62).max_length == 12
    assert spec.definition(48).description == "Acme additional data"
    assert spec.definition(2).field_type is FieldType.LLVAR  # not in the spec: the standard's
    assert Spec.from_dict(spec.to_dict()) == spec


def test_messages_build_and_parse_through_the_spec():
    spec = Spec.from_dict(ACME)
    raw = ISO8583Builder(spec=spec).build(ISO8583Message(mti="0100", fields=dict(FIELDS)))
    # Field 62 goes as 12 fixed characters, with no length prefix: the spec's layout.
    assert raw.endswith("ACME1       ")
    parsed = ISO8583Parser(spec=spec).parse(raw)
    assert parsed.fields[62] == "ACME1" and parsed.fields[41] == "TERM0001"
    # Without the spec, the same field is a three-digit length and its data.
    assert ISO8583Builder().build(ISO8583Message(mti="0100", fields=dict(FIELDS))).endswith("005ACME1")


def test_the_validator_holds_values_to_the_spec():
    spec = Spec.from_dict(ACME)
    message = ISO8583Message(mti="0100", fields={**FIELDS, 48: "X" * 21})
    assert any("48" in error for error in ISO8583Validator(spec=spec).validate_message(message))
    assert not any("48" in error for error in ISO8583Validator().validate_message(message))


@pytest.mark.parametrize(
    "data, problem",
    [
        ({"fields": {"62": {"type": "an"}}}, "type and max_length are required"),
        ({"fields": {"62": {"type": "money", "max_length": 3}}}, "type must be one of"),
        ({"fields": {"1": {"type": "an", "max_length": 3}}}, "Field numbers are 2 to 128"),
        ({"fields": {"sixty": {"type": "an", "max_length": 3}}}, "Field numbers are 2 to 128"),
        ({"fields": {"62": {"type": "an", "max_length": 3, "colour": "red"}}}, "unknown keys colour"),
        ({"fields": {"62": {"type": "an", "max_length": 0}}}, "Field 62"),
        ({"version": "1999"}, "version must be one of"),
        ({"name": "x", "extra": 1}, "Unknown keys extra"),
    ],
)
def test_problems_are_named(data, problem):
    with pytest.raises(SpecError, match=problem):
        Spec.from_dict(data)


def test_specs_are_read_from_json_and_yaml_files(tmp_path):
    json_file = tmp_path / "acme.json"
    json_file.write_text(json.dumps(ACME))
    yaml_file = tmp_path / "acme.yaml"
    yaml_file.write_text(
        "name: Acme network\n"
        'version: "1987"\n'
        "fields:\n"
        '  62: {type: an, max_length: 12, padding_char: " ", padding_direction: right}\n'
        "  48: {type: lllvar, max_length: 20, description: Acme additional data}\n"
    )
    assert Spec.from_file(json_file) == Spec.from_file(yaml_file)
    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    with pytest.raises(SpecError, match="isn't valid JSON"):
        Spec.from_file(broken)


def test_the_command_line_takes_a_spec(tmp_path):
    spec_file = tmp_path / "acme.json"
    spec_file.write_text(json.dumps(ACME))
    fields_file = tmp_path / "fields.json"
    fields_file.write_text(json.dumps({str(k): v for k, v in FIELDS.items()}))
    runner = CliRunner()
    built = runner.invoke(app, ["build", "--mti", "0100", "--fields", str(fields_file), "--spec", str(spec_file)])
    assert built.exit_code == 0, built.output
    raw = ISO8583Builder(spec=Spec.from_dict(ACME)).build(ISO8583Message(mti="0100", fields=dict(FIELDS)))
    parsed = runner.invoke(app, ["parse", raw, "--format", "json", "--spec", str(spec_file)])
    assert parsed.exit_code == 0, parsed.output
    assert '"62": "ACME1"' in parsed.output
    # The card makes it a VISA message, whose own required fields this one lacks; field 62 is fine.
    validated = runner.invoke(app, ["validate", raw, "--spec", str(spec_file)])
    assert "Field 62" not in validated.output and "Required field 14" in validated.output
