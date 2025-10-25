# Message Generator

The `MessageGenerator` class uses LLMs to create ISO 8583 messages from natural language descriptions.

## Quick Start

```python
from iso8583sim.llm import MessageGenerator

generator = MessageGenerator()

# Generate from natural language
message = generator.generate("$50 VISA purchase at a coffee shop")

print(f"MTI: {message.mti}")
print(f"PAN: {message.fields.get(2)}")
print(f"Amount: {message.fields.get(4)}")
```

## Generating Messages

### Simple Purchase

```python
message = generator.generate("$100 purchase with Mastercard")

# Result:
# MTI: 0100
# Field 2: 5500000000000004
# Field 3: 000000
# Field 4: 000000010000
```

### Specific Scenarios

```python
# ATM withdrawal
message = generator.generate("$200 ATM cash withdrawal with VISA card")

# Refund
message = generator.generate("Refund $25 to card ending in 4444")

# Balance inquiry
message = generator.generate("Balance inquiry at ATM for debit card")

# International transaction
message = generator.generate("$500 purchase in EUR at a Paris hotel")
```

### With Validation

By default, generated messages are validated:

```python
# With validation (default)
message = generator.generate("$50 purchase", validate=True)

# Skip validation (faster, for testing)
message = generator.generate("$50 purchase", validate=False)
```

## Suggesting Missing Fields

Complete a partial message:

```python
from iso8583sim.core.types import ISO8583Message

# Create partial message
partial = ISO8583Message(
    mti="0100",
    fields={
        0: "0100",
        2: "4111111111111111",
        4: "000000010000",
    }
)

# Get suggestions for missing fields
suggestions = generator.suggest_fields(partial)

print("Suggested fields:")
for field_num, value in suggestions.items():
    print(f"  Field {field_num}: {value}")
```

Output:
```
Suggested fields:
  Field 3: 000000
  Field 7: 1225120000
  Field 11: 123456
  Field 14: 2512
  Field 22: 051
  Field 41: TERM0001
  Field 42: MERCHANT123456
```

## Generation Examples

### Authorization Request

```python
message = generator.generate(
    "Authorization request for $250 EMV chip transaction at gas station, "
    "VISA card ending in 1234"
)
```

### Financial Transaction

```python
message = generator.generate(
    "Financial transaction (0200) for $75.50 at retail store, "
    "contactless Mastercard payment"
)
```

### Reversal

```python
message = generator.generate(
    "Reversal for failed $100 transaction, original STAN 123456"
)
```

### Response Message

```python
message = generator.generate(
    "Approval response for authorization request, "
    "response code 00, auth code A12345"
)
```

## Custom Provider

```python
from iso8583sim.llm import MessageGenerator, get_provider

# Use a specific provider
provider = get_provider("openai")
generator = MessageGenerator(provider=provider)

# Use a specific model for faster generation
from iso8583sim.llm.providers.anthropic import AnthropicProvider
provider = AnthropicProvider(model="claude-3-haiku-20240307")
generator = MessageGenerator(provider=provider)
```

## Test Data Generation

Generate test datasets:

```python
from iso8583sim.llm import MessageGenerator
from iso8583sim.core.builder import ISO8583Builder

generator = MessageGenerator()
builder = ISO8583Builder()

scenarios = [
    "$100 VISA purchase at retail store",
    "$50 Mastercard at restaurant with tip",
    "$200 ATM withdrawal",
    "Declined transaction, insufficient funds",
    "EMV chip transaction at gas pump",
]

test_messages = []
for scenario in scenarios:
    try:
        message = generator.generate(scenario, validate=False)
        raw = builder.build(message)
        test_messages.append({
            "scenario": scenario,
            "message": message,
            "raw": raw,
        })
    except Exception as e:
        print(f"Failed to generate '{scenario}': {e}")
```

## Guidance for Better Results

Provide specific details for better generation:

```python
# Less specific - may generate generic values
message = generator.generate("A purchase")

# More specific - generates accurate message
message = generator.generate(
    "$150.00 purchase at electronics store, "
    "VISA chip card (no PIN), "
    "terminal ID ELEC0001, "
    "merchant ID BESTBUY123456"
)
```

### Helpful Details to Include

- Transaction amount and currency
- Card network (VISA, Mastercard, etc.)
- Card entry mode (chip, swipe, contactless, manual)
- Transaction type (purchase, refund, withdrawal)
- Merchant type or name
- Terminal and merchant IDs

## Error Handling

```python
from iso8583sim.llm import MessageGenerator, LLMError
from iso8583sim.core.types import BuildError

generator = MessageGenerator()

try:
    message = generator.generate(description)
except LLMError as e:
    print(f"LLM error: {e}")
except BuildError as e:
    print(f"Generated message failed validation: {e}")
```

## Limitations

- Generated messages may not pass all network-specific validations
- Complex multi-message scenarios may need manual adjustment
- Generated PANs are test numbers, not real card numbers
- Some network-specific fields may be missing

## API Reference

See [LLM API Reference](../api/llm.md#iso8583simllmgenerator) for complete API documentation.
