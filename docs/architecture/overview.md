# Architecture Overview

iso8583sim is designed with a focus on performance, extensibility, and ease of use.

## Design Principles

### 1. Network-Agnostic Core

The core parsing and building logic is network-agnostic. Network-specific handling (VISA, Mastercard, etc.) is layered on top through:

- `CardNetwork` enum for network identification
- `NETWORK_SPECIFIC_FIELDS` for network-specific field definitions
- `NETWORK_REQUIRED_FIELDS` for network validation rules

### 2. Performance First

Performance optimizations include:

- **Optional Cython extensions**: 2x speedup for parsing operations
- **Object pooling**: Reusable message objects for high-throughput scenarios
- **Pre-compiled regex patterns**: Avoid recompilation overhead
- **Cached field lookups**: Network and version-specific field caching

### 3. Optional LLM Integration

LLM features are completely optional:

- Core functionality works without any LLM dependencies
- Provider-agnostic design supports Anthropic, OpenAI, Google, Ollama
- Auto-detection of available providers based on installed packages and API keys

## Package Structure

```
iso8583sim/
├── core/               # Core message handling
│   ├── types.py        # Data types, enums, field definitions
│   ├── parser.py       # Message parsing
│   ├── builder.py      # Message building
│   ├── validator.py    # Message validation
│   ├── emv.py          # EMV/TLV data handling
│   ├── pool.py         # Object pooling
│   └── _*.pyx          # Cython extensions (optional)
├── llm/                # LLM-powered features
│   ├── base.py         # Provider interface
│   ├── explainer.py    # Message explanation
│   ├── generator.py    # Message generation
│   └── providers/      # LLM provider implementations
│       ├── anthropic.py
│       ├── openai.py
│       ├── google.py
│       └── ollama.py
├── cli/                # Command-line interface
│   └── commands.py     # Click-based CLI commands
├── web/                # REST API (future)
└── demo.py             # Interactive demo helpers
```

## Key Components

### ISO8583Message

The central data structure representing a parsed or constructed message:

```python
@dataclass(slots=True)
class ISO8583Message:
    mti: str                                    # Message Type Indicator
    fields: dict[int, str]                      # Field number -> value
    bitmap: str = ""                            # Primary bitmap (hex)
    secondary_bitmap: str | None = None         # Secondary bitmap
    network: CardNetwork | None = None          # Detected card network
    version: ISO8583Version = ISO8583Version.V1987
    raw: str = ""                               # Original raw message
    emv_data: dict[str, str] | None = None      # Parsed Field 55 EMV data
```

### ISO8583Parser

Stateful parser that converts raw message strings into `ISO8583Message` objects:

- Auto-detects card network from PAN prefix
- Supports ISO 8583 versions 1987, 1993, 2003
- Handles primary and secondary bitmaps
- Parses LLVAR/LLLVAR variable-length fields
- Optional Cython acceleration

### ISO8583Builder

Constructs raw ISO 8583 message strings from `ISO8583Message` objects:

- Validates messages before building
- Handles field formatting (padding, length prefixes)
- Builds bitmap from present fields
- Network-aware field formatting

### ISO8583Validator

Validates message structure and field content:

- MTI validation
- Field type validation (numeric, alpha, alphanumeric, binary)
- Network-specific required field validation
- PAN Luhn check validation

### EMV Handling

Field 55 (ICC Data) contains EMV chip card data in TLV format:

- `parse_emv_data()`: Parse TLV bytes into tag dictionary
- `build_emv_data()`: Build TLV bytes from tag dictionary
- Support for multi-byte tags (9F26, 9F27, etc.)

## Data Flow

See [Message Flow](message-flow.md) for detailed data flow diagrams.

## Extension Points

### Adding New Card Networks

1. Add enum value to `CardNetwork`
2. Add field definitions to `NETWORK_SPECIFIC_FIELDS`
3. Add required fields to `NETWORK_REQUIRED_FIELDS`
4. Add validation method to `ISO8583Validator`

### Adding LLM Providers

1. Implement `LLMProvider` interface
2. Add provider to `_PROVIDERS` registry in `providers/__init__.py`
3. Implement `is_available()` function

### Custom Field Definitions

```python
from iso8583sim.core.types import FieldDefinition, FieldType

custom_field = FieldDefinition(
    field_type=FieldType.ALPHANUMERIC,
    max_length=20,
    description="Custom field",
    field_number=120,
)
```
