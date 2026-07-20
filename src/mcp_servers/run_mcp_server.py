#!/usr/bin/env python3
"""
Start the GitHub Issues MCP server (stdio transport for Cursor).

Usage::

    python src/mcp_servers/run_mcp_server.py

Requires ``GITHUB_TOKEN`` in ``.env`` or the environment for reliable API access.
Cursor invokes this script via ``.cursor/mcp.json``.
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
_src_path = _project_root / "src"

try:
    from dotenv import load_dotenv

    load_dotenv(_project_root / ".env")
except ImportError:
    pass

if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from mcp_servers.server_tools import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
