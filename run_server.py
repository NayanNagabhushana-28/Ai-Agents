#!/usr/bin/env python3
"""
Start the GitHub Issues MCP server (stdio transport for Cursor).

Usage::

    python run_server.py

Requires ``GITHUB_TOKEN`` in ``.env`` or the environment for reliable API access.
Cursor invokes this script via ``.cursor/mcp.json``.
"""

import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from github_issues_mcp.mcp_server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
