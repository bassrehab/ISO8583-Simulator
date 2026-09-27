# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Google (Gemini) LLM provider implementation."""

from __future__ import annotations

import os
from typing import Any

from iso8583sim.llm.base import LLMError, LLMProvider, LLMResponse, ProviderConfigError, ProviderNotAvailableError

# subhadipmitra@: Uses the google-genai SDK. The older google-generativeai package is
# deprecated and no longer maintained, and its GenerativeModel API does not reach
# current Gemini models reliably.
try:
    from google import genai
    from google.genai import types

    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False


class GoogleProvider(LLMProvider):
    """LLM provider using Google's Gemini API.

    Example:
        >>> provider = GoogleProvider()  # Uses GOOGLE_API_KEY env var
        >>> response = provider.complete("Explain ISO 8583")
        >>> print(response)

        >>> # Or with explicit API key
        >>> provider = GoogleProvider(api_key="...")
    """

    # subhadipmitra@: Google recommends gemini-3.8-flash for new projects. Gemini 1.5 and
    # 2.0 are shut down.
    DEFAULT_MODEL = "gemini-3.8-flash"
    MAX_TOKENS = 16000

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ):
        """Initialize the Google provider.

        Args:
            api_key: Google API key. If not provided, uses GOOGLE_API_KEY env var.
            model: Model to use. Defaults to gemini-3.8-flash.
            max_tokens: Maximum tokens in response. Defaults to 16000.

        Raises:
            ProviderNotAvailableError: If google-genai package is not installed.
            ProviderConfigError: If no API key is available.
        """
        if not _GOOGLE_AVAILABLE:
            raise ProviderNotAvailableError("Google", "google-genai")

        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self._api_key:
            raise ProviderConfigError(
                "Google API key not found. Set GOOGLE_API_KEY environment variable or pass api_key parameter."
            )

        self._model_name = model or self.DEFAULT_MODEL
        self._max_tokens = max_tokens or self.MAX_TOKENS
        self._client = genai.Client(api_key=self._api_key)

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "Google"

    @property
    def model(self) -> str:
        """Return the model name being used."""
        return self._model_name

    def _generate(self, prompt: str, system: str | None) -> Any:
        """Send one request to Gemini."""
        # subhadipmitra@: The new SDK takes the system prompt as a real system instruction,
        # so it no longer has to be pasted in front of the user prompt.
        config = types.GenerateContentConfig(system_instruction=system, max_output_tokens=self._max_tokens)
        return self._client.models.generate_content(model=self._model_name, contents=prompt, config=config)

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt to Gemini and return the response.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt for context

        Returns:
            The response text from Gemini

        Raises:
            LLMError: If the API call fails
        """
        try:
            return _text_of(self._generate(prompt, system))
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"Google API error: {e}") from e

    def complete_with_metadata(self, prompt: str, system: str | None = None) -> LLMResponse:
        """Send a prompt and return response with metadata.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt for context

        Returns:
            LLMResponse with content and metadata
        """
        try:
            response = self._generate(prompt, system)

            usage = None
            if response.usage_metadata:
                usage = {
                    "input_tokens": response.usage_metadata.prompt_token_count,
                    "output_tokens": response.usage_metadata.candidates_token_count,
                }

            return LLMResponse(
                content=_text_of(response),
                model=self._model_name,
                provider=self.name,
                usage=usage,
            )
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"Google API error: {e}") from e


def _text_of(response: Any) -> str:
    """Return the reply text, raising LLMError if the prompt was blocked."""
    # subhadipmitra@: A blocked prompt returns no candidates and response.text is None.
    # Report the block reason instead of returning an empty explanation.
    feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(feedback, "block_reason", None)
    if block_reason:
        raise LLMError(f"Gemini blocked this request: {block_reason}")
    return response.text or ""


def is_available() -> bool:
    """Check if Google provider is available.

    Returns:
        True if google-genai package is installed and API key is configured.
    """
    if not _GOOGLE_AVAILABLE:
        return False
    return bool(os.environ.get("GOOGLE_API_KEY"))


__all__ = ["GoogleProvider", "is_available"]
