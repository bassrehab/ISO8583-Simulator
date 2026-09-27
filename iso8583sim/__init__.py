"""ISO 8583 message simulator."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("iso8583sim")
except PackageNotFoundError:
    __version__ = "0.0.0"
