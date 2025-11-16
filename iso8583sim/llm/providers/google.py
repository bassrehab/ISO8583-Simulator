"""Google (Gemini) LLM provider implementation."""

from __future__ import annotations

import os

from iso8583sim.llm.base import LLMError, LLMProvider, LLMResponse, ProviderConfigError, ProviderNotAvailableError

try:
    import google.generativeai as genai

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

    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        """Initialize the Google provider.

        Args:
            api_key: Google API key. If not provided, uses GOOGLE_API_KEY env var.
            model: Model to use. Defaults to gemini-1.5-flash.

        Raises:
            ProviderNotAvailableError: If google-generativeai package is not installed.
            ProviderConfigError: If no API key is available.
        """
        if not _GOOGLE_AVAILABLE:
            raise ProviderNotAvailableError("Google", "google-generativeai")

        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self._api_key:
            raise ProviderConfigError(
                "Google API key not found. " "Set GOOGLE_API_KEY environment variable or pass api_key parameter."
            )

        self._model_name = model or self.DEFAULT_MODEL
        genai.configure(api_key=self._api_key)
        self._model = genai.GenerativeModel(self._model_name)

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "Google"

    @property
    def model(self) -> str:
        """Return the model name being used."""
        return self._model_name

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
            # Combine system and user prompts for Gemini
            full_prompt = prompt
            if system:
                full_prompt = f"{system}\n\n{prompt}"

            response = self._model.generate_content(full_prompt)
            return response.text
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
            full_prompt = prompt
            if system:
                full_prompt = f"{system}\n\n{prompt}"

            response = self._model.generate_content(full_prompt)

            usage = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = {
                    "input_tokens": response.usage_metadata.prompt_token_count,
                    "output_tokens": response.usage_metadata.candidates_token_count,
                }

            return LLMResponse(
                content=response.text,
                model=self._model_name,
                provider=self.name,
                usage=usage,
            )
        except Exception as e:
            raise LLMError(f"Google API error: {e}") from e


def is_available() -> bool:
    """Check if Google provider is available.

    Returns:
        True if google-generativeai package is installed and API key is configured.
    """
    if not _GOOGLE_AVAILABLE:
        return False
    return bool(os.environ.get("GOOGLE_API_KEY"))


__all__ = ["GoogleProvider", "is_available"]
