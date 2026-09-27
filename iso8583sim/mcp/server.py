"""MCP server exposing the ISO 8583 toolkit to MCP clients (Claude, Cursor, etc.)."""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from typing import Any, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError

from .. import __version__, security
from ..core.builder import ISO8583Builder
from ..core.codes import (
    PROCESSING_CODES,
    RESPONSE_CODES,
    detect_network_from_pan,
)
from ..core.convert import convert_message
from ..core.describe import decode_emv_tags, describe_message, field_entries, field_name
from ..core.emv import EMV_TAGS
from ..core.parser import ISO8583Parser
from ..core.samples import sample_message
from ..core.types import (
    ISO8583_FIELDS,
    CardNetwork,
    ISO8583Error,
    ISO8583Message,
    ISO8583Version,
    get_field_definition,
)
from ..core.validator import ISO8583Validator

# subhadipmitra@: Sent to the client when it connects. It tells the model the shared input
# conventions once, so each tool description can stay short.
INSTRUCTIONS = """\
Tools for working with ISO 8583 payment messages (card authorizations, financial
transactions, reversals and network management).

Messages are passed as ASCII strings: MTI, hex bitmap, then field data. Field
numbers in `fields` arguments are strings ("2", "4", "41"). Versions are "1987",
"1993" or "2003". Networks are VISA, MASTERCARD, AMEX, DISCOVER, JCB or UNIONPAY.

Start with parse_message or explain_message to understand a message, and
validate_message before sending one anywhere.
"""

F = TypeVar("F", bound=Callable[..., Any])


def _reported_as(error_type: type[Exception]) -> Callable[[F], F]:
    """Turn expected input errors into MCP errors whose message reaches the client."""

    # subhadipmitra@: The MCP SDK treats any other exception as a crash and hides its message
    # from the client. Bad input (unknown network, unparseable message) is not a crash, and
    # the model needs the reason to fix its next call, so those errors are re-raised as
    # ToolError or ResourceError. functools.wraps keeps the signature the SDK reads to build
    # each tool's input schema.

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
    # subhadipmitra@: Only strip line endings. Fixed-width fields such as 42 (merchant ID) end
    # in significant trailing spaces, and a full strip() breaks parsing of the last field.
    return ISO8583Parser(version=_version(version)).parse(message.rstrip("\r\n"), network=_network(network))


def _fields_in(fields: dict[str, str]) -> dict[int, str]:
    # subhadipmitra@: JSON object keys are always strings, but ISO8583Message keys fields by
    # int. A string key would silently miss every lookup, so convert them here.
    try:
        return {int(k): str(v) for k, v in fields.items()}
    except ValueError:
        raise ValueError('Field numbers must be integers, e.g. {"2": "4111111111111111"}') from None


def create_server() -> MCPServer:
    """Create the iso8583sim MCP server with its tools, resources and prompts."""
    # subhadipmitra@: WARNING keeps the parser's per-message INFO logs off stderr, where MCP
    # clients show server output.
    server = MCPServer(name="iso8583sim", version=__version__, instructions=INSTRUCTIONS, log_level="WARNING")
    # subhadipmitra@: A builder is tied to one ISO version, so build one per version up front
    # and reuse them across calls.
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
            "fields": field_entries(parsed),
        }
        if 55 in parsed.fields:
            try:
                result["emv"] = decode_emv_tags(parsed.fields[55])
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
        return describe_message(_parse(message, network, version))

    @server.tool()
    @tool_errors
    def decode_emv(data: str) -> dict[str, Any]:
        """Decode EMV chip data (field 55, hex TLV) into named tags, including TVR and CID explanations."""
        return {"tags": decode_emv_tags(data.strip())}

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
        message = sample_message(message_type, _network(network), pan, amount_minor_units, currency, stan)
        raw = builder_for[ISO8583Version.V1987].build(message)
        net = message.network
        return {
            "message": raw,
            "mti": message.mti,
            "network": net.value if net else None,
            "fields": field_entries(message),
        }

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
        # subhadipmitra@: The response is built without a network on purpose. The network
        # required-field lists describe requests, and a response echoes only a few request
        # fields, so applying them would reject every valid response.
        response = builder_for[v].create_response(request, response_fields)
        raw = builder_for[v].build(response)
        return {"message": raw, "mti": response.mti, "fields": field_entries(response)}

    @server.tool()
    @tool_errors
    def create_reversal(message: str, version: str = "1987") -> dict[str, Any]:
        """Create a reversal (04xx) for an original message, with field 90 set to the original data elements."""
        v = _version(version)
        original = _parse(message, version=version)
        reversal = builder_for[v].create_reversal(original)
        raw = builder_for[v].build(reversal)
        return {"message": raw, "mti": reversal.mti, "fields": field_entries(reversal)}

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
            name = field_name(n, a.network or b.network, a.version)
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

    @server.tool()
    @tool_errors
    def convert_version(
        message: str, target_version: str, source_version: str = "1987", network: str | None = None
    ) -> dict[str, Any]:
        """Convert a message to another ISO 8583 version (1987, 1993, 2003).

        Rewrites the MTI version digit and moves original data elements between fields 90
        and 56. Fields that can't be carried over (e.g. PIN data, MACs) are listed in
        "dropped" with a reason. "notes" lists fields whose meaning differs between versions.
        """
        parsed = _parse(message, network, source_version)
        target = _version(target_version)
        result = convert_message(parsed, target)
        # subhadipmitra@: Same rule as the CLI. A network guessed from the PAN is not
        # enforced on the output, so conversion never rejects a message the input accepted.
        if not network:
            result.message.network = None
        raw = builder_for[target].build(result.message)
        return {
            "message": raw,
            "mti": result.message.mti,
            "dropped": {str(n): reason for n, reason in result.dropped.items()},
            "notes": result.notes,
            "lossless": result.lossless,
        }

    @server.tool()
    @tool_errors
    def check_network_rules(message: str, networks: list[str] | None = None, version: str = "1987") -> dict[str, Any]:
        """Check a message against card networks' rules without changing it.

        Checks every network when "networks" is omitted. Answers "which networks would accept this message?".
        """
        parsed = _parse(message, version=version)
        targets = [net for net in (_network(name) for name in networks or []) if net]
        results = validator.validate_for_networks(parsed, targets or None)
        return {net.value: {"passed": not errors, "errors": errors} for net, errors in results.items()}

    @server.tool()
    @tool_errors
    def encrypt_pin_block(pin: str, pan: str | None, key: str, block_format: int = 0) -> dict[str, Any]:
        """Build an encrypted ISO 9564 PIN block for field 52. TEST KEYS AND PINS ONLY.

        block_format 0, 1 or 3 uses a TDES key (32 or 48 hex characters) and gives 8 bytes.
        Format 4 uses an AES key (32, 48 or 64 hex characters) and gives 16 bytes.
        Format 1 does not use the PAN. Needs the security extra.
        """
        block = security.encrypt_pin_block(pin, pan, key, block_format)
        return {"pin_block": block, "format": block_format, "bytes": len(block) // 2}

    @server.tool()
    @tool_errors
    def decrypt_pin_block(pin_block: str, pan: str | None, key: str, block_format: int = 0) -> dict[str, Any]:
        """Recover the PIN from an encrypted ISO 9564 PIN block. TEST KEYS AND PINS ONLY.

        Fails with a clear error when the key, PAN or format is wrong. Needs the security extra.
        """
        return {"pin": security.decrypt_pin_block(pin_block, pan, key, block_format)}

    @server.tool()
    @tool_errors
    def sign_message(
        message: str, key: str, algorithm: int = 3, padding: int = 1, version: str = "1987"
    ) -> dict[str, Any]:
        """Add or replace the MAC of a message (field 64, or 128 with a secondary bitmap).

        algorithm 3 is the ANSI X9.19 retail MAC (16-byte key), algorithm 1 is CBC-MAC.
        TEST KEYS ONLY. Needs the security extra.
        """
        v = _version(version)
        parsed = _parse(message, version=version)
        # subhadipmitra@: Sign without the guessed network so the builder applies the same
        # rules the message was built under.
        parsed.network = None
        raw = security.sign_message(parsed, key, builder=builder_for[v], algorithm=algorithm, padding=padding)
        field = security.mac_field(parsed.fields)
        return {"message": raw, "mac_field": field, "mac": parsed.fields[field]}

    @server.tool()
    @tool_errors
    def verify_message_mac(
        message: str, key: str, algorithm: int = 3, padding: int = 1, version: str = "1987"
    ) -> dict[str, Any]:
        """Check the MAC in field 64 or 128 of a message. TEST KEYS ONLY. Needs the security extra."""
        valid = security.verify_message(message.rstrip("\r\n"), key, algorithm, padding, _version(version))
        return {"valid": valid}

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
