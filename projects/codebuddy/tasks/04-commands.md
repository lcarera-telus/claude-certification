# Task 04 — CLI entry point and the three commands

Implement this specification exactly. Do not read the other files in `tasks/`.
This specification is the complete contract. Ask no questions. Write the files.

All paths below are relative to `projects/codebuddy/`.

## Goal

Create the CLI and the three commands:

- `codebuddy/__main__.py` — argument parsing, error handling, exit codes.
- `codebuddy/commands/_common.py` — one shared agent driver.
- `codebuddy/commands/explore.py`
- `codebuddy/commands/boilerplate.py`
- `codebuddy/commands/chores.py`

## Modules that already exist

Read these four files before you start. Use their public functions. Do not modify them.

- `codebuddy/config.py` — provides `CodebuddyError`, `load_env()`, `resolve_model()`,
  `sdk_env()`, `preflight()`, `explain()`.
- `codebuddy/observability.py` — provides `ToolCallLogger` with `hooks()`, `render()`,
  and `summary()`.
- `codebuddy/permissions.py` — provides `ToolPolicy`, `for_explore()`,
  `for_boilerplate()`, `for_chores()`, `bash_guard_hooks()`.
- `codebuddy/mcp.py` — provides `SERVER_NAME`, `filesystem_server()`,
  `allowed_tool_patterns()`, `unavailable_reason()`.

If a name in this spec does not match what those files export, use the name that the file
actually exports and note the difference in your final report.

---

## Step 0 — Create the environment first

The acceptance checks import `claude_agent_sdk`, so install it before you write anything.

```bash
cd projects/codebuddy
python -m venv .venv
.venv/Scripts/python.exe -m pip install --quiet -r requirements.txt
.venv/Scripts/python.exe -m pip show claude-agent-sdk
```

Use `.venv/Scripts/python.exe` for every check in this task. Record the installed
`claude-agent-sdk` version in your final report.

Read the four existing modules with the installed SDK available. If any name in this spec
disagrees with the real SDK surface, trust the SDK and report the difference.

---

## Reference documentation

Use the excerpts below. Do not use memory.

| Topic | URL |
|---|---|
| Overview | https://code.claude.com/docs/en/agent-sdk/overview |
| Quickstart | https://code.claude.com/docs/en/agent-sdk/quickstart |
| Python SDK reference | https://code.claude.com/docs/en/agent-sdk/python |
| Hooks | https://code.claude.com/docs/en/agent-sdk/hooks |
| MCP | https://code.claude.com/docs/en/agent-sdk/mcp |
| Permissions | https://code.claude.com/docs/en/agent-sdk/permissions |
| Tools reference | https://code.claude.com/docs/en/tools-reference |
| Troubleshooting | https://code.claude.com/docs/en/agent-sdk/troubleshooting |

### Excerpt A — the agentic loop, quoted from the quickstart

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage


async def main():
    # Agentic loop: streams messages as Claude works
    async for message in query(
        prompt="Review utils.py for bugs that would cause crashes. Fix any issues you find.",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Glob"],  # Auto-approve these tools
            permission_mode="acceptEdits",  # Auto-approve file edits
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")


asyncio.run(main())
```

Quoted: *"The `async for` loop keeps running as Claude thinks, calls tools, observes
results, and decides what to do next. ... The loop ends when Claude finishes the task or
hits an error."*

### Excerpt B — the `query()` signature

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
```

`SystemPromptPreset`, used to keep the Claude Code system prompt and add to it:

```python
class SystemPromptPreset(TypedDict):
    type: Literal["preset"]
    preset: Literal["claude_code"]
    append: NotRequired[str]
    exclude_dynamic_sections: NotRequired[bool]
```

### Excerpt D — path-scoped rules anchor at the session working directory

Quoted from the permissions page:

> Use `//path` for an absolute filesystem path ... With a single leading slash,
> `Edit(/secrets/**)` anchors at the rule's source instead. For rules passed through
> `allowed_tools` or `disallowed_tools`, that means the session's working directory, so
> the rule doesn't block `/secrets` on disk.

Consequence for this task: a relative rule such as `Edit(EXPLORATION.md)` resolves against
`ClaudeAgentOptions.cwd`. Therefore `cwd` decides where the rule points. Set `cwd`
deliberately in each command and comment why.

### Excerpt E — result subtypes

Quoted from the MCP page:

```python
if isinstance(message, ResultMessage) and message.subtype == "error_during_execution":
    print("Execution failed")
```

A successful run reports `subtype == "success"`.

### Excerpt F — hooks are a dictionary of lists

Quoted from the hooks page:

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

Quoted: *"When an event fires, all matching hooks run in parallel. For permission
decisions, the most restrictive result applies: a single `deny` blocks the tool call
regardless of what the other hooks return."*

Consequence: two sources both register `PreToolUse` in this project. The transparency
logger registers one matcher, and the chores safety guard registers another. You must
**merge the lists**. Replacing the key would silently drop one of them.

### Excerpt G — Windows console encoding

The Windows console default code page cannot encode many Unicode characters. Use ASCII
characters only in every string this program prints. Do not use a Unicode ellipsis, arrow,
box drawing, or emoji.

---

## File 1 — `codebuddy/commands/_common.py`

Budget: 30 lines of code, excluding comments and blank lines.

```python
def merge_hooks(*hook_dicts: dict | None) -> dict: ...

async def run_agent(
    *,
    prompt: str,
    policy,                 # permissions.ToolPolicy
    logger,                 # observability.ToolCallLogger
    model: str,
    cwd: str,
    mcp_servers: dict | None = None,
    extra_allowed: list[str] | None = None,
    extra_hooks: dict | None = None,
    system_prompt_append: str | None = None,
    max_turns: int | None = None,
) -> int: ...
```

`merge_hooks` takes several hook dictionaries and returns one dictionary. For a key that
appears in more than one input, concatenate the lists. Ignore `None` inputs.
Add a comment stating that a plain `dict.update` would drop a matcher, per Excerpt F.

`run_agent`:

1. Build `ClaudeAgentOptions`. Set `allowed_tools` to `policy.allowed_tools` plus
   `extra_allowed`. Set `disallowed_tools`, `permission_mode`, `model`, `cwd`, and
   `env=config.sdk_env()`.
2. Set `mcp_servers` only when `mcp_servers` is truthy.
3. Set `hooks=merge_hooks(logger.hooks(), extra_hooks)`.
4. Set `system_prompt` to a `claude_code` preset with `append=system_prompt_append` when
   that argument is given. Otherwise leave `system_prompt` unset.
   Comment why the preset is used: it keeps Claude Code's own tool-use guidance, and the
   append adds only the task-specific rules.
5. Set `max_turns`. Set `max_budget_usd` from the environment variable
   `CODEBUDDY_MAX_USD`, defaulting to `2.0`. Comment that this is a hard cost ceiling and
   a reliability control, not a performance tuning knob.
6. Set `stderr` to a callback that stores the last few stderr lines. Print them only when
   the run ends in a failure. Comment why: the troubleshooting page states that
   `ProcessError.stderr` is fixed placeholder text, so a `stderr` callback is the only way
   to see what the CLI actually wrote.
7. Iterate `async for message in query(prompt=prompt, options=options)` and call
   `logger.render(message)` for every message.
8. Return `0` when the final `ResultMessage.subtype` is `"success"`. Return `1` otherwise.
   Return `1` when no `ResultMessage` arrived at all.

---

## File 2 — `codebuddy/commands/explore.py`

Budget: 55 lines of code, excluding comments and blank lines.

```python
async def run(target: str, *, model: str, quiet: bool) -> int: ...
```

Behaviour:

1. Resolve `target`. Raise `CodebuddyError` when it is not an existing directory. The
   message must name the path.
2. Build the policy with `permissions.for_explore()`.
3. Call `mcp.filesystem_server(target)`. When it returns `None`, print
   `mcp.unavailable_reason()` as a warning and remove the `mcp__fs__*` entry from the
   allowed tools. The run must continue on built-in tools only.
4. Set `cwd` to the resolved target directory. Comment why: per Excerpt D, the relative
   rule `Edit(EXPLORATION.md)` anchors at the session working directory, so this is what
   makes the summary land inside the explored repository and nowhere else.
5. `max_turns=25`.
6. Run the agent. Then check that `<target>/EXPLORATION.md` exists. When it is missing,
   print a warning that names the expected path. Do not raise.
7. Print `logger.summary()` at the end.

### The prompt

Write the prompt so the transcript teaches tool choice. It must instruct the agent, in
this order:

1. Use **Glob** to list the file structure. State in the prompt that Glob is the right
   tool because it returns paths sorted by modification time without spawning a shell.
2. Use **Grep** to find entry points and every `TODO` and `FIXME`. State that Grep is the
   right tool rather than a Bash `grep` because it is a first-class tool with structured
   output, it needs no shell, and it works the same on Windows where `grep` may be absent.
3. Use **Read** on only the few files that matter. State that reading everything wastes
   the context window.
4. Use one **MCP filesystem tool** to list the directory, and say plainly in the summary
   which MCP tool was used and how its result compared with the built-in equivalent.
5. Write `EXPLORATION.md` in the repository root with these sections: Purpose, Structure,
   Entry points, Conventions detected, The confusing part, Open TODOs and FIXMEs, and
   Risks. Require the Conventions section to state the test file naming pattern, the
   import style, and the docstring style, because a later command copies them.
6. Tell the agent to trust the source code over any README prose, and to say so
   explicitly when the two disagree.

Keep the prompt in a module-level constant. Format it with the target path.

---

## File 3 — `codebuddy/commands/boilerplate.py`

Budget: 45 lines of code, excluding comments and blank lines.

```python
OUTPUT_DIR = "codebuddy_generated"
TESTS_DIR = "codebuddy_generated/tests"

async def run(component: str, *, target: str, model: str, quiet: bool) -> int: ...
```

Behaviour:

1. Validate `component`. Accept only lowercase letters, digits, and underscores. Raise
   `CodebuddyError` naming the rule when it does not match.
2. Look for `<target>/EXPLORATION.md`. When it is missing, raise `CodebuddyError` whose
   message tells the user to run `codebuddy explore <target>` first. The message must be
   one actionable sentence. Do not raise a traceback.
3. Build the policy with `permissions.for_boilerplate(OUTPUT_DIR, TESTS_DIR)`.
4. Set `cwd` to the project root, which is the parent of the `codebuddy` package.
   Comment why: the `Edit(...)` rules are relative, so the project root is what scopes the
   writes to `codebuddy_generated/`.
5. `max_turns=15`.
6. The prompt must instruct the agent to read `<target>/EXPLORATION.md` first, take the
   conventions from its Conventions section, then use **Write** twice: once for
   `codebuddy_generated/<component>.py` and once for
   `codebuddy_generated/tests/test_<component>.py`. State in the prompt that Write is
   correct here rather than a Bash heredoc, because Write is a first-class tool that the
   permission layer can scope by path.
7. After the run, print which of the two expected files exist.

---

## File 4 — `codebuddy/commands/chores.py`

Budget: 55 lines of code, excluding comments and blank lines.

```python
async def run(*, target: str, model: str, quiet: bool) -> int: ...
```

Behaviour:

1. Resolve `target`. Compute the project root, which is the parent of the `codebuddy`
   package. Raise `CodebuddyError` when the resolved target is not inside the project
   root. The message must name both paths. Comment why this check exists: the chores
   policy allows `Bash(sed:*)`, and `sed -i` can rewrite any existing file it can reach,
   so the code must bound the target itself.
2. Build the policy with `permissions.for_chores(<target path relative to the project
   root, using forward slashes>)`.
3. Pass `extra_hooks=permissions.bash_guard_hooks()`. Comment that `run_agent` merges this
   with the logger hooks, and that both fire for a Bash call.
4. Set `cwd` to the project root, so `git status` and `git diff` run inside the repository.
5. `max_turns=20`.
6. The prompt must instruct the agent to do three things in order:
   a. Find files with CRLF line endings under the target, then rewrite them to LF.
   b. Run `python -m black` on the target.
   c. Summarise what changed using `git diff --stat`, and list each file with the reason
      it changed.
   Tell the agent that its Bash surface is a short allowlist, that anything outside it is
   denied, and that it must report a denial rather than work around it.
7. Print `logger.summary()` at the end.

---

## File 5 — `codebuddy/__main__.py`

Budget: 65 lines of code, excluding comments and blank lines.

### Required header comment block

The very top of the file, before any import, must be a comment block that lists every
documentation URL used to build this project. Include all eight URLs from the Reference
documentation table above, each on its own line. Add one line stating the date the docs
were read: `2026-08-30`. Add one line stating that the SDK API changes often, so these
URLs are the source of truth rather than memory.

### CLI

Use `argparse`. Three subcommands.

```
codebuddy explore <path> [--model M] [--quiet]
codebuddy boilerplate <component-name> [--path DIR] [--model M] [--quiet]
codebuddy chores [--path DIR] [--model M] [--quiet]
```

- `--path` defaults to `sample-legacy-app` for both `boilerplate` and `chores`, resolved
  against the project root.
- `--model` defaults to `None` and is passed to `config.resolve_model`.
- `--quiet` is a store-true flag passed to the command.
- Running with no subcommand prints the help text and exits with code `2`.

### `main()`

1. Parse the arguments first, before any preflight. Resolve the model.
   Add a comment saying why the order matters: `--help` and an argument error must still
   work when the SDK is not installed, so `preflight()` must not run before parsing.
   A `preflight()` call placed first would turn every `--help` into an install error.
2. Call `config.load_env()`, then `config.preflight()`.
3. Build one `ToolCallLogger`. Pass it to the command.
4. Call `asyncio.run(<command>.run(...))` and use the returned integer as the exit code.
5. Wrap everything in one `try`. Catch `CodebuddyError` and print
   `f"codebuddy: {exc}"` to stderr, then exit `1`.
6. Catch `KeyboardInterrupt` and exit `130` with a short message.
7. Catch `BaseException` last, print `config.explain(exc)` to stderr, then exit `1`.
   Comment that `config.explain` translates the SDK exception classes into an action the
   user can take.
8. Add `if __name__ == "__main__": raise SystemExit(main())`.

---

## Commenting requirements

1. Every `ClaudeAgentOptions` field that is set gets a WHY comment. `cwd`, `max_turns`,
   `max_budget_usd`, `permission_mode`, and `hooks` all need one.
2. Every command module states, in a comment near its prompt constant, which built-in
   tools it expects the agent to use and why each one beats the alternative.
3. `explore.py` must carry the Grep versus Bash grep reasoning as a comment, and the Glob
   versus `ls` reasoning as a comment.
4. `_common.py` must carry the hook-merging reasoning as a comment.
5. Cite a `code.claude.com` URL in a comment wherever a non-obvious API shape is used.

Keep the comment prose simple and direct. Use short sentences. Use the active voice.

---

## Acceptance criteria

The reviewer runs these checks. All must pass.

1. All five files exist.
2. `.venv/Scripts/python.exe -m compileall -q codebuddy` reports no error.
3. `.venv/Scripts/python.exe -m codebuddy --help` prints help and lists the three subcommands.
   `.venv/Scripts/python.exe -m codebuddy explore --help` works. Same for the other two.
4. `.venv/Scripts/python.exe -m codebuddy` with no subcommand prints help and exits with code `2`.
5. The first non-blank line of `__main__.py` is a comment. The header block contains at
   least eight distinct `https://code.claude.com/` URLs and the date `2026-08-30`.
   Check with `grep -c 'https://code.claude.com/' codebuddy/__main__.py`.
6. `merge_hooks` concatenates. Verify with `python -c` that
   `merge_hooks({"PreToolUse": [1]}, {"PreToolUse": [2]})` equals
   `{"PreToolUse": [1, 2]}`, and that a `None` argument is ignored.
7. `boilerplate` fails cleanly when `EXPLORATION.md` is absent. Run
   `.venv/Scripts/python.exe -m codebuddy boilerplate demo_widget --path sample-legacy-app` while
   `sample-legacy-app/EXPLORATION.md` does not exist. It must print a single
   `codebuddy: ...` line naming `codebuddy explore`, exit `1`, and print no traceback.
8. `chores` refuses a target outside the project root. Run
   `.venv/Scripts/python.exe -m codebuddy chores --path C:/Windows`. It must print a single
   `codebuddy: ...` line naming both paths, exit `1`, and print no traceback.
9. `explore` fails cleanly on a missing directory. Run
   `.venv/Scripts/python.exe -m codebuddy explore no_such_dir_xyz`. Same expectations as check 8.
10. `grep -n 'Write(' codebuddy/permissions.py` still returns nothing. You did not modify
    that file.
11. Code line counts, excluding comments and blank lines, are within budget:
    `_common.py` at most 30, `explore.py` at most 55, `boilerplate.py` at most 45,
    `chores.py` at most 55, `__main__.py` at most 65. Check each with
    `grep -vE '^[[:space:]]*(#|$)' <file> | wc -l`.
12. No non-ASCII character appears in any of the five files. Check with
    `grep -rnP '[^\x00-\x7F]' codebuddy/`, which must return nothing.
13. The total for the whole package stays at or under 500. Check with
    `cat $(find codebuddy -name '*.py') | grep -vE '^[[:space:]]*(#|$)' | wc -l`.

Checks 7, 8, and 9 are the only ones that run the CLI. None of them reaches the Claude
API, because each must fail during validation. Do not run a command that reaches the API.
That costs money and it is task 05's job.

## Out of scope

Do not modify `config.py`, `observability.py`, `permissions.py`, or `mcp.py`.
Do not create `README.md`, `DECISIONS.md`, or `COORDINATION.md`.
Do not modify anything under `sample-legacy-app/`.
Do not run any command that calls the Claude API.
Do not run `git add` or `git commit`.

## When you finish

List the files you created. Print the result of every acceptance check. Print all five
line counts and the package total. Report any name mismatch you found between this spec
and the existing modules. Then stop.
