# LLM Features

iso8583sim includes AI-powered features for message explanation and generation using large language models.

## Overview

The LLM module provides two main capabilities:

- **MessageExplainer**: Explain ISO 8583 messages in plain English
- **MessageGenerator**: Generate messages from natural language descriptions

## Installation

LLM features require an LLM provider. Install your preferred provider:

```bash
# Anthropic (Claude) - Recommended
pip install iso8583sim[anthropic]

# OpenAI (GPT)
pip install iso8583sim[openai]

# Google (Gemini)
pip install iso8583sim[google]

# Ollama (Local models)
pip install iso8583sim[ollama]

# All providers
pip install iso8583sim[llm]
```

## Configuration

Set your API key as an environment variable:

```bash
# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# Google
export GOOGLE_API_KEY="..."

# Ollama (no key needed for local)
```

## Quick Start

### Explain a Message

```python
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.llm import MessageExplainer

# Parse a message
parser = ISO8583Parser()
message = parser.parse(raw_message)

# Create explainer (auto-detects provider)
explainer = MessageExplainer()

# Get plain English explanation
explanation = explainer.explain(message)
print(explanation)
```

### Generate a Message

```python
from iso8583sim.llm import MessageGenerator

generator = MessageGenerator()

# Generate from natural language
message = generator.generate("$50 VISA purchase at a coffee shop")

print(f"MTI: {message.mti}")
print(f"Amount: {message.fields.get(4)}")
```

## Provider Auto-Detection

When no provider is specified, the first available provider is used:

1. Anthropic (if installed and configured)
2. OpenAI (if installed and configured)
3. Google (if installed and configured)
4. Ollama (if installed and running)

```python
from iso8583sim.llm import list_available_providers, list_installed_providers

# See what's installed
print(list_installed_providers())  # ['anthropic', 'openai']

# See what's configured (has API key)
print(list_available_providers())  # ['anthropic']
```

## Module Structure

```
iso8583sim.llm/
├── __init__.py         # Public API exports
├── base.py             # Provider interface
├── explainer.py        # MessageExplainer
├── generator.py        # MessageGenerator
└── providers/
    ├── __init__.py     # Provider factory
    ├── anthropic.py    # Claude provider
    ├── openai.py       # GPT provider
    ├── google.py       # Gemini provider
    └── ollama.py       # Ollama provider
```

## Next Steps

- [Providers](providers.md) - Configure and customize LLM providers
- [Message Explainer](explainer.md) - Detailed explanation features
- [Message Generator](generator.md) - Advanced generation options
