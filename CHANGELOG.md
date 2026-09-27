# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Python 3.13 and 3.14 support.
- `iso8583sim.core.codes` with response, processing, network management and currency code tables, and `detect_network_from_pan`.

### Fixed

- The parser now detects Discover cards and Mastercard 2-series BINs (2221 to 2720).
- The `iso8583sim` command is now installed with the package. Previously it was missing from the package entry points.
- Reversals built with `create_reversal` now fill field 90 (original data elements) with the original STAN, transmission date/time and institution IDs. Previously the STAN was always blank.
- `iso8583sim version` reported `v0.1.0` instead of the installed version.

### Changed

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

[Unreleased]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.1.3...HEAD
[1.1.3]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/bassrehab/ISO8583-Simulator/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/bassrehab/ISO8583-Simulator/releases/tag/v1.0.0
