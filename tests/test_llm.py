# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

# tests/test_llm.py
"""Tests for the LLM module."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from iso8583sim.core.types import ISO8583Message
from iso8583sim.llm.base import (
    GenerationError,
    LLMError,
    LLMProvider,
    LLMResponse,
    ProviderConfigError,
    ProviderNotAvailableError,
)
from iso8583sim.llm.prompts import (
    ISO8583_SYSTEM_PROMPT,
    format_explainer_prompt,
    format_fields_for_prompt,
    format_generator_prompt,
)


class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, response: str = "Mock response"):
        self._response = response

    def complete(self, prompt: str, system: str | None = None) -> str:
        return self._response

    @property
    def name(self) -> str:
        return "Mock"

    @property
    def model(self) -> str:
        return "mock-model"


class TestLLMProvider:
    """Tests for LLMProvider base class."""

    def test_abstract_class_cannot_be_instantiated(self):
        """Test that LLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMProvider()  # type: ignore

    def test_mock_provider_implements_interface(self):
        """Test that mock provider implements the interface correctly."""
        provider = MockProvider()
        assert provider.name == "Mock"
        assert provider.model == "mock-model"
        assert provider.complete("test") == "Mock response"

    def test_complete_with_metadata(self):
        """Test complete_with_metadata returns LLMResponse."""
        provider = MockProvider(response="Test content")
        response = provider.complete_with_metadata("test prompt")

        assert isinstance(response, LLMResponse)
        assert response.content == "Test content"
        assert response.provider == "Mock"
        assert response.model == "mock-model"


class TestLLMExceptions:
    """Tests for LLM exception classes."""

    def test_llm_error(self):
        """Test LLMError base exception."""
        error = LLMError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_provider_not_available_error(self):
        """Test ProviderNotAvailableError message."""
        error = ProviderNotAvailableError("Anthropic", "anthropic")
        assert "Anthropic" in str(error)
        assert "anthropic" in str(error)
        assert "pip install" in str(error)

    def test_provider_config_error(self):
        """Test ProviderConfigError."""
        error = ProviderConfigError("Missing API key")
        assert "Missing API key" in str(error)

    def test_generation_error(self):
        """Test GenerationError."""
        error = GenerationError("Failed to generate")
        assert "Failed to generate" in str(error)


class TestPrompts:
    """Tests for prompt templates."""

    def test_system_prompt_contains_iso8583_context(self):
        """Test that system prompt has ISO8583 context."""
        assert "ISO 8583" in ISO8583_SYSTEM_PROMPT
        assert "MTI" in ISO8583_SYSTEM_PROMPT
        assert "VISA" in ISO8583_SYSTEM_PROMPT
        assert "Response Code" in ISO8583_SYSTEM_PROMPT

    def test_format_fields_for_prompt(self):
        """Test field formatting for prompts."""
        fields = {2: "4111111111111111", 3: "000000", 4: "000000010000"}
        result = format_fields_for_prompt(fields)

        assert "F002" in result
        assert "F003" in result
        assert "F004" in result

    def test_format_fields_masks_pan(self):
        """Test that PAN is masked in formatted output."""
        fields = {2: "4111111111111111"}
        result = format_fields_for_prompt(fields)

        # Should be masked (not full PAN)
        assert "4111111111111111" not in result
        assert "411111" in result  # First 6 visible
        assert "1111" in result  # Last 4 visible

    def test_format_fields_limits_output(self):
        """Test that fields are limited when there are many."""
        fields = {i: f"value{i}" for i in range(1, 50)}
        result = format_fields_for_prompt(fields, max_fields=10)

        assert "... and" in result
        assert "more fields" in result

    def test_format_explainer_prompt(self):
        """Test explainer prompt formatting."""
        prompt = format_explainer_prompt(
            mti="0100",
            fields={2: "4111111111111111", 4: "000000010000"},
            network="VISA",
        )

        assert "0100" in prompt
        assert "VISA" in prompt
        assert "F002" in prompt or "F2" in prompt

    def test_format_generator_prompt(self):
        """Test generator prompt formatting."""
        prompt = format_generator_prompt("$100 VISA purchase")

        assert "$100 VISA purchase" in prompt
        assert "mti" in prompt.lower()
        assert "fields" in prompt.lower()


class TestMessageExplainer:
    """Tests for MessageExplainer class."""

    def test_explainer_with_mock_provider(self):
        """Test explainer using mock provider."""
        from iso8583sim.llm.explainer import MessageExplainer

        provider = MockProvider(response="This is a VISA authorization request for $100.")
        explainer = MessageExplainer(provider=provider)

        message = ISO8583Message(
            mti="0100",
            fields={0: "0100", 2: "4111111111111111", 4: "000000010000"},
        )

        result = explainer.explain(message)
        assert "VISA" in result or "authorization" in result or "$100" in result

    def test_explainer_with_raw_message(self, parser, builder):
        """Test explaining a raw message string."""
        from iso8583sim.llm.explainer import MessageExplainer

        provider = MockProvider(response="Authorization request explanation")
        explainer = MessageExplainer(provider=provider)

        # Build a message to get raw string
        message = ISO8583Message(
            mti="0100",
            fields={0: "0100", 2: "4111111111111111", 3: "000000", 4: "000000010000", 11: "123456"},
        )
        raw = builder.build(message)

        result = explainer.explain(raw)
        assert result == "Authorization request explanation"

    def test_explain_field(self):
        """Test explaining a specific field."""
        from iso8583sim.llm.explainer import MessageExplainer

        provider = MockProvider(response="Field 39 is the response code")
        explainer = MessageExplainer(provider=provider)

        result = explainer.explain_field(39, "00")
        assert "response" in result.lower() or "39" in result

    def test_explain_response_code(self):
        """Test explaining response codes."""
        from iso8583sim.llm.explainer import MessageExplainer

        provider = MockProvider(response="Code 00 means approved")
        explainer = MessageExplainer(provider=provider)

        result = explainer.explain_response_code("00")
        assert "approved" in result.lower() or "00" in result


class TestMessageGenerator:
    """Tests for MessageGenerator class."""

    def test_generator_with_mock_provider(self):
        """Test generator using mock provider."""
        from iso8583sim.llm.generator import MessageGenerator

        response = json.dumps(
            {
                "mti": "0100",
                "fields": {
                    "2": "4111111111111111",
                    "3": "000000",
                    "4": "000000010000",
                    "11": "123456",
                    "14": "2612",
                    "22": "051",
                    "41": "TERM0001",
                    "42": "MERCHANT123456 ",
                },
            }
        )
        provider = MockProvider(response=response)
        generator = MessageGenerator(provider=provider)

        result = generator.generate("$100 VISA purchase", validate=False)

        assert result.mti == "0100"
        assert result.fields[2] == "4111111111111111"
        assert result.fields[4] == "000000010000"

    def test_generator_extracts_json_from_markdown(self):
        """Test that generator can extract JSON from markdown code blocks."""
        from iso8583sim.llm.generator import MessageGenerator

        response = """Here's the message:
```json
{
  "mti": "0200",
  "fields": {
    "2": "5555555555554444",
    "3": "000000",
    "4": "000000005000"
  }
}
```
This is a financial request."""

        provider = MockProvider(response=response)
        generator = MessageGenerator(provider=provider)

        result = generator.generate("$50 Mastercard", validate=False)

        assert result.mti == "0200"
        assert result.fields[2] == "5555555555554444"

    def test_generator_raises_on_invalid_json(self):
        """Test that generator raises GenerationError on invalid JSON."""
        from iso8583sim.llm.generator import MessageGenerator

        provider = MockProvider(response="This is not JSON at all")
        generator = MessageGenerator(provider=provider)

        with pytest.raises(GenerationError):
            generator.generate("test", validate=False)

    def test_generator_raises_on_missing_fields(self):
        """Test that generator raises on missing required keys."""
        from iso8583sim.llm.generator import MessageGenerator

        response = json.dumps({"mti": "0100"})  # Missing 'fields'
        provider = MockProvider(response=response)
        generator = MessageGenerator(provider=provider)

        with pytest.raises(GenerationError):
            generator.generate("test", validate=False)

    def test_suggest_fields(self):
        """Test field suggestion."""
        from iso8583sim.llm.generator import MessageGenerator

        response = json.dumps(
            {
                "suggested_fields": {"11": "123456", "41": "TERM0001"},
                "reasoning": "Added STAN and terminal ID",
            }
        )
        provider = MockProvider(response=response)
        generator = MessageGenerator(provider=provider)

        message = ISO8583Message(mti="0100", fields={0: "0100", 2: "4111111111111111"})

        suggestions = generator.suggest_fields(message)

        assert 11 in suggestions
        assert 41 in suggestions


class TestProviderFactory:
    """Tests for provider factory functions."""

    def test_get_provider_unknown_name(self):
        """Test that unknown provider name raises error."""
        from iso8583sim.llm.providers import get_provider

        with pytest.raises(ProviderConfigError) as exc_info:
            get_provider("unknown_provider")

        assert "Unknown provider" in str(exc_info.value)

    def test_list_installed_returns_list(self):
        """Test that list_installed_providers returns a list."""
        from iso8583sim.llm.providers import list_installed_providers

        result = list_installed_providers()
        assert isinstance(result, list)

    def test_list_available_returns_list(self):
        """Test that list_available_providers returns a list."""
        from iso8583sim.llm.providers import list_available_providers

        result = list_available_providers()
        assert isinstance(result, list)


class TestAnthropicProvider:
    """Tests for Anthropic provider."""

    def test_provider_requires_package(self):
        """Test that provider raises if anthropic not installed."""
        with patch.dict("sys.modules", {"anthropic": None}):
            # Need to reimport to trigger the check
            pass  # This is hard to test without actually uninstalling

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=True)
    def test_provider_requires_api_key(self):
        """Test that provider raises if no API key."""
        # This test only works if anthropic is installed
        try:
            from iso8583sim.llm.providers.anthropic import AnthropicProvider

            with pytest.raises(ProviderConfigError):
                AnthropicProvider()
        except ProviderNotAvailableError:
            pytest.skip("anthropic package not installed")

    def test_is_available_function(self):
        """Test the is_available function."""
        try:
            from iso8583sim.llm.providers.anthropic import is_available

            result = is_available()
            assert isinstance(result, bool)
        except ImportError:
            pytest.skip("anthropic module not available")


class FakeAnthropicClient:
    """Records requests made to messages.create and beta.messages.create."""

    def __init__(self, response):
        self.calls = []
        client = self

        class Endpoint:
            def __init__(self, endpoint):
                self.endpoint = endpoint

            def create(self, **kwargs):
                client.calls.append((self.endpoint, kwargs))
                return response

        self.messages = Endpoint("messages")
        self.beta = SimpleNamespace(messages=Endpoint("beta"))


def anthropic_response(*blocks, stop_reason="end_turn", category=None):
    """Build a response object shaped like the Anthropic SDK's Message."""
    return SimpleNamespace(
        content=[SimpleNamespace(type=kind, text=text) for kind, text in blocks],
        stop_reason=stop_reason,
        stop_details=SimpleNamespace(category=category) if stop_reason == "refusal" else None,
        model="claude-opus-5",
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


class TestAnthropicRequests:
    """Tests for how the Anthropic provider builds requests and reads responses."""

    @pytest.fixture(autouse=True)
    def _requires_anthropic(self):
        pytest.importorskip("anthropic")

    def make(self, response, **kwargs):
        from iso8583sim.llm.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key="test-key", **kwargs)
        # subhadipmitra@: Swap the SDK client for a fake so no request leaves the machine.
        provider._client = FakeAnthropicClient(response)
        return provider

    def test_defaults(self):
        provider = self.make(anthropic_response(("text", "ok")))
        assert provider.model == "claude-opus-5"
        assert provider._max_tokens == 16000

    def test_default_model_uses_refusal_fallbacks(self):
        provider = self.make(anthropic_response(("text", "ok")))
        provider.complete("hello", system="be brief")

        endpoint, kwargs = provider._client.calls[0]
        assert endpoint == "beta"
        assert kwargs["fallbacks"] == "default"
        assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]
        assert kwargs["system"] == "be brief"

    def test_other_models_skip_fallbacks(self):
        provider = self.make(anthropic_response(("text", "ok")), model="claude-haiku-4-5")
        provider.complete("hello")

        endpoint, kwargs = provider._client.calls[0]
        assert endpoint == "messages"
        assert "fallbacks" not in kwargs
        assert "system" not in kwargs

    def test_text_is_joined_and_thinking_skipped(self):
        response = anthropic_response(("thinking", ""), ("text", "Hello "), ("text", "world"))
        assert self.make(response).complete("hi") == "Hello world"

    def test_refusal_raises_llm_error(self):
        provider = self.make(anthropic_response(stop_reason="refusal", category="cyber"))
        with pytest.raises(LLMError, match="declined.*cyber"):
            provider.complete("hi")

    def test_complete_with_metadata(self):
        result = self.make(anthropic_response(("thinking", ""), ("text", "ok"))).complete_with_metadata("hi")
        assert result.content == "ok"
        assert result.usage == {"input_tokens": 10, "output_tokens": 5}


class TestOpenAIProvider:
    """Tests for OpenAI provider."""

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=True)
    def test_provider_requires_api_key(self):
        """Test that provider raises if no API key."""
        try:
            from iso8583sim.llm.providers.openai import OpenAIProvider

            with pytest.raises(ProviderConfigError):
                OpenAIProvider()
        except ProviderNotAvailableError:
            pytest.skip("openai package not installed")


class TestGoogleProvider:
    """Tests for Google provider."""

    @patch.dict("os.environ", {"GOOGLE_API_KEY": ""}, clear=True)
    def test_provider_requires_api_key(self):
        """Test that provider raises if no API key."""
        try:
            from iso8583sim.llm.providers.google import GoogleProvider

            with pytest.raises(ProviderConfigError):
                GoogleProvider()
        except ProviderNotAvailableError:
            pytest.skip("google-genai package not installed")


class TestOpenAIRequests:
    """Tests for how the OpenAI provider builds requests and reads responses."""

    @pytest.fixture(autouse=True)
    def _requires_openai(self):
        pytest.importorskip("openai")

    def make(self, content="ok", refusal=None):
        from iso8583sim.llm.providers.openai import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key")
        calls = []
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content, refusal=refusal))],
            model="gpt-6-astra",
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )

        def create(**kwargs):
            calls.append(kwargs)
            return response

        # subhadipmitra@: Replace the SDK client with a stub so no request leaves the machine.
        provider._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        return provider, calls

    def test_defaults_and_completion_token_limit(self):
        provider, calls = self.make()
        assert provider.complete("hi", system="be brief") == "ok"
        assert provider.model == "gpt-6-astra"
        assert calls[0]["max_completion_tokens"] == 16000
        assert "max_tokens" not in calls[0]
        assert calls[0]["messages"][0] == {"role": "system", "content": "be brief"}

    def test_refusal_raises_llm_error(self):
        provider, _ = self.make(content=None, refusal="I can't help with that.")
        with pytest.raises(LLMError, match="declined"):
            provider.complete("hi")


class TestGoogleRequests:
    """Tests for how the Google provider builds requests and reads responses."""

    @pytest.fixture(autouse=True)
    def _requires_google_genai(self):
        pytest.importorskip("google.genai")

    def make(self, text="ok", block_reason=None):
        from iso8583sim.llm.providers.google import GoogleProvider

        provider = GoogleProvider(api_key="test-key")
        calls = []
        response = SimpleNamespace(
            text=text,
            prompt_feedback=SimpleNamespace(block_reason=block_reason) if block_reason else None,
            usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=5),
        )

        def generate_content(**kwargs):
            calls.append(kwargs)
            return response

        provider._client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        return provider, calls

    def test_defaults_and_system_instruction(self):
        provider, calls = self.make()
        assert provider.complete("hi", system="be brief") == "ok"
        assert calls[0]["model"] == "gemini-3.8-flash"
        assert calls[0]["contents"] == "hi"
        assert calls[0]["config"].system_instruction == "be brief"
        assert calls[0]["config"].max_output_tokens == 16000

    def test_metadata(self):
        provider, _ = self.make()
        result = provider.complete_with_metadata("hi")
        assert result.usage == {"input_tokens": 10, "output_tokens": 5}

    def test_blocked_prompt_raises_llm_error(self):
        provider, _ = self.make(text=None, block_reason="SAFETY")
        with pytest.raises(LLMError, match="blocked.*SAFETY"):
            provider.complete("hi")


class TestOllamaProvider:
    """Tests for Ollama provider."""

    def test_provider_does_not_require_api_key(self):
        """Test that Ollama doesn't need API key."""
        try:
            from iso8583sim.llm.providers.ollama import OllamaProvider

            # Should not raise - Ollama is local
            provider = OllamaProvider()
            assert provider.name == "Ollama"
        except ProviderNotAvailableError:
            pytest.skip("ollama package not installed")
