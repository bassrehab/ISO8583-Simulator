# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""OpenAI (GPT) LLM provider implementation."""

from __future__ import annotations

import os
from typing import Any

from iso8583sim.llm.base import LLMError, LLMProvider, LLMResponse, ProviderConfigError, ProviderNotAvailableError

try:
    import openai

    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False


class OpenAIProvider(LLMProvider):
    """LLM provider using OpenAI's GPT API.

    Example:
        >>> provider = OpenAIProvider()  # Uses OPENAI_API_KEY env var
        >>> response = provider.complete("Explain ISO 8583")
        >>> print(response)

        >>> # Or with explicit API key
        >>> provider = OpenAIProvider(api_key="sk-...")
    """

    # subhadipmitra@: gpt-6-astra is OpenAI's recommended starting model. It is a reasoning
    # model, and reasoning tokens count against the completion limit, so the limit leaves
    # room for reasoning plus the reply.
    DEFAULT_MODEL = "gpt-6-astra"
    MAX_TOKENS = 16000

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ):
        """Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: Model to use. Defaults to gpt-6-astra.
            max_tokens: Maximum tokens in response, including reasoning. Defaults to 16000.

        Raises:
            ProviderNotAvailableError: If openai package is not installed.
            ProviderConfigError: If no API key is available.
        """
        if not _OPENAI_AVAILABLE:
            raise ProviderNotAvailableError("OpenAI", "openai")

        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ProviderConfigError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        self._model = model or self.DEFAULT_MODEL
        self._max_tokens = max_tokens or self.MAX_TOKENS
        self._client = openai.OpenAI(api_key=self._api_key)

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "OpenAI"

    @property
    def model(self) -> str:
        """Return the model name being used."""
        return self._model

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt to GPT and return the response.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt for context

        Returns:
            The response text from GPT

        Raises:
            LLMError: If the API call fails
        """
        try:
            messages: list[Any] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self._client.chat.completions.create(
                model=self._model,
                # subhadipmitra@: Reasoning models reject max_tokens with a 400.
                # max_completion_tokens works on both reasoning and older chat models.
                max_completion_tokens=self._max_tokens,
                messages=messages,
            )
            return _text_of(response)
        except LLMError:
            raise
        except openai.APIError as e:
            raise LLMError(f"OpenAI API error: {e}") from e
        except Exception as e:
            raise LLMError(f"Unexpected error calling OpenAI: {e}") from e

    def complete_with_metadata(self, prompt: str, system: str | None = None) -> LLMResponse:
        """Send a prompt and return response with metadata.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt for context

        Returns:
            LLMResponse with content and usage metadata
        """
        try:
            messages: list[Any] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self._client.chat.completions.create(
                model=self._model,
                # subhadipmitra@: Reasoning models reject max_tokens with a 400.
                # max_completion_tokens works on both reasoning and older chat models.
                max_completion_tokens=self._max_tokens,
                messages=messages,
            )

            usage = None
            if response.usage:
                usage = {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                }

            return LLMResponse(
                content=_text_of(response),
                model=response.model,
                provider=self.name,
                usage=usage,
            )
        except LLMError:
            raise
        except openai.APIError as e:
            raise LLMError(f"OpenAI API error: {e}") from e
        except Exception as e:
            raise LLMError(f"Unexpected error calling OpenAI: {e}") from e


def _text_of(response: Any) -> str:
    """Return the reply text, raising LLMError if the model refused."""
    message = response.choices[0].message
    # subhadipmitra@: A refusal comes back as a normal response with content set to None and
    # the reason in message.refusal. Surface it instead of returning an empty explanation.
    refusal = getattr(message, "refusal", None)
    if refusal:
        raise LLMError(f"OpenAI declined this request: {refusal}")
    return message.content or ""


def is_available() -> bool:
    """Check if OpenAI provider is available.

    Returns:
        True if openai package is installed and API key is configured.
    """
    if not _OPENAI_AVAILABLE:
        return False
    return bool(os.environ.get("OPENAI_API_KEY"))


__all__ = ["OpenAIProvider", "is_available"]
