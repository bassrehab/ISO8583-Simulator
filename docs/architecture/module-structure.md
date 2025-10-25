# Module Structure

This document describes the package organization and module responsibilities.

## Package Overview

```
iso8583sim/
├── __init__.py                 # Package root (minimal)
├── core/                       # Core message handling
├── llm/                        # LLM-powered features
├── cli/                        # Command-line interface
├── web/                        # REST API (placeholder)
└── demo.py                     # Interactive demo helpers
```

## Core Module (`iso8583sim.core`)

The core module handles ISO 8583 message parsing, building, and validation.

### types.py

Central type definitions and field specifications.

**Classes:**
- `ISO8583Version` - Protocol version enum (1987, 1993, 2003)
- `FieldType` - Field data type enum (NUMERIC, ALPHA, LLVAR, etc.)
- `CardNetwork` - Card network enum (VISA, MASTERCARD, etc.)
- `MessageClass` - Message class enum (AUTHORIZATION, FINANCIAL, etc.)
- `MessageFunction` - Message function enum (REQUEST, RESPONSE, etc.)
- `FieldDefinition` - Field metadata dataclass
- `ISO8583Message` - Message data structure
- `ParseError` / `BuildError` - Exception types

**Data:**
- `ISO8583_FIELDS` - Standard ISO 8583 field definitions (128 fields)
- `NETWORK_SPECIFIC_FIELDS` - Network-specific field overrides
- `VERSION_SPECIFIC_FIELDS` - Version-specific field overrides

**Functions:**
- `get_field_definition()` - Get field definition with network/version overrides
- `detect_network()` - Identify card network from PAN

### parser.py

Message parsing from raw string to `ISO8583Message`.

**Classes:**
- `ISO8583Parser` - Main parser class
- `EMVTag` - EMV tag data structure

**Key Methods:**
- `parse(message, network=None)` - Parse raw message string
- `_parse_mti()` - Extract Message Type Indicator
- `_parse_bitmap()` - Parse primary/secondary bitmaps
- `_parse_fields()` - Parse individual fields

### builder.py

Message building from `ISO8583Message` to raw string.

**Classes:**
- `ISO8583Builder` - Main builder class

**Key Methods:**
- `build(message)` - Build raw message string
- `_format_field_value()` - Format field with padding
- `_build_bitmap()` - Generate bitmap from fields
- `_build_field()` - Build field with length prefix

### validator.py

Message validation with network-specific rules.

**Classes:**
- `ISO8583Validator` - Main validator class

**Key Methods:**
- `validate_message(message)` - Full message validation
- `validate_field(field_number, value, field_def)` - Single field validation
- `_validate_pan_luhn()` - PAN Luhn checksum validation
- `_validate_visa_specific()` - VISA-specific rules
- `_validate_mastercard_specific()` - Mastercard-specific rules

### emv.py

EMV/ICC chip card data handling.

**Functions:**
- `parse_emv_data(data)` - Parse Field 55 TLV data
- `build_emv_data(tags)` - Build Field 55 from tags
- `format_emv_tag()` - Format EMV tag for display

### pool.py

Object pooling for high-throughput scenarios.

**Classes:**
- `MessagePool` - Reusable message object pool

**Key Methods:**
- `acquire()` - Get message from pool
- `release(message)` - Return message to pool

## LLM Module (`iso8583sim.llm`)

AI-powered message explanation and generation.

### base.py

Provider interface and exceptions.

**Classes:**
- `LLMProvider` - Abstract base class for providers
- `LLMResponse` - Response with metadata dataclass
- `LLMError` - Base LLM exception
- `ProviderConfigError` - Configuration error
- `ProviderNotAvailableError` - Missing provider/package

### explainer.py

Message explanation using LLMs.

**Classes:**
- `MessageExplainer` - Explain messages in plain English

**Key Methods:**
- `explain(message, verbose=False)` - Explain a message
- `explain_field(field_number, value)` - Explain a single field
- `explain_response_code(code)` - Explain response code

### generator.py

Message generation from natural language.

**Classes:**
- `MessageGenerator` - Generate messages from descriptions

**Key Methods:**
- `generate(description, validate=True)` - Generate message
- `suggest_fields(partial_message)` - Suggest missing fields

### providers/

LLM provider implementations.

**Files:**
- `__init__.py` - Provider factory and auto-detection
- `anthropic.py` - Anthropic (Claude) provider
- `openai.py` - OpenAI (GPT) provider
- `google.py` - Google (Gemini) provider
- `ollama.py` - Ollama (local) provider

**Key Functions:**
- `get_provider(name=None)` - Get provider instance
- `list_available_providers()` - List configured providers
- `list_installed_providers()` - List installed providers

## CLI Module (`iso8583sim.cli`)

Command-line interface using Click.

### commands.py

CLI command implementations.

**Commands:**
- `parse` - Parse a raw ISO 8583 message
- `build` - Build a message from fields
- `validate` - Validate a message
- `generate` - Generate sample messages

## Demo Module (`iso8583sim.demo`)

Interactive helpers for notebooks and exploration.

**Functions:**
- `generate_auth_request()` - Generate authorization request
- `generate_emv_auth()` - Generate EMV authorization
- `pretty_print()` - Format message for display

## Cython Extensions

Optional compiled extensions for performance.

**Files:**
- `core/_parser_fast.pyx` - Fast parsing functions
- `core/_bitmap.pyx` - Fast bitmap operations
- `core/_validator_fast.pyx` - Fast validation functions

**Detection:**
```python
try:
    from ._parser_fast import parse_mti_fast
    _USE_CYTHON = True
except ImportError:
    _USE_CYTHON = False
```

## Import Patterns

### Basic Usage
```python
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.types import ISO8583Message
```

### With Validation
```python
from iso8583sim.core.validator import ISO8583Validator
from iso8583sim.core.types import CardNetwork
```

### With LLM Features
```python
from iso8583sim.llm import MessageExplainer, MessageGenerator
from iso8583sim.llm import get_provider, list_available_providers
```

### Demo/Interactive
```python
from iso8583sim.demo import generate_auth_request, pretty_print
```
