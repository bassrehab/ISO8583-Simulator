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

### MCP Server

To use iso8583sim from Claude, Cursor or another MCP client:

```bash
pip install iso8583sim[mcp]
```

See [MCP Server](../mcp/index.md) for client setup.

### REST API

```bash
pip install iso8583sim[web]
```

See [REST API](../web/index.md).

### PIN Blocks and MACs

```bash
pip install iso8583sim[security]
```

See [PIN Blocks and MACs](../core/security.md).

### Performance Extensions

The compiled Cython extensions (about 2x faster parsing) are included in the wheels on PyPI for CPython 3.10 to 3.14 on:

- Linux: x86_64 and aarch64 (glibc and musl)
- macOS: Intel and Apple Silicon
- Windows: x64

On other platforms pip builds from source. With a C compiler the extensions are compiled; without one, iso8583sim installs as pure Python and works the same, only slower. To check which you have:

```bash
python -c "import iso8583sim.core.parser as p; print(p._USE_CYTHON)"
```

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
