"""Anthropic (Claude) LLM provider implementation."""

from __future__ import annotations

import os

from iso8583sim.llm.base import LLMError, LLMProvider, LLMResponse, ProviderConfigError, ProviderNotAvailableError

try:
    import anthropic

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


class AnthropicProvider(LLMProvider):
    """LLM provider using Anthropic's Claude API.

    Example:
        >>> provider = AnthropicProvider()  # Uses ANTHROPIC_API_KEY env var
        >>> response = provider.complete("Explain ISO 8583")
        >>> print(response)

        >>> # Or with explicit API key
        >>> provider = AnthropicProvider(api_key="sk-ant-...")
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ):
        """Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            model: Model to use. Defaults to claude-sonnet-4-20250514.
            max_tokens: Maximum tokens in response. Defaults to 4096.

        Raises:
            ProviderNotAvailableError: If anthropic package is not installed.
            ProviderConfigError: If no API key is available.
        """
        if not _ANTHROPIC_AVAILABLE:
            raise ProviderNotAvailableError("Anthropic", "anthropic")

        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ProviderConfigError(
                "Anthropic API key not found. " "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        self._model = model or self.DEFAULT_MODEL
        self._max_tokens = max_tokens or self.MAX_TOKENS
        self._client = anthropic.Anthropic(api_key=self._api_key)

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "Anthropic"

    @property
    def model(self) -> str:
        """Return the model name being used."""
        return self._model

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt to Claude and return the response.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt for context

        Returns:
            The response text from Claude

        Raises:
            LLMError: If the API call fails
        """
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system or "",
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except anthropic.APIError as e:
            raise LLMError(f"Anthropic API error: {e}") from e
        except Exception as e:
            raise LLMError(f"Unexpected error calling Anthropic: {e}") from e

    def complete_with_metadata(self, prompt: str, system: str | None = None) -> LLMResponse:
        """Send a prompt and return response with metadata.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt for context

        Returns:
            LLMResponse with content and usage metadata
        """
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system or "",
                messages=[{"role": "user", "content": prompt}],
            )
            return LLMResponse(
                content=message.content[0].text,
                model=message.model,
                provider=self.name,
                usage={
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
            )
        except anthropic.APIError as e:
            raise LLMError(f"Anthropic API error: {e}") from e
        except Exception as e:
            raise LLMError(f"Unexpected error calling Anthropic: {e}") from e


def is_available() -> bool:
    """Check if Anthropic provider is available.

    Returns:
        True if anthropic package is installed and API key is configured.
    """
    if not _ANTHROPIC_AVAILABLE:
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


__all__ = ["AnthropicProvider", "is_available"]
