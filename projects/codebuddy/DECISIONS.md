# DECISIONS.md

Architecture decision records for `codebuddy`. Each record states the decision, the
reason, the alternatives that were rejected, and the cost accepted.

Documentation read on 2026-08-30 from `https://code.claude.com/docs/en/agent-sdk/`.

---

## ADR-001 — Build on the Claude Agent SDK, not on the API tool runner

**Status:** accepted.

**Decision.** Use the `claude-agent-sdk` Python package.

**Reason.** The exam scenario names the built-in tools Read, Write, Bash, Grep, and Glob.
Only the Agent SDK ships those tools. It packages the Claude Code harness as a library.
It supplies the agent loop, context management, hooks, permissions, subagents, and MCP.

**Rejected alternative.** The Anthropic API SDK offers `client.beta.messages.tool_runner`.
That helper also runs a tool loop. It has no built-in tools. Every tool would have to be
written by hand. The learner would then study our tool code instead of the SDK's.

**Rejected alternative.** Managed Agents runs the loop on Anthropic servers. It hosts a
sandbox per session. It cannot explore a repository on the learner's own disk.

**Cost accepted.** The Agent SDK launches the Claude Code CLI as a subprocess. Therefore
the CLI is a hard prerequisite. The package bundles a binary for common platforms, and it
falls back to the `claude` on `PATH`.

**Note for the exam.** These three surfaces are easy to confuse. The Agent SDK and the
tool runner both supply a harness only, and you host both yourself. Managed Agents supplies
the harness and the deployment.

---

## ADR-002 — Write the project in Python

**Status:** accepted.

**Decision.** Use Python 3.13 with `requirements.txt`.

**Reason.** Every other exercise in this study repository is Python. The sibling project
`projects/claudecertificationguide/` uses `requirements.txt` and a shared client module.
A single language keeps the toolchain small.

**Cost accepted.** The Python SDK has a smaller hook surface than the TypeScript SDK.
`SessionStart` and `SessionEnd` are not available as Python callbacks. In Python they exist
only as shell command hooks in a settings file. This project does not need them.

---

## ADR-003 — Scope tool permissions per command, and layer the guards

**Status:** accepted. This is the central design decision of the project.

### The evaluation order that the design depends on

The SDK checks a tool request in a fixed order of six steps.

1. Hooks.
2. Deny rules, from `disallowed_tools` and `settings.json`.
3. Ask rules, from `settings.json`.
4. Permission mode.
5. Allow rules, from `allowed_tools` and `settings.json`.
6. The `can_use_tool` callback.

Two consequences drive the design. First, a call that any earlier step approves never
reaches `can_use_tool`. Second, a deny rule beats every permission mode, including
`bypassPermissions`.

### Decision 3a — one policy per command, never one global policy

Each command declares its own allow list, deny list, and mode. `explore` cannot run a
shell. `boilerplate` cannot run a shell. Only `chores` can, and only a short list of
commands.

**Reason.** A single global policy would have to be the union of all three. The union is
the widest surface. A read-only exploration would then carry shell access it never needs.

### Decision 3b — `permission_mode="dontAsk"`, not `"default"`

**Reason.** `codebuddy` is a non-interactive CLI. In `default` mode an unmatched tool call
falls through to `can_use_tool`. This project supplies no such callback, so the call would
stall or resolve silently. `dontAsk` converts every unresolved call into a hard denial.
The failure is then loud and legible in the transcript.

**Rejected alternative.** `acceptEdits` auto-approves file edits and filesystem shell
commands such as `rm` and `mv`. That is wider than any command here needs. It also does
**not** auto-approve MCP tools, so it would not have removed the need for an explicit MCP
allow entry.

**Rejected alternative.** `bypassPermissions` approves everything that reaches step 4.
`allowed_tools` does not constrain it. Setting `allowed_tools=["Read"]` next to
`bypassPermissions` still approves `Bash`, `Write`, and `Edit`.

### Decision 3c — scope file writes with `Edit(path)`, never `Write(path)`

**Reason.** The permissions documentation is explicit. `Edit(path)` rules govern every
built-in tool that writes files, including `Write` and `NotebookEdit`. A `Write(path)`
rule is never matched by the file permission checks.

**Why this matters more than it looks.** A `Write(sandbox/**)` rule does not raise an
error. It matches nothing. The call then falls through to the permission mode. Under
`dontAsk` the write is denied, and the agent looks broken. Under `acceptEdits` the write
succeeds, and the rule looks like it worked. The bug only appears when the mode changes.

`explore` therefore allows `Edit(EXPLORATION.md)`. `boilerplate` allows
`Edit(codebuddy_generated/**)` and `Edit(codebuddy_generated/tests/**)`.

### Decision 3d — relative rules anchor at the session working directory

A rule passed through `allowed_tools` with a single leading slash, or with no slash,
anchors at the session's working directory. Therefore `ClaudeAgentOptions.cwd` decides
where `Edit(EXPLORATION.md)` points.

Each command sets `cwd` on purpose. `explore` sets it to the directory being explored, so
the summary lands inside that repository and nowhere else. `boilerplate` and `chores` set
it to the project root, so their rules and their `git` commands resolve there.

### Decision 3e — a bare deny name removes the tool; a scoped deny keeps it

`disallowed_tools=["Bash"]` removes the Bash tool definition from the request. The agent
never sees the tool and cannot attempt it. `disallowed_tools=["Bash(rm *)"]` keeps Bash
available and denies only matching calls.

`explore` and `boilerplate` use the bare form for `Bash`, `WebFetch`, and `WebSearch`.
Removing the definition is stronger than denying calls to it. It also saves context,
because an unused tool schema is not sent.

`chores` needs Bash, so it uses the scoped form.

### Decision 3f — four independent guards on `chores`

`chores` is the only command that runs a shell. Its guards are deliberately redundant.
Each one fails in a different direction.

| Guard | What it stops | What defeats it alone |
|---|---|---|
| A command-scoped allow list, for example `Bash(git diff:*)` | Any command not named | A future change to `bypassPermissions` |
| A deny list, for example `Bash(rm *)` | Named destructive commands, in every mode | A destructive command nobody listed |
| A `PreToolUse` hook that scans the command string | Any command containing a destructive pattern | A pattern nobody thought of |
| A path check in the command layer | A target outside the project root | Nothing in the tool layer |

The deny list is redundant with the allow list today. That is the point. Deny rules are
evaluated before the permission mode, so they survive a careless later change of mode.
The hook is redundant with both. Hooks are step one of six, so the hook survives even
`bypassPermissions`.

### Decision 3g — accept the `Bash(sed:*)` risk, and bound it in code

`chores` must rewrite CRLF line endings in place. `sed -i` does that in one command.

**Risk accepted.** `sed -i` can rewrite any existing file that the process can reach. The
allow rule cannot express a path restriction on a Bash command.

**Mitigation.** The `chores` command resolves its target and refuses to run when the target
is not inside the project root. The bound lives in Python, not in the rule.

**Rejected alternative.** Use the `Edit` tool for line endings instead. `Edit` can be
scoped by path, which is stronger. It was rejected because the editing tools may preserve
a file's existing line endings, which is the exact thing the chore must change.

---

## ADR-004 — Report tool use through two channels, and teach the difference

**Status:** accepted.

**Decision.** `observability.py` prints every tool call twice over, from two sources.

1. A `PreToolUse` hook and a `PostToolUse` hook, both registered with **no matcher**.
2. The message stream returned by `query()`.

**Reason for no matcher.** A matcher filters on the tool name. Any matcher would silently
miss tools, including every MCP tool. An omitted matcher fires for every event of that
type. The documentation recommends exactly this for logging.

**Reason for two channels.** They are not redundant. A hook runs inside this process,
synchronously, **before** the tool call. It can deny the call, rewrite its input, or add
context. A stream message is the after-the-fact transcript and can change nothing. A
learner who watches only the stream never learns that hooks are an interception point.

**Decision.** Both hook callbacks return `{}`.

**Reason.** `{}` means "allow, no change". Returning `permissionDecision: "allow"` instead
would widen the tool surface. A logging layer must observe, not decide.

**Rejected alternative.** Use the `can_use_tool` callback for logging. It would miss
calls. Any call approved by an allow rule, by `acceptEdits`, or by `bypassPermissions`
never reaches `can_use_tool`. A `PreToolUse` hook runs before all of those steps.

---

## ADR-005 — Connect one stdio filesystem MCP server

**Status:** accepted.

**Decision.** Use `@modelcontextprotocol/server-filesystem` over stdio, launched with
`npx -y`, scoped to the single directory being explored. Register it under the server name
`fs`, and allow its tools with `mcp__fs__*`.

**Reason.** The demo must work offline against a bundled sample repository. A stdio server
runs locally and needs no account and no network endpoint.

**Reason for accepting the overlap with built-in tools.** The filesystem server duplicates
what `Read` and `Glob` already do. That overlap is the teaching value. The README puts the
two paths side by side. A built-in tool runs in process, is always present, and is scoped
by `Read` and `Edit` path rules. An MCP tool arrives over a protocol from a separate
process, is named `mcp__<server>__<tool>`, has its schema discovered at connect time, and
needs an explicit `allowed_tools` entry.

**Rejected alternative.** The hosted documentation MCP server at
`https://code.claude.com/docs/mcp` offers a genuinely different capability. It needs
network access, so it breaks the offline requirement.

**Decision.** The allow entry is `mcp__fs__*`, not `mcp__*`.

**Reason.** An allow-rule glob is legal only after a literal `mcp__<server>__` prefix. The
server segment must be glob-free. A bare `mcp__*` is ignored with a startup warning and
grants nothing. This fails quietly, so it is worth naming.

**Cost accepted.** A stdio server delays the first turn until it connects. The default
deadline is 30 seconds, set by `MCP_TIMEOUT`. When `npx` is missing, `explore` prints one
warning, drops the MCP allow entry, and continues on built-in tools only. A degraded run
beats a crash in a teaching tool.

---

## ADR-006 — Default to `claude-opus-5`, and cap spend in code

**Status:** accepted.

**Decision.** Resolve the model in this order: the `--model` flag, then the
`CODEBUDDY_MODEL` environment variable, then `claude-opus-5`. Set `max_budget_usd` from
`CODEBUDDY_MAX_USD`, defaulting to `2.0`. Set `max_turns` per command: 25 for `explore`,
15 for `boilerplate`, 20 for `chores`.

**Reason.** Model choice is the user's decision, not the tool's. The default is the most
capable model. For repeat demonstrations, set `CODEBUDDY_MODEL=claude-sonnet-5`, which
costs less per run.

**Reason for two ceilings.** `max_turns` bounds the loop. `max_budget_usd` bounds the
money. They fail differently. A tight loop hits the turn cap. One expensive turn hits the
budget cap.

---

## ADR-007 — Split the coordinator from the implementer

**Status:** accepted.

**Decision.** One agent designs, specifies, and reviews. A second agent, in its own Orca
terminal, writes all source. The coordinator writes only plans, task specs, reviews,
`README.md`, `DECISIONS.md`, and `COORDINATION.md`.

**Reason.** The task specification becomes the sole contract. The implementer receives one
instruction: read the spec file and implement it. No design context leaks through the
prompt. A spec that produces the wrong result is therefore a spec defect, and it is
visible as one.

**Deviation from the original brief.** The brief named Codex as the implementer. Codex is
not installed on this machine. `Get-Command codex` finds nothing, `npm ls -g` does not
list it, `~/.codex` does not exist, and `orca account list` reports no managed Codex
accounts. The user chose Claude Code in a separate Orca terminal instead.

**Cost accepted.** The implementer shares this repository's `CLAUDE.md`, so it inherits
the same house rules. That is convenient, and it slightly weakens the isolation. The
`COORDINATION.md` log records every dispatch and verdict so the boundary stays auditable.

---

## ADR-008 — Leave `sample-legacy-app/` deliberately under-commented

**Status:** accepted.

**Decision.** Add no explanatory comments and no docstrings inside `sample-legacy-app/`.
Allow exactly one `TODO` and one `FIXME`, both in `legacy_pricing.py`.

**Reason.** The sample repository is the thing the agent must explain. Comments would do
the agent's work for it. The `README.md` there is stale on purpose, and it contradicts the
code in two ways, so `explore` has to prefer the source over the prose.

**Cost accepted.** The repository now contains one directory that violates the commenting
standard applied everywhere else. This record is the explanation.
