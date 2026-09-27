"""ISO 8583 message simulator."""

from importlib.metadata import PackageNotFoundError, version

# subhadipmitra@: Read the version from the installed package metadata so it can never drift
# from pyproject.toml again (the CLI used to print a hardcoded v0.1.0). The fallback covers
# running from a source tree that was never pip-installed.
try:
    __version__ = version("iso8583sim")
except PackageNotFoundError:
    __version__ = "0.0.0"
