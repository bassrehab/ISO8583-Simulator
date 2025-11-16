"""LLM provider factory and auto-detection.

This module provides a factory function to create LLM providers
and auto-detect available providers based on installed packages
and configured API keys.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from iso8583sim.llm.base import LLMProvider, ProviderConfigError

if TYPE_CHECKING:
    pass

# Provider registry - maps names to (module, class_name, is_available_func)
_PROVIDERS: dict[str, tuple[str, str, str]] = {
    "anthropic": ("iso8583sim.llm.providers.anthropic", "AnthropicProvider", "is_available"),
    "openai": ("iso8583sim.llm.providers.openai", "OpenAIProvider", "is_available"),
    "google": ("iso8583sim.llm.providers.google", "GoogleProvider", "is_available"),
    "ollama": ("iso8583sim.llm.providers.ollama", "OllamaProvider", "is_available"),
}

# Priority order for auto-detection
_PROVIDER_PRIORITY = ["anthropic", "openai", "google", "ollama"]


def _import_provider(name: str) -> tuple[type[LLMProvider], bool]:
    """Import a provider class and its availability checker.

    Args:
        name: Provider name (e.g., 'anthropic')

    Returns:
        Tuple of (provider_class, is_available)

    Raises:
        ProviderConfigError: If provider is not found
    """
    if name not in _PROVIDERS:
        available = ", ".join(_PROVIDERS.keys())
        raise ProviderConfigError(f"Unknown provider: {name}. Available: {available}")

    module_name, class_name, avail_func = _PROVIDERS[name]

    try:
        import importlib

        module = importlib.import_module(module_name)
        provider_class = getattr(module, class_name)
        is_available = getattr(module, avail_func)()
        return provider_class, is_available
    except ImportError:
        return None, False  # type: ignore


def get_provider(name: str | None = None, **kwargs) -> LLMProvider:
    """Get an LLM provider instance.

    If name is provided, creates that specific provider.
    If name is None, auto-detects the first available provider.

    Args:
        name: Provider name ('anthropic', 'openai', 'google', 'ollama')
              or None for auto-detection
        **kwargs: Additional arguments passed to the provider constructor

    Returns:
        An initialized LLMProvider instance

    Raises:
        ProviderConfigError: If no provider is available or configured

    Example:
        >>> provider = get_provider()  # Auto-detect
        >>> provider = get_provider("anthropic")  # Specific provider
        >>> provider = get_provider("openai", model="gpt-4-turbo")
    """
    if name:
        # Specific provider requested
        provider_class, is_available = _import_provider(name.lower())
        if provider_class is None:
            raise ProviderConfigError(
                f"{name} provider package is not installed. " f"Install with: pip install iso8583sim[{name.lower()}]"
            )
        return provider_class(**kwargs)

    # Auto-detect available provider
    for provider_name in _PROVIDER_PRIORITY:
        provider_class, is_available = _import_provider(provider_name)
        if provider_class and is_available:
            return provider_class(**kwargs)

    # No provider available
    raise ProviderConfigError(
        "No LLM provider available. Install one of:\n"
        "  pip install iso8583sim[anthropic]  # Claude\n"
        "  pip install iso8583sim[openai]     # GPT\n"
        "  pip install iso8583sim[google]     # Gemini\n"
        "  pip install iso8583sim[ollama]     # Local\n"
        "  pip install iso8583sim[llm]        # All providers\n"
        "\nThen set the appropriate API key environment variable."
    )


def list_available_providers() -> list[str]:
    """List all available and configured providers.

    Returns:
        List of provider names that are installed and configured
    """
    available = []
    for name in _PROVIDER_PRIORITY:
        _, is_available = _import_provider(name)
        if is_available:
            available.append(name)
    return available


def list_installed_providers() -> list[str]:
    """List all installed providers (may not be configured).

    Returns:
        List of provider names that have their packages installed
    """
    installed = []
    for name in _PROVIDER_PRIORITY:
        provider_class, _ = _import_provider(name)
        if provider_class is not None:
            installed.append(name)
    return installed


__all__ = [
    "get_provider",
    "list_available_providers",
    "list_installed_providers",
]
