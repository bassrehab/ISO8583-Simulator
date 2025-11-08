# ISO8583 Simulator - Performance Benchmarks

**Date:** 2025-11-01 (v0.3.0 optimizations)
**System:** macOS 15.7.2 arm64, Python 3.12.6, Apple Silicon

## Summary

| Operation | v0.2.0 TPS | v0.3.0 TPS | Improvement |
|-----------|------------|------------|-------------|
| Parse (basic) | ~95,000 | ~105,000 | +10% |
| Parse (VISA) | ~64,000 | ~75,000 | +17% |
| Parse (EMV) | ~104,000 | ~113,000 | +9% |
| Build | ~143,000 | ~150,000 | +5% |
| Build + Validate | ~106,000 | ~116,000 | +9% |
| Roundtrip (full) | ~45,000 | ~49,000 | +10% |
| Roundtrip (no validate) | ~54,000 | ~58,000 | +7% |
| Request/Response | ~25,000 | ~27,000 | +7% |

## Optimizations Applied (v0.3.0)

1. **Field definition caching** - `@lru_cache(maxsize=512)` on `get_field_definition()`
2. **Pre-compiled regex patterns** - Module-level compiled patterns for hex validation
3. **Optimized bitmap parsing** - Direct integer bit manipulation instead of string operations

## Detailed Results (v0.3.0)

### Parser Benchmarks

```
--- Batch size: 10,000 messages ---
Basic messages:     104,608 TPS (min: 90,815, max: 110,581)
VISA messages:       74,979 TPS (min: 70,357, max: 78,584)
EMV messages:       113,318 TPS (min: 108,125, max: 114,726)
```

### Builder Benchmarks

```
--- Batch size: 10,000 messages ---
build():             150,107 TPS (min: 146,798, max: 151,702)
create_message():    115,629 TPS (min: 113,990, max: 116,608)
```

### Roundtrip Benchmarks

```
--- Batch size: 10,000 messages ---
Build->Parse->Validate:   49,163 TPS (min: 47,115, max: 49,820)
Build->Parse only:        57,659 TPS (min: 54,004, max: 59,554)
Request->Response flow:   26,981 TPS (min: 26,866, max: 27,099)
```

## Targets vs Actual

| Target | v0.2.0 | v0.3.0 | Status |
|--------|--------|--------|--------|
| 100k TPS generation | 143k | 150k | ✅ Exceeded |
| 50k TPS processing | 45k | 49k | 🟡 98% of target |

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
