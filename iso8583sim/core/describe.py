"""Rule-based, human-readable descriptions of ISO 8583 messages.

These helpers need no LLM. They power `iso8583sim explain --no-llm` and the
MCP server's explain_message tool.
"""

from __future__ import annotations

from typing import Any

from .codes import CURRENCY_CODES, NETWORK_MANAGEMENT_CODES, PROCESSING_CODES, RESPONSE_CODES
from .emv import explain_cid, explain_tvr, get_tag_name, parse_emv_data
from .types import (
    CardNetwork,
    ISO8583Message,
    ISO8583Version,
    MessageClass,
    MessageFunction,
    MessageOrigin,
    get_field_definition,
)


def field_name(field_number: int, network: CardNetwork | None, version: ISO8583Version) -> str:
    """Return a field's description, or "Unknown" if it is not defined."""
    field_def = get_field_definition(field_number, network, version)
    return field_def.description if field_def else "Unknown"


def field_entries(message: ISO8583Message) -> list[dict[str, Any]]:
    """List a message's fields (excluding the MTI) as number, name and value entries."""
    return [
        {"number": n, "name": field_name(n, message.network, message.version), "value": v}
        for n, v in sorted(message.fields.items())
        if n != 0
    ]


def mask_pan(pan: str) -> str:
    """Mask a PAN, keeping the first six and last four digits."""
    # subhadipmitra@: First six (BIN) and last four is the PCI DSS display limit. The BIN
    # identifies the issuer and network, which is what a reader needs to see.
    if len(pan) < 10:
        return pan
    return pan[:6] + "*" * (len(pan) - 10) + pan[-4:]


def format_amount(amount: str, currency: str | None) -> str:
    """Format a minor-unit amount (field 4) using the currency's exponent, e.g. "10.00 USD"."""
    # subhadipmitra@: Field 4 is in minor units, so the currency exponent decides the decimal
    # point (JPY has 0, USD has 2). Unknown currencies fall back to 2 decimals and show the code.
    code, exponent = CURRENCY_CODES.get(currency or "", (currency or "", 2))
    value = int(amount) / (10**exponent) if amount.isdigit() else amount
    if isinstance(value, float):
        return f"{value:,.{exponent}f} {code}".strip()
    return f"{value} {code}".strip()


def decode_emv_tags(data: str) -> list[dict[str, Any]]:
    """Decode EMV TLV data into named tags, explaining the TVR (95) and CID (9F27)."""
    tags = []
    for tag, value in parse_emv_data(data).items():
        entry: dict[str, Any] = {"tag": tag, "name": get_tag_name(tag), "value": value}
        if tag == "95":
            entry["explanation"] = explain_tvr(value)
        elif tag == "9F27":
            entry["explanation"] = explain_cid(value)
        tags.append(entry)
    return tags


def describe_mti(mti: str) -> dict[str, str]:
    """Describe an MTI's message class, function and origin."""

    def lookup(enum: Any, char: str) -> str:
        try:
            return enum(char).name.replace("_", " ").lower()
        except ValueError:
            return "unknown"

    return {
        "class": lookup(MessageClass, mti[1]),
        "function": lookup(MessageFunction, mti[2]),
        "origin": lookup(MessageOrigin, mti[3]),
    }


def describe_message(message: ISO8583Message) -> dict[str, Any]:
    """Describe a message in plain language without an LLM.

    Args:
        message: Parsed message

    Returns:
        Dictionary with a one-paragraph "summary", the MTI breakdown, named fields
        and, when field 55 is present, decoded EMV tags
    """
    # subhadipmitra@: Build the summary from a fixed set of well-known fields, in the order a
    # payments engineer reads a message: what, which card, what kind, how much, outcome, where.
    fields = message.fields
    mti_info = describe_mti(message.mti)
    facts: list[str] = [f"MTI {message.mti}: {mti_info['class']} {mti_info['function']} from {mti_info['origin']}."]

    if message.network:
        facts.append(f"Card network: {message.network.value}.")
    if 2 in fields:
        # subhadipmitra@: Never put the full PAN in a summary, since it may be pasted into chats or logs.
        facts.append(f"Card: {mask_pan(fields[2])}.")
    if 3 in fields:
        kind = PROCESSING_CODES.get(fields[3][:2], f"processing code {fields[3]}")
        facts.append(f"Transaction type: {kind}.")
    if 4 in fields:
        facts.append(f"Amount: {format_amount(fields[4], fields.get(49))}.")
    if 39 in fields:
        meaning = RESPONSE_CODES.get(fields[39], "unrecognised response code")
        facts.append(f"Response code {fields[39]}: {meaning}.")
    if 38 in fields:
        facts.append(f"Approval code: {fields[38].strip()}.")
    if 70 in fields:
        facts.append(f"Network management: {NETWORK_MANAGEMENT_CODES.get(fields[70], fields[70])}.")
    if 41 in fields:
        facts.append(f"Terminal: {fields[41].strip()}.")
    if 42 in fields:
        facts.append(f"Merchant: {fields[42].strip()}.")
    if 55 in fields:
        facts.append("Chip (EMV) data is present in field 55.")

    result: dict[str, Any] = {
        "summary": " ".join(facts),
        "mti": {"value": message.mti, **mti_info},
        "fields": field_entries(message),
    }
    # subhadipmitra@: Bad EMV data shouldn't hide the rest of the description, so decoding
    # errors are reported alongside it instead of raised.
    if 55 in fields:
        try:
            result["emv"] = decode_emv_tags(fields[55])
        except Exception as e:
            result["emv_error"] = str(e)
    return result
