# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

# iso8583sim/core/spec.py

"""Custom field definitions from a file: a network's or a host's own fields over a standard version.

A spec names the ISO 8583 version it builds on and the fields it defines differently. Pass it to
the parser, builder and validator, and its fields are used wherever it defines them::

    spec = Spec.from_file("acme.yaml")
    message = ISO8583Parser(spec=spec).parse(raw)
    raw = ISO8583Builder(spec=spec).build(message)

The file is JSON, or YAML with PyYAML installed (``pip install "iso8583sim[yaml]"``)::

    name: Acme network
    version: "1987"
    fields:
      48: {type: lllvar, max_length: 120, description: Acme additional data}
      62: {type: an, max_length: 12, padding_char: " ", padding_direction: right}

Field entries take what a FieldDefinition does: ``type`` (n, a, an, b, s, z, ll or lll, or the
names NUMERIC, ALPHANUMERIC, LLVAR and so on), ``max_length``, and optionally ``min_length``,
``description``, ``padding_char``, ``padding_direction`` (left or right) and ``encoding``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .types import CardNetwork, FieldDefinition, FieldType, ISO8583Version, get_field_definition

_KEYS = {"type", "max_length", "min_length", "description", "padding_char", "padding_direction", "encoding"}


class SpecError(ValueError):
    """A spec file or definition that can't be used, saying what's wrong and where."""


def _field_type(value: Any, where: str) -> FieldType:
    if isinstance(value, str):
        text = value.strip()
        for field_type in FieldType:
            if text.lower() == field_type.value or text.upper() == field_type.name:
                return field_type
    choices = ", ".join(t.value for t in FieldType)
    raise SpecError(f"{where}: type must be one of {choices} (or their names), not {value!r}")


def _definition(number: int, entry: Any) -> FieldDefinition:
    where = f"Field {number}"
    if not isinstance(entry, Mapping):
        raise SpecError(f"{where}: expected a mapping of type, max_length and so on")
    unknown = set(entry) - _KEYS
    if unknown:
        raise SpecError(f"{where}: unknown keys {', '.join(sorted(map(str, unknown)))}")
    if "type" not in entry or "max_length" not in entry:
        raise SpecError(f"{where}: type and max_length are required")
    try:
        return FieldDefinition(
            field_type=_field_type(entry["type"], where),
            max_length=int(entry["max_length"]),
            description=str(entry.get("description") or f"Field {number}"),
            field_number=number,
            encoding=str(entry.get("encoding", "ascii")),
            min_length=int(entry["min_length"]) if entry.get("min_length") is not None else None,
            padding_char=entry.get("padding_char"),
            padding_direction=str(entry.get("padding_direction", "left")),
        )
    except SpecError:
        raise
    except (TypeError, ValueError) as e:
        raise SpecError(f"{where}: {e}") from None


@dataclass(frozen=True)
class Spec:
    """Field definitions over a standard version. Fields the spec doesn't define keep the version's."""

    name: str
    version: ISO8583Version = ISO8583Version.V1987
    fields: Mapping[int, FieldDefinition] = field(default_factory=dict)

    def definition(
        self, number: int, network: CardNetwork | None = None, version: ISO8583Version | None = None
    ) -> FieldDefinition | None:
        """The definition of a field: the spec's own, or the standard one for the version and network."""
        own = self.fields.get(number)
        if own is not None:
            return own
        return get_field_definition(number, network, version or self.version)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Spec:
        if not isinstance(data, Mapping):
            raise SpecError("A spec is a mapping with name, version and fields")
        unknown = set(data) - {"name", "version", "fields"}
        if unknown:
            raise SpecError(f"Unknown keys {', '.join(sorted(map(str, unknown)))}: a spec has name, version and fields")
        version_text = str(data.get("version", "1987"))
        try:
            version = ISO8583Version(version_text)
        except ValueError:
            choices = ", ".join(v.value for v in ISO8583Version)
            raise SpecError(f"version must be one of {choices}, not {version_text!r}") from None
        entries = data.get("fields") or {}
        if not isinstance(entries, Mapping):
            raise SpecError("fields must be a mapping of field numbers to definitions")
        fields: dict[int, FieldDefinition] = {}
        for key, entry in entries.items():
            try:
                number = int(key)
            except (TypeError, ValueError):
                raise SpecError(f"Field numbers are 2 to 128, not {key!r}") from None
            if not 2 <= number <= 128:
                raise SpecError(f"Field numbers are 2 to 128, not {number}")
            fields[number] = _definition(number, entry)
        return cls(name=str(data.get("name") or "Custom spec"), version=version, fields=fields)

    @classmethod
    def from_file(cls, path: str | Path) -> Spec:
        """Read a spec from a JSON file, or a YAML one (.yaml or .yml) with PyYAML installed."""
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() in (".yaml", ".yml"):
            try:
                import yaml  # type: ignore[import-untyped]
            except ImportError:
                raise SpecError('Reading a YAML spec needs PyYAML: pip install "iso8583sim[yaml]"') from None
            try:
                data = yaml.safe_load(text)
            except yaml.YAMLError as e:
                raise SpecError(f"{path.name} isn't valid YAML: {e}") from None
        else:
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                raise SpecError(f"{path.name} isn't valid JSON: {e}") from None
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        """The spec as from_dict reads it, for saving or sharing."""
        fields: dict[str, Any] = {}
        for number in sorted(self.fields):
            definition = self.fields[number]
            entry: dict[str, Any] = {
                "type": definition.field_type.value,
                "max_length": definition.max_length,
                "description": definition.description,
            }
            if definition.min_length is not None:
                entry["min_length"] = definition.min_length
            if definition.padding_char is not None:
                entry["padding_char"] = definition.padding_char
                entry["padding_direction"] = definition.padding_direction
            if definition.encoding != "ascii":
                entry["encoding"] = definition.encoding
            fields[str(number)] = entry
        return {"name": self.name, "version": self.version.value, "fields": fields}
