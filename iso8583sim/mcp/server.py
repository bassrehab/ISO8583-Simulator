"""MCP server exposing the ISO 8583 toolkit to MCP clients (Claude, Cursor, etc.)."""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from typing import Any, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError

from .. import __version__
from ..core.builder import ISO8583Builder
from ..core.codes import (
    CURRENCY_CODES,
    NETWORK_MANAGEMENT_CODES,
    PROCESSING_CODES,
    RESPONSE_CODES,
    detect_network_from_pan,
)
from ..core.emv import EMV_TAGS, explain_cid, explain_tvr, get_tag_name, parse_emv_data
from ..core.parser import ISO8583Parser
from ..core.types import (
    ISO8583_FIELDS,
    CardNetwork,
    ISO8583Error,
    ISO8583Message,
    ISO8583Version,
    MessageClass,
    MessageFunction,
    MessageOrigin,
    get_field_definition,
)
from ..core.validator import ISO8583Validator

INSTRUCTIONS = """\
Tools for working with ISO 8583 payment messages (card authorizations, financial
transactions, reversals and network management).

Messages are passed as ASCII strings: MTI, hex bitmap, then field data. Field
numbers in `fields` arguments are strings ("2", "4", "41"). Versions are "1987",
"1993" or "2003". Networks are VISA, MASTERCARD, AMEX, DISCOVER, JCB or UNIONPAY.

Start with parse_message or explain_message to understand a message, and
validate_message before sending one anywhere.
"""

SAMPLE_PANS = {
    CardNetwork.VISA: "4111111111111111",
    CardNetwork.MASTERCARD: "5555555555554444",
    CardNetwork.AMEX: "378282246310005",
    CardNetwork.DISCOVER: "6011111111111117",
    CardNetwork.JCB: "3530111333300000",
    CardNetwork.UNIONPAY: "6200000000000005",
}

MESSAGE_TYPES = {"auth": "0100", "financial": "0200", "echo": "0800"}

F = TypeVar("F", bound=Callable[..., Any])


def _reported_as(error_type: type[Exception]) -> Callable[[F], F]:
    """Turn expected input errors into MCP errors whose message reaches the client."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except (ValueError, ISO8583Error) as e:
                raise error_type(str(e)) from e

        return wrapper  # type: ignore[return-value]

    return decorator


tool_errors = _reported_as(ToolError)
resource_errors = _reported_as(ResourceError)


def _version(version: str) -> ISO8583Version:
    try:
        return ISO8583Version(version)
    except ValueError:
        raise ValueError(f"Unknown version {version!r}. Use 1987, 1993 or 2003.") from None


def _network(network: str | None) -> CardNetwork | None:
    if not network:
        return None
    try:
        return CardNetwork(network.upper())
    except ValueError:
        names = ", ".join(n.value for n in CardNetwork)
        raise ValueError(f"Unknown network {network!r}. Use one of: {names}.") from None


def _parse(message: str, network: str | None = None, version: str = "1987") -> ISO8583Message:
    return ISO8583Parser(version=_version(version)).parse(message.rstrip("\r\n"), network=_network(network))


def _field_name(field_number: int, network: CardNetwork | None, version: ISO8583Version) -> str:
    field_def = get_field_definition(field_number, network, version)
    return field_def.description if field_def else "Unknown"


def _fields_out(message: ISO8583Message) -> list[dict[str, Any]]:
    return [
        {"number": n, "name": _field_name(n, message.network, message.version), "value": v}
        for n, v in sorted(message.fields.items())
        if n != 0
    ]


def _fields_in(fields: dict[str, str]) -> dict[int, str]:
    try:
        return {int(k): str(v) for k, v in fields.items()}
    except ValueError:
        raise ValueError('Field numbers must be integers, e.g. {"2": "4111111111111111"}') from None


def _mask_pan(pan: str) -> str:
    if len(pan) < 10:
        return pan
    return pan[:6] + "*" * (len(pan) - 10) + pan[-4:]


def _format_amount(amount: str, currency: str | None) -> str:
    code, exponent = CURRENCY_CODES.get(currency or "", (currency or "", 2))
    value = int(amount) / (10**exponent) if amount.isdigit() else amount
    if isinstance(value, float):
        return f"{value:,.{exponent}f} {code}".strip()
    return f"{value} {code}".strip()


def _decode_emv(data: str) -> list[dict[str, Any]]:
    tags = []
    for tag, value in parse_emv_data(data).items():
        entry: dict[str, Any] = {"tag": tag, "name": get_tag_name(tag), "value": value}
        if tag == "95":
            entry["explanation"] = explain_tvr(value)
        elif tag == "9F27":
            entry["explanation"] = explain_cid(value)
        tags.append(entry)
    return tags


def _describe_mti(mti: str) -> dict[str, str]:
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


def _explain(message: ISO8583Message) -> dict[str, Any]:
    fields = message.fields
    mti_info = _describe_mti(message.mti)
    facts: list[str] = [f"MTI {message.mti}: {mti_info['class']} {mti_info['function']} from {mti_info['origin']}."]

    if message.network:
        facts.append(f"Card network: {message.network.value}.")
    if 2 in fields:
        facts.append(f"Card: {_mask_pan(fields[2])}.")
    if 3 in fields:
        kind = PROCESSING_CODES.get(fields[3][:2], f"processing code {fields[3]}")
        facts.append(f"Transaction type: {kind}.")
    if 4 in fields:
        facts.append(f"Amount: {_format_amount(fields[4], fields.get(49))}.")
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
        "fields": _fields_out(message),
    }
    if 55 in fields:
        try:
            result["emv"] = _decode_emv(fields[55])
        except Exception as e:
            result["emv_error"] = str(e)
    return result


def create_server() -> MCPServer:
    """Create the iso8583sim MCP server with its tools, resources and prompts."""
    server = MCPServer(name="iso8583sim", version=__version__, instructions=INSTRUCTIONS, log_level="WARNING")
    builder_for = {v: ISO8583Builder(version=v) for v in ISO8583Version}
    validator = ISO8583Validator()

    # Tools

    @server.tool()
    @tool_errors
    def parse_message(message: str, network: str | None = None, version: str = "1987") -> dict[str, Any]:
        """Parse a raw ISO 8583 message into its MTI, bitmap and named fields.

        The network is detected from the PAN when not given.
        """
        parsed = _parse(message, network, version)
        result: dict[str, Any] = {
            "mti": parsed.mti,
            "version": parsed.version.value,
            "network": parsed.network.value if parsed.network else None,
            "bitmap": parsed.bitmap,
            "fields": _fields_out(parsed),
        }
        if 55 in parsed.fields:
            try:
                result["emv"] = _decode_emv(parsed.fields[55])
            except Exception as e:
                result["emv_error"] = str(e)
        return result

    @server.tool()
    @tool_errors
    def build_message(
        mti: str, fields: dict[str, str], network: str | None = None, version: str = "1987"
    ) -> dict[str, Any]:
        """Build a raw ISO 8583 message from an MTI and a map of field number to value.

        Example fields: {"2": "4111111111111111", "3": "000000", "4": "000000001000", "11": "123456"}
        """
        v = _version(version)
        message = ISO8583Message(mti=mti, fields=_fields_in(fields), version=v, network=_network(network))
        raw = builder_for[v].build(message)
        return {"message": raw, "length": len(raw)}

    @server.tool()
    @tool_errors
    def validate_message(message: str, network: str | None = None, version: str = "1987") -> dict[str, Any]:
        """Check a raw message for format, length and network-specific rule violations."""
        try:
            parsed = _parse(message, network, version)
        except Exception as e:
            return {"valid": False, "errors": [f"Parse error: {e}"]}
        errors = validator.validate_message(parsed)
        return {
            "valid": not errors,
            "errors": errors,
            "network": parsed.network.value if parsed.network else None,
        }

    @server.tool()
    @tool_errors
    def explain_message(message: str, network: str | None = None, version: str = "1987") -> dict[str, Any]:
        """Explain a raw message in plain language: transaction type, amount, card, outcome and fields.

        Rule-based, so it needs no LLM API key.
        """
        return _explain(_parse(message, network, version))

    @server.tool()
    @tool_errors
    def decode_emv(data: str) -> dict[str, Any]:
        """Decode EMV chip data (field 55, hex TLV) into named tags, including TVR and CID explanations."""
        return {"tags": _decode_emv(data.strip())}

    @server.tool()
    @tool_errors
    def generate_test_message(
        message_type: str = "auth",
        network: str | None = None,
        pan: str | None = None,
        amount_minor_units: int = 1000,
        currency: str = "840",
        stan: str = "123456",
    ) -> dict[str, Any]:
        """Generate a valid test message.

        message_type is one of: auth (0100), financial (0200), echo (0800).
        Amount is in minor units (1000 = 10.00). Uses a well-known test PAN for the network when none is given.
        """
        if message_type not in MESSAGE_TYPES:
            raise ValueError(f"Unknown message_type {message_type!r}. Use one of: {', '.join(MESSAGE_TYPES)}.")
        mti = MESSAGE_TYPES[message_type]
        net = _network(network)

        if message_type == "echo":
            fields = {7: "1215143022", 11: stan, 70: "301"}
        else:
            card = pan or SAMPLE_PANS.get(net or CardNetwork.VISA, SAMPLE_PANS[CardNetwork.VISA])
            net = net or detect_network_from_pan(card)
            fields = {
                2: card,
                3: "000000",
                4: f"{amount_minor_units:012d}",
                11: stan,
                14: "2612",
                22: "051",
                24: "001",
                25: "00",
                41: "TERM0001",
                42: "MERCHANT123456 ",
                49: currency,
            }
            if message_type == "financial":
                fields.update({12: "143022", 13: "1215"})

        message = ISO8583Message(mti=mti, fields=fields, network=net)
        raw = builder_for[ISO8583Version.V1987].build(message)
        return {"message": raw, "mti": mti, "network": net.value if net else None, "fields": _fields_out(message)}

    @server.tool()
    @tool_errors
    def create_response(
        message: str, response_code: str = "00", approval_code: str | None = None, version: str = "1987"
    ) -> dict[str, Any]:
        """Create the response to a request message (0100 -> 0110, 0200 -> 0210, 0800 -> 0810).

        Copies the matching fields from the request and sets the response code (field 39).
        """
        v = _version(version)
        request = _parse(message, version=version)
        response_fields = {39: response_code}
        if approval_code:
            response_fields[38] = approval_code.ljust(6)[:6]
        response = builder_for[v].create_response(request, response_fields)
        raw = builder_for[v].build(response)
        return {"message": raw, "mti": response.mti, "fields": _fields_out(response)}

    @server.tool()
    @tool_errors
    def create_reversal(message: str, version: str = "1987") -> dict[str, Any]:
        """Create a reversal (04xx) for an original message, with field 90 set to the original data elements."""
        v = _version(version)
        original = _parse(message, version=version)
        reversal = builder_for[v].create_reversal(original)
        raw = builder_for[v].build(reversal)
        return {"message": raw, "mti": reversal.mti, "fields": _fields_out(reversal)}

    @server.tool()
    @tool_errors
    def lookup_field(field_number: int, network: str | None = None, version: str = "1987") -> dict[str, Any]:
        """Look up a field definition: name, type, length and padding, including network and version overrides."""
        field_def = get_field_definition(field_number, _network(network), _version(version))
        if field_def is None:
            raise ValueError(f"Field {field_number} is not defined.")
        return {
            "number": field_number,
            "name": field_def.description,
            "type": field_def.field_type.name,
            "max_length": field_def.max_length,
            "min_length": field_def.min_length,
            "padding_char": field_def.padding_char,
            "padding_direction": field_def.padding_direction,
        }

    @server.tool()
    @tool_errors
    def detect_network(pan: str) -> dict[str, Any]:
        """Detect the card network from a PAN's issuer prefix."""
        net = detect_network_from_pan(pan.strip())
        return {"network": net.value if net else None}

    @server.tool()
    @tool_errors
    def diff_messages(message_a: str, message_b: str, version: str = "1987") -> dict[str, Any]:
        """Compare two raw messages field by field and report added, removed and changed fields."""
        a = _parse(message_a, version=version)
        b = _parse(message_b, version=version)
        numbers = sorted((set(a.fields) | set(b.fields)) - {0})
        added, removed, changed = [], [], []
        for n in numbers:
            name = _field_name(n, a.network or b.network, a.version)
            if n not in a.fields:
                added.append({"number": n, "name": name, "value": b.fields[n]})
            elif n not in b.fields:
                removed.append({"number": n, "name": name, "value": a.fields[n]})
            elif a.fields[n] != b.fields[n]:
                changed.append({"number": n, "name": name, "a": a.fields[n], "b": b.fields[n]})
        return {
            "mti": {"a": a.mti, "b": b.mti, "changed": a.mti != b.mti},
            "added": added,
            "removed": removed,
            "changed": changed,
            "identical": a.mti == b.mti and not (added or removed or changed),
        }

    # Resources

    def _field_table(version: str, network: str | None) -> str:
        v, net = _version(version), _network(network)
        table = {}
        for n in sorted(ISO8583_FIELDS):
            field_def = get_field_definition(n, net, v)
            if field_def is not None:
                table[n] = {
                    "name": field_def.description,
                    "type": field_def.field_type.name,
                    "max_length": field_def.max_length,
                }
        return json.dumps(table, indent=2)

    @server.resource("iso8583://fields/{version}", mime_type="application/json")
    @resource_errors
    def fields_for_version(version: str) -> str:
        """Standard field definitions for an ISO 8583 version (1987, 1993 or 2003)."""
        return _field_table(version, None)

    @server.resource("iso8583://fields/{version}/{network}", mime_type="application/json")
    @resource_errors
    def fields_for_network(version: str, network: str) -> str:
        """Field definitions for a version with a card network's overrides applied."""
        return _field_table(version, network)

    @server.resource("iso8583://codes/response", mime_type="application/json")
    @resource_errors
    def response_codes() -> str:
        """Response codes (field 39) and their meanings."""
        return json.dumps(RESPONSE_CODES, indent=2)

    @server.resource("iso8583://codes/processing", mime_type="application/json")
    @resource_errors
    def processing_codes() -> str:
        """Processing code transaction types (first two digits of field 3)."""
        return json.dumps(PROCESSING_CODES, indent=2)

    @server.resource("iso8583://emv/tags", mime_type="application/json")
    @resource_errors
    def emv_tags() -> str:
        """EMV tag dictionary used to decode field 55."""
        return json.dumps(EMV_TAGS, indent=2)

    # Prompts

    @server.prompt()
    def debug_declined_transaction(message: str) -> str:
        """Work out why a transaction was declined or rejected."""
        return (
            "Investigate why this ISO 8583 transaction was declined or rejected.\n\n"
            f"Message:\n{message}\n\n"
            "1. Use explain_message to see what the transaction is and its response code (field 39).\n"
            "2. Use validate_message to find any format or network rule violations.\n"
            "3. If field 55 is present, use decode_emv and check the TVR (tag 95) and CID (tag 9F27).\n"
            "4. Summarise the most likely cause and what to change to get an approval."
        )

    @server.prompt()
    def build_test_suite(network: str = "VISA") -> str:
        """Plan and generate a set of test messages for a card network."""
        return (
            f"Build a test suite of ISO 8583 messages for {network}.\n\n"
            "Cover: an approved authorization, a financial request, a decline with response code 51, "
            "a reversal of the authorization, and an echo test.\n\n"
            "Use generate_test_message for requests, create_response for responses, create_reversal for the "
            "reversal, and validate_message on every message. Return the messages as a table with MTI, "
            "purpose and raw message."
        )

    return server


def main() -> None:
    """Run the MCP server over stdio."""
    create_server().run("stdio")
