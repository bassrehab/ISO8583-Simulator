# ISO8583 Simulator - Performance Benchmarks

**Date:** 2025-11-01 (v0.3.0 optimizations + Cython)
**System:** macOS 15.7.2 arm64, Python 3.12.6, Apple Silicon

## Summary

| Operation | v0.2.0 TPS | v0.3.0 TPS | v0.3.0+Cython | Total Improvement |
|-----------|------------|------------|---------------|-------------------|
| Parse (basic) | ~95,000 | ~105,000 | ~182,000 | +91% |
| Parse (VISA) | ~64,000 | ~75,000 | ~121,000 | +89% |
| Parse (EMV) | ~104,000 | ~113,000 | ~197,000 | +89% |
| Build | ~143,000 | ~150,000 | ~150,000 | +5% |
| Build + Validate | ~106,000 | ~116,000 | ~116,000 | +9% |
| Roundtrip (full) | ~45,000 | ~49,000 | ~65,000 | +44% |
| Roundtrip (no validate) | ~54,000 | ~58,000 | ~81,000 | +50% |
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

## Detailed Results (v0.3.0 + Cython)

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
Build->Parse->Validate:   64,994 TPS (min: 63,751, max: 65,459)
Build->Parse only:        81,089 TPS (min: 80,475, max: 81,894)
Request->Response flow:   32,122 TPS (min: 31,684, max: 32,383)
```

## Targets vs Actual

| Target | v0.2.0 | v0.3.0 | v0.3.0+Cython | Status |
|--------|--------|--------|---------------|--------|
| 100k TPS generation | 143k | 150k | 150k | ✅ Exceeded |
| 100k TPS parsing | 95k | 105k | 182k | ✅ Exceeded |
| 100k TPS roundtrip | 45k | 49k | 65k | 🟡 65% of target |

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
