# Quick Start

This guide will get you parsing and building ISO 8583 messages in under 5 minutes.

## Building Your First Message

```python
from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.types import ISO8583Message

# Create a builder
builder = ISO8583Builder()

# Define a message
message = ISO8583Message(
    mti="0100",  # Authorization request
    fields={
        0: "0100",                    # MTI
        2: "4111111111111111",        # PAN (Primary Account Number)
        3: "000000",                  # Processing Code (purchase)
        4: "000000001000",            # Amount ($10.00)
        11: "123456",                 # STAN (System Trace Audit Number)
        41: "TERM0001",               # Terminal ID
        42: "MERCHANT123456 ",        # Merchant ID
    }
)

# Build the raw message
raw_message = builder.build(message)
print(f"Raw message: {raw_message}")
```

## Parsing a Message

```python
from iso8583sim.core.parser import ISO8583Parser

parser = ISO8583Parser()

# Parse the raw message
parsed = parser.parse(raw_message)

print(f"MTI: {parsed.mti}")
print(f"PAN: {parsed.fields.get(2)}")
print(f"Amount: {parsed.fields.get(4)}")
```

## Validating a Message

```python
from iso8583sim.core.validator import ISO8583Validator

validator = ISO8583Validator()

# Validate the message
errors = validator.validate_message(parsed)

if errors:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Message is valid!")
```

## Using Demo Helpers

The `demo` module provides convenient functions for generating test messages:

```python
from iso8583sim.demo import generate_auth_request, pretty_print

# Generate an authorization request
auth_msg = generate_auth_request(
    pan="4111111111111111",
    amount=10000,  # $100.00 in cents
    terminal_id="TERM0001",
    merchant_id="GASSTATION12345",
)

# Pretty print the message
pretty_print(auth_msg)
```

## EMV/Chip Card Messages

```python
from iso8583sim.demo import generate_emv_auth

# Generate an EMV authorization
emv_msg = generate_emv_auth(
    pan="4111111111111111",
    amount=25000,  # $250.00
    cryptogram="1234567890ABCDEF",
)

pretty_print(emv_msg)
```

## CLI Usage

Parse a message from the command line:

```bash
iso8583sim parse "0100702406C120E09000..."
```

Build a message:

```bash
iso8583sim build --mti 0100 --fields fields.json
```

Validate a message:

```bash
iso8583sim validate "0100702406C120E09000..."
```

## LLM Features

Explain a message in plain English:

```python
from iso8583sim.llm import MessageExplainer

explainer = MessageExplainer()
explanation = explainer.explain(parsed)
print(explanation)
```

Generate a message from natural language:

```python
from iso8583sim.llm import MessageGenerator

generator = MessageGenerator()
message = generator.generate("$50 VISA purchase at a coffee shop")
```

## Next Steps

- [ISO 8583 Concepts](concepts.md) - Learn about MTI, bitmaps, and fields
- [Parser Guide](../core/parser.md) - Deep dive into parsing
- [Builder Guide](../core/builder.md) - Advanced message building
- [Network Support](../networks/index.md) - VISA, Mastercard, and more
