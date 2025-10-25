# ISO8583 Simulator

A modern, high-performance ISO 8583 message simulator with CLI, Python SDK, and LLM-powered features.

## Features

- **Message Handling**: Parse, build, and validate ISO 8583 messages at 180k+ TPS
- **Multi-Network Support**: VISA, Mastercard, AMEX, Discover, JCB, UnionPay
- **EMV/Chip Card Data**: Full Field 55 TLV parsing and building
- **LLM Integration**: AI-powered message explanation and generation
- **Multiple Interfaces**: Python SDK, CLI, and interactive Jupyter notebooks

## Quick Start

```python
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.types import ISO8583Message

# Build a message
builder = ISO8583Builder()
message = ISO8583Message(
    mti="0100",
    fields={
        0: "0100",
        2: "4111111111111111",
        3: "000000",
        4: "000000001000",
        11: "123456",
        41: "TERM0001",
        42: "MERCHANT123456 ",
    }
)
raw = builder.build(message)

# Parse a message
parser = ISO8583Parser()
parsed = parser.parse(raw)
```

## Installation

```bash
pip install iso8583sim

# With LLM features
pip install iso8583sim[anthropic]  # Claude
pip install iso8583sim[openai]     # GPT
pip install iso8583sim[llm]        # All providers

# With Cython performance extensions
pip install iso8583sim[perf]
```

## Documentation Overview

| Section | Description |
|---------|-------------|
| [Getting Started](getting-started/installation.md) | Installation and quick tutorial |
| [Architecture](architecture/overview.md) | Design decisions and module structure |
| [Core Module](core/index.md) | Parser, builder, validator, and types |
| [Networks](networks/index.md) | VISA, Mastercard, and other card networks |
| [LLM Features](llm/index.md) | AI-powered message explanation and generation |
| [CLI Reference](cli/index.md) | Command-line interface usage |
| [API Reference](api/core.md) | Auto-generated API documentation |

## Performance

Benchmarks on Apple Silicon (M-series), Python 3.12:

| Operation | Pure Python | With Cython |
|-----------|-------------|-------------|
| Parse | ~105k TPS | ~182k TPS |
| Build | ~150k TPS | ~150k TPS |
| Roundtrip | ~49k TPS | ~63k TPS |

See the [Performance Guide](performance.md) for optimization techniques.

## License

MIT License - see [LICENSE](https://github.com/bassrehab/ISO8583-Simulator/blob/main/LICENSE) for details.
