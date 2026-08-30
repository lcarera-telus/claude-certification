"""Filesystem MCP server wiring for codebuddy, with graceful degradation.

The server is optional. When its launcher is missing, codebuddy keeps running with the
built-in tools and says why, instead of failing at the first turn.
Reference: https://code.claude.com/docs/en/agent-sdk/mcp
"""

# All text in this file is ASCII only, for the same console encoding reason as the rest
# of the package.
#
# WHY this module never imports the Agent SDK package: it builds plain dictionaries,
# which is all ClaudeAgentOptions.mcp_servers needs. Keeping the SDK out means the module
# imports and tests without the SDK installed, so the degradation path above can be
# checked on a machine that has no agent runtime at all.
#
# TIMING: a stdio MCP server delays the first turn until it connects. The wait deadline
# is MCP_TIMEOUT, 30 seconds by default, and the connection fails at that deadline. In
# the init message a status of "pending" is not a failure on its own; only "failed" and
# "needs-auth" are. https://code.claude.com/docs/en/agent-sdk/mcp

from __future__ import annotations

import os
import shutil
from pathlib import Path

# The tool names this server exposes are mcp__fs__<tool-name>, built from this name.
# https://code.claude.com/docs/en/agent-sdk/mcp
SERVER_NAME = "fs"
PACKAGE = "@modelcontextprotocol/server-filesystem"


def filesystem_server(target: "os.PathLike[str] | str") -> dict | None:
    """Return the mcp_servers mapping for target, or None when npx is absent."""
    if shutil.which("npx") is None:
        return None
    # WHY the bare launcher name and not the resolved absolute path: the bare name is the
    # form the MCP documentation uses. On Windows the resolved path is a .CMD batch shim,
    # and cmd.exe re-parses a batch shim, so the resolved path is the riskier of the two
    # forms. shutil.which stays above, but only to decide whether the server can start at
    # all. https://code.claude.com/docs/en/agent-sdk/mcp
    # WHY resolve the target: the server can reach this directory and nothing else, so a
    # relative path would scope it to whatever the working directory happened to be.
    return {SERVER_NAME: {"command": "npx",
                          "args": ["-y", PACKAGE, str(Path(target).resolve())]}}


def allowed_tool_patterns() -> list[str]:
    """Return the allow-rule entries that approve every tool from this server."""
    # The glob is legal only after the literal mcp__<server>__ prefix. A bare mcp__* is
    # ignored with a startup warning. MCP tools need this explicit permission, or Claude
    # sees the tools and cannot call them.
    return [f"mcp__{SERVER_NAME}__*"]


def unavailable_reason() -> str | None:
    """Return one actionable sentence when the server cannot start, else None."""
    if shutil.which("npx") is not None:
        return None
    return ("Node.js and its npx launcher are not on PATH, so the fs MCP server cannot "
            "start; install Node.js to enable it, and codebuddy will continue with the "
            "built-in tools only.")
