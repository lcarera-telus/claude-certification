# Task 03 — Permission policies and MCP server wiring

Implement this specification exactly. Do not read the other files in `tasks/`.
This specification is the complete contract. Ask no questions. Write the files.

All paths below are relative to `projects/codebuddy/`.

## Goal

Create two modules:

- `codebuddy/permissions.py` — one scoped tool policy per command, plus a safety hook.
- `codebuddy/mcp.py` — one MCP server configuration, with graceful degradation.

The permission rules are teaching material. Each rule must carry a comment that says why
that exact rule form was chosen. The wrong rule form fails silently, so the comments
matter more than the code.

---

## Reference documentation

Use the excerpts below. Do not use memory. These are the source pages:

| Topic | URL |
|---|---|
| Permissions | https://code.claude.com/docs/en/agent-sdk/permissions |
| MCP | https://code.claude.com/docs/en/agent-sdk/mcp |
| Hooks | https://code.claude.com/docs/en/agent-sdk/hooks |
| Python SDK reference | https://code.claude.com/docs/en/agent-sdk/python |

### Excerpt A — the permission evaluation order

Quoted from the permissions page. A tool request is checked in this fixed order:

1. **Hooks** — run first. A hook can deny the call outright or pass it on.
2. **Deny rules** — from `disallowed_tools` and `settings.json`. Quoted: *"If a deny rule
   matches, the tool is blocked, even in `bypassPermissions` mode."*
3. **Ask rules** — from `settings.json`.
4. **Permission mode**.
5. **Allow rules** — from `allowed_tools` and `settings.json`.
6. **`can_use_tool` callback**.

### Excerpt B — allow and deny rule behaviour

Quoted table from the permissions page:

| Option | Effect |
|---|---|
| `allowed_tools=["Read", "Grep"]` | `Read` and `Grep` are auto-approved. Other tools not listed here still exist and fall through to the permission mode and `can_use_tool`. |
| `disallowed_tools=["Bash"]` | The `Bash` tool definition is removed from the request. Claude does not see the tool and cannot attempt it. |
| `disallowed_tools=["Bash(rm *)"]` | `Bash` stays available. Calls matching `rm *` are denied in every permission mode, including `bypassPermissions`. Other `Bash` calls fall through to the permission mode. |
| `disallowed_tools=["*"]` | Every tool definition is removed from the request. |

Quoted, on MCP globs in allow rules:

> Allow rules accept tool-name globs only after a literal `mcp__<server>__` prefix. The
> server segment must be glob-free so the rule names a specific server you configured:
> `mcp__puppeteer__*` matches every tool from the `puppeteer` server. An unanchored entry
> like `allowed_tools=["*"]` or `allowed_tools=["mcp__*"]` is ignored with a startup
> warning and does not auto-approve anything.

Quoted, on path-scoped rules. **This is the most important sentence in this spec:**

> Scoped rules for `Read` and `Edit` take a path pattern. `Edit(path)` rules govern all
> built-in tools that write files, including `Write` and `NotebookEdit`; a `Write(path)`
> rule is never matched by the file permission checks.

Therefore: to scope a file write by path, write `Edit(...)`. Never write `Write(...)`.
A `Write(...)` rule matches nothing and the call silently falls through to the mode.

Quoted, on anchoring:

> Use `//path` for an absolute filesystem path ... With a single leading slash,
> `Edit(/secrets/**)` anchors at the rule's source instead. For rules passed through
> `allowed_tools` or `disallowed_tools`, that means the session's working directory.

### Excerpt C — permission modes

Quoted table:

| Mode | Description | Tool behavior |
|---|---|---|
| `default` | Standard permission behavior | No auto-approvals; unmatched tools trigger your `can_use_tool` callback |
| `dontAsk` | Deny instead of prompting | Anything not pre-approved by `allowed_tools` or rules is denied. `can_use_tool` is never called |
| `acceptEdits` | Auto-accept file edits | File edits and filesystem operations (`mkdir`, `rm`, `mv`, etc.) are automatically approved |
| `bypassPermissions` | Bypass permission checks | Tools run without permission prompts. Use with caution |
| `plan` | Planning mode | Claude explores and plans without editing your source files |
| `auto` | Model-classified approvals | A model classifier approves or denies permission prompts |

Quoted, the locked-down agent pattern:

> For a locked-down agent, pair `allowedTools` with `permissionMode: "dontAsk"`. Listed
> tools are approved ... anything else is denied outright instead of prompting.

Quoted warning:

> **`allowed_tools` does not constrain `bypassPermissions`.** ... Setting
> `allowed_tools=["Read"]` alongside `permission_mode="bypassPermissions"` still approves
> every tool, including `Bash`, `Write`, and `Edit`. If you need `bypassPermissions` but
> want specific tools blocked, use `disallowed_tools`.

Quoted, on `acceptEdits` and MCP:

> `permissionMode: "acceptEdits"` does not auto-approve MCP tools (only file edits and
> filesystem Bash commands).

### Excerpt D — a PreToolUse hook that denies a call

Quoted Python from the hooks page, adapted shape:

```python
async def block_etc_writes(input_data, tool_use_id, context):
    file_path = input_data["tool_input"].get("file_path", "")
    ...
```

The deny return shape, described on the hooks page:

- `permissionDecision` takes `"allow"`, `"deny"`, `"ask"`, or `"defer"`.
- `permissionDecisionReason` tells the model why, so it avoids retrying.
- `systemMessage` shows the user what happened.
- Include `hookEventName` in `hookSpecificOutput` to identify the hook type.

So a deny returns:

```python
{
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "<why, addressed to the model>",
    },
    "systemMessage": "<why, addressed to the user>",
}
```

Quoted: *"If any hook returns `deny`, the operation is blocked regardless of other
hooks."* And: *"A hook that returns `allow` does not skip the deny and ask rules below."*

`HookMatcher` registration, quoted:

```python
options = ClaudeAgentOptions(
    hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[my_callback])]}
)
```

### Excerpt E — MCP stdio server configuration in Python

Quoted from the MCP page:

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
    allowed_tools=["mcp__filesystem__read_file", "mcp__filesystem__list_directory"],
)
```

Quoted, the naming convention:

> MCP tools follow the naming pattern `mcp__<server-name>__<tool-name>`. For example, a
> GitHub server named `"github"` with a `list_issues` tool becomes
> `mcp__github__list_issues`.

Quoted, on permission:

> MCP tools require explicit permission before Claude can use them. Without permission,
> Claude will see that tools are available but won't be able to call them.

Quoted, on connection status:

> The `status` field can be `"pending"`, `"connected"`, `"failed"`, `"needs-auth"`, or
> `"disabled"`. ... In the init message, don't treat `"pending"` as a failure on its own.

Quoted, on stdio timing:

> stdio server, or HTTP/SSE server without a cached tool list — Delays the first turn:
> Yes, until it connects. First-turn wait timeout: `MCP_TIMEOUT`, 30 seconds by default;
> the connection fails at that deadline.

Verified package fact: `@modelcontextprotocol/server-filesystem` is published on npm at
version `2026.7.10` and is not deprecated.

---

## File 1 — `codebuddy/permissions.py`

Budget: 70 lines of code, excluding comments and blank lines.

Write a module docstring. Then implement exactly this public surface.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ToolPolicy:
    allowed_tools: list[str]
    disallowed_tools: list[str]
    permission_mode: str

def for_explore() -> ToolPolicy: ...
def for_boilerplate(output_dir: str, tests_dir: str) -> ToolPolicy: ...
def for_chores(target_dir: str) -> ToolPolicy: ...
def bash_guard_hooks() -> dict: ...
DESTRUCTIVE_PATTERNS: tuple[str, ...]
```

### `for_explore()`

Return exactly this policy. Do not add or remove entries.

```python
allowed_tools = [
    "Read",
    "Glob",
    "Grep",
    "Edit(EXPLORATION.md)",
    "mcp__fs__*",
]
disallowed_tools = ["Bash", "WebFetch", "WebSearch"]
permission_mode = "dontAsk"
```

### `for_boilerplate(output_dir, tests_dir)`

```python
allowed_tools = [
    "Read",
    "Glob",
    "Grep",
    f"Edit({output_dir}/**)",
    f"Edit({tests_dir}/**)",
]
disallowed_tools = ["Bash", "WebFetch", "WebSearch"]
permission_mode = "dontAsk"
```

### `for_chores(target_dir)`

```python
allowed_tools = [
    "Read",
    "Glob",
    "Grep",
    f"Edit({target_dir}/**)",
    "Bash(git status:*)",
    "Bash(git diff:*)",
    "Bash(git ls-files:*)",
    "Bash(sed:*)",
    "Bash(python -m black:*)",
    "Bash(python -m py_compile:*)",
]
disallowed_tools = [
    "Bash(rm *)",
    "Bash(rmdir *)",
    "Bash(del *)",
    "Bash(git push:*)",
    "Bash(git commit:*)",
    "Bash(git reset:*)",
    "Bash(git checkout:*)",
    "Bash(curl *)",
    "WebFetch",
    "WebSearch",
]
permission_mode = "dontAsk"
```

### `DESTRUCTIVE_PATTERNS` and `bash_guard_hooks()`

`DESTRUCTIVE_PATTERNS` is a tuple of lowercase substrings that must never appear in a
Bash command during a chores run. Use exactly these:

```python
("rm ", "rmdir", "del ", "git push", "git reset", "git commit", "git checkout",
 "shutdown", "format ", "mkfs", ":(){", "curl ", "iwr ", "invoke-webrequest")
```

`bash_guard_hooks()` returns a dictionary for `ClaudeAgentOptions.hooks`:

```python
{"PreToolUse": [HookMatcher(matcher="Bash", hooks=[_deny_destructive_bash])]}
```

Use `matcher="Bash"` here. This is the opposite choice from the transparency layer, and
the comment must say why: this guard only concerns shell commands, so a narrow matcher
keeps it cheap and prevents it from inspecting unrelated tool inputs.

`_deny_destructive_bash(input_data, tool_use_id, context)` is an `async def` callback. It:

1. Returns `{}` when `input_data.get("hook_event_name")` is not `"PreToolUse"`.
2. Returns `{}` when `input_data.get("tool_name")` is not `"Bash"`.
3. Reads the command from `input_data["tool_input"].get("command", "")` and lowercases it.
4. Returns the deny shape from Excerpt D when any pattern from `DESTRUCTIVE_PATTERNS`
   appears in the command. Name the matched pattern in both messages.
5. Returns `{}` otherwise.

### Required comments in `permissions.py`

Each is graded. Write them as comments in the file, in your own words, in short sentences.

1. Above `Edit("EXPLORATION.md")` in `for_explore`: state that `Edit(path)` is the rule
   form that governs `Write`, and that a `Write(path)` rule is never matched, so it would
   silently fail. Cite the permissions doc URL.
2. Above `disallowed_tools` in `for_explore`: state that a bare tool name in a deny rule
   removes the tool definition from the request, so the agent cannot even attempt it.
   Contrast that with a scoped deny such as `Bash(rm *)`, which keeps the tool available.
3. Above `"mcp__fs__*"`: state that an allow-rule glob is only legal after a literal
   `mcp__<server>__` prefix, and that a bare `mcp__*` is ignored with a startup warning.
   Also state that `acceptEdits` does not auto-approve MCP tools, so this explicit entry
   is required.
4. Above `permission_mode` in every policy: state why `dontAsk` and not `default`.
   `codebuddy` is non-interactive, so an unresolved call must die loudly rather than wait
   on a prompt that nobody will answer.
5. Above the `disallowed_tools` list in `for_chores`: state that the list is deliberately
   redundant with the narrow allowlist. Deny rules are evaluated before the permission
   mode and hold even under `bypassPermissions`, so they survive a later careless change
   of mode.
6. Above `"Bash(sed:*)"`: state the accepted risk. `sed -i` can rewrite any existing file
   the process can reach, so the command layer must still validate the target path.
7. Above `bash_guard_hooks`: state that hooks are step one of six in the evaluation order,
   so this guard holds even if somebody later sets `bypassPermissions`.

---

## File 2 — `codebuddy/mcp.py`

Budget: 30 lines of code, excluding comments and blank lines.

Write a module docstring. Then implement exactly this public surface.

```python
SERVER_NAME = "fs"
PACKAGE = "@modelcontextprotocol/server-filesystem"

def filesystem_server(target: "os.PathLike[str] | str") -> dict | None: ...
def allowed_tool_patterns() -> list[str]: ...
def unavailable_reason() -> str | None: ...
```

Behaviour, exactly:

1. `filesystem_server(target)` returns a value for `ClaudeAgentOptions.mcp_servers`:

   ```python
   {SERVER_NAME: {"command": <npx>, "args": ["-y", PACKAGE, str(Path(target).resolve())]}}
   ```

   Resolve the target to an absolute path. The server can then reach that directory only.
   Return `None` when `shutil.which("npx")` finds nothing.

2. `<npx>` is `shutil.which("npx")` when that returns a path, otherwise the literal
   `"npx"`. Add a comment saying why: on Windows `npx` is a `.cmd` shim, and passing the
   resolved absolute path avoids a `PATH` lookup inside the spawned server process.

3. `allowed_tool_patterns()` returns `[f"mcp__{SERVER_NAME}__*"]`.

4. `unavailable_reason()` returns `None` when `npx` is on `PATH`. Otherwise it returns one
   actionable sentence naming Node.js and `npx` as the missing prerequisite, and stating
   that `codebuddy` will continue with built-in tools only.

Do not import `claude_agent_sdk` in this module. It builds plain dictionaries only.
Add a comment saying why that matters: the module stays importable and testable without
the SDK installed.

Add a comment stating that a stdio MCP server delays the first turn until it connects,
with a default 30 second `MCP_TIMEOUT` deadline. Cite the MCP doc URL.

---

## Acceptance criteria

The reviewer runs these checks. All must pass.

1. `codebuddy/permissions.py` and `codebuddy/mcp.py` exist.
2. `python -m compileall -q codebuddy` reports no error.
3. Neither file contains the string `Write(`. Check with
   `grep -n 'Write(' codebuddy/permissions.py`, which must return nothing.
4. `for_explore().allowed_tools` equals the exact list in this spec, in the same order.
5. `for_explore().disallowed_tools` equals `["Bash", "WebFetch", "WebSearch"]`.
6. Every returned `permission_mode` is the string `dontAsk`.
7. `grep -c 'mcp__fs__\*' codebuddy/permissions.py` returns at least 1.
8. `codebuddy/mcp.py` does not import `claude_agent_sdk`.
9. `allowed_tool_patterns()` returns `["mcp__fs__*"]`.
10. `filesystem_server` returns `None` when `npx` is absent. Verify by monkeypatching
    `shutil.which` in a one-off `python -c` check.
11. `_deny_destructive_bash` is `async def`, and it returns a dictionary whose
    `hookSpecificOutput.permissionDecision` is `deny` for the input
    `{"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}`.
    It returns `{}` for `{"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "git status"}}`.
    Verify both with `python -c` and `asyncio.run`.
12. `bash_guard_hooks()` uses `matcher="Bash"`.
13. All seven required comments from the list above are present in `permissions.py`.
14. Both files reference at least one `code.claude.com` doc URL in a comment.
15. Code line counts, excluding comments and blank lines, are at most 70 for
    `permissions.py` and at most 30 for `mcp.py`. Check each with
    `grep -vE '^[[:space:]]*(#|$)' <file> | wc -l`.
16. No non-ASCII character appears in either file. Check with
    `grep -nP '[^\x00-\x7F]' codebuddy/permissions.py codebuddy/mcp.py`, which must return
    nothing.

## Out of scope

Do not create `__main__.py` or any command module.
Do not modify `codebuddy/config.py` or `codebuddy/observability.py`.
Do not create `README.md`, `DECISIONS.md`, or `COORDINATION.md`.
Do not modify anything under `sample-legacy-app/`.
Do not run `git add` or `git commit`.

## When you finish

List the files you created. Print the result of every acceptance check you could run.
Print the two line counts from check 15. Then stop.
