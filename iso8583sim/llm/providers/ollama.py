"""Ollama (local) LLM provider implementation."""

from __future__ import annotations

from iso8583sim.llm.base import LLMError, LLMProvider, LLMResponse, ProviderNotAvailableError

try:
    import ollama

    _OLLAMA_AVAILABLE = True
except ImportError:
    _OLLAMA_AVAILABLE = False


class OllamaProvider(LLMProvider):
    """LLM provider using local Ollama server.

    Example:
        >>> provider = OllamaProvider()  # Uses llama3.2 on localhost
        >>> response = provider.complete("Explain ISO 8583")
        >>> print(response)

        >>> # Or with custom model and host
        >>> provider = OllamaProvider(model="mistral", host="http://192.168.1.100:11434")
    """

    DEFAULT_MODEL = "llama3.2"
    DEFAULT_HOST = "http://localhost:11434"

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
    ):
        """Initialize the Ollama provider.

        Args:
            model: Model to use. Defaults to llama3.2.
            host: Ollama server URL. Defaults to http://localhost:11434.

        Raises:
            ProviderNotAvailableError: If ollama package is not installed.
        """
        if not _OLLAMA_AVAILABLE:
            raise ProviderNotAvailableError("Ollama", "ollama")

        self._model_name = model or self.DEFAULT_MODEL
        self._host = host or self.DEFAULT_HOST
        self._client = ollama.Client(host=self._host)

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "Ollama"

    @property
    def model(self) -> str:
        """Return the model name being used."""
        return self._model_name

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt to Ollama and return the response.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt for context

        Returns:
            The response text from Ollama

        Raises:
            LLMError: If the API call fails
        """
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self._client.chat(
                model=self._model_name,
                messages=messages,
            )
            return response["message"]["content"]
        except Exception as e:
            raise LLMError(f"Ollama error: {e}") from e

    def complete_with_metadata(self, prompt: str, system: str | None = None) -> LLMResponse:
        """Send a prompt and return response with metadata.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt for context

        Returns:
            LLMResponse with content and metadata
        """
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self._client.chat(
                model=self._model_name,
                messages=messages,
            )

            usage = None
            if "eval_count" in response or "prompt_eval_count" in response:
                usage = {
                    "input_tokens": response.get("prompt_eval_count", 0),
                    "output_tokens": response.get("eval_count", 0),
                }

            return LLMResponse(
                content=response["message"]["content"],
                model=self._model_name,
                provider=self.name,
                usage=usage,
            )
        except Exception as e:
            raise LLMError(f"Ollama error: {e}") from e


def is_available() -> bool:
    """Check if Ollama provider is available.

    Returns:
        True if ollama package is installed. Note: doesn't check if server is running.
    """
    return _OLLAMA_AVAILABLE


__all__ = ["OllamaProvider", "is_available"]
