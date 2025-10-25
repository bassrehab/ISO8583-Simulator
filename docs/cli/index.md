# CLI Reference

iso8583sim provides a command-line interface for parsing, building, and validating ISO 8583 messages.

## Installation

The CLI is included with iso8583sim:

```bash
pip install iso8583sim
```

## Basic Usage

```bash
# Get help
iso8583sim --help

# Parse a message
iso8583sim parse "0100702406C120E09000..."

# Build a message
iso8583sim build --mti 0100 --fields fields.json

# Validate a message
iso8583sim validate "0100702406C120E09000..."

# Generate sample messages
iso8583sim generate --type auth --pan 4111111111111111
```

## Commands

### parse

Parse a raw ISO 8583 message and display its contents.

```bash
iso8583sim parse MESSAGE [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `MESSAGE` | Raw ISO 8583 message as hex string |

**Options:**

| Option | Description |
|--------|-------------|
| `--version` | ISO 8583 version (1987, 1993, 2003) |
| `--network` | Card network (visa, mastercard, amex, etc.) |
| `--format` | Output format (table, json, raw) |
| `--verbose` | Show detailed field information |

**Examples:**

```bash
# Basic parsing
iso8583sim parse "0100702406C120E09000..."

# With version specification
iso8583sim parse "0100..." --version 1993

# JSON output
iso8583sim parse "0100..." --format json

# Verbose output with field descriptions
iso8583sim parse "0100..." --verbose
```

### build

Build an ISO 8583 message from field values.

```bash
iso8583sim build [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--mti` | Message Type Indicator (required) |
| `--fields` | JSON file with field values |
| `--field` | Individual field (can be repeated): `--field 2=4111111111111111` |
| `--version` | ISO 8583 version |
| `--output` | Output file (default: stdout) |

**Examples:**

```bash
# Build from JSON file
iso8583sim build --mti 0100 --fields fields.json

# Build with inline fields
iso8583sim build --mti 0100 \
    --field 2=4111111111111111 \
    --field 3=000000 \
    --field 4=000000010000

# Save to file
iso8583sim build --mti 0100 --fields fields.json --output message.hex
```

**fields.json format:**

```json
{
    "2": "4111111111111111",
    "3": "000000",
    "4": "000000010000",
    "11": "123456",
    "41": "TERM0001",
    "42": "MERCHANT123456 "
}
```

### validate

Validate an ISO 8583 message for structure and content.

```bash
iso8583sim validate MESSAGE [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--network` | Validate against network requirements |
| `--strict` | Enable strict validation mode |

**Examples:**

```bash
# Basic validation
iso8583sim validate "0100..."

# With network validation
iso8583sim validate "0100..." --network visa

# Strict mode
iso8583sim validate "0100..." --strict
```

**Output:**

```
Validation Results:
  Message is VALID

  Fields validated: 7
  Network: VISA (auto-detected)

Or with errors:

Validation Results:
  Message is INVALID

  Errors:
    - Field 4 must contain only digits
    - Missing required field: 11
```

### generate

Generate sample ISO 8583 messages.

```bash
iso8583sim generate [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--type` | Message type (auth, financial, reversal) |
| `--pan` | Primary Account Number |
| `--amount` | Transaction amount (in cents) |
| `--count` | Number of messages to generate |
| `--output` | Output file |

**Examples:**

```bash
# Generate authorization request
iso8583sim generate --type auth --pan 4111111111111111 --amount 10000

# Generate multiple messages
iso8583sim generate --type auth --count 10

# Save to file
iso8583sim generate --type auth --output messages.txt
```

## Output Formats

### Table (default)

```
┌─────────┬───────────────────────────┬────────────────────────┐
│ Field   │ Value                     │ Description            │
├─────────┼───────────────────────────┼────────────────────────┤
│ MTI     │ 0100                      │ Authorization Request  │
│ 2       │ 4111111111111111          │ Primary Account Number │
│ 3       │ 000000                    │ Processing Code        │
│ 4       │ 000000010000              │ Amount                 │
└─────────┴───────────────────────────┴────────────────────────┘
```

### JSON

```bash
iso8583sim parse "0100..." --format json
```

```json
{
    "mti": "0100",
    "bitmap": "7024058020C09000",
    "fields": {
        "2": "4111111111111111",
        "3": "000000",
        "4": "000000010000"
    },
    "network": "VISA"
}
```

### Raw

```bash
iso8583sim parse "0100..." --format raw
```

```
0100
7024058020C09000
2: 4111111111111111
3: 000000
4: 000000010000
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Parse error |
| 2 | Validation error |
| 3 | Build error |
| 4 | File not found |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ISO8583SIM_VERSION` | Default ISO 8583 version |
| `ISO8583SIM_NETWORK` | Default card network |
| `ANTHROPIC_API_KEY` | For LLM features |
| `OPENAI_API_KEY` | For LLM features |

## Piping and Scripting

```bash
# Pipe messages
cat messages.txt | while read line; do
    iso8583sim parse "$line" --format json
done

# Parse from file
iso8583sim parse "$(cat message.hex)"

# Build and parse roundtrip
iso8583sim build --mti 0100 --fields fields.json | iso8583sim parse -
```

## Troubleshooting

### Common Issues

**"Command not found":**
```bash
# Ensure iso8583sim is in PATH
pip show iso8583sim  # Check installation
python -m iso8583sim.cli --help  # Alternative invocation
```

**"Invalid hex string":**
```bash
# Ensure message contains only hex characters (0-9, A-F)
# Remove any spaces or newlines
```

**"Parse error: Invalid bitmap":**
```bash
# Check that bitmap is 16 hex characters
# Primary bitmap must be exactly 8 bytes (16 hex chars)
```
