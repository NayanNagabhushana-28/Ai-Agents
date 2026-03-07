#!/usr/bin/env python3
"""Entry point for the GitHub Issues MCP server. Run with: python run_server.py"""

import sys
from pathlib import Path

# Load .env from project root (if present)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# Ensure src is on the path when run from project root
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from github_issues_mcp.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
