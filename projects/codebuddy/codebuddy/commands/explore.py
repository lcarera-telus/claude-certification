# The explore command: a read-only survey of a codebase that ends in EXPLORATION.md.
# Reference: https://code.claude.com/docs/en/tools-reference
#
# All text in this file is ASCII only, for the same console encoding reason as the rest
# of the package.

from __future__ import annotations

from pathlib import Path

from .. import config, mcp, observability, permissions
from ._common import run_agent

# TOOL PLAN. This command expects four tools, and the prompt below names each one with
# the reason it wins over its alternative. The reasons are repeated here because a
# reader of the code should not have to read a prompt string to learn the design.
#
# Glob, not a Bash "ls" or "dir": Glob is a first-class tool. It returns matching paths
# sorted by modification time, so the recently touched files arrive first, and it needs
# no shell at all. A shell listing would also differ between cmd.exe and a POSIX shell.
#
# Grep, not a Bash "grep": Grep is a first-class tool with structured output, so the
# agent gets file and line data instead of text it must re-parse. It needs no shell, and
# it behaves the same on Windows, where the grep binary is often simply absent. The
# explore policy denies Bash outright, so a shell grep would be refused anyway.
#
# Read, used sparingly: Read pulls a whole file into the context window. Reading every
# file would exhaust that window long before the survey is written, so the prompt tells
# the agent to read only the few files the Glob and Grep passes proved to matter.
#
# One MCP filesystem tool: this proves the MCP server reached the model and gives the
# transcript a built-in versus MCP comparison. https://code.claude.com/docs/en/agent-sdk/mcp

PROMPT = """Survey the codebase at {target} and write one report about it.

Work in this order. Each step names the tool to use and the reason that tool is correct.

1. Use Glob to list the file structure. Glob is right here because it is a first-class
   tool that returns paths sorted by modification time and needs no shell, so the files
   that changed most recently appear first. Do not use a shell listing command.

2. Use Grep to find the entry points, and to find every TODO and every FIXME. Grep is
   right here rather than a Bash grep because it is a first-class tool with structured
   output, it needs no shell, and it behaves the same on Windows, where the grep binary
   is often absent. A shell is not available to you in this run.

3. Use Read on only the few files that the first two steps proved to matter. Reading
   every file wastes the context window and leaves no room to write the report.

4. Use exactly one MCP filesystem tool to list the directory. In the report, say plainly
   which MCP tool you used and how its result compared with the built-in equivalent. If
   no MCP tool is available to you, say that instead and continue.

5. Write EXPLORATION.md in the repository root. Use these sections, in this order:

   Purpose
   Structure
   Entry points
   Conventions detected
   The confusing part
   Open TODOs and FIXMEs
   Risks

   The Conventions detected section must state three things explicitly: the test file
   naming pattern, the import style, and the docstring style. A later command reads that
   section and copies these conventions, so an omission there breaks it.

6. Trust the source code over any README prose. Where the two disagree, say so
   explicitly in the report, name the file, and give the code as the correct version.

Be concrete. Name files and line numbers. Do not invent anything you did not read.
"""


async def run(target: str, *, model: str, quiet: bool, logger=None) -> int:
    """Survey the target directory and write EXPLORATION.md inside it. Return an exit code."""
    root = Path(target).expanduser().resolve()
    if not root.is_dir():
        raise config.CodebuddyError(f"Not a directory: {root}. Give the path of an existing directory to explore.")
    logger = logger or observability.ToolCallLogger(quiet=quiet)
    policy = permissions.for_explore()
    servers = mcp.filesystem_server(root)
    # Graceful degradation. When the launcher is missing the run continues on the
    # built-in tools, so the mcp__fs__* allow rule must go too. A rule that names a
    # server which never started is dead weight and misreports the real tool surface.
    if servers is None:
        print(f"codebuddy: warning: {mcp.unavailable_reason()}", flush=True)
        keep = [rule for rule in policy.allowed_tools if rule not in mcp.allowed_tool_patterns()]
        policy = permissions.ToolPolicy(keep, policy.disallowed_tools, policy.permission_mode)
    # WHY cwd is the explored directory: the explore policy allows Edit(EXPLORATION.md),
    # which is a relative rule. A relative rule anchors at the session working directory,
    # not at the filesystem root, so cwd is the only thing that decides where that rule
    # points. Setting it here is what makes the report land inside the explored repository
    # and nowhere else. https://code.claude.com/docs/en/agent-sdk/permissions
    # WHY max_turns=25: a survey needs several Glob, Grep, and Read rounds before it can
    # write. 25 leaves room for that and still bounds a loop that stops making progress.
    code = await run_agent(prompt=PROMPT.format(target=root), policy=policy, logger=logger,
                           model=model, cwd=str(root), mcp_servers=servers, max_turns=25)
    # Verify the artefact instead of trusting the exit code. The agent can report success
    # and still not have written the file. Warn, but do not raise: the transcript is worth
    # keeping, and the caller already has the agent's own exit code.
    report = root / "EXPLORATION.md"
    if not report.is_file():
        print(f"codebuddy: warning: the run finished but {report} does not exist.", flush=True)
    print(logger.summary(), flush=True)
    return code
