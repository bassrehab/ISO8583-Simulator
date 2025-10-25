# Troubleshooting

Common issues and solutions when using iso8583sim.

## Installation Issues

### "Module not found: iso8583sim"

**Problem:** Python cannot find the iso8583sim module.

**Solutions:**

1. Verify installation:
   ```bash
   pip show iso8583sim
   ```

2. Check you're in the right virtual environment:
   ```bash
   which python
   pip list | grep iso8583sim
   ```

3. Reinstall:
   ```bash
   pip uninstall iso8583sim
   pip install iso8583sim
   ```

### Cython compilation fails

**Problem:** `python setup.py build_ext --inplace` fails.

**Solutions:**

1. Ensure Cython is installed:
   ```bash
   pip install cython>=3.0.0
   ```

2. Check you have a C compiler:
   - **macOS:** `xcode-select --install`
   - **Linux:** `apt install build-essential`
   - **Windows:** Install Visual Studio Build Tools

3. The library works without Cython - it falls back to pure Python automatically.

### LLM provider not available

**Problem:** `ProviderNotAvailableError: anthropic provider package is not installed`

**Solutions:**

1. Install the provider:
   ```bash
   pip install iso8583sim[anthropic]
   # or
   pip install anthropic>=0.40.0
   ```

2. Check what's installed:
   ```python
   from iso8583sim.llm import list_installed_providers
   print(list_installed_providers())
   ```

### LLM provider not configured

**Problem:** `ProviderConfigError: Anthropic API key not found`

**Solutions:**

1. Set the environment variable:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

2. Pass API key directly:
   ```python
   from iso8583sim.llm.providers.anthropic import AnthropicProvider
   provider = AnthropicProvider(api_key="sk-ant-...")
   ```

3. Check what's configured:
   ```python
   from iso8583sim.llm import list_available_providers
   print(list_available_providers())
   ```

## Parsing Issues

### ParseError: Invalid bitmap

**Problem:** `ParseError: Invalid bitmap format`

**Causes:**
- Bitmap is not exactly 16 hex characters
- Contains non-hex characters
- Message is truncated

**Solution:**
```python
# Bitmap must be exactly 16 hex characters (8 bytes)
# Example valid bitmap: "7024058020C09000"

# Check your message structure:
message = "0100702406C120E09000..."
#          ^^^^                   = MTI (4 chars)
#              ^^^^^^^^^^^^^^^^   = Bitmap (16 chars)
#                              ^^ = Field data starts here
```

### ParseError: Field length exceeds maximum

**Problem:** A field value is longer than allowed.

**Solution:**
```python
# Check field definition
from iso8583sim.core.types import get_field_definition

field_def = get_field_definition(2)
print(f"Field 2 max length: {field_def.max_length}")

# For LLVAR fields, check the length prefix
# "164111111111111111" = 16 chars, value is 16 chars
# "204111111111111111" = 20 chars, but value is only 18 chars - MISMATCH
```

### ParseError: Unknown field

**Problem:** Parsing fails on a network-specific field.

**Solution:**
```python
# Specify the network when parsing
from iso8583sim.core.types import CardNetwork

parser = ISO8583Parser()
message = parser.parse(raw, network=CardNetwork.VISA)
```

## Building Issues

### BuildError: Validation failed

**Problem:** Message doesn't pass validation during build.

**Solution:**
```python
# Check what's wrong before building
from iso8583sim.core.validator import ISO8583Validator

validator = ISO8583Validator()
errors = validator.validate_message(message)
for error in errors:
    print(error)

# Fix the issues, then build
```

### BuildError: Unknown field definition

**Problem:** Building fails because field isn't recognized.

**Solution:**
```python
# Check field exists
from iso8583sim.core.types import ISO8583_FIELDS

if field_number not in ISO8583_FIELDS:
    print(f"Field {field_number} is not a standard ISO 8583 field")

# For network-specific fields, set the network
message.network = CardNetwork.VISA
```

### Field padding incorrect

**Problem:** Field values aren't padded correctly.

**Solution:**
```python
# The builder handles padding automatically
# But you can check field definitions:

from iso8583sim.core.types import get_field_definition

field_def = get_field_definition(4)  # Amount
print(f"Type: {field_def.field_type}")
print(f"Length: {field_def.max_length}")
print(f"Padding: {field_def.padding_char} ({field_def.padding_direction})")

# Field 4 (Amount): 12 digits, left-padded with zeros
# "1000" becomes "000000001000"
```

## Validation Issues

### PAN fails Luhn check

**Problem:** `Field 2 (PAN) failed Luhn check`

**Solution:**
```python
# Use a valid test PAN
# These are valid Luhn-check PANs for testing:
VALID_TEST_PANS = {
    "VISA": "4111111111111111",
    "Mastercard": "5500000000000004",
    "AMEX": "378282246310005",
    "Discover": "6011111111111117",
}
```

### Missing required field

**Problem:** `Missing required field: 22`

**Solution:**
```python
# Different networks require different fields
# Check requirements for your network:

from iso8583sim.core.validator import ISO8583Validator

validator = ISO8583Validator()
required = validator.network_required_fields.get(CardNetwork.VISA, [])
print(f"VISA requires: {required}")

# Add missing fields to your message
message.fields[22] = "051"  # POS Entry Mode
```

## LLM Issues

### LLMError: API rate limit

**Problem:** `LLMError: Rate limit exceeded`

**Solution:**
```python
import time

# Add delay between requests
for message in messages:
    try:
        explanation = explainer.explain(message)
    except LLMError:
        time.sleep(1)  # Wait and retry
        explanation = explainer.explain(message)
```

### Generated message invalid

**Problem:** LLM generates an invalid message.

**Solution:**
```python
# Always validate generated messages
message = generator.generate(description, validate=False)

# Then validate manually
errors = validator.validate_message(message)
if errors:
    print("LLM generated invalid message:")
    for error in errors:
        print(f"  - {error}")
```

## Performance Issues

### Slow parsing

**Problem:** Parsing is slower than expected.

**Solutions:**

1. Install Cython extensions:
   ```bash
   pip install iso8583sim[perf]
   python setup.py build_ext --inplace
   ```

2. Reuse parser instances:
   ```python
   # Good
   parser = ISO8583Parser()
   for msg in messages:
       result = parser.parse(msg)

   # Bad
   for msg in messages:
       result = ISO8583Parser().parse(msg)
   ```

3. Disable debug logging:
   ```python
   import logging
   logging.getLogger('iso8583sim').setLevel(logging.WARNING)
   ```

### Memory usage high

**Problem:** Memory grows with message volume.

**Solution:**
```python
# Use object pooling
from iso8583sim.core.pool import MessagePool

pool = MessagePool(size=1000)
parser = ISO8583Parser(pool=pool)

for raw in messages:
    msg = parser.parse(raw)
    process(msg)
    pool.release(msg)  # Return to pool
```

## Getting Help

If you can't resolve an issue:

1. Check the [API Reference](api/core.md) for correct usage
2. Search [GitHub Issues](https://github.com/bassrehab/ISO8583-Simulator/issues)
3. Open a new issue with:
   - Python version (`python --version`)
   - iso8583sim version (`pip show iso8583sim`)
   - Minimal code to reproduce
   - Full error traceback
