# ISO8583 Simulator

[![PyPI version](https://img.shields.io/pypi/v/iso8583sim.svg)](https://pypi.org/project/iso8583sim/)
[![Python versions](https://img.shields.io/pypi/pyversions/iso8583sim.svg)](https://pypi.org/project/iso8583sim/)
[![License](https://img.shields.io/github/license/bassrehab/ISO8583-Simulator.svg)](https://github.com/bassrehab/ISO8583-Simulator/blob/main/LICENSE)
[![CI](https://github.com/bassrehab/ISO8583-Simulator/actions/workflows/ci.yml/badge.svg)](https://github.com/bassrehab/ISO8583-Simulator/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-iso8583.subhadipmitra.com-blue.svg)](https://iso8583.subhadipmitra.com)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A modern, high-performance ISO 8583 message simulator with CLI, Python SDK, and interactive Jupyter notebooks.

## Features

- **Message Handling**:
  - Parse ISO 8583 messages (180k+ TPS with Cython)
  - Build ISO 8583 messages (150k+ TPS)
  - Validate message structure and content
  - Support for ISO versions (1987, 1993, 2003)

- **Network Support**:
  - VISA, Mastercard, AMEX, Discover, JCB, UnionPay
  - Network-specific field validation
  - EMV/chip card data handling (Field 55)

- **Multiple Interfaces**:
  - Command Line Interface (CLI)
  - Python SDK for programmatic usage
  - Interactive Jupyter notebooks

- **Performance Optimized**:
  - Optional Cython extensions for 2x speedup
  - Object pooling for high-throughput scenarios
  - See [Performance Guide](docs/performance.md)

## Installation

```bash
pip install iso8583sim

# For Cython performance extensions
pip install iso8583sim[perf]
python setup.py build_ext --inplace
```

## Quick Start

### Python SDK

```python
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.validator import ISO8583Validator
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

# Validate a message
validator = ISO8583Validator()
errors = validator.validate_message(parsed)
```

### CLI Usage

```bash
# Parse a message
iso8583sim parse "0100..." --version 1987

# Build a message
iso8583sim build --mti 0100 --fields fields.json

# Validate a message
iso8583sim validate "0100..."

# Generate sample messages
iso8583sim generate --type auth --pan 4111111111111111 --amount 1000
```

## Interactive Notebooks

Learn ISO 8583 with our Jupyter notebooks:

| Notebook | Description |
|----------|-------------|
| [01_getting_started.ipynb](notebooks/01_getting_started.ipynb) | Basic concepts and quick start |
| [02_parsing_messages.ipynb](notebooks/02_parsing_messages.ipynb) | Deep dive into message parsing |
| [03_building_messages.ipynb](notebooks/03_building_messages.ipynb) | Building various message types |
| [04_network_specifics.ipynb](notebooks/04_network_specifics.ipynb) | VISA, Mastercard, and other networks |
| [05_emv_data.ipynb](notebooks/05_emv_data.ipynb) | Working with EMV/chip card data |
| [06_benchmarking.ipynb](notebooks/06_benchmarking.ipynb) | Performance testing and benchmarks |

Run locally:
```bash
pip install jupyter
jupyter notebook notebooks/
```

## Performance

Benchmarks on Apple Silicon (M-series), Python 3.12:

| Operation | Pure Python | With Cython |
|-----------|-------------|-------------|
| Parse | ~105k TPS | ~182k TPS |
| Build | ~150k TPS | ~150k TPS |
| Roundtrip | ~49k TPS | ~63k TPS |

See [benchmarks/BASELINE.md](benchmarks/BASELINE.md) for detailed results.

## Documentation

Full documentation is available at **[iso8583.subhadipmitra.com](https://iso8583.subhadipmitra.com)**

- [Getting Started](https://iso8583.subhadipmitra.com/getting-started/quickstart/) - Quick start guide
- [Architecture](https://iso8583.subhadipmitra.com/architecture/overview/) - System design and decisions
- [API Reference](https://iso8583.subhadipmitra.com/api/core/) - Complete API documentation
- [Performance Guide](https://iso8583.subhadipmitra.com/performance/) - Optimization techniques

## Development

```bash
# Clone and setup
git clone https://github.com/bassrehab/ISO8583-Simulator.git
cd iso8583sim
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Run benchmarks
python benchmarks/bench_parser.py
python benchmarks/bench_roundtrip.py
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Create a Pull Request

## Author

**Subhadip Mitra** - [subhadipmitra.com](https://subhadipmitra.com)

- GitHub: [@bassrehab](https://github.com/bassrehab)
- LinkedIn: [subhadipmitra](https://linkedin.com/in/subhadipmitra)

## License

MIT License - see [LICENSE](LICENSE) for details.
