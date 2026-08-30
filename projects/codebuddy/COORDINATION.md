# COORDINATION.md — dispatch and review log

This file records every task dispatch, every review verdict, and every iteration.
The newest entry is at the bottom of the log.

## Roles

| Role | Who | May write |
|---|---|---|
| Coordinator | Claude Code, this session | Plans, task specs, reviews, `README.md`, `DECISIONS.md`, `COORDINATION.md` |
| Implementer | Claude Code, separate Orca terminal | All source, tests, configs, and `sample-legacy-app/` |

The coordinator writes no source code and no tests.

## Deviation from the original brief

The brief named **Codex** as the implementer. Codex is not installed on this machine.
Evidence collected on 2026-08-30:

- `Get-Command codex` reports `NOT FOUND`.
- `npm ls -g --depth=0` does not list any Codex package.
- `C:/Users/lcare/.codex` does not exist.
- `orca account list` reports `No managed Codex accounts.`

The user chose **Claude Code in a separate Orca terminal** as the replacement implementer.
The rest of the protocol did not change. Specs stay the sole contract. The coordinator
reads and reviews every output against the acceptance criteria.

## Dispatch mechanics

```
orca terminal create --worktree active --title "IMPL-codebuddy" --json
orca terminal send   --terminal <handle> --text "<command>" --enter --json
orca terminal wait   --terminal <handle> --for exit --timeout-ms <ms> --json
orca terminal read   --terminal <handle> --json
```

The implementer runs `claude -p` in non-interactive print mode. Therefore each dispatch
is one shot with a readable transcript. The implementer receives one instruction: read
the spec file and implement it. No design context passes through the prompt.

## Log

### 2026-08-30 — Setup

- Researched the current Claude Agent SDK documentation. Recorded the URLs in the plan.
- Verified the toolchain: `claude` 2.1.251, Python 3.13.14, Node 22.14.0, npx 10.9.2.
- Verified `@modelcontextprotocol/server-filesystem` on npm at version `2026.7.10`.
- Confirmed `claude-agent-sdk` is not yet installed.
- Wrote `tasks/01-scaffold-and-sample-app.md`.
- Created the implementer terminal.

### 2026-08-30 — Task 01 dispatch and review

**Dispatch.** Terminal `term_588203f6`. Command: `claude -p` in print mode, with
`--permission-mode acceptEdits` and a narrow `--allowedTools` list.

**Verdict: PASS.** The coordinator re-ran the acceptance checks and did not rely on the
implementer report. Results:

| # | Check | Result |
|---|---|---|
| 1 | All files exist | PASS |
| 2 | `python -m compileall -q` | PASS |
| 3 | `app.main()` runs | PASS, printed a quote dictionary |
| 4 | Exactly two CRLF files | PASS, `handlers.py` and `utils.py` only |
| 5 | One TODO and one FIXME | PASS |
| 6 | Both markers only in `legacy_pricing.py` | PASS |
| 7 | Unreachable final branch | PASS, `d > 10` then `d > 5` then `d > 20` |
| 8 | `black --check` fails | DEFERRED, black is not installed yet |
| 9 | README makes two false claims | PASS, claims three modules and `app.run()` |
| 10 | No explanatory comments in the sample app | PASS, only the TODO and the FIXME |
| 11 | No SDK import | PASS |

`legacy_pricing.py` reached four levels of nesting, four single-letter parameters, and ten
unexplained numeric literals. That is enough to make the module genuinely hard to read.

**Carried forward.** Check 8 moves to task 05, which installs the requirements.

### 2026-08-30 — Task 02 dispatch

Wrote `tasks/02-config-and-observability.md`. The spec carries nine verbatim doc excerpts,
because the implementer must not write the SDK API from memory. Dispatched to the same
terminal. Wrote `tasks/03-permissions-and-mcp.md` while task 02 ran.

### 2026-08-30 — Task 02 review

**Verdict: PASS.** The coordinator re-ran all 14 acceptance checks.

| # | Check | Result |
|---|---|---|
| 1 | Both files exist | PASS |
| 2 | `compileall` | PASS |
| 3 | Two `HookMatcher(hooks=` calls, no matcher argument | PASS, lines 58 and 59 |
| 4 | No `permissionDecision` outside comments | PASS |
| 5 | Both callbacks are `async def` | PASS, lines 62 and 85 |
| 6 | Doc URL cited in a comment | PASS, 7 citations |
| 7 | All four exception classes handled | PASS |
| 8 | Windows batch-script refusal handled by text | PASS |
| 9 | `resolve_model` order | PASS |
| 10 | `sdk_env` drops empty values | PASS |
| 11 | Imports without the SDK installed | PASS |
| 12 | Line budgets | PASS, config 58 of 60, observability 89 of 90 |
| 13 | Every SDK call site has a reason comment | PASS |
| 14 | ASCII only | PASS |

**Quality notes, no rework needed.**

- The two-channel block comment above `hooks()` is correct and well aimed. It names the
  hook as the "before" edge that supplies the duration, and the stream as the source of
  the init line and the final cost. That is the distinction the learner needs.
- `_brief` flattens newlines before it cuts. That preserves the one-line-per-call rule.
- The pre hook keys its timer on `tool_use_id`, so parallel tool calls do not mix up
  their start times.

**One claim to verify later.** A comment in `config.explain` states that
`CLINotFoundError` subclasses `CLIConnectionError`. The documentation does not state this.
The ordering is safe either way. Task 05 installs the SDK, so verify the claim then and
correct the comment if it is wrong.

**Minor, accepted.** `_on_post_tool_use` does not guard on `hook_event_name`. The pre hook
does. The spec required the guard on the pre hook only, so this is within contract.

### 2026-08-30 — Task 03 dispatch

Dispatched `tasks/03-permissions-and-mcp.md`. Wrote `tasks/04-commands.md`,
`tasks/05-smoke-run.md`, and `DECISIONS.md` while task 03 ran.

### 2026-08-30 — Open item from task 02 resolved

The coordinator read `src/claude_agent_sdk/_errors.py` from the SDK repository on GitHub
rather than wait for the install. The hierarchy is:

```
ClaudeSDKError
├── CLIConnectionError
│   └── CLINotFoundError
├── ProcessError
│   └── ResultError
```

Both subclass claims in the `config.explain` comment are correct. The ordering in
`explain` is therefore also correct, on both branches. No rework needed. Removed from the
task 05 check list.

### 2026-08-30 — Task 03 review

**Verdict: PASS, with one coordinator-side spec defect found.**

| # | Check | Result |
|---|---|---|
| 1 | Both files exist | PASS |
| 2 | `compileall` | PASS |
| 3 | No write-tool path rule in `permissions.py` | PASS |
| 4 | `for_explore().allowed_tools` exact and ordered | PASS |
| 5 | `for_explore().disallowed_tools` exact | PASS |
| 6 | Every mode is `dontAsk` | PASS, three call sites |
| 7 | `mcp__fs__*` present | PASS |
| 8 | `mcp.py` does not import the SDK | PASS |
| 9 | `allowed_tool_patterns()` returns `["mcp__fs__*"]` | PASS |
| 10 | `filesystem_server` returns `None` without npx | PASS |
| 11 | Deny hook returns a deny for `rm -rf /` | DEFERRED, needs the SDK for the import |
| 12 | `matcher="Bash"` on the guard | PASS |
| 13 | All seven required comments present | PASS |
| 14 | Doc URL cited | PASS, 4 in permissions and 3 in mcp |
| 15 | Line budgets | PASS, permissions 67 of 70, mcp 29 of 30 |
| 16 | ASCII only | PASS |

**Spec defect found by the coordinator, not by the implementer.**

The task 03 spec told the implementer to pass `shutil.which("npx")` as the MCP server
`command`. On this machine that call returns:

```
C:\Program Files\nodejs\npx.CMD
```

That value is wrong on two counts. It is a `.CMD` batch shim, and Windows runs a batch
file through `cmd.exe`, which re-parses the command line. The SDK already refuses to launch
the `claude` CLI from a `.bat` or `.cmd` path for this exact reason. The value also contains
a space. The MCP documentation passes the bare name `"npx"` instead, and the process that
launches the server resolves the launcher itself.

The implementer followed the spec correctly. The spec was wrong. Cost of finding it now
rather than at task 05: zero, instead of one failed API run.

### 2026-08-30 — Revision 03R dispatch and review

Wrote `tasks/03r-mcp-npx-command.md`. It changes one file and one line of behaviour.
`shutil.which("npx")` stays as the availability probe. The `command` value becomes the bare
literal `"npx"`.

**Verdict: PASS.** All eight checks pass. `filesystem_server('sample-legacy-app')` now
returns `command='npx'` with an absolute target path, and it still returns `None` when
`npx` is absent. The dead `found or "npx"` line is gone. `mcp.py` is now 27 code lines.

Revision count for task 03: **1 of the 1 allowed.** No escalation needed.

### 2026-08-30 — Task 04 dispatch, after two spec corrections

Two defects were corrected in `tasks/04-commands.md` before dispatch.

1. **Ordering bug.** The spec had `main()` call `config.preflight()` before `argparse`.
   `preflight()` raises when `claude-agent-sdk` is missing, so `--help` would have failed
   with an install error, and all three negative tests would have reported the install
   error instead of the validation error they exist to check. The spec now parses first
   and states why.
2. **Missing environment step.** The task 04 checks import the SDK, so the venv and the
   install moved from task 05 into a new Step 0 of task 04. Every check command now names
   `.venv/Scripts/python.exe`.

**Dispatch note on permissions.** The task 04 checks run `.venv/Scripts/python.exe`, which
a `Bash(python:*)` allow rule does not match. The dispatch therefore grants bare `Bash` and
bounds it with `--disallowedTools` covering `rm`, `rmdir`, and the mutating `git`
subcommands. Deny rules are evaluated before the permission mode, so they hold regardless
of the mode. That is the same layering this project teaches in ADR-003.

### 2026-08-30 — Task 04 review

**Verdict: PASS.** Installed SDK version: `claude-agent-sdk 0.2.148`.

| # | Check | Result |
|---|---|---|
| 1 | All five files exist | PASS |
| 2 | `compileall` | PASS |
| 3 | `--help` on the root and all three subcommands | PASS |
| 4 | No subcommand exits `2` | PASS |
| 5 | Header block, 8 doc URLs and the date | PASS |
| 6 | `merge_hooks` concatenates, ignores `None` | PASS |
| 7 | `boilerplate` without EXPLORATION.md | PASS, one line, exit 1, no traceback |
| 8 | `chores --path C:/Windows` refused | PASS, names both paths |
| 9 | `explore no_such_dir_xyz` refused | PASS |
| 10 | `permissions.py` untouched | PASS |
| 11 | Per-file line budgets | PASS, all nine within budget |
| 12 | ASCII only | PASS |
| 13 | Package total at or under 500 | PASS, **459** |

**Extra verification the coordinator added.** Every `ClaudeAgentOptions` field the code
sets was checked against the installed SDK with `dataclasses.fields`. All 14 exist:
`allowed_tools`, `disallowed_tools`, `permission_mode`, `model`, `cwd`, `env`, `hooks`,
`mcp_servers`, `max_turns`, `max_budget_usd`, `stderr`, `system_prompt`,
`setting_sources`, `effort`. The pasted doc excerpt matched the shipped package, so no
field was written from memory.

The real options object was then built end to end with the real policy, the real logger,
the real guard, and the real MCP mapping. It reports 2 `PreToolUse` matchers and 1
`PostToolUse` matcher, which proves `merge_hooks` keeps both the audit hook and the
safety hook instead of dropping one.

**Deferred check from task 03 now closed.** `_deny_destructive_bash` returns
`permissionDecision: deny` for `rm -rf /` and `{}` for `git status`. PASS.

**Line counts.**

| File | Code lines | Budget |
|---|---|---|
| `__main__.py` | 55 | 65 |
| `commands/_common.py` | 30 | 30 |
| `commands/explore.py` | 52 | 55 |
| `commands/boilerplate.py` | 43 | 45 |
| `commands/chores.py` | 35 | 55 |
| `config.py` | 58 | 60 |
| `observability.py` | 89 | 90 |
| `permissions.py` | 67 | 70 |
| `mcp.py` | 27 | 30 |
| **Total** | **459** | 500 |

### 2026-08-30 — Task 05 dispatch

Dispatched `tasks/05-smoke-run.md`. This is the first task that calls the Claude API, so it
costs money. The spec caps the retries: fix one cause, try once more, then report.

### 2026-08-30 — Task 05 review

**Verdict: PARTIAL PASS.** 26 of 29 checks pass. Three API runs, total cost
`$1.774` (`explore` $0.769, `boilerplate` $0.527, `chores` $0.478). Package total 464 code
lines, still under 500.

**What works.** `explore` returned `subtype=success` in 15 turns. It called Glob once,
Grep three times, Read seven times, `mcp__fs__list_directory` once, and Write once.
`EXPLORATION.md` names `legacy_pricing.py` as the confusing module, reports both markers,
carries a Conventions section, and states that the sample README contradicts the code.
`boilerplate` wrote both files and the generated test copies the convention exactly: module
docstring, `test_<function>_<case>` names, plain asserts, no class, no fixture. `chores`
returned success and removed every CRLF pair, 23 in `handlers.py` and 10 in `utils.py`. The
sample app still runs. The destructive-command guard denies `rm -rf /`.

**Failure 1, real: the formatter never ran.** `black --check` still reports that both files
would be reformatted. The implementer diagnosed it precisely. `codebuddy` starts as
`.venv/Scripts/python.exe -m codebuddy`, which does not put the virtual environment on
`PATH`. The bare `python` in the agent's Bash shell therefore resolves to the system
interpreter, which has no black, so the call returned `No module named black`. The
`ClaudeAgentOptions.env` overlay does reach the CLI process, at
`claude_agent_sdk/_internal/transport/subprocess_cli.py:809-813`, but it does not reach the
shell that the Bash tool starts, because Claude Code rebuilds that shell's `PATH` from its
own snapshot.

The agent behaved exactly as the prompt asked. It reported the denial, named `pip install`
as outside its allowlist, and refused to work around it. The defect is in the command and
the allow rule, not in the agent.

This is the **second** failure of `chores`. The implementer had already tried a `PATH`
overlay and seen the same result. Per the protocol, that is the escalation point.

**Failure 2, not a real defect: `git diff --stat` is empty.** `projects/codebuddy/` is
untracked, and `git diff` reports tracked files only. The check cannot pass while the
directory is untracked, and task 05 forbids `git add`. Check 6.2 is the sound evidence
instead: both files held CRLF before and hold none after. This is a defect in the check I
wrote, not in the code.

**Failure 3, found by the coordinator, not by the implementer: MCP configuration
pollution.** The `[mcp-discovery]` line reports **33 MCP servers**, not one. Seven are
connected: `fs`, plus the user's `github` plugin, Atlassian, Figma, Gmail, Google Calendar,
and Google Drive. Roughly **190 MCP tool schemas** entered the agent's context.

Cause: `setting_sources` was never set, so the SDK loads the user and project settings by
default, and that includes the user's global MCP configuration. The permission layer held,
because `allowed_tools` only granted `mcp__fs__*`, so the agent could not call any of them.
The schemas still consumed context, and the transcript shows the behavioural consequence:
the agent called `ToolSearch`, which it only needs when the tool list is large.

Three reasons this matters here. The `[mcp-discovery]` line is the project's headline
teaching artefact and it is three screenfuls of unrelated connectors. The context waste
contradicts what this project teaches about context management. And the run is not
reproducible on another machine, because the output depends on the reader's own connectors.

Both fixes are verified against the installed SDK 0.2.148:

- `strict_mcp_config: bool` exists. The matching CLI flag reads *"Only use MCP servers from
  --mcp-config, ignoring all other MCP configurations."*
- `setting_sources: list[Literal['user','project','local']] | None` exists. An empty list
  loads none of them.
- For the formatter, `Path(sys.executable).as_posix()` gives
  `C:/.../.venv/Scripts/python.exe`, which has no space on this machine and uses forward
  slashes, so it is safe inside a permission rule where a backslash would be a glob escape.

**Escalated to the user.** `chores` has failed twice, and the remaining fixes cost about
two more API runs. That is the user's call, so the coordinator stopped and reported.

### 2026-08-30 — Revision 05R review

**Verdict: PASS.** Both escalated defects are fixed. Cost of this revision: `$0.808` over
two runs. `boilerplate` was not re-run, as instructed.

**Defect 1 fixed.** The explore transcript now opens with one line:

```
[mcp-discovery] servers: fs=connected
[mcp-discovery] tool schemas: ['mcp__fs__create_directory', 'mcp__fs__directory_tree', ...]
```

One server instead of 33. Only `mcp__fs__*` schemas instead of about 190 names across
seven connected servers. `strict_mcp_config=True` and `setting_sources=[]` did it. The
transcript is now reproducible on any machine, because it no longer depends on the reader's
own connectors.

**Defect 2 fixed.** `black --check` on the two sample files now exits `0` and reports
"2 files would be left unchanged". Before this revision it exited `1` on both files. The
fix was to name the interpreter absolutely in both the prompt and the allow rule, built
from `Path(sys.executable).as_posix()`. Both sample files also hold zero CRLF pairs, and
the sample app still runs. The failed `PATH` overlay was removed from `config.py`, which
brought that file back to 59 lines, inside its 60-line budget.

Retry accounting: `chores` failed twice, was escalated to the user, and the user approved
one more attempt. That attempt succeeded. No further escalation.

**One check reported FAIL. It is not a defect, and the check was wrong.**

Spec 05R step 6 check 4 required that no `ToolSearch` call appear. One still does:

```
-> [builtin] ToolSearch query=select:mcp__fs__list_directory max_results=1
```

The coordinator misdiagnosed this. In the earlier polluted run, `ToolSearch` looked like a
symptom of 190 tool schemas crowding the context. It is not. MCP tool search is **enabled
by default**, so MCP tool definitions are withheld from the context and loaded only when
the agent needs one. The agent therefore has to fetch the schema for
`mcp__fs__list_directory` before it can call it, and the very next line in the transcript
is that call succeeding.

This turns out to be the clearest possible answer to the question the README has to
address, which is how the SDK discovers MCP tool schemas. The check is withdrawn, and the
behaviour is documented in `README.md` as intended rather than as a fault.

**Two accepted minor deviations, neither worth a revision.**

1. `observability.py` is 91 code lines against a 90-line budget. The file was last changed
   during task 05, not by this revision, so the out-of-scope rule held. The package total
   is 474 of 500, so the constraint that matters is met.
2. `transcripts/chores-run.txt` contains non-ASCII bytes, so `grep` reports it as binary.
   The source is black's own success message, which prints emoji. No file in `codebuddy/`
   contains a non-ASCII character, which is the constraint that was set.

### 2026-08-30 — Final tally

| Package | Dispatches | Revisions | Verdict |
|---|---|---|---|
| 01 scaffold and sample app | 1 | 0 | PASS |
| 02 config and observability | 1 | 0 | PASS |
| 03 permissions and MCP | 1 | 1 (03R) | PASS |
| 04 CLI and commands | 1 | 0 | PASS |
| 05 smoke run | 1 | 1 (05R) | PASS |

Seven dispatches in total. Two revisions, both within the one-per-failure budget. One
escalation to the user, which the user resolved by approving the final two runs.

**Defect origin.** Four of the five defects found were **spec defects written by the
coordinator**, not implementation defects: the `shutil.which("npx")` instruction, the
`preflight()` before `argparse` ordering, the missing environment step in task 04, and the
`ToolSearch` check. One was a genuine implementation-level gap that no spec anticipated:
the formatter's `PATH` problem. The implementer followed every spec correctly each time.

**Total API cost across all runs: about `$2.58`.**

Package size: **474** code lines of 500, excluding comments and blank lines.

