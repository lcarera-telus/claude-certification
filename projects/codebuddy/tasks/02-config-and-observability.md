# Task 02 — Configuration layer and tool-use transparency layer

Implement this specification exactly. Do not read the other files in `tasks/`.
This specification is the complete contract. Ask no questions. Write the files.

All paths below are relative to `projects/codebuddy/`.

## Goal

Create two modules:

- `codebuddy/config.py` — environment loading, model choice, and error translation.
- `codebuddy/observability.py` — a layer that prints every tool call to the console.

The learner must watch the agent work. Therefore the transparency layer is the most
important file in this project. Comment it as teaching material.

---

## Reference documentation

The Claude Agent SDK API changes often. Use the excerpts below. Do not use memory.
These are the source pages:

| Topic | URL |
|---|---|
| Python SDK reference | https://code.claude.com/docs/en/agent-sdk/python |
| Hooks | https://code.claude.com/docs/en/agent-sdk/hooks |
| Permissions | https://code.claude.com/docs/en/agent-sdk/permissions |
| MCP | https://code.claude.com/docs/en/agent-sdk/mcp |
| Troubleshooting | https://code.claude.com/docs/en/agent-sdk/troubleshooting |
| Quickstart | https://code.claude.com/docs/en/agent-sdk/quickstart |

### Excerpt A — package install and message types

```
pip install claude-agent-sdk
```

```python
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    AssistantMessage,
    UserMessage,
    SystemMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ThinkingBlock,
)
```

Key message classes, quoted from the reference:

- `AssistantMessage` - Claude's response with `content` blocks
- `ResultMessage` - Indicates turn completion with `result` and `terminal_reason`
- `ToolUseBlock` - Tool invocation in message content
- `ToolResultBlock` - Tool execution result
- `TextBlock` - Text content block
- `ThinkingBlock` - Extended thinking content

### Excerpt B — the `query()` entry point

```python
async def query(
    *,
    prompt: str | AsyncIterable[dict[str, Any]],
    options: ClaudeAgentOptions | None = None,
    transport: Transport | None = None
) -> AsyncIterator[Message]
```

### Excerpt C — relevant `ClaudeAgentOptions` fields

```python
@dataclass
class ClaudeAgentOptions:
    allowed_tools: list[str] = field(default_factory=list)
    system_prompt: str | SystemPromptPreset | SystemPromptFile | None = None
    mcp_servers: dict[str, McpServerConfig] | str | Path = field(default_factory=dict)
    permission_mode: PermissionMode | None = None
    max_turns: int | None = None
    max_budget_usd: float | None = None
    disallowed_tools: list[str] = field(default_factory=list)
    model: str | None = None
    cwd: str | Path | None = None
    env: dict[str, str] = field(default_factory=dict)
    stderr: Callable[[str], None] | None = None
    hooks: dict[HookEvent, list[HookMatcher]] | None = None
    setting_sources: list[SettingSource] | None = None
    effort: EffortLevel | None = None
```

`SystemPromptPreset`:

```python
class SystemPromptPreset(TypedDict):
    type: Literal["preset"]
    preset: Literal["claude_code"]
    append: NotRequired[str]
    exclude_dynamic_sections: NotRequired[bool]
```

### Excerpt D — how to register hooks in Python

```python
options = ClaudeAgentOptions(
    hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[my_callback])]}
)
```

`HookMatcher` fields: `matcher` (optional string), `hooks` (required list of callbacks),
`timeout` (optional seconds).

Quoted from the hooks page:

> Use the `matcher` pattern to target specific tools whenever possible. A matcher with
> `'Bash'` only runs for Bash commands, while omitting the pattern runs your callbacks for
> every occurrence of the event. **Omit it on purpose to log every tool call your session
> makes.**

Registering more than one matcher, quoted:

```python
options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Write|Edit|NotebookEdit", hooks=[file_security_hook]),
            HookMatcher(matcher="^mcp__", hooks=[mcp_audit_hook]),
            HookMatcher(hooks=[global_logger]),
        ]
    }
)
```

### Excerpt E — the hook callback contract

Every hook callback takes three positional arguments:

1. `input_data` — a dictionary. All hook inputs share `session_id`, `cwd`, and
   `hook_event_name`. `PreToolUse` input adds `tool_name` and `tool_input`.
2. `tool_use_id` — `str | None`. It correlates `PreToolUse` with `PostToolUse` for the
   same tool call.
3. `context` — reserved for future use in Python.

Quoted from the hooks page:

> Return `{}` to allow the operation without changes.

A working Python callback, quoted from the hooks page:

```python
async def auto_approve_read_only(input_data, tool_use_id, context):
    if input_data["hook_event_name"] != "PreToolUse":
        return {}

    read_only_tools = ["Read", "Glob", "Grep"]
    if input_data["tool_name"] in read_only_tools:
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "allow",
                "permissionDecisionReason": "Read-only tool auto-approved",
            }
        }
    return {}
```

Hook events available in the **Python** SDK: `PreToolUse`, `PostToolUse`,
`PostToolUseFailure`, `UserPromptSubmit`, `Stop`, `SubagentStart`, `SubagentStop`,
`PreCompact`, `PermissionRequest`, `Notification`.

`SessionStart` and `SessionEnd` are **not** available as Python callbacks. Do not use them.

### Excerpt F — reading the init message and MCP server status

Quoted Python code from the MCP page:

```python
async for message in query(prompt="...", options=options):
    if isinstance(message, SystemMessage) and message.subtype == "init":
        mcp_tools = [t for t in message.data.get("tools", []) if t.startswith("mcp__")]
        print("Available MCP tools:", mcp_tools)
```

```python
if isinstance(message, SystemMessage) and message.subtype == "init":
    for server in message.data.get("mcp_servers", []):
        if server.get("status") == "failed":
            print(f"Server {server['name']} failed to connect")
```

The `status` field can be `"pending"`, `"connected"`, `"failed"`, `"needs-auth"`, or
`"disabled"`. Quoted: *"don't treat `"pending"` as a failure on its own."*

Error results arrive on the result message:

```python
if isinstance(message, ResultMessage) and message.subtype == "error_during_execution":
    print("Execution failed")
```

### Excerpt G — permission evaluation order

Quoted from the permissions page, the order in which a tool request is checked:

1. **Hooks** — run first. A hook can deny the call outright or pass it on.
2. **Deny rules** — from `disallowed_tools` and `settings.json`.
3. **Ask rules** — from `settings.json`.
4. **Permission mode**.
5. **Allow rules** — from `allowed_tools` and `settings.json`.
6. **`can_use_tool` callback**.

Quoted warning: *"Auto-approved tools never reach `can_use_tool`. A tool call approved at
any earlier step ... skips your `can_use_tool` callback."* And: *"For checks that must run
on every tool call, use a `PreToolUse` hook: hooks run before every other step."*

### Excerpt H — exceptions raised by the Python SDK

Confirmed class names, importable from `claude_agent_sdk`:

| Class | Cause |
|---|---|
| `CLINotFoundError` | No `claude` executable found. The message includes the configured path when `cli_path` is set. |
| `CLIConnectionError` | Three cases. The CLI path is a Windows `.bat` or `.cmd` batch script and the SDK refuses to run it. The file exists but failed to launch. A `ClaudeSDKClient` method was called before `connect()`. |
| `ProcessError` | The CLI exited with a nonzero code. It carries `exit_code` and `stderr` attributes. |
| `ResultError` | The CLI reported an error result before it exited. It carries a `data` attribute. **It subclasses `ProcessError`.** |

Quoted: *"`ResultError` subclasses `ProcessError`, so `except ProcessError` catches both.
To handle them differently, put the `except ResultError` clause first."*

The Windows batch-script refusal message, quoted in part:

> Refusing to execute batch script '...\npm\claude.cmd': Windows runs .bat/.cmd files via
> cmd.exe ... Use a native claude executable instead: install Claude Code natively
> (irm https://claude.ai/install.ps1 | iex), point ClaudeAgentOptions(cli_path=...) at a
> claude.exe, or install the claude-agent-sdk wheel for a platform that bundles claude.exe

This project runs on Windows. Therefore this error must be handled by name.

### Excerpt I — authentication

Quoted from the quickstart:

> The SDK reads the key from the environment of the process that runs your agent; it
> doesn't load `.env` files automatically. If you keep the key in a `.env` file, load it
> yourself, for example with the `dotenv` package, before calling the SDK.

---

## File 1 — `codebuddy/config.py`

Budget: 60 lines of code, excluding comments and blank lines.

Write a module docstring. Then implement exactly this public surface.

```python
class CodebuddyError(Exception):
    """An error the user can act on. The CLI prints its message and exits non-zero."""

def load_env() -> None: ...
def resolve_model(cli_value: str | None) -> str: ...
def sdk_env() -> dict[str, str]: ...
def preflight() -> None: ...
def explain(exc: BaseException) -> str: ...
```

Behaviour, exactly:

1. `load_env()` calls `dotenv.load_dotenv` on `<project root>/.env`. Derive the project
   root from `__file__`. The project root is the parent of the `codebuddy` package.
   Do not fail when the file is absent.

2. `resolve_model(cli_value)` returns the first value that is set, in this order:
   `cli_value`, then `os.environ["CODEBUDDY_MODEL"]`, then the literal
   `"claude-opus-5"`. Ignore empty strings.

3. `sdk_env()` returns a dictionary for `ClaudeAgentOptions.env`. Copy across only these
   variables, and only when they are set and non-empty: `ANTHROPIC_API_KEY`,
   `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`. Return an empty dictionary when none are
   set. Never log a value. Never raise.

4. `preflight()` raises `CodebuddyError` with an actionable message in one case only:
   `import claude_agent_sdk` fails. The message must tell the user to run
   `pip install -r requirements.txt`.
   Do not check credentials here. The local `claude` CLI may hold its own login, so an
   unset `ANTHROPIC_API_KEY` is not an error.

5. `explain(exc)` returns a short, actionable string. Handle the classes from Excerpt H.
   Order the checks most specific first: `ResultError`, then `ProcessError`, then
   `CLINotFoundError`, then `CLIConnectionError`, then a generic fallback.
   For `CLIConnectionError`, test whether the message contains the text
   `Refusing to execute batch script`. When it does, tell the user to install Claude Code
   natively with `irm https://claude.ai/install.ps1 | iex`, or to set `cli_path` to a
   `claude.exe`.
   Import the exception classes inside the function body, not at module import time, so
   that `explain` still works when the SDK is missing.

---

## File 2 — `codebuddy/observability.py`

Budget: 90 lines of code, excluding comments and blank lines.

This module has one job. It makes every tool interaction visible. It reports through
**two independent channels**. Implement both. Comment why both exist.

```python
class ToolCallLogger:
    def __init__(self, quiet: bool = False, max_value_chars: int = 120,
                 max_line_chars: int = 220) -> None: ...

    def hooks(self) -> dict: ...
    def render(self, message: object) -> None: ...
    def summary(self) -> str: ...
```

### Channel 1 — hooks

`hooks()` returns a dictionary suitable for `ClaudeAgentOptions.hooks`:

```python
{
    "PreToolUse":  [HookMatcher(hooks=[self._on_pre_tool_use])],
    "PostToolUse": [HookMatcher(hooks=[self._on_post_tool_use])],
}
```

Register **no matcher**. The reason is in Excerpt D. An omitted matcher fires for every
tool call, which is what a transparency layer needs. A matcher would silently miss tools,
including MCP tools.

`_on_pre_tool_use(input_data, tool_use_id, context)`:

- Guard first. When `input_data.get("hook_event_name")` is not `"PreToolUse"`, return `{}`.
- Read `tool_name` and `tool_input`.
- Print one line. Show an arrow, the tool name, and the truncated inputs.
- Mark MCP tools visibly. A tool name that starts with `mcp__` is an MCP tool.
- Increment a per-tool counter. Keep a separate counter for MCP tools and built-in tools.
- Store `tool_use_id` with a monotonic start time. The post hook reports the duration.
- **Return `{}` and nothing else.**

`_on_post_tool_use(input_data, tool_use_id, context)`:

- Print one line. Show a return arrow, the tool name, the elapsed milliseconds, and a
  short size or status of the result.
- **Return `{}` and nothing else.**

Both callbacks must be `async def`.

### Truncation rules

Write one private helper for truncation. It must do all of the following.

- Render `tool_input` as compact `key=value` pairs. Do not print raw JSON.
- Cut each individual value at `max_value_chars`. Append three ASCII dots.
- Cut the whole assembled line at `max_line_chars`. Append three ASCII dots.
- Replace newlines and carriage returns with a single space before you cut.
- Never raise on an unexpected input shape. Fall back to a truncated `repr()`.

Use ASCII characters only in all console output. Do not use a Unicode ellipsis, box
drawing, or emoji. The Windows console default code page cannot always encode them, and
an encoding error would crash the run.

### Channel 2 — the message stream

`render(message)` inspects one message from the `query()` async iterator. It prints a
human-readable line. Handle these cases and no others.

- `SystemMessage` with `subtype == "init"`. Print the MCP server names with their status.
  Print the discovered tool names that start with `mcp__`. Use `message.data` as shown in
  Excerpt F. This line is the live proof of MCP schema discovery. Label it clearly.
- `AssistantMessage`. For each block, print `TextBlock` text. Print a marker for
  `ToolUseBlock`. Skip `ThinkingBlock`.
- `UserMessage`. Print a marker for each `ToolResultBlock`. State whether it is an error.
- `ResultMessage`. Print the subtype, the turn count, and the cost, when those attributes
  exist. Use `getattr` with a default, because attribute names vary by SDK version.

Use `isinstance` checks against the imported classes. Import them at module top level.

`quiet=True` suppresses everything except the init line and the result line.

### `summary()`

Return a one-line string. Include the total tool-call count. Include the count per tool
name, sorted by descending count. Include the built-in versus MCP split.

---

## Commenting requirements

This is the graded part of the task.

1. Every call into the Claude Agent SDK gets a **WHY** comment, not a WHAT comment.
   Bad: `# register the hooks`. Good: `# No matcher: an omitted matcher fires for every
   tool call, so nothing escapes the log. A matcher would silently skip MCP tools.`
2. Add a block comment above `hooks()`. Explain in three or four sentences how tool-call
   events surface in the SDK. It must state the difference between the two channels.
   A hook runs inside this process, synchronously, **before** the call, and it can block
   or rewrite the call. A stream message is the after-the-fact transcript and it can
   change nothing.
3. Add a comment on both `return {}` statements. State that `{}` means "allow, no change".
   State that returning `permissionDecision: "allow"` instead would widen the tool surface
   and skip later deny rules. Never return `permissionDecision` from these hooks.
4. Add a comment on the `explain` chain. State why `ResultError` is caught before
   `ProcessError`.
5. Reference the exact doc URL in a comment wherever a non-obvious API shape is used,
   for example `message.data["mcp_servers"]`.

Keep the prose in the comments simple and direct. Use short sentences. Use the active
voice.

---

## Acceptance criteria

The reviewer runs these checks. All must pass.

1. `codebuddy/config.py` and `codebuddy/observability.py` exist.
2. `python -m compileall -q codebuddy` reports no error.
3. `grep -n 'HookMatcher(hooks=' codebuddy/observability.py` matches twice. Neither match
   passes a `matcher=` argument.
4. The hooks never return a permission decision. Outside comments, the string
   `permissionDecision` does not appear in `codebuddy/observability.py`.
5. Both hook callbacks are declared with `async def`.
6. `grep -n 'code.claude.com' codebuddy/observability.py` returns at least one line.
7. `config.explain` handles all four class names from Excerpt H. Verify by grep. The names
   `ResultError`, `ProcessError`, `CLINotFoundError`, and `CLIConnectionError` all appear.
8. `grep -n 'Refusing to execute batch script' codebuddy/config.py` returns one line.
9. `resolve_model(None)` returns `claude-opus-5` when `CODEBUDDY_MODEL` is unset.
   `resolve_model("x")` returns `"x"`.
10. `sdk_env()` never returns a key whose value is an empty string.
11. Importing `codebuddy.config` succeeds even when `claude_agent_sdk` is not installed.
    Check with `python -c "import codebuddy.config as c; print(c.resolve_model(None))"`.
12. The code line count, excluding comments and blank lines, is at most 60 for
    `config.py` and at most 90 for `observability.py`. Check each file with
    `grep -vE '^[[:space:]]*(#|$)' <file> | wc -l`.
13. Every SDK call site has a comment above it or on it that gives a reason.
14. No console output string contains a non-ASCII character. Check with
    `grep -nP '[^\x00-\x7F]' codebuddy/observability.py`, which must return nothing.

## Out of scope

Do not create `permissions.py`, `mcp.py`, `__main__.py`, or any command module.
Do not create `README.md`, `DECISIONS.md`, or `COORDINATION.md`.
Do not modify anything under `sample-legacy-app/`.
Do not run `git add` or `git commit`.
You may create a virtual environment at `projects/codebuddy/.venv` and run
`pip install -r requirements.txt` inside it if you need to verify an import.

## When you finish

List the files you created. Print the result of every acceptance check you could run.
Print the two line counts from check 12. Then stop.
