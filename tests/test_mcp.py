"""Tests for the MCP server, called through the MCP client in-process."""

import asyncio
import json

import pytest

pytest.importorskip("mcp")

from mcp.client import Client  # noqa: E402

from iso8583sim.mcp import create_server  # noqa: E402

EXPECTED_TOOLS = {
    "parse_message",
    "build_message",
    "validate_message",
    "explain_message",
    "decode_emv",
    "generate_test_message",
    "create_response",
    "create_reversal",
    "lookup_field",
    "detect_network",
    "diff_messages",
    "convert_version",
    "check_network_rules",
    "encrypt_pin_block",
    "decrypt_pin_block",
    "sign_message",
    "verify_message_mac",
}


def run(coro_fn):
    """Run an async function that takes a connected client."""

    async def runner():
        async with Client(create_server()) as client:
            return await coro_fn(client)

    return asyncio.run(runner())


def call(name, **arguments):
    """Call a tool and return its result."""
    return run(lambda c: c.call_tool(name, arguments))


def data(name, **arguments):
    """Call a tool, assert it succeeded and return its structured content."""
    result = call(name, **arguments)
    assert not result.is_error, result.content
    return result.structured_content


@pytest.fixture(scope="module")
def auth_message():
    return data("generate_test_message", message_type="auth", network="VISA")["message"]


class TestDiscovery:
    def test_lists_all_tools(self):
        tools = run(lambda c: c.list_tools())
        assert {t.name for t in tools.tools} == EXPECTED_TOOLS

    def test_lists_resources(self):
        resources = run(lambda c: c.list_resources())
        templates = run(lambda c: c.list_resource_templates())
        assert {str(r.uri) for r in resources.resources} == {
            "iso8583://codes/response",
            "iso8583://codes/processing",
            "iso8583://emv/tags",
        }
        assert {t.uri_template for t in templates.resource_templates} == {
            "iso8583://fields/{version}",
            "iso8583://fields/{version}/{network}",
        }

    def test_lists_prompts(self):
        prompts = run(lambda c: c.list_prompts())
        assert {p.name for p in prompts.prompts} == {"debug_declined_transaction", "build_test_suite"}


class TestTools:
    @pytest.mark.parametrize("network", ["VISA", "MASTERCARD", "AMEX", "DISCOVER", "JCB", "UNIONPAY"])
    def test_generated_messages_are_valid(self, network):
        message = data("generate_test_message", network=network)["message"]
        result = data("validate_message", message=message)
        assert result == {"valid": True, "errors": [], "network": network}

    def test_generate_echo(self):
        result = data("generate_test_message", message_type="echo")
        assert result["mti"] == "0800"

    def test_generate_rejects_unknown_type(self):
        result = call("generate_test_message", message_type="refund")
        assert result.is_error
        assert "Unknown message_type" in result.content[0].text

    def test_parse_message(self, auth_message):
        result = data("parse_message", message=auth_message)
        fields = {f["number"]: f for f in result["fields"]}
        assert result["mti"] == "0100"
        assert result["network"] == "VISA"
        assert fields[2]["value"] == "4111111111111111"
        assert fields[2]["name"] == "Primary Account Number (PAN)"

    def test_parse_error_is_reported(self):
        result = call("parse_message", message="not a message")
        assert result.is_error
        assert "Invalid MTI" in result.content[0].text

    def test_build_message(self):
        result = data("build_message", mti="0800", fields={"7": "1215143022", "11": "000001", "70": "301"})
        assert result["message"].startswith("0800")
        assert result["length"] == len(result["message"])

    def test_build_rejects_non_numeric_field_keys(self):
        result = call("build_message", mti="0800", fields={"seven": "1215143022"})
        assert result.is_error

    def test_validate_reports_parse_errors(self):
        result = data("validate_message", message="01")
        assert result["valid"] is False
        assert result["errors"]

    def test_explain_message(self, auth_message):
        result = data("explain_message", message=auth_message)
        assert "authorization request" in result["summary"]
        assert "411111******1111" in result["summary"]
        assert "10.00 USD" in result["summary"]
        assert "4111111111111111" not in result["summary"]

    def test_create_response_and_explain(self, auth_message):
        response = data("create_response", message=auth_message, response_code="51")
        assert response["mti"] == "0110"
        summary = data("explain_message", message=response["message"])["summary"]
        assert "Response code 51: Insufficient funds" in summary

    def test_create_reversal(self, auth_message):
        reversal = data("create_reversal", message=auth_message)
        fields = {f["number"]: f["value"] for f in reversal["fields"]}
        assert reversal["mti"] == "0400"
        assert fields[90].startswith("0100123456")
        assert len(fields[90]) == 42

    def test_decode_emv(self):
        result = data("decode_emv", data="9F2608AABBCCDDEEFF00119F27018095050000008000")
        tags = {t["tag"]: t for t in result["tags"]}
        assert tags["9F26"]["name"] == "Application Cryptogram"
        assert "ARQC" in tags["9F27"]["explanation"]

    def test_lookup_field(self):
        result = data("lookup_field", field_number=41)
        assert result["max_length"] == 8

    def test_lookup_unknown_field(self):
        result = call("lookup_field", field_number=999)
        assert result.is_error
        assert "not defined" in result.content[0].text

    def test_detect_network(self):
        assert data("detect_network", pan="6011111111111117") == {"network": "DISCOVER"}
        assert data("detect_network", pan="0000000000000000") == {"network": None}

    def test_unknown_network_is_reported(self, auth_message):
        result = call("parse_message", message=auth_message, network="DINERS")
        assert result.is_error
        assert "Unknown network" in result.content[0].text

    def test_diff_messages(self, auth_message):
        response = data("create_response", message=auth_message)["message"]
        diff = data("diff_messages", message_a=auth_message, message_b=response)
        assert diff["mti"] == {"a": "0100", "b": "0110", "changed": True}
        assert [f["number"] for f in diff["added"]] == [39]
        assert not diff["identical"]

    def test_diff_identical(self, auth_message):
        assert data("diff_messages", message_a=auth_message, message_b=auth_message)["identical"]


TEST_KEY = "0123456789ABCDEFFEDCBA9876543210"


class TestConversionAndNetworkTools:
    def test_convert_version(self, auth_message):
        result = data("convert_version", message=auth_message, target_version="1993")
        assert result["mti"] == "1100"
        assert result["message"].startswith("1100")
        assert result["lossless"] is True

    def test_convert_version_reports_dropped_fields(self):
        built = data(
            "build_message",
            mti="0200",
            fields={
                "2": "4111111111111111",
                "3": "000000",
                "4": "000000001000",
                "11": "123456",
                "52": "2A3D408A1977DDE9",
            },
        )
        result = data("convert_version", message=built["message"], target_version="2003")
        assert "52" in result["dropped"]
        assert result["lossless"] is False

    def test_check_all_networks(self, auth_message):
        result = data("check_network_rules", message=auth_message)
        assert set(result) == {"VISA", "MASTERCARD", "AMEX", "DISCOVER", "JCB", "UNIONPAY"}
        assert result["VISA"]["passed"] is True

    def test_check_selected_networks(self, auth_message):
        result = data("check_network_rules", message=auth_message, networks=["amex"])
        assert list(result) == ["AMEX"]


class TestSecurityTools:
    @pytest.fixture(autouse=True)
    def _requires_cryptography(self):
        pytest.importorskip("cryptography")

    def test_pin_block_round_trip(self):
        block = data("encrypt_pin_block", pin="1234", pan="4111111111111111", key=TEST_KEY)
        assert block == {"pin_block": "2A3D408A1977DDE9", "format": 0, "bytes": 8}
        assert data("decrypt_pin_block", pin_block=block["pin_block"], pan="4111111111111111", key=TEST_KEY) == {
            "pin": "1234"
        }

    def test_format_4(self):
        key = "00112233445566778899AABBCCDDEEFF"
        block = data("encrypt_pin_block", pin="4321", pan="4111111111111111", key=key, block_format=4)
        assert block["bytes"] == 16
        result = data(
            "decrypt_pin_block", pin_block=block["pin_block"], pan="4111111111111111", key=key, block_format=4
        )
        assert result["pin"] == "4321"

    def test_wrong_key_is_a_tool_error(self):
        result = call("decrypt_pin_block", pin_block="2A3D408A1977DDE9", pan="4111111111111111", key="11" * 16)
        assert result.is_error
        assert "PIN block" in result.content[0].text

    def test_sign_and_verify(self, auth_message):
        signed = data("sign_message", message=auth_message, key=TEST_KEY)
        assert signed["mac_field"] == 64
        assert signed["message"].endswith(signed["mac"])
        assert data("verify_message_mac", message=signed["message"], key=TEST_KEY) == {"valid": True}
        assert data("verify_message_mac", message=signed["message"], key="11" * 16) == {"valid": False}

    def test_missing_extra_gives_install_hint(self, monkeypatch):
        from iso8583sim.security import _cipher

        # subhadipmitra@: Simulate an install without the security extra.
        monkeypatch.setattr(_cipher, "_CRYPTO_AVAILABLE", False)
        result = call("encrypt_pin_block", pin="1234", pan="4111111111111111", key=TEST_KEY)
        assert result.is_error
        assert "iso8583sim[security]" in result.content[0].text


class TestResources:
    def read(self, uri):
        result = run(lambda c: c.read_resource(uri))
        return json.loads(result.contents[0].text)

    def test_response_codes(self):
        assert self.read("iso8583://codes/response")["00"] == "Approved"

    def test_emv_tags(self):
        assert self.read("iso8583://emv/tags")["9F26"] == "Application Cryptogram"

    def test_fields_for_version(self):
        fields = self.read("iso8583://fields/1987")
        assert fields["2"]["name"] == "Primary Account Number (PAN)"

    def test_fields_for_network(self):
        fields = self.read("iso8583://fields/1993/VISA")
        assert "41" in fields


class TestPrompts:
    def test_debug_declined_transaction(self, auth_message):
        result = run(lambda c: c.get_prompt("debug_declined_transaction", {"message": auth_message}))
        text = result.messages[0].content.text
        assert auth_message in text
        assert "explain_message" in text

    def test_build_test_suite(self):
        result = run(lambda c: c.get_prompt("build_test_suite", {"network": "AMEX"}))
        assert "AMEX" in result.messages[0].content.text
