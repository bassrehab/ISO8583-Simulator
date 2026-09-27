# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Anthropic (Claude) LLM provider implementation."""

from __future__ import annotations

import os
from typing import Any

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

    # subhadipmitra@: Claude Opus 5 is Anthropic's recommended default. It thinks before
    # answering, so max_tokens leaves room for thinking plus the reply. 16000 stays well
    # under the SDK's non-streaming timeout.
    DEFAULT_MODEL = "claude-opus-5"
    MAX_TOKENS = 16000

    # subhadipmitra@: Models that accept fallbacks="default". On a safety-classifier refusal
    # the API re-runs the request on Anthropic's recommended fallback model instead of
    # returning the refusal. Other models (e.g. a --model override to Haiku) reject the
    # parameter, so it is only sent for these.
    FALLBACK_MODELS = frozenset({"claude-opus-5", "claude-fable-5", "claude-fable-5-1"})
    FALLBACK_BETA = "server-side-fallback-2026-07-01"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ):
        """Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            model: Model to use. Defaults to claude-opus-5.
            max_tokens: Maximum tokens in response. Defaults to 16000.

        Raises:
            ProviderNotAvailableError: If anthropic package is not installed.
            ProviderConfigError: If no API key is available.
        """
        if not _ANTHROPIC_AVAILABLE:
            raise ProviderNotAvailableError("Anthropic", "anthropic")

        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ProviderConfigError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
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

    def _create(self, prompt: str, system: str | None) -> Any:
        """Send one request, with refusal fallbacks when the model supports them."""
        params: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        # subhadipmitra@: Omit system entirely when there is none, rather than sending "".
        if system:
            params["system"] = system

        if self._model in self.FALLBACK_MODELS:
            # subhadipmitra@: fallbacks is a beta parameter, so it goes through the beta
            # endpoint with its header. The response shape is the same for our purposes.
            return self._client.beta.messages.create(**params, betas=[self.FALLBACK_BETA], fallbacks="default")
        return self._client.messages.create(**params)

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
            return _text_of(self._create(prompt, system))
        except LLMError:
            raise
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
            message = self._create(prompt, system)
            return LLMResponse(
                content=_text_of(message),
                model=message.model,
                provider=self.name,
                usage={
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
            )
        except LLMError:
            raise
        except anthropic.APIError as e:
            raise LLMError(f"Anthropic API error: {e}") from e
        except Exception as e:
            raise LLMError(f"Unexpected error calling Anthropic: {e}") from e


def _text_of(message: Any) -> str:
    """Return the text of a response, raising LLMError if the model refused.

    Args:
        message: Response from messages.create

    Returns:
        All text blocks joined together
    """
    # subhadipmitra@: A refusal is an HTTP 200 whose content may be empty or partial, so it
    # has to be checked before reading any text. With fallbacks enabled, a refusal here means
    # the fallback model declined as well.
    if message.stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        category = getattr(details, "category", None)
        reason = f" (category: {category})" if category else ""
        raise LLMError(f"Claude declined this request{reason}.")

    # subhadipmitra@: Current models can put thinking or fallback blocks before the answer,
    # so content[0] is not necessarily text. Collect every text block instead.
    return "".join(block.text for block in message.content if block.type == "text")


def is_available() -> bool:
    """Check if Anthropic provider is available.

    Returns:
        True if anthropic package is installed and API key is configured.
    """
    if not _ANTHROPIC_AVAILABLE:
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


__all__ = ["AnthropicProvider", "is_available"]
