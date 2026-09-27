# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Convert messages between ISO 8583 versions (1987, 1993, 2003)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .builder import ISO8583Builder
from .types import MTI_VERSION_DIGITS, ISO8583Message, ISO8583Version, get_field_definition
from .validator import ISO8583Validator

# subhadipmitra@: Fields whose content is cryptographic or bound to a key. Their size changes
# between versions (field 52 is 8, 16 or 32 bytes), and padding a PIN block or security
# control data to the new size would produce a value no host could use. They have to be
# regenerated for the target version, so conversion drops them and says why.
_REGENERATE = {
    52: "PIN data must be re-encrypted for the target version's PIN block size",
    53: "security control information must be regenerated for the target version",
    64: "the MAC must be recomputed after conversion",
    128: "the MAC must be recomputed after conversion",
}

# subhadipmitra@: In the 1987 version original data elements live in field 90 (fixed 42).
# The 2003 definitions in this package move them to field 56 (LLLVAR).
_ORIGINAL_DATA_1987 = 90
_ORIGINAL_DATA_2003 = 56


@dataclass
class ConversionResult:
    """Outcome of a version conversion."""

    message: ISO8583Message
    dropped: dict[int, str] = field(default_factory=dict)  # field number -> reason
    notes: list[str] = field(default_factory=list)

    @property
    def lossless(self) -> bool:
        """True when every field was carried over."""
        return not self.dropped


def _meaning(description: str) -> str:
    return re.sub(r"\s*\((1987|1993|2003)\)$", "", description)


def convert_mti(mti: str, target: ISO8583Version) -> str:
    """Rewrite the MTI's version digit for the target version."""
    if len(mti) != 4 or mti[0] not in MTI_VERSION_DIGITS.values():
        raise ValueError(f"Cannot convert MTI {mti!r}: its version digit is not 0, 1 or 2")
    return MTI_VERSION_DIGITS[target] + mti[1:]


def convert_message(message: ISO8583Message, target: ISO8583Version) -> ConversionResult:
    """Convert a message to another ISO 8583 version.

    The MTI version digit is rewritten, original data elements move between field 90 and
    field 56 where the versions differ, and every other field is checked against the
    target version's definition. Fields that don't fit are dropped and reported rather
    than truncated, because a shortened value would be silently wrong.

    Args:
        message: Parsed message in its source version
        target: Version to convert to

    Returns:
        ConversionResult with the converted message, dropped fields and notes
    """
    source = message.version
    result = ConversionResult(
        message=ISO8583Message(mti=convert_mti(message.mti, target), fields={}, version=target, network=message.network)
    )
    if source == target:
        result.message.fields.update(message.fields)
        result.notes.append("Source and target versions are the same. Nothing to convert.")
        return result

    fields = {n: v for n, v in message.fields.items() if n != 0}
    moved: set[int] = set()

    # subhadipmitra@: Move original data elements to where the target version expects them.
    # Only do it when the destination is free, so an explicit value is never overwritten.
    if target == ISO8583Version.V2003 and _ORIGINAL_DATA_1987 in fields and _ORIGINAL_DATA_2003 not in fields:
        fields[_ORIGINAL_DATA_2003] = fields.pop(_ORIGINAL_DATA_1987)
        moved.add(_ORIGINAL_DATA_2003)
        result.notes.append("Moved original data elements from field 90 to field 56.")
    elif source == ISO8583Version.V2003 and _ORIGINAL_DATA_2003 in fields and _ORIGINAL_DATA_1987 not in fields:
        value = fields.pop(_ORIGINAL_DATA_2003)
        if len(value) <= 42:
            fields[_ORIGINAL_DATA_1987] = value.ljust(42, "0")
            moved.add(_ORIGINAL_DATA_1987)
            result.notes.append("Moved original data elements from field 56 to field 90.")
        else:
            result.dropped[_ORIGINAL_DATA_2003] = "original data elements are longer than field 90's 42 characters"

    builder = ISO8583Builder(version=target)
    validator = ISO8583Validator()
    for number, value in sorted(fields.items()):
        source_def = get_field_definition(number, message.network, source)
        target_def = get_field_definition(number, message.network, target)
        if target_def is None:
            result.dropped[number] = f"field {number} is not defined in the {target.value} version"
            continue
        if number in _REGENERATE and source_def != target_def:
            result.dropped[number] = _REGENERATE[number]
            continue

        # subhadipmitra@: Pad the value the way the target builder would, then validate it.
        # This catches values that are too long or have the wrong character type for the
        # target definition, e.g. a 60 character field 43 going back to 1987's fixed 40.
        try:
            formatted = builder._format_field_value(number, value, target_def)
        except Exception as e:
            result.dropped[number] = str(e)
            continue
        valid, error = validator.validate_field(number, formatted, target_def)
        if not valid:
            result.dropped[number] = error or "value does not fit the target definition"
            continue

        result.message.fields[number] = value
        # subhadipmitra@: Compare descriptions without the "(1993)" / "(2003)" suffix, so the
        # note only appears when a field's meaning changes (e.g. 57 to 59 in 2003).
        if (
            number not in moved
            and source_def is not None
            and _meaning(source_def.description) != _meaning(target_def.description)
        ):
            result.notes.append(
                f"Field {number} is '{target_def.description}' in {target.value} "
                f"(was '{source_def.description}'). Check the value still means the same thing."
            )

    return result
