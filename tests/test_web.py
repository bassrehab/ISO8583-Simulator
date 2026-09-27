# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Tests for the REST API."""

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from iso8583sim import __version__  # noqa: E402
from iso8583sim.llm import LLMProvider, ProviderConfigError  # noqa: E402
from iso8583sim.web.app import create_app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


@pytest.fixture(scope="module")
def auth_message(client):
    return client.post("/generate", json={"network": "VISA"}).json()["message"]


class FakeProvider(LLMProvider):
    def __init__(self, response):
        self.response = response

    def complete(self, prompt, system=None):
        return self.response

    @property
    def name(self):
        return "Fake"

    @property
    def model(self):
        return "fake-1"


def use_llm(monkeypatch, response=None, error=None):
    """Route the API's LLM calls to a fake provider (or make provider lookup fail)."""
    import iso8583sim.llm

    def fake_get_provider(name=None, **kwargs):
        if error:
            raise error
        return FakeProvider(response)

    monkeypatch.setattr(iso8583sim.llm, "get_provider", fake_get_provider)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "version": __version__}


def test_openapi_schema_lists_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/health", "/parse", "/build", "/validate", "/explain", "/generate", "/convert"} <= set(paths)


class TestParseAndBuild:
    def test_build_then_parse(self, client):
        built = client.post(
            "/build",
            json={"mti": "0800", "fields": {"7": "1215143022", "11": "000001", "70": "301"}},
        )
        assert built.status_code == 200
        raw = built.json()["message"]
        assert built.json()["length"] == len(raw)

        parsed = client.post("/parse", json={"message": raw}).json()
        assert parsed["mti"] == "0800"
        assert {f["number"]: f["value"] for f in parsed["fields"]}[70] == "301"

    def test_parse_detects_network(self, client, auth_message):
        parsed = client.post("/parse", json={"message": auth_message}).json()
        assert parsed["network"] == "VISA"
        assert parsed["fields"][0]["name"] == "Primary Account Number (PAN)"

    def test_parse_error_is_422(self, client):
        response = client.post("/parse", json={"message": "not a message"})
        assert response.status_code == 422
        assert "Invalid MTI" in response.json()["detail"]

    def test_invalid_mti_is_rejected_by_schema(self, client):
        assert client.post("/build", json={"mti": "01", "fields": {}}).status_code == 422

    def test_unknown_network_is_rejected(self, client, auth_message):
        assert client.post("/parse", json={"message": auth_message, "network": "DINERS"}).status_code == 422


class TestValidate:
    def test_valid(self, client, auth_message):
        assert client.post("/validate", json={"message": auth_message}).json() == {
            "valid": True,
            "errors": [],
            "networks": None,
        }

    def test_parse_failure_is_reported_as_invalid(self, client):
        result = client.post("/validate", json={"message": "0100"}).json()
        assert result["valid"] is False
        assert result["errors"][0].startswith("Parse error")

    def test_against_all_networks(self, client, auth_message):
        result = client.post("/validate", json={"message": auth_message, "against": []}).json()
        assert set(result["networks"]) == {"VISA", "MASTERCARD", "AMEX", "DISCOVER", "JCB", "UNIONPAY"}
        assert result["networks"]["VISA"]["passed"] is True

    def test_against_selected_networks(self, client, auth_message):
        result = client.post("/validate", json={"message": auth_message, "against": ["AMEX"]}).json()
        assert list(result["networks"]) == ["AMEX"]


class TestExplain:
    def test_rule_based(self, client, auth_message):
        result = client.post("/explain", json={"message": auth_message}).json()
        assert result["source"] == "rules"
        assert "411111******1111" in result["summary"]

    def test_llm(self, client, auth_message, monkeypatch):
        use_llm(monkeypatch, response="A $10 VISA purchase.")
        result = client.post("/explain", json={"message": auth_message, "llm": True}).json()
        assert result["summary"] == "A $10 VISA purchase."
        assert result["source"] == "llm:fake/fake-1"

    def test_llm_unavailable_is_503(self, client, auth_message, monkeypatch):
        use_llm(monkeypatch, error=ProviderConfigError("No LLM provider available."))
        response = client.post("/explain", json={"message": auth_message, "llm": True})
        assert response.status_code == 503
        assert response.json()["detail"] == "No LLM provider available."


class TestGenerate:
    @pytest.mark.parametrize("network", ["VISA", "MASTERCARD", "AMEX", "DISCOVER", "JCB", "UNIONPAY"])
    def test_template_per_network(self, client, network):
        result = client.post("/generate", json={"network": network}).json()
        assert result["network"] == network
        assert result["source"] == "template"
        assert client.post("/validate", json={"message": result["message"]}).json()["valid"]

    def test_echo(self, client):
        assert client.post("/generate", json={"message_type": "echo"}).json()["mti"] == "0800"

    def test_invalid_options_are_422(self, client):
        assert client.post("/generate", json={"message_type": "refund"}).status_code == 422
        assert client.post("/generate", json={"currency": "USD"}).status_code == 422

    def test_llm_description(self, client, monkeypatch):
        reply = (
            '{"mti": "0200", "fields": {"2": "5555555555554444", "3": "200000", "4": "000000005000", "11": "654321"}}'
        )
        use_llm(monkeypatch, response=reply)
        result = client.post("/generate", json={"description": "$50 Mastercard refund"}).json()
        assert result["mti"] == "0200"
        assert result["source"] == "llm:fake/fake-1"

    def test_llm_bad_output_is_502(self, client, monkeypatch):
        use_llm(monkeypatch, response="not json")
        assert client.post("/generate", json={"description": "anything"}).status_code == 502


class TestConvert:
    def test_convert(self, client, auth_message):
        result = client.post("/convert", json={"message": auth_message, "target_version": "2003"}).json()
        assert result["mti"] == "2100"
        assert result["lossless"] is True

    def test_convert_reports_dropped(self, client):
        raw = client.post(
            "/build",
            json={
                "mti": "0200",
                "fields": {"2": "4111111111111111", "3": "000000", "4": "000000001000", "52": "2A3D408A1977DDE9"},
            },
        ).json()["message"]
        result = client.post("/convert", json={"message": raw, "target_version": "1993"}).json()
        assert "52" in result["dropped"]
        assert result["lossless"] is False


class TestPublicMode:
    @pytest.fixture(scope="class")
    def public_client(self):
        return TestClient(create_app(public=True))

    def test_llm_explain_is_refused(self, public_client, auth_message, monkeypatch):
        use_llm(monkeypatch, response="should not be called")
        response = public_client.post("/explain", json={"message": auth_message, "llm": True})
        assert response.status_code == 403
        assert "turned off" in response.json()["detail"]

    def test_llm_generate_is_refused(self, public_client, monkeypatch):
        use_llm(monkeypatch, response="should not be called")
        response = public_client.post("/generate", json={"description": "a VISA auth for $10"})
        assert response.status_code == 403

    def test_rule_based_features_still_work(self, public_client, auth_message):
        assert public_client.post("/explain", json={"message": auth_message}).json()["source"] == "rules"
        assert public_client.post("/generate", json={}).status_code == 200

    def test_cors_allows_any_origin(self, public_client):
        response = public_client.options(
            "/build",
            headers={"Origin": "https://example.com", "Access-Control-Request-Method": "POST"},
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "*"

    def test_cors_is_off_by_default(self, client):
        response = client.get("/health", headers={"Origin": "https://example.com"})
        assert "access-control-allow-origin" not in response.headers

    def test_env_var_turns_it_on(self, monkeypatch):
        monkeypatch.setenv("ISO8583SIM_PUBLIC", "1")
        assert create_app().user_middleware


def test_oversized_message_is_rejected(client):
    response = client.post("/parse", json={"message": "0" * 40_000})
    assert response.status_code == 422
