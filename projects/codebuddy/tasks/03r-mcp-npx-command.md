# Task 03R — Revision: use the bare `npx` name as the MCP server command

Implement this specification exactly. Do not read the other files in `tasks/`.
This is a small, single-file correction. Change nothing else.

All paths below are relative to `projects/codebuddy/`.

## Why this revision exists

The earlier spec told you to pass the resolved absolute path from `shutil.which("npx")` as
the MCP server `command`. That instruction was wrong. On this machine `shutil.which("npx")`
returns:

```
C:\Program Files\nodejs\npx.CMD
```

That value has two problems.

1. It is a `.CMD` batch shim. Windows runs a batch file through `cmd.exe`, which re-parses
   the command line. The Agent SDK already refuses to launch the `claude` CLI from a
   `.bat` or `.cmd` path for exactly this reason.
2. It contains a space. A spaced path is one more thing that can break in a spawn.

The documented example passes the bare name instead:

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                "/Users/me/projects",
            ],
        }
    },
    allowed_tools=["mcp__filesystem__*"],
)
```

Source: https://code.claude.com/docs/en/agent-sdk/mcp

The process that launches an MCP server resolves the launcher itself. Therefore the bare
name is both simpler and safer than a resolved `.CMD` path.

## The change

Edit `codebuddy/mcp.py` only.

In `filesystem_server`, keep `shutil.which("npx")` as the **availability probe**, so the
function still returns `None` when `npx` is absent. Stop using its return value as the
command. Pass the literal string `"npx"` as `command`.

Delete the now-dead `command = found or "npx"` line, because `found` can never be falsy at
that point.

Replace the existing comment that justifies the resolved path. The new comment must state:

- The bare launcher name is what the MCP documentation uses.
- On Windows the resolved path is a `.CMD` batch shim, and a batch shim is re-parsed by
  `cmd.exe`, so it is the riskier of the two forms.
- `shutil.which` stays, but only to decide whether the server can start at all.

Keep the citation to `https://code.claude.com/docs/en/agent-sdk/mcp`.

## Acceptance criteria

1. `codebuddy/mcp.py` contains the exact string `"command": "npx"` or an equivalent that
   passes the bare literal `"npx"`. Verify with
   `grep -n '"npx"' codebuddy/mcp.py`.
2. `grep -n 'found or' codebuddy/mcp.py` returns nothing.
3. `shutil.which` is still called, and `filesystem_server` still returns `None` when it
   finds nothing. Verify with:
   ```
   python -c "import shutil, codebuddy.mcp as m; shutil.which = lambda *a, **k: None; print(m.filesystem_server('.'))"
   ```
   It must print `None`.
4. With `npx` present, `filesystem_server('sample-legacy-app')` returns a mapping whose
   `command` is exactly `npx`, and whose third argument is an absolute path. Verify with:
   ```
   python -c "import codebuddy.mcp as m; d=m.filesystem_server('sample-legacy-app'); print(d['fs']['command']); print(d['fs']['args'][2])"
   ```
5. `codebuddy/mcp.py` still does not import `claude_agent_sdk`.
6. The code line count of `codebuddy/mcp.py`, excluding comments and blank lines, is at
   most 30. Check with `grep -vE '^[[:space:]]*(#|$)' codebuddy/mcp.py | wc -l`.
7. No non-ASCII character appears in the file. Check with
   `grep -nP '[^\x00-\x7F]' codebuddy/mcp.py`, which must return nothing.
8. `python -m compileall -q codebuddy` reports no error.

## Out of scope

Change no file other than `codebuddy/mcp.py`.
Do not touch `permissions.py`, `config.py`, or `observability.py`.
Do not create any file.
Do not run `git add` or `git commit`.

## When you finish

Print the changed lines of `codebuddy/mcp.py`, the result of each acceptance check, and the
line count. Then stop.
