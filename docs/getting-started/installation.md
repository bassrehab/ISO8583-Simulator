# Installation

## Requirements

- Python 3.10 or higher
- pip package manager

## Basic Installation

Install iso8583sim from PyPI:

```bash
pip install iso8583sim
```

## Optional Dependencies

### LLM Providers

For AI-powered message explanation and generation:

```bash
# Anthropic (Claude) - Recommended
pip install iso8583sim[anthropic]

# OpenAI (GPT)
pip install iso8583sim[openai]

# Google (Gemini)
pip install iso8583sim[google]

# Ollama (Local models)
pip install iso8583sim[ollama]

# All LLM providers
pip install iso8583sim[llm]
```

After installation, set your API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# or
export OPENAI_API_KEY="sk-..."
# or
export GOOGLE_API_KEY="..."
```

### Performance Extensions

For maximum throughput with Cython:

```bash
pip install iso8583sim[perf]
python setup.py build_ext --inplace
```

This provides ~2x speedup for parsing operations.

### Development

For development and testing:

```bash
pip install iso8583sim[dev]
```

This includes pytest, ruff, mypy, and pre-commit hooks.

### Documentation

To build documentation locally:

```bash
pip install iso8583sim[docs]
mkdocs serve
```

## Development Installation

Clone and install in development mode:

```bash
git clone https://github.com/bassrehab/ISO8583-Simulator.git
cd iso8583sim
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Verify Installation

```python
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.builder import ISO8583Builder

print("iso8583sim installed successfully!")
```

## Next Steps

- [Quick Start Tutorial](quickstart.md) - Build your first message
- [ISO 8583 Concepts](concepts.md) - Learn the basics
