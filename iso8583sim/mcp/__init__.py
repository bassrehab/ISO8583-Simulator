# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""MCP (Model Context Protocol) server for iso8583sim.

Requires the optional dependency: pip install iso8583sim[mcp]
"""

from .server import create_server, main

__all__ = ["create_server", "main"]
