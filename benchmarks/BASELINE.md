# ISO8583 Simulator - Performance Benchmarks

**Date:** 2025-11-02 (v0.3.0 final)
**System:** macOS 15.7.2 arm64, Python 3.12.6, Apple Silicon

## Summary

| Operation | v0.2.0 TPS | v0.3.0 TPS | v0.3.0+Cython | Total Improvement |
|-----------|------------|------------|---------------|-------------------|
| Parse (basic) | ~95,000 | ~105,000 | ~182,000 | +91% |
| Parse (VISA) | ~64,000 | ~75,000 | ~121,000 | +89% |
| Parse (EMV) | ~104,000 | ~113,000 | ~197,000 | +89% |
| Build | ~143,000 | ~150,000 | ~150,000 | +5% |
| Roundtrip (full) | ~45,000 | ~49,000 | ~63,000 | +40% |
| Roundtrip (no validate) | ~54,000 | ~58,000 | ~78,000 | +44% |
| Pooled roundtrip | - | - | ~63,000 | N/A |
| Request/Response | ~25,000 | ~27,000 | ~32,000 | +28% |

## Optimizations Applied (v0.3.0)

### Phase 1: Pure Python Optimizations
1. **Field definition caching** - `@lru_cache(maxsize=512)` on `get_field_definition()`
2. **Pre-compiled regex patterns** - Module-level compiled patterns for hex validation
3. **Optimized bitmap parsing** - Direct integer bit manipulation instead of string operations
4. **Lazy logging** - Use `%s` formatting instead of f-strings for deferred evaluation
5. **`__slots__`** - Added to dataclasses for memory efficiency (Python 3.10+)
6. **Dict lookup caching** - Cache network/version field dicts at parse time

### Phase 2: Cython Compilation
7. **Compiled bitmap parsing** - `_bitmap.pyx` with optimized bit manipulation
8. **Compiled field parsing** - `_parser_fast.pyx` with C-level string operations
9. **Compiled validation** - `_validator_fast.pyx` with Luhn algorithm and string checks

### Phase 3: Object Pooling
10. **MessagePool** - Thread-safe object pool for high-throughput scenarios

## Detailed Results (v0.3.0 Final)

### Parser Benchmarks

```
--- Batch size: 10,000 messages ---
Basic messages:     181,918 TPS (min: 175,627, max: 185,688)
VISA messages:      121,374 TPS (min: 120,517, max: 121,828)
EMV messages:       196,828 TPS (min: 190,087, max: 200,059)
```

### Roundtrip Benchmarks

```
--- Batch size: 10,000 messages ---
Build->Parse->Validate:   62,752 TPS (min: 61,159, max: 63,774)
Build->Parse only:        78,376 TPS (min: 76,552, max: 79,410)
Pooled (with validate):   62,858 TPS (min: 62,184, max: 63,536)
Request->Response flow:   31,493 TPS (min: 31,126, max: 31,819)
```

## Targets vs Actual

| Target | v0.2.0 | v0.3.0 | v0.3.0+Cython | Status |
|--------|--------|--------|---------------|--------|
| 100k TPS generation | 143k | 150k | 150k | ✅ Exceeded |
| 100k TPS parsing | 95k | 105k | 182k | ✅ Exceeded |
| 100k TPS roundtrip | 45k | 49k | 63k | 🟡 63% of target |

## Notes on Object Pooling

Object pooling shows minimal improvement in benchmarks because:
- Python's memory allocator is already efficient for small objects
- The `slots=True` dataclasses have very low allocation overhead
- Pool lock contention can offset allocation savings

Pooling is most beneficial for:
- Long-running applications processing millions of messages
- Scenarios where memory fragmentation is a concern
- Applications that can explicitly manage message lifecycle

See [docs/performance.md](../docs/performance.md) for detailed usage guidance.

## Previous Baseline (v0.2.0)

```
--- Batch size: 10,000 messages ---
Basic messages:      95,442 TPS
VISA messages:       64,278 TPS
EMV messages:       104,278 TPS
build():            143,033 TPS
create_message():   105,781 TPS
Build->Parse->Validate:   44,548 TPS
Build->Parse only:        54,018 TPS
Request->Response flow:   25,264 TPS
```

## Future Optimization Opportunities

1. **Lazy logging** - Check log level before formatting strings
2. **`__slots__`** - Add to dataclasses for memory efficiency (requires Python 3.10+)
3. **memoryview** - Zero-copy parsing for large messages
4. **Cython** - Compile hot paths for 2-5x additional speedup
