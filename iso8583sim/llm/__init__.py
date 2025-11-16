"""LLM-powered features for ISO 8583 message handling.

This module provides AI-powered tools for explaining and generating
ISO 8583 messages using various LLM providers.

Features:
- MessageExplainer: Explain messages in plain English
- MessageGenerator: Generate messages from natural language

Supported Providers:
- Anthropic (Claude)
- OpenAI (GPT)
- Google (Gemini)
- Ollama (local models)

Example:
    >>> from iso8583sim.llm import MessageExplainer, MessageGenerator
    >>>
    >>> # Explain a message
    >>> explainer = MessageExplainer()  # Auto-detects provider
    >>> print(explainer.explain(message))
    >>>
    >>> # Generate a message
    >>> generator = MessageGenerator(provider="anthropic")
    >>> message = generator.generate("$100 VISA purchase")

Installation:
    # Install with all LLM providers
    pip install iso8583sim[llm]

    # Or install specific providers
    pip install iso8583sim[anthropic]
    pip install iso8583sim[openai]
    pip install iso8583sim[google]
    pip install iso8583sim[ollama]
"""

from iso8583sim.llm.base import (
    GenerationError,
    LLMError,
    LLMProvider,
    LLMResponse,
    ProviderConfigError,
    ProviderNotAvailableError,
)
from iso8583sim.llm.explainer import MessageExplainer
from iso8583sim.llm.generator import MessageGenerator
from iso8583sim.llm.providers import get_provider, list_available_providers, list_installed_providers

__all__ = [
    # Main classes
    "MessageExplainer",
    "MessageGenerator",
    # Provider management
    "LLMProvider",
    "LLMResponse",
    "get_provider",
    "list_available_providers",
    "list_installed_providers",
    # Exceptions
    "LLMError",
    "GenerationError",
    "ProviderConfigError",
    "ProviderNotAvailableError",
]
