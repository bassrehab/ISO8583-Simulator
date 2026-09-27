# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- API reference pages for `iso8583sim.security`, `iso8583sim.wire`, `iso8583sim.net`, the REST and MCP servers, and the newer core modules (`codes`, `describe`, `convert`, `samples`, `network_rules`).

### Changed

- Network field rules were rewritten from published sources (`iso8583sim.core.network_rules`). For VISA and Mastercard, field 22 must now use a known PAN entry mode and PIN entry capability, and Mastercard rejects the Visa-only mode `95`. Mastercard field 48 must be a transaction category code followed by well-formed subelements.
- `NETWORK_FIELD_FORMATS` is now empty. Its old patterns were not real network formats and were never used.

### Fixed

- VISA field 44 was rejected unless it was hexadecimal, although it holds response data such as a CVV2 result (`M`). The check is removed.
- Mastercard field 48 was rejected unless it started with `MC`. Real field 48 values start with a transaction category code.
- The network pages of the docs had the field 22 PIN capability digit reversed for VISA and several wrong Mastercard codes.

### Removed

- Seven private `ISO8583Parser` methods that were never called (`_calculate_field_length`, `_handle_network_specific`, `_handle_version_specific`, `_parse_length_indicator`, `_process_bitmap_fields`, `_process_emv_field`, `_validate_field_content`).
- Unused validator methods that held unverified rules (`_validate_visa_compliance`, `_validate_mastercard_compliance`, `_validate_network_field` and the per-network `_validate_*_specific` methods).

## [1.4.0] - 2026-09-27

### Added

- `iso8583sim.wire`: encode messages to bytes and decode them back in configurable wire formats. Binary or hex bitmaps, packed BCD, EBCDIC, binary length prefixes and raw binary fields, with presets `ascii_hex`, `ascii_binary`, `bcd` and `ebcdic`. Decoded messages match what the string parser returns, so all existing features work on them. `ISO8583Builder.build_bytes` and `ISO8583Parser.parse_bytes` are shortcuts. The string API is unchanged.
- `iso8583sim.net`: `Framing` (2 or 4 byte binary or ASCII length headers, optional TPDU), an asyncio `ISO8583Client` that matches responses to requests by STAN so many can be in flight on one connection, and a `MockHost` issuer that answers by rules (match on MTI, PAN prefix, amount, network or field values; respond with a code, delay, drop to simulate a timeout, or close the connection). Rules can be loaded from JSON or YAML.
- CLI commands `serve` (run the mock host; stops cleanly on Ctrl+C or SIGTERM with a summary), `send` (send one message and show the response) and `load` (load test with throughput, latency percentiles and response codes). All take `--format`, `--header` and `--tpdu`.
- `iso8583sim.net.run_load` and `LoadReport` for load testing from Python, and `benchmarks/bench_network.py`.
- Upgrading guide (docs: Getting Started, Upgrading) listing every dependency and behaviour change since 1.1 that can affect an upgrade.
- MCP tool `send_to_host`. It only connects to hosts in the `ISO8583SIM_ALLOWED_HOSTS` environment variable (default: this machine only).

## [1.3.1] - 2026-09-27

### Fixed

- `iso8583sim generate --amount` multiplied the amount by 100, and did it twice, so the default `000000001000` (10.00) was sent as 100,000.00. Plain digits are now minor units, as documented. A decimal amount such as `10.00` is also accepted and converted exactly with the currency's decimal places. Negative amounts, amounts over 12 digits and too many decimal places are rejected.

## [1.3.0] - 2026-09-27

### Added

- `iso8583sim.security` (install with `pip install iso8583sim[security]`): ISO 9564-1 PIN blocks in formats 0, 1, 3 and 4 (`encrypt_pin_block`, `decrypt_pin_block`, and clear `encode_pin_block` / `decode_pin_block`), and ISO 9797-1 MACs with algorithm 1 (CBC-MAC) and algorithm 3 (retail MAC) and padding methods 1 and 2.
- `ISO8583Builder.build_with_mac` fills in the MAC in field 64, or field 128 when the message has a secondary bitmap. `ISO8583Validator.verify_mac` checks it.
- `iso8583sim.core.convert.convert_message` converts messages between the 1987, 1993 and 2003 versions. It rewrites the MTI version digit, moves original data elements between fields 90 and 56, and reports fields it had to drop (such as PIN data and MACs, which must be regenerated) instead of truncating them. The new `iso8583sim convert` command wraps it.
- REST API (`pip install iso8583sim[web]`, then `iso8583sim web`) with `/health`, `/parse`, `/build`, `/validate`, `/explain`, `/generate` and `/convert`. Interactive docs at `/docs`. Explain and generate use rules or templates by default, and an LLM on request.
- `iso8583sim.core.samples.sample_message` creates valid test messages for any network.
- MCP tools `convert_version`, `check_network_rules`, `encrypt_pin_block`, `decrypt_pin_block`, `sign_message` and `verify_message_mac`. The PIN and MAC tools need the `security` extra and report an install hint without it.
- `ISO8583Validator.validate_for_network` and `validate_for_networks` check a message against other networks' rules without changing it. `iso8583sim validate --against all` (or a comma separated list) prints a pass/fail table per network.

### Fixed

- `iso8583sim validate` reported a failed validation as "Error validating message", because the exit was raised inside the error handler.
- 2003 messages could not be built or validated, because MTI version digit 2 was rejected. `MTI_VERSION_DIGITS` in `iso8583sim.core.types` now maps each version to its digit.

## [1.2.0] - 2026-09-27

### Added

- Python 3.13 and 3.14 support.
- MCP server for AI assistants such as Claude and Cursor. Install with `pip install iso8583sim[mcp]` and run `iso8583sim mcp`. It provides 11 tools (parse, build, validate, explain, decode EMV, generate test messages, create responses and reversals, look up fields, detect networks, diff messages), resources for field definitions, response codes and EMV tags, and two prompts.
- `iso8583sim explain` command. Explains a message with an LLM (`--provider`, `--model`, `--verbose`), or with `--no-llm` gives a rule-based summary that needs no API key.
- `iso8583sim generate --llm "description"` generates a message from a plain English description. `--type` is no longer required when `--llm` is used.
- `iso8583sim.core.describe` with `describe_message` for rule-based, human-readable message summaries.
- `iso8583sim.core.codes` with response, processing, network management and currency code tables, and `detect_network_from_pan`.

### Fixed

- The OpenAI provider sends `max_completion_tokens` instead of `max_tokens`, which current OpenAI reasoning models reject.
- The Anthropic provider reads every text block instead of `content[0]`, which fails when a model returns a thinking block first.
- Model refusals from Anthropic and OpenAI, and blocked prompts from Gemini, now raise `LLMError` instead of returning an empty explanation.
- The parser now detects Discover cards and Mastercard 2-series BINs (2221 to 2720).
- The `iso8583sim` command is now installed with the package. Previously it was missing from the package entry points.
- Reversals built with `create_reversal` now fill field 90 (original data elements) with the original STAN, transmission date/time and institution IDs. Previously the STAN was always blank.
- `iso8583sim version` reported `v0.1.0` instead of the installed version.

### Changed

- Default LLM models updated: Anthropic `claude-opus-5` (was `claude-sonnet-4-20250514`), OpenAI `gpt-6-astra` (was `gpt-4o`), Google `gemini-3.8-flash` (was `gemini-1.5-flash`, which is shut down). Ollama stays on `llama3.2`.
- The Anthropic, OpenAI and Google providers now allow 16000 output tokens by default (was 4096), leaving room for thinking or reasoning tokens.
- The Google provider uses the `google-genai` SDK instead of the deprecated `google-generativeai`, and sends the system prompt as a system instruction. The `google` extra installs `google-genai`.
- The `anthropic` extra now requires `anthropic>=1.0.0`.
- With `claude-opus-5` and Claude Fable models, Anthropic requests opt into server-side refusal fallbacks (`fallbacks: "default"`).
- Type checking is stricter (`check_untyped_defs`), and mypy now runs in CI and pre-commit.
- Removed the empty `iso8583sim.utils` package.
- `fastapi` and `uvicorn` are no longer installed by default. They moved to the new `web` extra (`pip install iso8583sim[web]`).
- Documentation links now point to [iso8583sim.com](https://iso8583sim.com).
- Fixed the author LinkedIn link in the README.

## [1.1.3] - 2025-12-31

### Added

- AI-Powered Features section in the README.

## [1.1.2] - 2025-12-31

### Added

- Ollama LLM features notebook with executed outputs.
- Ollama usage in the LLM documentation and README.

## [1.1.1] - 2025-12-31

### Added

- Architecture diagrams, performance charts and network charts in the README and docs.
- Executed LLM outputs in the LLM features notebook.
- MIT license text.

### Fixed

- Removed an invalid `detect_network` import.

### Changed

- Docs theme color set to lime.
- Updated ruff and reformatted test files.

## [1.1.0] - 2025-12-30

### Changed

- README now links to the documentation site and credits the author.

## [1.0.0] - 2025-10-25

First stable release.

### Added

- ISO 8583 parser, builder and validator for the 1987, 1993 and 2003 versions.
- Network support for VISA, Mastercard, AMEX, Discover, JCB and UnionPay, with network detection from the PAN.
- EMV (field 55) TLV parsing and building.
- CLI with `parse`, `build`, `validate`, `generate` and an interactive `shell`.
- LLM-powered message explanation and generation with Anthropic, OpenAI, Google and Ollama providers.
- Cython extensions for the parser, bitmap and validator hot paths (about 2x parser throughput).
- Object pooling for high-throughput workloads.
- Benchmarking framework and a volumetric testing notebook.
- Jupyter notebooks and a demo module.
- MkDocs documentation site.
- GitHub Actions for CI, PyPI publishing and docs deployment.

[Unreleased]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.1.3...v1.2.0
[1.1.3]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/bassrehab/ISO8583-Simulator/releases/tag/v1.0.0
