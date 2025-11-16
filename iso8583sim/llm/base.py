"""Base classes for LLM providers.

This module defines the abstract base class for LLM providers, allowing
multiple backend implementations (Anthropic, OpenAI, Google, Ollama).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    provider: str
    usage: dict[str, int] | None = None


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class ProviderNotAvailableError(LLMError):
    """Raised when a provider's dependencies are not installed."""

    def __init__(self, provider: str, package: str):
        self.provider = provider
        self.package = package
        super().__init__(
            f"{provider} provider requires '{package}' package. "
            f"Install with: pip install iso8583sim[{provider.lower()}]"
        )


class ProviderConfigError(LLMError):
    """Raised when provider configuration is invalid."""

    pass


class GenerationError(LLMError):
    """Raised when message generation fails."""

    pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM providers must implement this interface to be compatible
    with MessageExplainer and MessageGenerator.

    Example:
        >>> class MyProvider(LLMProvider):
        ...     def complete(self, prompt, system=None):
        ...         return "response"
        ...     @property
        ...     def name(self):
        ...         return "my-provider"
    """

    @abstractmethod
    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt to the LLM and return the response text.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt for context

        Returns:
            The LLM's response text

        Raises:
            LLMError: If the API call fails
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name for logging/display."""
        pass

    @property
    def model(self) -> str:
        """Return the model name being used."""
        return "unknown"

    def complete_with_metadata(self, prompt: str, system: str | None = None) -> LLMResponse:
        """Send a prompt and return response with metadata.

        Default implementation wraps complete(). Providers can override
        for more detailed metadata.

        Args:
            prompt: The user prompt to send
            system: Optional system prompt for context

        Returns:
            LLMResponse with content and metadata
        """
        content = self.complete(prompt, system)
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.name,
        )


__all__ = [
    "LLMProvider",
    "LLMResponse",
    "LLMError",
    "ProviderNotAvailableError",
    "ProviderConfigError",
    "GenerationError",
]
