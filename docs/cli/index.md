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
| `--network`, `-n` | Validate against one network's requirements |
| `--against`, `-a` | Check against several networks: comma separated names, or `all` |
| `--version`, `-v` | ISO 8583 version (1987, 1993, 2003) |

**Examples:**

```bash
# Basic validation
iso8583sim validate "0100..."

# With network validation
iso8583sim validate "0100..." --network visa

# Which networks would accept this message?
iso8583sim validate "0100..." --against all
```

**Output (`--against all`):**

```
                       Network Compliance
┏━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Network    ┃ Result ┃ Issues                                 ┃
┡━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ VISA       │ PASS   │ -                                      │
│ MASTERCARD │ PASS   │ -                                      │
│ UNIONPAY   │ FAIL   │ Required field 49 missing for UNIONPAY │
└────────────┴────────┴────────────────────────────────────────┘
```

The command exits with status 1 when any check fails.

### convert

Convert a message to another ISO 8583 version.

```bash
iso8583sim convert MESSAGE --to VERSION [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--to`, `-t` | Target version (1987, 1993, 2003) |
| `--from`, `-f` | Version of the input message (default 1987) |
| `--network`, `-n` | Card network. Network rules are only enforced on the output when this is given |
| `--output`, `-o` | Output file |

**Example:**

```bash
iso8583sim convert "0400..." --to 2003
```

The output shows the converted message, notes about fields whose meaning differs between versions, and any fields that had to be dropped. See [Version Conversion](../core/convert.md) for the rules.

### explain

Explain a message in plain English.

```bash
iso8583sim explain MESSAGE [OPTIONS]
```

By default the explanation comes from an LLM (see [LLM Features](../llm/index.md) for provider setup). With `--no-llm` you get a rule-based summary instead, which works offline and needs no API key.

**Options:**

| Option | Description |
|--------|-------------|
| `--no-llm` | Rule-based summary, no LLM or API key needed |
| `--provider`, `-p` | LLM provider: `anthropic`, `openai`, `google` or `ollama`. Auto-detected if omitted |
| `--model`, `-m` | Model name for the provider |
| `--verbose` | Ask the LLM for more technical detail |
| `--version`, `-v` | ISO 8583 version (1987, 1993, 2003) |
| `--network`, `-n` | Card network (detected from the PAN if omitted) |

**Examples:**

```bash
# Explain with the first configured LLM provider
iso8583sim explain "0100..."

# Use a specific provider and model
iso8583sim explain "0100..." --provider ollama --model qwen3

# Offline, rule-based summary
iso8583sim explain "0110..." --no-llm
```

**Output (`--no-llm`):**

```
MTI 0110: authorization response from acquirer. Card network: MASTERCARD. Card:
555555******4444. Transaction type: Purchase. Amount: 25.00 EUR. Response code 51:
Insufficient funds. Terminal: TERM0001. Merchant: MERCHANT123456.
```

followed by a table of every field.

### generate

Generate sample ISO 8583 messages from a template, or from a plain English description with `--llm`.

```bash
iso8583sim generate [OPTIONS]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--type`, `-t` | Message type (auth, financial, reversal, network). Required unless `--llm` is given |
| `--pan`, `-p` | Primary Account Number |
| `--amount`, `-a` | Transaction amount (in minor units, e.g. cents) |
| `--currency`, `-c` | Currency code (ISO 4217, default 840) |
| `--network`, `-n` | Card network |
| `--llm`, `-l` | Describe the message in plain English and let an LLM build it |
| `--provider` | LLM provider for `--llm` |
| `--model` | Model name for `--llm` |
| `--output`, `-o` | Output file |

**Examples:**

```bash
# Generate authorization request
iso8583sim generate --type auth --pan 4111111111111111 --amount 10000

# Save to file
iso8583sim generate --type auth --output message.txt

# Generate from a description
iso8583sim generate --llm "$50 refund to a Mastercard at ACME Store"
```

With `--llm`, the generated message is validated before it's shown, and common problems are fixed automatically.

### mcp

Run the MCP server over stdio so AI assistants can use iso8583sim. Requires `pip install iso8583sim[mcp]`.

```bash
iso8583sim mcp
```

Your MCP client normally starts this command for you. See [MCP Server](../mcp/index.md) for setup.

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
