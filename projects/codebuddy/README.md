# codebuddy

A small CLI agent built on the **Claude Agent SDK**, written to be read rather than used.
It helps an engineer explore an unfamiliar codebase and automate a repetitive task, and it
prints every tool call it makes so that a learner can watch the agent work.

The project exists to make the Agent SDK's built-in tools concrete for the **Claude
Certified Architect – Foundations** exam. Exam scenario 4 is "Developer productivity:
codebase exploration, built-in tools (Read/Write/Bash/Grep/Glob), MCP servers". Every
design decision has a reason recorded in [`DECISIONS.md`](DECISIONS.md), and the
coordination log is in [`COORDINATION.md`](COORDINATION.md).

Documentation was read on **2026-08-30**. Verified against **`claude-agent-sdk 0.2.148`**
and **Claude Code 2.1.251**. The doc URLs used are listed at the top of
`codebuddy/__main__.py`, per the project brief.

---

## Quickstart

Prerequisites: Python 3.10 or later, and Node.js with `npx` for the MCP server. The Agent
SDK bundles a Claude Code binary on common platforms and otherwise finds `claude` on
`PATH`.

```bash
cd projects/codebuddy

python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS or Linux

cp .env.example .env      # optional, see Authentication below
```

Run the three commands against the bundled sample repository:

```bash
.venv/Scripts/python.exe -m codebuddy explore sample-legacy-app
.venv/Scripts/python.exe -m codebuddy boilerplate invoice_formatter --path sample-legacy-app
.venv/Scripts/python.exe -m codebuddy chores --path sample-legacy-app
```

Add `--quiet` to keep only the MCP discovery line and the final result line. Add
`--model claude-sonnet-5` to spend less.

### Authentication

The SDK reads credentials from the environment of the process that runs the agent. **It
does not read `.env` by itself**, so `codebuddy` loads `.env` with `python-dotenv` before
starting. Three variables are forwarded, and only when they are set and non-empty:

| Variable | Use |
|---|---|
| `ANTHROPIC_API_KEY` | First-party API key |
| `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` | A gateway, the pair used by the sibling exercises in this repository |

If none is set, `codebuddy` inherits whatever login the local `claude` CLI already holds.

### Cost

Each command makes real API calls. The runs recorded in `transcripts/` cost `$0.54`,
`$0.53`, and `$0.27`. Two ceilings bound this, and they fail differently:
`max_turns` bounds the loop, and `max_budget_usd` bounds the money. Set the latter with
`CODEBUDDY_MAX_USD`, default `2.0`.

---

## The three commands

Each command declares its own tool surface. There is no global policy, because the union of
three policies is the widest surface and a read-only survey should not carry shell access.

### `codebuddy explore <path>`

Maps an unfamiliar repository with Glob, Grep, Read, and one MCP filesystem tool, then
writes `EXPLORATION.md` into it.

| Setting | Value |
|---|---|
| Allowed | `Read`, `Glob`, `Grep`, `Edit(EXPLORATION.md)`, `mcp__fs__*` |
| Denied | `Bash`, `WebFetch`, `WebSearch` |
| Mode | `dontAsk` |
| Turn cap | 25 |

The generated report is real analysis, not a summary. On the bundled sample it located the
unreachable rebate branch, and it also found three problems nobody asked it to look for: an
empty cart is still charged a flat `4.25`, `config.discount_cap` is never applied on the
path that calculates money, and `round_money("abc")` raises an uncaught `ValueError`.

### `codebuddy boilerplate <component-name>`

Reads the Conventions section of `EXPLORATION.md`, then writes a module and its test with
`Write`.

| Setting | Value |
|---|---|
| Allowed | `Read`, `Glob`, `Grep`, `Edit(codebuddy_generated/**)`, `Edit(codebuddy_generated/tests/**)` |
| Denied | `Bash`, `WebFetch`, `WebSearch` |
| Mode | `dontAsk` |
| Turn cap | 15 |

Run without an `EXPLORATION.md` and it stops with one actionable line, not a traceback:

```
codebuddy: No EXPLORATION.md in ...\sample-legacy-app. Run: codebuddy explore ...\sample-legacy-app
```

The conventions transfer works. `sample-legacy-app/tests/test_utils.py` uses a module
docstring, `test_<function>_<case>` names, plain asserts, no class, and no fixture. The
generated `test_invoice_formatter.py` reproduces all five of those properties.

### `codebuddy chores`

Normalizes CRLF to LF, runs the formatter, and reports the diff per file.

| Setting | Value |
|---|---|
| Allowed | `Read`, `Glob`, `Grep`, `Edit(<target>/**)`, and only these shell prefixes: `Bash(git status:*)`, `Bash(git diff:*)`, `Bash(git ls-files:*)`, `Bash(sed:*)`, `Bash(<interpreter> -m black:*)`, `Bash(<interpreter> -m py_compile:*)` |
| Denied | `Bash(rm *)`, `Bash(rmdir *)`, `Bash(del *)`, `Bash(git push:*)`, `Bash(git commit:*)`, `Bash(git reset:*)`, `Bash(git checkout:*)`, `Bash(curl *)`, `WebFetch`, `WebSearch` |
| Mode | `dontAsk` |
| Turn cap | 20 |

---

## The permission model, and why it is layered

The SDK evaluates a tool request in a **fixed order of six steps**:

```
1. Hooks  ->  2. Deny rules  ->  3. Ask rules  ->  4. Permission mode  ->  5. Allow rules  ->  6. can_use_tool
```

Two consequences drive everything in this project. A call approved at any earlier step
**never reaches `can_use_tool`**. And a deny rule beats every permission mode, including
`bypassPermissions`.

`chores` is the only command with a shell, so it carries four guards. They are deliberately
redundant, because each fails in a different direction:

| Guard | Stops | Defeated alone by |
|---|---|---|
| Command-scoped allow list | Any command not named | A later change to a wider mode |
| Deny list (step 2) | Named destructive commands, in every mode | A destructive command nobody listed |
| `PreToolUse` hook (step 1) | Any command matching a destructive pattern | A pattern nobody thought of |
| Path check in Python | A target outside the project root | Nothing in the tool layer |

The fourth guard exists because `Bash(sed:*)` is not path-scoped: `sed -i` can rewrite any
existing file the process can reach. The bound has to live in code, not in a rule.

### Three rule-shape traps that fail silently

Each of these produces **no error**. The rule simply matches nothing.

1. **`Edit(path)`, never `Write(path)`.** `Edit(path)` rules govern every built-in tool
   that writes files, including `Write`. A `Write(path)` rule "is never matched by the file
   permission checks". Under `dontAsk` the write is then denied and the agent looks broken;
   under `acceptEdits` it succeeds and the rule looks like it worked.
2. **Forward slashes in rule paths.** A rule path is matched as a glob, and in a glob a
   backslash is an escape character. `Edit(sample-legacy-app\**)` allows no file at all.
   Hence `Path(...).as_posix()`.
3. **MCP globs must be anchored.** A glob is legal only after a literal `mcp__<server>__`
   prefix. `mcp__fs__*` works; a bare `mcp__*` or `*` is ignored with a startup warning and
   grants nothing.

Relative rules anchor at `ClaudeAgentOptions.cwd`, so each command sets `cwd` on purpose.
`explore` sets it to the directory being explored, which is what makes `Edit(EXPLORATION.md)`
land inside that repository and nowhere else.

---

## Tool-use transparency: how tool events surface in the SDK

`codebuddy/observability.py` reports through **two independent channels**. They are not
redundant, and the difference is the point.

**Channel 1, hooks.** A `PreToolUse` and a `PostToolUse` hook, both registered with **no
matcher**, so they fire for every tool call including MCP ones.

```python
{
    "PreToolUse":  [HookMatcher(hooks=[self._on_pre_tool_use])],
    "PostToolUse": [HookMatcher(hooks=[self._on_post_tool_use])],
}
```

A hook runs **inside your process, synchronously, before the tool executes**. It holds the
call open, so it can deny it, rewrite its input, or start a timer. Both callbacks here
return `{}`, which means "allow, no change". They must never return
`permissionDecision: "allow"` — that would widen the tool surface. A logger observes; it
does not decide.

**Channel 2, the message stream.** `query()` yields messages: `SystemMessage(subtype="init")`
carries the MCP server statuses and the discovered tool list, `AssistantMessage` carries
`ToolUseBlock`s, `UserMessage` carries `ToolResultBlock`s, and `ResultMessage` carries the
subtype, turn count, and cost. A stream message is the after-the-fact transcript and can
change nothing.

A learner who watches only the stream never learns that hooks are an interception point.
That is why both channels are printed.

**Why a hook and not `can_use_tool`.** `can_use_tool` would miss calls. Anything approved by
an allow rule, by `acceptEdits`, or by `bypassPermissions` never reaches it. A `PreToolUse`
hook runs before all of those steps.

**Two `PreToolUse` sources must be merged, not replaced.** The logger registers one matcher
and the `chores` safety guard registers another. `merge_hooks` concatenates the lists,
because a plain `dict.update` would silently drop one of them — losing either the audit
trail or the destructive-command guard, with no error.

---

## MCP integration

**What MCP is.** The Model Context Protocol is an open standard for connecting an agent to
external tools and data. An MCP server is a separate program. It advertises a set of tools
with JSON schemas, and the agent calls them over the protocol. This lets an agent reach a
database, a ticket tracker, or a filesystem without you writing a tool implementation.

`codebuddy` connects one stdio server, scoped to the single directory being explored:

```python
{"fs": {"command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "<absolute target>"]}}
```

### Built-in tools versus MCP tools

| | Built-in tool | MCP tool |
|---|---|---|
| Where it runs | In the agent process | In a separate server process |
| Name | `Read`, `Glob`, `Grep`, `Write`, `Bash` | `mcp__<server>__<tool>` |
| Availability | Always present | Only if its server connects |
| Schema | Fixed, shipped with the SDK | Discovered from the server at connect time |
| Permission | `Read`/`Edit` path rules, `Bash(cmd:*)` prefixes | Needs an explicit `allowed_tools` entry. `acceptEdits` does **not** cover MCP tools |
| Failure mode | Denied or errors | Server can also be `pending`, `failed`, `needs-auth`, or `disabled` |

Note the third row of asymmetry: a built-in tool cannot fail to exist, so there is no
degradation path for it. When `npx` is missing, `explore` prints one warning, **strips
`mcp__fs__*` from the allow list**, and continues on built-in tools only. Leaving a rule
that names a server which never started would misreport the real tool surface.

### How the SDK discovers MCP tool schemas

At startup the SDK connects each configured server and asks it for its tool list. The result
arrives on the `system` message with `subtype == "init"`, in `message.data["mcp_servers"]`
and `message.data["tools"]`. A stdio server delays the first turn until it connects, with a
default 30-second `MCP_TIMEOUT` deadline. `"pending"` at init is not a failure on its own;
only `"failed"` and `"needs-auth"` are.

**Discovery is a two-stage process, and the transcript proves it.** MCP tool *search* is
enabled by default, so the discovered definitions are withheld from the context window and
loaded only on demand. The agent therefore fetches a schema before it can call the tool:

```
-> [builtin] ToolSearch query=select:mcp__fs__list_directory max_results=1
<- ToolSearch 7ms ok 111 chars
-> [mcp] mcp__fs__list_directory path=...
<- mcp__fs__list_directory 14ms ok 181 chars
```

So stage one lists the *names* at init, and stage two loads the *schema* on first use. That
deferral is what keeps a large MCP surface from filling the context window.

### `strict_mcp_config` is a context control, not a permission control

An early run of this project printed **33 MCP servers and about 190 tool schemas**, because
`setting_sources` was unset and the SDK loaded the machine's global MCP configuration. The
permission layer held perfectly: `allowed_tools` granted only `mcp__fs__*`, so the agent
could not call any of the foreign tools. Their schemas still consumed context.

The fix is a different lever from `allowed_tools`:

```python
strict_mcp_config=True,   # only the servers passed in mcp_servers; ignore all other config
setting_sources=[],       # load no user, project, or local settings file
```

`allowed_tools` decides **what may run**. `strict_mcp_config` decides **what is even
described to the model**. Confusing the two is easy and costly.

---

## Annotated transcript of one full `explore` run

The unedited console output is in [`transcripts/explore-run.txt`](transcripts/explore-run.txt).
Long paths are shortened below with `...`; nothing else is changed.

```
[mcp-discovery] servers: fs=connected
```
**Channel 2, the init message.** One server, connected. This line is `strict_mcp_config`
working: without it, the reader's own connectors appear here and the transcript stops being
reproducible.

```
[mcp-discovery] tool schemas: ['mcp__fs__create_directory', 'mcp__fs__directory_tree',
 'mcp__fs__edit_file', ... 14 names, all mcp__fs__*]
```
Schema discovery, stage one. These names came from the server, not from `codebuddy`. Note
that 14 tools were advertised and the allow rule permits all of them, but the run uses one.

```
[claude] I'll start by surveying the file structure with Glob.
[stream] tool_use Glob
-> [builtin] Glob pattern=**/* path=...
<- Glob 83ms ok 561 chars
[stream] tool_result ok
```
Four lines for one tool call, from three sources. `[claude]` and `[stream]` are channel 2.
`->` is the `PreToolUse` hook firing **before** the call; `<-` is `PostToolUse` firing after,
which is where the 83 ms comes from. Glob, not a shell `ls`: it needs no shell, returns
paths sorted by modification time, and behaves identically on Windows.

```
[stream] tool_use Glob
-> [builtin] Glob pattern=**/*.py path=...
[claude] Glob shows 7 Python files, a README, and an existing EXPLORATION.md.
         Now Grep for entry points and TODO/FIXME markers.
```
A second Glob narrows to `*.py`. The agent states its plan before acting, so the transcript
records intent as well as action.

```
-> [builtin] Grep pattern=__main__|def main|app\.run|argparse|sys\.argv|if __name__ glob=*.py output_mode=content
<- Grep 143ms ok 156 chars
-> [builtin] Grep pattern=TODO|FIXME|XXX|HACK output_mode=content -n=True
<- Grep 142ms ok 287 chars
```
Grep, not a shell `grep`. It is a first-class tool with structured output and line numbers,
it needs no shell, and on Windows the `grep` binary is often simply absent. The `explore`
policy denies `Bash` outright, so a shell `grep` would have been refused anyway. Note the
first pattern includes `app\.run` — the agent is checking the README's claim against the
code. It searched for `XXX` and `HACK` too, which the prompt never asked for.

```
-> [builtin] ToolSearch query=select:mcp__fs__list_directory max_results=1
<- ToolSearch 7ms ok 111 chars
```
Schema discovery, stage two. The name was known at init; the schema is loaded here, on
demand, immediately before use.

```
-> [builtin] Read file_path=...   <- Read 32ms ok 661 chars
-> [builtin] Read file_path=...   <- Read 31ms ok 1187 chars
-> [builtin] Read file_path=...   <- Read 25ms ok 557 chars
```
Read is used **sparingly and late**, only on files the Glob and Grep passes proved to
matter. Read pulls a whole file into the context window, so reading everything first would
leave no room to write the report.

```
-> [mcp] mcp__fs__list_directory path=...
<- mcp__fs__list_directory 14ms ok 181 chars
```
The MCP call. The `[mcp]` tag comes from the hook checking the `mcp__` name prefix. It
returned 181 characters where the built-in Glob returned 561, which is the built-in versus
MCP comparison the report is asked to make.

```
[result] subtype=success num_turns=17 total_cost_usd=0.542284
tool calls: 16 (builtin 15, mcp 1) [Read x8, Grep x3, Glob x2, ToolSearch x1, Write x1,
                                    mcp__fs__list_directory x1]
```
`ResultMessage` closes channel 2 with the turn count and cost. The final line is the
logger's own tally, built from the hook counters. The shape is the lesson: **8 Reads after
5 cheap search calls**, and exactly 1 of 16 calls went to MCP.

---

## CCFA concept map

Where each SDK feature appears in this repository. Domain numbers are the exam's five
weighted domains.

| SDK feature | Where | What to notice | Domain |
|---|---|---|---|
| `query()` agentic loop | `commands/_common.py` `run_agent` | The only place this package calls the SDK | 1 |
| `ClaudeAgentOptions` | `commands/_common.py` | Every field set carries a WHY comment | 1 |
| Built-in `Glob` | `commands/explore.py` | Chosen over shell `ls`: no shell, mtime-sorted | 4 |
| Built-in `Grep` | `commands/explore.py` | Chosen over shell `grep`: structured output, absent binary on Windows | 4 |
| Built-in `Read` | `commands/explore.py` | Used late and sparingly, to protect the context window | 5 |
| Built-in `Write` | `commands/boilerplate.py` | Path-scopeable, unlike a Bash heredoc | 2 |
| Built-in `Bash` | `commands/chores.py` | Command-prefix allowlist, never bare `Bash` | 2 |
| Allow rules | `permissions.py` | `allowed_tools`; unlisted tools fall through to the mode | 2 |
| Deny rules | `permissions.py` | Bare name removes the tool; scoped name denies the call | 2 |
| Path-scoped rules | `permissions.py` `for_explore` | `Edit(...)` governs `Write`; `Write(...)` matches nothing | 2 |
| Glob escaping in rules | `commands/chores.py` `as_posix()` | A backslash in a rule path is an escape character | 2 |
| `permission_mode` | `permissions.py` | `dontAsk` for a non-interactive CLI | 3 |
| Six-step evaluation order | `DECISIONS.md` ADR-003 | Hooks first; deny beats every mode | 1 |
| `PreToolUse` hook, observing | `observability.py` | No matcher, returns `{}` | 1 |
| `PostToolUse` hook | `observability.py` | Supplies the duration; keyed on `tool_use_id` for parallel calls | 1 |
| `PreToolUse` hook, denying | `permissions.py` `_deny_destructive_bash` | Step 1, so it survives `bypassPermissions` | 1 |
| `HookMatcher` semantics | `observability.py` vs `permissions.py` | No matcher to observe; `matcher="Bash"` to adjudicate | 1 |
| Hook merging | `commands/_common.py` `merge_hooks` | `dict.update` would silently drop a matcher | 1 |
| MCP stdio server | `mcp.py` | Bare `npx`, absolute target, resolved once | 2 |
| MCP tool naming | `mcp.py`, `permissions.py` | `mcp__fs__*` must be anchored to a literal server segment | 2 |
| MCP schema discovery | `observability.py` `render` | Init message, then `ToolSearch` on demand | 2 |
| MCP degradation | `commands/explore.py` | Warn, strip the dead allow rule, continue | 5 |
| `strict_mcp_config` | `commands/_common.py` | Context control, distinct from `allowed_tools` | 5 |
| `setting_sources` | `commands/_common.py` | `[]` loads no settings file, so runs are reproducible | 3 |
| `SystemPromptPreset` | `commands/_common.py` | `claude_code` preset plus `append`, not a replacement string | 4 |
| Message stream types | `observability.py` `render` | `SystemMessage`, `AssistantMessage`, `UserMessage`, `ResultMessage` | 1 |
| `ResultMessage` subtype | `commands/_common.py` | `success` is the only exit-code-0 case | 5 |
| `max_turns`, `max_budget_usd` | `commands/_common.py` | Two ceilings that fail differently | 5 |
| `cwd` and rule anchoring | `commands/explore.py`, `chores.py` | `cwd` decides where a relative rule points | 2 |
| `env` passthrough | `config.py` `sdk_env` | Reaches the CLI process, **not** the Bash tool's shell | 3 |
| `stderr` callback | `commands/_common.py` | The only way to see real CLI stderr | 5 |
| SDK error classes | `config.py` `explain` | `ResultError` before `ProcessError`; `CLINotFoundError` before `CLIConnectionError` | 5 |
| Prompt-driven tool choice | `commands/*.py` `PROMPT` | The prompt names the tool and the reason | 4 |

---

## Known limitations

- **`env` does not reach the agent's shell.** `ClaudeAgentOptions.env` is merged into the
  spawned CLI process, but Claude Code rebuilds the `Bash` tool's shell `PATH` from its own
  snapshot. This is why `chores` names its interpreter absolutely instead of relying on
  `PATH`. A tooling command must be reachable without `PATH` help.
- **An interpreter path containing a space would break the formatter step.** A quoted
  command would not prefix-match the allow rule. `chores` detects this, warns, and falls
  back to bare `python`.
- **`git diff --stat` reports nothing here** while `projects/codebuddy/` is untracked, since
  `git diff` covers tracked files only. The CRLF byte counts are the evidence instead.
- **`transcripts/chores-run.txt` contains non-ASCII bytes.** They come from black's own
  success message, which prints emoji. No file under `codebuddy/` contains a non-ASCII
  character.
- **Model choice is not tuned.** The default is `claude-opus-5`. `claude-sonnet-5` costs
  less for repeat demonstrations.

---

## Layout

```
projects/codebuddy/
├── README.md                    this file
├── DECISIONS.md                 ADR-style records, including tool permission scoping
├── COORDINATION.md              dispatch and review log for every work package
├── tasks/                       the task specs the implementer worked from
├── requirements.txt             claude-agent-sdk, python-dotenv, black
├── .env.example
├── codebuddy/                   474 code lines, excluding comments
│   ├── __main__.py              CLI; the doc URLs used are at the top of this file
│   ├── config.py                env loading, model choice, error translation
│   ├── observability.py         the two transparency channels
│   ├── permissions.py           one policy per command, plus the destructive-shell guard
│   ├── mcp.py                   the filesystem MCP server, with degradation
│   └── commands/                _common.py driver, explore, boilerplate, chores
├── sample-legacy-app/           the demo target: 7 files, one deliberately confusing module
├── codebuddy_generated/         output of `boilerplate`, gitignored
└── transcripts/                 unedited console output of each command, plus smoke-results.md
```

`sample-legacy-app/` is deliberately under-commented and its `README.md` is deliberately
stale: it claims three modules where there are five, and tells the reader to call
`app.run()` where the real entry point is `app.main()`. `explore` has to prefer the source
over the prose, and it does. See ADR-008.
