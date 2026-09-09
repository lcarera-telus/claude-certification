# Task 05R — Revision: confine MCP config, fix the formatter, re-run two commands

Implement this specification exactly. Do not read the other files in `tasks/`.
This specification is the complete contract. Ask no questions.

All paths below are relative to `projects/codebuddy/`.

Use `.venv/Scripts/python.exe` for every command in this task. The virtual environment
already exists with the requirements installed.

## Two defects to fix

### Defect 1 — the agent loads every MCP server on the machine

The last `explore` run printed this at the top of its transcript:

```
[mcp-discovery] servers: plugin:github:github=connected, plugin:postman:postman=needs-auth,
fs=connected, claude.ai Braze=needs-auth, ... (33 servers in total)
[mcp-discovery] tool schemas: ['mcp__claude_ai_Atlassian__addCommentToJiraIssue', ...
(about 190 tool names)]
```

Only one server was passed in `ClaudeAgentOptions.mcp_servers`, the `fs` server. The other
32 came from the machine's own configuration.

Cause: `setting_sources` was never set. When it is unset, the SDK loads the user and
project settings by default, and those include the user's global MCP configuration.

Why this is a defect and not cosmetic:

1. That `[mcp-discovery]` line is the headline teaching artefact of this project. It is
   supposed to show one server and its tool schemas. Three screenfuls of unrelated
   connectors teach nothing.
2. About 190 MCP tool schemas entered the agent's context window. This project's own
   documentation is about context discipline, so the run contradicts it.
3. The output is not reproducible. It depends on whichever connectors the reader happens to
   have configured, so no two people see the same transcript.
4. The transcript shows the behavioural cost. The agent called `ToolSearch`, which it
   reaches for only when the tool list is large.

Note what did **not** go wrong. `allowed_tools` granted `mcp__fs__*` only, so the agent
could not call any of the 32 foreign servers. Permission scoping held. Context scoping is a
separate control, and it was missing.

**The fix, verified against the installed SDK 0.2.148.** Both fields exist on
`ClaudeAgentOptions`:

| Field | Type | Effect |
|---|---|---|
| `strict_mcp_config` | `bool` | The matching CLI flag documents it as: *"Only use MCP servers from --mcp-config, ignoring all other MCP configurations."* |
| `setting_sources` | `list[Literal['user','project','local']] \| None` | An explicit list loads only those sources. An empty list loads none. |

### Defect 2 — the formatter never ran

`black --check` still reports that both sample files would be reformatted, even though
`chores` returned success.

Cause, already diagnosed and confirmed twice. `codebuddy` starts as
`.venv/Scripts/python.exe -m codebuddy`. That does not put the virtual environment on
`PATH`. The bare `python` in the agent's Bash shell therefore resolves to the system
interpreter, which has no black, so the call returned `No module named black`.

An attempt to overlay `PATH` through `ClaudeAgentOptions.env` did not work. The overlay does
reach the spawned CLI process, at
`claude_agent_sdk/_internal/transport/subprocess_cli.py:809-813`, but it does not reach the
shell that the `Bash` tool starts, because Claude Code rebuilds that shell's `PATH` from its
own snapshot. **Do not try the `PATH` overlay again.** It has already failed twice.

**The fix.** Name the interpreter absolutely, in both the prompt and the allow rule, so
neither depends on `PATH`.

`Path(sys.executable).as_posix()` returns, on this machine:

```
C:/Users/lcare/orca/workspaces/claude-certification/Developer-Productivity-Agent-with-the-Claude-Agent-SDK/projects/codebuddy/.venv/Scripts/python.exe
```

Two properties make that value safe inside a permission rule. It contains no space, so the
agent does not need to quote it, and a quoted command would not prefix-match the rule. It
uses forward slashes, so no backslash is read as a glob escape character.

---

## Change 1 — `codebuddy/commands/_common.py`

Add two fields to the `ClaudeAgentOptions` construction.

```python
strict_mcp_config=True,
setting_sources=[],
```

Add a WHY comment on each. They must state the following.

For `strict_mcp_config`: only the servers passed in `mcp_servers` are used, and every other
MCP configuration on the machine is ignored. Without it, the reader's own connectors load,
their tool schemas fill the context window, and the transcript stops being reproducible.
Note that this is a **context** control, and that it is separate from `allowed_tools`, which
is a **permission** control. `allowed_tools` decides what may run. `strict_mcp_config`
decides what is even described to the model. Cite
`https://code.claude.com/docs/en/agent-sdk/mcp`.

For `setting_sources`: an empty list loads no settings file, so no user, project, or local
settings reach the run. That is what keeps the machine's global MCP configuration, its
memory files, and its shell hooks out of a teaching run. Cite
`https://code.claude.com/docs/en/agent-sdk/python`.

Change nothing else in this file.

## Change 2 — `codebuddy/permissions.py`

Change the signature of `for_chores` to:

```python
def for_chores(target_dir: str, python_exe: str) -> ToolPolicy: ...
```

In the allow list, replace the two bare-`python` entries with **four** entries: the absolute
form first, and the bare form kept as a fallback.

```python
f"Bash({python_exe} -m black:*)",
f"Bash({python_exe} -m py_compile:*)",
"Bash(python -m black:*)",
"Bash(python -m py_compile:*)",
```

Add a comment stating why the absolute form is needed. The bare `python` in the agent's
shell is not the interpreter that runs `codebuddy`, because starting `codebuddy` through a
virtual environment interpreter does not put that environment on `PATH`. Also state why the
value must use forward slashes: a permission rule path is matched as a glob, and a backslash
would be read as an escape character.

Keep the bare entries and say why in a comment: they cost nothing, and they still match if
the agent falls back to the plain command name.

Change nothing else in this file. Do not touch `for_explore` or `for_boilerplate`.
The line budget for this file rises to **75** code lines.

## Change 3 — `codebuddy/commands/chores.py`

1. Import `sys`.
2. Compute the interpreter once:

   ```python
   python_exe = Path(sys.executable).as_posix()
   ```

3. Guard the space case. When `" " in python_exe`, print one warning line saying that the
   interpreter path contains a space, so the run falls back to the bare `python` command and
   the formatter step may fail. Then set `python_exe = "python"`. Add a comment saying why:
   a quoted command would not prefix-match the allow rule.
4. Pass it to `permissions.for_chores(relative.as_posix(), python_exe)`.
5. In `PROMPT`, replace `python -m black` with `{python_exe} -m black`, and add
   `{python_exe}` to the `.format(...)` call. In the shell-allowlist paragraph of the prompt,
   name the absolute command rather than the bare one. Add one sentence telling the agent to
   use that exact command text, and not to quote it or shorten it, because the allowlist
   matches the command by prefix.

Change nothing else in this file.

---

## Step 4 — Restore the sample files so the chore has real work

The previous `chores` run already converted the two sample files to LF. Convert them back to
CRLF, so the re-run exercises the line-ending step for real.

```bash
.venv/Scripts/python.exe -c "
from pathlib import Path
for name in ('handlers.py', 'utils.py'):
    p = Path('sample-legacy-app') / name
    b = p.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    p.write_bytes(b)
    print(name, 'crlf pairs now', p.read_bytes().count(b'\r\n'))
"
```

Both counts must be greater than zero before you continue. Record them.

Do not change the formatting of those files. The bad formatting is still present, because
black never ran.

## Step 5 — Verify the code before spending money

Run these checks first. Do not run a command that calls the API until all of them pass.

1. `.venv/Scripts/python.exe -m compileall -q codebuddy` reports no error.
2. The options object still builds. Confirm the two new fields are set:
   ```
   .venv/Scripts/python.exe -c "
   import codebuddy.permissions as p, sys
   from pathlib import Path
   pol = p.for_chores('sample-legacy-app', Path(sys.executable).as_posix())
   print([r for r in pol.allowed_tools if 'black' in r])"
   ```
   It must print exactly two entries: one whose command begins with the absolute
   interpreter path, and one whose command begins with the bare word `python`.
   The full allow list must also hold the two matching `py_compile` entries, so the four
   new entries are present in total.
3. `.venv/Scripts/python.exe -m codebuddy --help` still works.
4. `.venv/Scripts/python.exe -m codebuddy chores --path C:/Windows` still refuses.
5. Line counts, excluding comments and blank lines:
   `permissions.py` at most 75, `chores.py` at most 60, `_common.py` at most 34,
   `config.py` at most 60.
6. The package total is at most 500:
   `cat $(find codebuddy -name '*.py') | grep -vE '^[[:space:]]*(#|$)' | wc -l`
7. No non-ASCII character in the package:
   `grep -rnP '[^\x00-\x7F]' --include='*.py' codebuddy/` returns nothing.

## Step 6 — Re-run `explore`, once

```bash
.venv/Scripts/python.exe -m codebuddy explore sample-legacy-app 2>&1 | tee transcripts/explore-run.txt
```

Overwrite the old transcript. Then check, and record each result:

1. The exit code is `0`.
2. The `[mcp-discovery] servers:` line names **exactly one** server, and it is `fs`.
   No `claude.ai`, `plugin:`, or other server appears on that line.
3. The `[mcp-discovery] tool schemas:` line contains **only** names starting with
   `mcp__fs__`. Count them and record the number.
4. The transcript contains no `ToolSearch` call.
5. The transcript shows at least one call to each of `Glob`, `Grep`, and `Read`.
6. The transcript shows at least one `mcp__fs__` call.
7. `sample-legacy-app/EXPLORATION.md` exists and still names `legacy_pricing.py` as the
   confusing module, reports the TODO and the FIXME, has a Conventions section naming the
   test file pattern, and states that the sample README contradicts the code.
8. Record the `[result]` line verbatim, including the turn count and the cost.

## Step 7 — Re-run `chores`, once

```bash
.venv/Scripts/python.exe -m codebuddy chores --path sample-legacy-app 2>&1 | tee transcripts/chores-run.txt
```

Overwrite the old transcript. Then check, and record each result:

1. The exit code is `0`.
2. The `[mcp-discovery] servers:` line names no server, because `chores` passes none.
3. Both sample files hold zero CRLF pairs:
   ```
   .venv/Scripts/python.exe -c "
   from pathlib import Path
   for n in ('handlers.py','utils.py'):
       print(n, Path('sample-legacy-app', n).read_bytes().count(b'\r\n'))"
   ```
4. `.venv/Scripts/python.exe -m black --check sample-legacy-app/handlers.py sample-legacy-app/utils.py`
   now exits `0`. **This is the check that failed before. It is the point of this task.**
5. The transcript shows a Bash call whose command contains `-m black`, and that call
   succeeded rather than reporting `No module named black`.
6. The transcript shows a per-file summary of what changed, with a reason for each file.
7. The sample app still runs:
   `.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'sample-legacy-app'); import app; app.main()"`
8. Record the `[result]` line verbatim.

## Step 8 — Update the results file

Rewrite `transcripts/smoke-results.md` so it reflects this run. Keep the same table shape:
Step, Check, Result. Cover every check in steps 5, 6, and 7 of **this** spec, plus the
checks from the earlier smoke run that still apply, which are the `boilerplate` checks and
the safety-guard check. Do not re-run `boilerplate`; carry its earlier PASS results forward
and say that they were carried forward.

In the Notes section, record the `git diff --stat` check as NOT APPLICABLE, and state the
reason: `projects/codebuddy/` is untracked, and `git diff` reports tracked files only, so
the CRLF byte counts are the evidence instead.

## Retry budget

`chores` has already failed twice. If step 7 check 4 fails again, **stop**. Do not try a
third approach, and do not run black by hand to make the check pass. Report the exact
command the agent ran, the exact error it received, and the transcript line numbers. A
false PASS is worse than an honest FAIL.

## Out of scope

Change only these four files:

- `codebuddy/commands/_common.py`
- `codebuddy/permissions.py`
- `codebuddy/commands/chores.py`
- `codebuddy/config.py`, **for one deletion only**

The `config.py` deletion. `sdk_env()` currently sets a `PATH` key, at about line 71, plus
the comment block above it at about lines 63 to 66. That overlay is the approach that
failed twice. Delete the `PATH` line and its comment block, and delete the now-unused
`sys` import if nothing else in the file uses it. Leave the rest of `sdk_env()` alone: it
must still return only the three credential variables. Removing this brings `config.py`
back inside its 60-line budget, which it currently exceeds at 61.

Do not change `observability.py`, `mcp.py`, `__main__.py`, `commands/explore.py`, or
`commands/boilerplate.py`.
Do not create `README.md`, `DECISIONS.md`, or `COORDINATION.md`.
Do not run `git add` or `git commit`.
Run `explore` once and `chores` once. Do not re-run `boilerplate`.

## When you finish

Report, in this order:

1. The diff of each of the three changed files, as the changed lines only.
2. Whether you removed a `PATH` overlay from `config.py`.
3. The CRLF counts from step 4.
4. The result of every step 5 check.
5. The result of every step 6 check, with the one-server discovery line quoted in full.
6. The result of every step 7 check, with the black exit code stated plainly.
7. The two `[result]` lines, and the total cost of this task's runs.
8. The per-file and total line counts.

Then stop.
