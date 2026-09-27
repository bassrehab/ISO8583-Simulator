"""MCP (Model Context Protocol) server for iso8583sim.

Requires the optional dependency: pip install iso8583sim[mcp]
"""

from .server import create_server, main

__all__ = ["create_server", "main"]
