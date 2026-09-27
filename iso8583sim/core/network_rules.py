"""Network-specific field format rules.

Only rules that can be traced to a published description of the field are included, so a
valid message is never rejected by a guessed format. Sources:

- Field 22 (POS entry mode): the DE022 code reference aligned to the Mastercard Customer
  Interface Specification (Feb 2024) and Visa VisaNet Authorization-Only Online Messages
  (Oct 2023), https://docs.tech.sofi.com/pro/reference/api-reference-de022-codes
- Mastercard field 48: the Mastercard Customer Interface Specification layout of DE 48,
  a transaction category code followed by subelements (ID n-2, length n-2, data).
"""

from __future__ import annotations

from collections.abc import Callable

from .types import CardNetwork

# PAN entry mode: first two digits of field 22
PAN_ENTRY_MODES = {
    "00": "Unknown",
    "01": "Manual entry",
    "02": "Magnetic stripe",
    "03": "Barcode",
    "04": "OCR",
    "05": "Chip (ICC)",
    "06": "Contactless, mapping service applied",
    "07": "Contactless chip",
    "09": "E-commerce with DSRP cryptogram",
    "10": "Credential on file",
    "51": "Chip plus PIN at ATM",
    "71": "Contactless chip plus PIN at ATM",
    "79": "Chip fallback, hybrid terminal failure",
    "80": "Chip fallback to magnetic stripe",
    "81": "E-commerce",
    "82": "Auto entry via server",
    "90": "Magnetic stripe, full track read",
    "91": "Contactless magnetic stripe",
    "95": "Chip with unreliable CVV (Visa only)",
}

# subhadipmitra@: The reference marks 95 as a Visa-only code. The rest are shared, so a
# Mastercard message with 95 is the one clear-cut network mismatch to report.
VISA_ONLY_PAN_ENTRY_MODES = frozenset({"95"})

# PIN entry capability: third digit of field 22
PIN_ENTRY_CAPABILITY = {
    "0": "Unknown",
    "1": "Terminal can accept PINs",
    "2": "Terminal cannot accept PINs",
    "3": "Software-based PIN entry (mPOS)",
    "8": "PIN pad not working",
}


def check_pos_entry_mode(value: str, network: CardNetwork) -> list[str]:
    """Check field 22 against the codes the network defines."""
    if len(value) != 3 or not value.isdigit():
        return [f"{network.value} field 22 must be 3 digits (PAN entry mode + PIN capability), got {value!r}"]
    errors = []
    mode, pin = value[:2], value[2]
    if mode not in PAN_ENTRY_MODES:
        errors.append(f"{network.value} field 22: unknown PAN entry mode {mode}")
    elif network == CardNetwork.MASTERCARD and mode in VISA_ONLY_PAN_ENTRY_MODES:
        errors.append(f"MASTERCARD field 22: PAN entry mode {mode} is Visa only")
    if pin not in PIN_ENTRY_CAPABILITY:
        errors.append(f"{network.value} field 22: unknown PIN entry capability {pin}")
    return errors


def check_mastercard_de48(value: str) -> list[str]:
    """Check Mastercard field 48: a transaction category code, then well-formed subelements."""
    if not value:
        return ["MASTERCARD field 48 is empty; it must start with a transaction category code"]
    # subhadipmitra@: Position 1 is the transaction category code (an-1, e.g. R for retail).
    # The rest is a sequence of subelements: 2-digit ID, 2-digit length, then that many
    # characters. Walking the sequence catches truncated or misaligned data.
    if not (value[0].isalnum() or value[0] == " "):
        return [f"MASTERCARD field 48: invalid transaction category code {value[0]!r}"]
    pos = 1
    while pos < len(value):
        header = value[pos : pos + 4]
        if len(header) < 4 or not header.isdigit():
            return [f"MASTERCARD field 48: expected a subelement ID and length at position {pos + 1}, got {header!r}"]
        length = int(header[2:])
        if pos + 4 + length > len(value):
            return [f"MASTERCARD field 48: subelement {header[:2]} says {length} characters but the field ends first"]
        pos += 4 + length
    return []


NETWORK_FIELD_RULES: dict[CardNetwork, dict[int, Callable[[str], list[str]]]] = {
    CardNetwork.VISA: {22: lambda v: check_pos_entry_mode(v, CardNetwork.VISA)},
    CardNetwork.MASTERCARD: {
        22: lambda v: check_pos_entry_mode(v, CardNetwork.MASTERCARD),
        48: check_mastercard_de48,
    },
}


def check_network_fields(fields: dict[int, str], network: CardNetwork) -> list[str]:
    """Apply the network's field rules to the fields that are present."""
    rules = NETWORK_FIELD_RULES.get(network, {})
    errors: list[str] = []
    for number, rule in rules.items():
        if number in fields:
            errors.extend(rule(fields[number]))
    return errors
