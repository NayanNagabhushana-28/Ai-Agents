"""
MCP server entry: creates the FastMCP app and registers all tool groups.

Tool implementations live under ``mcp_tools/`` (one module per domain).
Run via ``run_server.py`` (stdio). Do not import LLM/agent code here.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .mcp_tools import register_issue_list_tools

# Single MCP application — Cursor connects to this via run_server.py
mcp = FastMCP("GitHub Issues", json_response=True)

# Register tool groups (add more register_* calls as new MCP capabilities land)
register_issue_list_tools(mcp)
