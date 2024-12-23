# ISO8583 Simulator

A modern, hybrid ISO 8583 message simulator with both CLI and web interfaces for financial message testing and simulation.

## Features

- **Message Handling**:
  - Parse ISO 8583 messages
  - Build ISO 8583 messages
  - Validate message structure and content
  - Support for different ISO versions (1987, 1993, 2003)

- **Multiple Interfaces**:
  - Command Line Interface (CLI) for automation and scripting
  - Web Interface for interactive testing (Coming Soon)
  - Python SDK for programmatic usage

- **Advanced Features**:
  - Transaction simulation (Sale, Void, Reversal, Authorization)
  - Real-time message validation
  - Custom field definitions
  - Configurable message templates
  - Test scenario generation
  - Rich output formatting

## Installation

```bash
pip install iso8583sim
```

## Quick Start

### CLI Usage

1. Parse an ISO 8583 message:
```bash
iso8583sim parse "0100..." --version 1987 --output parsed.json
```

2. Build a message:
```bash
iso8583sim build --mti 0100 --fields fields.json --output message.txt
```

3. Validate a message:
```bash
iso8583sim validate "0100..."
```

4. Generate sample messages:
```bash
iso8583sim generate --type auth --pan 4111111111111111 --amount 000000001000
```

5. Start interactive shell:
```bash
iso8583sim shell
```

### Python SDK Usage

```python
from iso8583sim.core import ISO8583Parser, ISO8583Builder, ISO8583Validator

# Parse message
parser = ISO8583Parser()
message = parser.parse("0100...")

# Build message
builder = ISO8583Builder()
result = builder.build(message)

# Validate message
validator = ISO8583Validator()
errors = validator.validate_message(message)
```

## Configuration

The simulator can be configured through:
- Command line arguments
- Configuration file (`~/.config/iso8583sim/config.json`)
- Environment variables

## Documentation

For detailed documentation, please visit [documentation link].

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Create a new Pull Request

## Testing

```bash
pytest tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Original ISO 8583 Simulator project that inspired this modernization
- ISO 8583 specification and documentation
- Financial messaging standards community