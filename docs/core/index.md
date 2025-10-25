# Core Module

The core module provides all ISO 8583 message handling functionality.

## Components

| Component | Description |
|-----------|-------------|
| [Types & Fields](types.md) | Data types, enums, and field definitions |
| [Parser](parser.md) | Parse raw messages into structured objects |
| [Builder](builder.md) | Build raw messages from objects |
| [Validator](validator.md) | Validate message structure and content |
| [EMV Data](emv.md) | Handle Field 55 chip card data |
| [Object Pool](pool.md) | High-throughput object pooling |

## Quick Start

```python
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.validator import ISO8583Validator
from iso8583sim.core.types import ISO8583Message, CardNetwork

# Parse
parser = ISO8583Parser()
message = parser.parse("0100702406C120E09000...")

# Build
builder = ISO8583Builder()
raw = builder.build(message)

# Validate
validator = ISO8583Validator()
errors = validator.validate_message(message)
```

## Features

### Network-Agnostic Design

The core module is network-agnostic by default. Network-specific behavior is added through:

- `CardNetwork` parameter for network-specific field definitions
- Auto-detection from PAN prefix when parsing

```python
# Auto-detect network from PAN
message = parser.parse(raw_message)
print(message.network)  # CardNetwork.VISA

# Or specify explicitly
message = parser.parse(raw_message, network=CardNetwork.MASTERCARD)
```

### Version Support

Supports ISO 8583 versions 1987, 1993, and 2003:

```python
from iso8583sim.core.types import ISO8583Version

parser = ISO8583Parser(version=ISO8583Version.V1993)
builder = ISO8583Builder(version=ISO8583Version.V1993)
```

### Performance Optimization

Optional Cython extensions provide ~2x speedup:

```bash
pip install iso8583sim[perf]
python setup.py build_ext --inplace
```

Detection is automatic - the parser/validator use Cython functions when available.

### Object Pooling

For high-throughput scenarios, use `MessagePool`:

```python
from iso8583sim.core.pool import MessagePool
from iso8583sim.core.parser import ISO8583Parser

pool = MessagePool(size=1000)
parser = ISO8583Parser(pool=pool)

# Messages are recycled automatically
for raw in raw_messages:
    message = parser.parse(raw)
    # ... process message ...
    pool.release(message)  # Return to pool
```

## Architecture

See [Module Structure](../architecture/module-structure.md) for detailed architecture documentation.
