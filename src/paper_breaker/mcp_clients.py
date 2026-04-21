"""Load external MCP servers as BeeAI tools so agents can call them.

Config shape (see mcp_servers.example.json):

    [
      {
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        "env": { "FOO": "bar" },            # optional
        "include": ["read_file", "list_directory"]   # optional allowlist
      }
    ]

At startup the agent server reads mcp_servers.json (if present), connects to
each listed server over stdio, and collects their advertised tools into a flat
list. Agents accept this list as an `extra_tools` kwarg.

Cached for the life of the process — connections stay alive.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from mcp import StdioServerParameters
    from mcp.client.stdio import stdio_client
    from beeai_framework.tools.mcp import MCPTool
    from beeai_framework.tools import AnyTool

    _MCP_AVAILABLE = True
except ImportError:  # pragma: no cover
    _MCP_AVAILABLE = False


_CONFIG_PATH = Path(os.getenv("MCP_SERVERS_JSON", "mcp_servers.json"))
_cache: list[Any] | None = None


def _load_config() -> list[dict]:
    if not _CONFIG_PATH.exists():
        return []
    return json.loads(_CONFIG_PATH.read_text())


async def load_external_mcp_tools() -> list[Any]:
    """Return a flat list of BeeAI tools exposed by every configured MCP server.

    Idempotent — subsequent calls return the cached list.
    """
    global _cache
    if _cache is not None:
        return _cache
    if not _MCP_AVAILABLE:
        _cache = []
        return _cache

    config = _load_config()
    all_tools: list[AnyTool] = []
    for entry in config:
        params = StdioServerParameters(
            command=entry["command"],
            args=entry.get("args", []),
            env={**os.environ, **(entry.get("env") or {})},
        )
        server_tools = await MCPTool.from_client(stdio_client(params))
        include = entry.get("include")
        if include:
            server_tools = [t for t in server_tools if t.name in include]
        all_tools.extend(server_tools)
    _cache = all_tools
    return _cache
