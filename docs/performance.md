# Performance Optimization Guide

This document describes the performance optimizations implemented in iso8583sim v0.3.0 and how to leverage them for high-throughput message processing.

## Overview

The iso8583sim library has been optimized for high-performance ISO 8583 message processing. Through a combination of pure Python optimizations and optional Cython compilation, the library achieves:

- **182,000+ TPS** for message parsing
- **150,000+ TPS** for message building
- **63,000+ TPS** for full roundtrip (build → parse → validate)

## Benchmark Results

### Performance Comparison

| Operation | v0.2.0 Baseline | v0.3.0 Optimized | Improvement |
|-----------|-----------------|------------------|-------------|
| Parse (basic messages) | 95,000 TPS | 182,000 TPS | +91% |
| Parse (VISA messages) | 64,000 TPS | 121,000 TPS | +89% |
| Parse (EMV messages) | 104,000 TPS | 197,000 TPS | +89% |
| Build messages | 143,000 TPS | 150,000 TPS | +5% |
| Roundtrip (with validation) | 45,000 TPS | 63,000 TPS | +40% |
| Roundtrip (parse only) | 54,000 TPS | 78,000 TPS | +44% |
| Request/Response flow | 25,000 TPS | 32,000 TPS | +28% |

*Benchmarks run on macOS 15.7.2 arm64, Python 3.12.6, Apple Silicon*

### Running Benchmarks

```bash
# Run all benchmarks
python benchmarks/bench_parser.py
python benchmarks/bench_builder.py
python benchmarks/bench_roundtrip.py
```

## Optimization Techniques

### Phase 1: Pure Python Optimizations

These optimizations are always active and require no additional dependencies.

#### 1. Lazy Logging

Log statements use `%s` formatting instead of f-strings to defer string formatting until the log level is enabled:

```python
# Before (always formats string)
self.logger.debug(f"Parsed field {field_number}: {value}")

# After (only formats if DEBUG enabled)
self.logger.debug("Parsed field %d: %s", field_number, value)
```

#### 2. Dataclass Slots

All dataclasses use `slots=True` for reduced memory footprint and faster attribute access:

```python
@dataclass(slots=True)
class ISO8583Message:
    mti: str
    fields: dict[int, str]
    # ...
```

**Note:** This requires Python 3.10+.

#### 3. Dictionary Lookup Caching

Network and version-specific field definitions are cached at parse time to avoid repeated dictionary lookups:

```python
class ISO8583Parser:
    def __init__(self, version=ISO8583Version.V1987):
        # Cache version fields at init (doesn't change)
        self._version_fields = VERSION_SPECIFIC_FIELDS.get(version, {})

    def parse(self, message, network=None):
        # Cache network fields for this parse operation
        self._network_fields = NETWORK_SPECIFIC_FIELDS.get(network, {})
```

#### 4. LRU Cache for Field Definitions

The `get_field_definition()` function uses `@lru_cache` for fast repeated lookups:

```python
@lru_cache(maxsize=512)
def get_field_definition(field_number, network=None, version=ISO8583Version.V1987):
    # Returns cached result for repeated calls
    ...
```

### Phase 2: Cython Compilation

For maximum performance, iso8583sim includes optional Cython extensions that compile hot paths to C code.

#### Building Cython Extensions

```bash
# Install Cython
pip install cython>=3.0.0

# Build extensions
python setup.py build_ext --inplace
```

The following modules are compiled:

| Module | Functions | Speedup |
|--------|-----------|---------|
| `_bitmap.pyx` | `get_present_fields_fast()`, `build_bitmap_fast()` | 2-3x |
| `_parser_fast.pyx` | `parse_mti_fast()`, `parse_bitmap_fast()` | 1.5-2x |
| `_validator_fast.pyx` | `validate_pan_luhn()`, `is_valid_hex()`, etc. | 1.5-2x |

#### Automatic Fallback

The library automatically detects Cython availability and falls back to pure Python:

```python
# In parser.py
try:
    from ._bitmap import get_present_fields_fast
    _USE_CYTHON = True
except ImportError:
    _USE_CYTHON = False

def _get_present_fields(self, bitmap):
    if _USE_CYTHON:
        return get_present_fields_fast(bitmap)
    # Pure Python fallback
    ...
```

### Phase 3: Object Pooling

For high-throughput applications processing millions of messages, object pooling reduces allocation overhead:

```python
from iso8583sim.core.pool import MessagePool
from iso8583sim.core.parser import ISO8583Parser

# Create a pool
pool = MessagePool(size=100)

# Create parser with pool
parser = ISO8583Parser(pool=pool)

# Parse messages (pool reuses objects)
for raw_message in messages:
    msg = parser.parse(raw_message)

    # Process message...

    # Return to pool when done
    pool.release(msg)
```

#### Pool API

```python
class MessagePool:
    def __init__(self, size: int = 100):
        """Create pool with maximum size."""

    def acquire(self, mti, fields, ...) -> ISO8583Message:
        """Get message from pool or create new one."""

    def release(self, msg: ISO8583Message) -> None:
        """Return message to pool for reuse."""

    def clear(self) -> None:
        """Clear all pooled messages."""

    @property
    def size(self) -> int:
        """Current number of pooled messages."""
```

#### When to Use Pooling

Object pooling is most beneficial when:
- Processing millions of messages in a long-running application
- Memory fragmentation is a concern
- You can explicitly control message lifecycle

For typical usage, the `slots=True` dataclasses are already efficient enough that pooling provides minimal benefit.

## Configuration Recommendations

### High-Throughput Production

For maximum performance in production:

1. **Install Cython extensions:**
   ```bash
   pip install iso8583sim[perf]
   python setup.py build_ext --inplace
   ```

2. **Use object pooling for sustained loads:**
   ```python
   pool = MessagePool(size=1000)
   parser = ISO8583Parser(pool=pool)
   ```

3. **Reuse parser/builder instances** (they cache field definitions):
   ```python
   # Good - reuse parser
   parser = ISO8583Parser()
   for msg in messages:
       result = parser.parse(msg)

   # Bad - creates new parser each time
   for msg in messages:
       result = ISO8583Parser().parse(msg)
   ```

4. **Disable debug logging in production:**
   ```python
   import logging
   logging.getLogger('iso8583sim').setLevel(logging.WARNING)
   ```

### Development/Testing

For development, the pure Python implementation is sufficient:

```python
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.builder import ISO8583Builder

parser = ISO8583Parser()
builder = ISO8583Builder()
```

## System Requirements

| Feature | Minimum Python |
|---------|----------------|
| Core library | 3.10+ |
| `slots=True` dataclasses | 3.10+ |
| Cython extensions | 3.10+ |
| Object pooling | 3.10+ |

## Profiling Your Application

To identify bottlenecks in your specific use case:

```python
import cProfile
import pstats

# Profile your code
cProfile.run('your_message_processing_function()', 'output.prof')

# Analyze results
stats = pstats.Stats('output.prof')
stats.sort_stats('cumulative')
stats.print_stats(20)
```

## Future Optimization Opportunities

Potential areas for further optimization:

1. **memoryview** - Zero-copy parsing for very large messages
2. **Async batch processing** - Parallel processing of message batches
3. **SIMD operations** - Vectorized bitmap operations for modern CPUs
4. **Pre-compiled message templates** - For common message patterns
