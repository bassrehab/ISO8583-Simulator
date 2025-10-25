# LLM Providers

iso8583sim supports multiple LLM providers with a unified interface.

## Available Providers

| Provider | Package | Model Default | Env Variable |
|----------|---------|---------------|--------------|
| Anthropic | `anthropic` | claude-sonnet-4-20250514 | `ANTHROPIC_API_KEY` |
| OpenAI | `openai` | gpt-4o | `OPENAI_API_KEY` |
| Google | `google-generativeai` | gemini-1.5-pro | `GOOGLE_API_KEY` |
| Ollama | `ollama` | llama3.2 | (none) |

## Installation

```bash
# Single provider
pip install iso8583sim[anthropic]
pip install iso8583sim[openai]
pip install iso8583sim[google]
pip install iso8583sim[ollama]

# All providers
pip install iso8583sim[llm]
```

## Configuration

### Environment Variables

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
```

### Check Availability

```python
from iso8583sim.llm import list_installed_providers, list_available_providers

# Packages installed
print(list_installed_providers())
# ['anthropic', 'openai']

# Installed + configured (has API key)
print(list_available_providers())
# ['anthropic']
```

## Provider Factory

### Auto-Detection

```python
from iso8583sim.llm import get_provider

# Auto-detect first available provider
provider = get_provider()
print(f"Using: {provider.name}")  # "Anthropic"
```

### Specific Provider

```python
from iso8583sim.llm import get_provider

# Request specific provider
provider = get_provider("openai")
provider = get_provider("anthropic")
provider = get_provider("google")
provider = get_provider("ollama")
```

### Custom Model

```python
from iso8583sim.llm import get_provider

# Use a specific model
provider = get_provider("anthropic", model="claude-3-haiku-20240307")
provider = get_provider("openai", model="gpt-4-turbo")
```

## Direct Provider Usage

### Anthropic

```python
from iso8583sim.llm.providers.anthropic import AnthropicProvider

provider = AnthropicProvider(
    api_key="sk-ant-...",  # Or use env var
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
)

response = provider.complete("Explain ISO 8583 Field 55")
print(response)
```

### OpenAI

```python
from iso8583sim.llm.providers.openai import OpenAIProvider

provider = OpenAIProvider(
    api_key="sk-...",  # Or use env var
    model="gpt-4o",
    max_tokens=4096,
)

response = provider.complete("Explain ISO 8583 Field 55")
print(response)
```

### Google

```python
from iso8583sim.llm.providers.google import GoogleProvider

provider = GoogleProvider(
    api_key="...",  # Or use env var
    model="gemini-1.5-pro",
)

response = provider.complete("Explain ISO 8583 Field 55")
```

### Ollama (Local)

```python
from iso8583sim.llm.providers.ollama import OllamaProvider

# Requires Ollama running locally
provider = OllamaProvider(
    model="llama3.2",
    host="http://localhost:11434",
)

response = provider.complete("Explain ISO 8583 Field 55")
```

## Using with Explainer/Generator

```python
from iso8583sim.llm import MessageExplainer, get_provider

# Auto-detect
explainer = MessageExplainer()

# Specific provider
provider = get_provider("anthropic")
explainer = MessageExplainer(provider=provider)

# Custom model
from iso8583sim.llm.providers.anthropic import AnthropicProvider
provider = AnthropicProvider(model="claude-3-haiku-20240307")
explainer = MessageExplainer(provider=provider)
```

## Response Metadata

Get usage information with `complete_with_metadata`:

```python
from iso8583sim.llm import get_provider

provider = get_provider()
response = provider.complete_with_metadata("Explain ISO 8583")

print(f"Content: {response.content}")
print(f"Model: {response.model}")
print(f"Provider: {response.provider}")
print(f"Input tokens: {response.usage['input_tokens']}")
print(f"Output tokens: {response.usage['output_tokens']}")
```

## Error Handling

```python
from iso8583sim.llm import (
    get_provider,
    LLMError,
    ProviderConfigError,
    ProviderNotAvailableError,
)

try:
    provider = get_provider("anthropic")
    response = provider.complete("...")
except ProviderNotAvailableError as e:
    print(f"Provider not installed: {e}")
except ProviderConfigError as e:
    print(f"Provider not configured: {e}")
except LLMError as e:
    print(f"API error: {e}")
```

## Provider Interface

All providers implement `LLMProvider`:

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'Anthropic')"""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Model being used"""
        pass

    @abstractmethod
    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send prompt and return response text"""
        pass

    @abstractmethod
    def complete_with_metadata(
        self, prompt: str, system: str | None = None
    ) -> LLMResponse:
        """Send prompt and return response with metadata"""
        pass
```

## API Reference

See [LLM API Reference](../api/llm.md#iso8583simllmproviders) for complete API documentation.
