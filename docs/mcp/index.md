# MCP Server

iso8583sim includes an [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server. It lets AI assistants such as Claude, Cursor and other MCP clients parse, build, validate and explain ISO 8583 messages directly.

With the server connected you can ask things like:

- "Explain this message: `0100702405800...`"
- "Why was this transaction declined?"
- "Generate a Mastercard authorization for $25 and the matching approval response."
- "What's different between these two messages?"

## Installation

```bash
pip install iso8583sim[mcp]
```

The server runs over stdio:

```bash
iso8583sim mcp
```

You don't normally run this yourself. Your MCP client starts it.

## Client Setup

### Claude Code

```bash
claude mcp add iso8583sim -- iso8583sim mcp
```

To share the server with everyone working in a repository, add it to `.mcp.json` at the project root:

```json
{
  "mcpServers": {
    "iso8583sim": {
      "command": "iso8583sim",
      "args": ["mcp"]
    }
  }
}
```

### Claude Desktop

Open **Settings > Developer > Edit Config** and add the server to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "iso8583sim": {
      "command": "iso8583sim",
      "args": ["mcp"]
    }
  }
}
```

Restart Claude Desktop after saving.

### Cursor

Add the server to `~/.cursor/mcp.json` (all projects) or `.cursor/mcp.json` (one project):

```json
{
  "mcpServers": {
    "iso8583sim": {
      "command": "iso8583sim",
      "args": ["mcp"]
    }
  }
}
```

### Running without installing

With [uv](https://docs.astral.sh/uv/), a client can run the server without a separate install step:

```json
{
  "mcpServers": {
    "iso8583sim": {
      "command": "uvx",
      "args": ["--from", "iso8583sim[mcp]", "iso8583sim", "mcp"]
    }
  }
}
```

!!! tip "Virtual environments"
    If you installed iso8583sim in a virtual environment, use the full path to the command, for example `/path/to/.venv/bin/iso8583sim`. GUI apps such as Claude Desktop don't see your shell's `PATH`.

## Tools

| Tool | What it does |
|------|--------------|
| `parse_message` | Parse a raw message into its MTI, bitmap and named fields. Decodes field 55 when present. |
| `build_message` | Build a raw message from an MTI and a map of field numbers to values. |
| `validate_message` | Check format, length and network rules. Returns `valid` and a list of errors. |
| `explain_message` | Plain-language summary: transaction type, amount, masked card, network, response code meaning. Rule-based, so no LLM key is needed. |
| `decode_emv` | Decode EMV TLV data (field 55) into named tags, with TVR and CID explanations. |
| `generate_test_message` | Generate a valid `auth` (0100), `financial` (0200) or `echo` (0800) message. Uses a standard test PAN for the network when none is given. |
| `create_response` | Create the response to a request (0100 to 0110, 0200 to 0210) with a chosen response code. |
| `create_reversal` | Create a reversal (04xx) with field 90 set to the original data elements. |
| `lookup_field` | Field definition (name, type, length, padding), including network and version overrides. |
| `detect_network` | Detect the card network from a PAN prefix. |
| `diff_messages` | Compare two messages and list added, removed and changed fields. |

Conventions shared by all tools:

- Messages are ASCII strings: MTI, hex bitmap, then field data.
- Field numbers in `fields` are strings, for example `{"2": "4111111111111111", "4": "000000001000"}`.
- `version` is `"1987"` (default), `"1993"` or `"2003"`.
- `network` is optional: `VISA`, `MASTERCARD`, `AMEX`, `DISCOVER`, `JCB` or `UNIONPAY`. Most tools detect it from the PAN when you leave it out.

Invalid input returns a tool error that explains the problem, for example `Unknown network 'DINERS'` or `Invalid MTI format - must be numeric`.

## Resources

| URI | Contents |
|-----|----------|
| `iso8583://fields/{version}` | Field definitions for a version |
| `iso8583://fields/{version}/{network}` | Field definitions with a network's overrides applied |
| `iso8583://codes/response` | Response codes (field 39) and their meanings |
| `iso8583://codes/processing` | Processing code transaction types (field 3) |
| `iso8583://emv/tags` | EMV tag dictionary |

## Prompts

| Prompt | Arguments | Purpose |
|--------|-----------|---------|
| `debug_declined_transaction` | `message` | Walks the assistant through explaining, validating and decoding a message to find why it was declined. |
| `build_test_suite` | `network` | Generates a set of test messages for a network: approval, financial, decline, reversal and echo. |

## Example

A conversation with the server connected:

> **You:** Generate a Visa auth for $10 and explain the response if the issuer declines it for insufficient funds.
>
> **Assistant** calls `generate_test_message`, then `create_response` with `response_code: "51"`, then `explain_message`:
>
> MTI 0110: authorization response from acquirer. Card network: VISA. Card: 411111\*\*\*\*\*\*1111. Transaction type: Purchase. Amount: 10.00. Response code 51: Insufficient funds. Terminal: TERM0001. Merchant: MERCHANT123456.

## Using the server from Python

The server is a regular [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) server, so you can also call it in-process, for example in tests:

```python
import asyncio

from mcp.client import Client

from iso8583sim.mcp import create_server


async def main():
    async with Client(create_server()) as client:
        result = await client.call_tool("generate_test_message", {"network": "VISA"})
        message = result.structured_content["message"]

        explained = await client.call_tool("explain_message", {"message": message})
        print(explained.structured_content["summary"])


asyncio.run(main())
```

## Privacy

The server runs locally and makes no network calls. Messages you give the assistant are sent to your AI provider as part of the conversation, like any other text you paste, so use test data rather than real card numbers. `explain_message` masks the PAN in its summary.
