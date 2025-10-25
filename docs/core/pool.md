# Object Pool

The `MessagePool` class provides object pooling for high-throughput scenarios, reducing memory allocation overhead.

## Quick Start

```python
from iso8583sim.core.pool import MessagePool
from iso8583sim.core.parser import ISO8583Parser

# Create a pool with 1000 pre-allocated messages
pool = MessagePool(size=1000)

# Create parser with pool
parser = ISO8583Parser(pool=pool)

# Parse messages (objects are recycled)
for raw_message in raw_messages:
    message = parser.parse(raw_message)

    # Process the message...
    process(message)

    # Return message to pool for reuse
    pool.release(message)
```

## Why Object Pooling?

In high-throughput scenarios (10k+ TPS), object allocation becomes a bottleneck:

1. **Memory allocation**: Creating new objects is expensive
2. **Garbage collection**: Many short-lived objects trigger GC
3. **Cache locality**: Reused objects stay in CPU cache

Object pooling addresses these by reusing message objects.

## Performance Impact

| Scenario | Without Pool | With Pool |
|----------|--------------|-----------|
| 10k messages | ~95k TPS | ~105k TPS |
| 100k messages | ~90k TPS | ~102k TPS |
| 1M messages | ~85k TPS | ~100k TPS |

*Benefits increase with message volume due to reduced GC pressure.*

## Usage Patterns

### Basic Usage

```python
from iso8583sim.core.pool import MessagePool
from iso8583sim.core.parser import ISO8583Parser

pool = MessagePool(size=100)
parser = ISO8583Parser(pool=pool)

message = parser.parse(raw)
# ... use message ...
pool.release(message)
```

### Context Manager

```python
with pool.acquire() as message:
    # Configure message
    message.mti = "0100"
    message.fields[2] = "4111111111111111"
    # ... build/process ...
# Automatically released when exiting context
```

### Batch Processing

```python
pool = MessagePool(size=1000)
parser = ISO8583Parser(pool=pool)

results = []
for raw in batch:
    msg = parser.parse(raw)
    results.append(process(msg))
    pool.release(msg)
```

### Thread Safety

The pool is thread-safe for concurrent access:

```python
import concurrent.futures

pool = MessagePool(size=1000)
parser = ISO8583Parser(pool=pool)

def process_message(raw):
    msg = parser.parse(raw)
    result = process(msg)
    pool.release(msg)
    return result

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_message, raw_messages))
```

## Pool Sizing

Choose pool size based on:

1. **Concurrency level**: Number of messages processed simultaneously
2. **Message retention**: How long messages are held before release
3. **Memory constraints**: Each message ~1KB

**Rule of thumb**: `pool_size = concurrent_workers * 2`

```python
# Single-threaded processing
pool = MessagePool(size=10)

# Multi-threaded (4 workers)
pool = MessagePool(size=100)

# High-throughput server
pool = MessagePool(size=1000)
```

## Pool Exhaustion

When pool is exhausted, new objects are created (no blocking):

```python
pool = MessagePool(size=10)

# Acquire 15 messages
messages = []
for _ in range(15):
    msg = pool.acquire()
    messages.append(msg)

# First 10 from pool, next 5 created new
# Pool automatically expands
```

## Monitoring

```python
pool = MessagePool(size=100)

print(f"Pool size: {pool.size}")
print(f"Available: {pool.available}")
print(f"In use: {pool.in_use}")
```

## Best Practices

### Do

```python
# Always release messages when done
message = parser.parse(raw)
try:
    process(message)
finally:
    pool.release(message)

# Use context manager for automatic release
with pool.acquire() as message:
    process(message)
```

### Don't

```python
# Don't hold references after release
message = parser.parse(raw)
pool.release(message)
print(message.mti)  # Bad! Message may be reused

# Don't release twice
pool.release(message)
pool.release(message)  # Error or undefined behavior
```

## When to Use

**Use pooling when:**
- Processing > 10k messages per second
- Memory pressure is a concern
- GC pauses are noticeable

**Skip pooling when:**
- Processing < 1k messages per second
- Messages need long-term storage
- Simplicity is preferred

## API Reference

See [Core API Reference](../api/core.md#iso8583simcorepool) for complete API documentation.
