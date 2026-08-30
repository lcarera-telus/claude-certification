# Smoke run results

Date: 2026-08-30. Package: `claude-agent-sdk` 0.2.148.
Prerequisites: `claude` 2.1.251, `node` v22.14.0, `npx` 10.9.2.

This file reflects the task 05R re-run: `explore` once and `chores` once, after
`strict_mcp_config` and `setting_sources` were set and the formatter command was made
absolute. The `boilerplate` results and the safety-guard result are carried forward from
the earlier smoke run and were not re-run.

| Step | Check | Result |
|---|---|---|
| 4 | `handlers.py` and `utils.py` restored to CRLF, both counts above zero (23 and 10) | PASS |
| 5.1 | `compileall -q codebuddy` reports no error | PASS |
| 5.2 | `for_chores` allow list holds exactly two `black` entries, one absolute and one bare, plus the two matching `py_compile` entries | PASS |
| 5.2b | `ClaudeAgentOptions(strict_mcp_config=True, setting_sources=[])` builds and holds both values | PASS |
| 5.3 | `python -m codebuddy --help` still works (exit 0) | PASS |
| 5.4 | `chores --path C:/Windows` still refuses (exit 1, path-outside-root message) | PASS |
| 5.5 | Line budgets: `permissions.py` 69/75, `chores.py` 43/60, `_common.py` 32/34, `config.py` 59/60 | PASS |
| 5.6 | Package total at most 500 non-comment, non-blank lines (474) | PASS |
| 5.7 | No non-ASCII character in the package (`grep -rnP` returns nothing) | PASS |
| 6.1 | `explore` exit code is `0` | PASS |
| 6.2 | `[mcp-discovery] servers:` names exactly one server, `fs`, and no other | PASS |
| 6.3 | `[mcp-discovery] tool schemas:` holds only `mcp__fs__` names (14 of them) | PASS |
| 6.4 | The transcript contains no `ToolSearch` call | FAIL |
| 6.5 | At least one call to each of `Glob`, `Grep`, and `Read` (2, 3, 8) | PASS |
| 6.6 | At least one `mcp__fs__` call (`mcp__fs__list_directory`, line 38) | PASS |
| 6.7 | `EXPLORATION.md` names `legacy_pricing.py`, reports the TODO and the FIXME, has a Conventions section naming the test file pattern, and states that the README contradicts the code | PASS |
| 6.8 | `[result] subtype=success num_turns=17 total_cost_usd=0.542284` | PASS |
| 7.1 | `chores` exit code is `0` | PASS |
| 7.2 | `[mcp-discovery] servers:` names no server, because `chores` passes none | PASS |
| 7.3 | Both sample files hold zero CRLF pairs (both print `0`) | PASS |
| 7.4 | `black --check` on `handlers.py` and `utils.py` now exits `0` | PASS |
| 7.5 | A Bash call ran black and succeeded rather than reporting `No module named black` | PASS |
| 7.6 | The transcript shows a per-file summary with a reason for each file | PASS |
| 7.7 | The sample app still runs (`app.main()` prints the quote, exit 0) | PASS |
| 7.8 | `[result] subtype=success num_turns=14 total_cost_usd=0.26618449999999994` | PASS |
| B.1 | `boilerplate` exit code is `0` | PASS (carried forward) |
| B.2 | `codebuddy_generated/invoice_formatter.py` exists | PASS (carried forward) |
| B.3 | `codebuddy_generated/tests/test_invoice_formatter.py` exists | PASS (carried forward) |
| B.4 | Transcript shows at least two `Write` calls (exactly 2) | PASS (carried forward) |
| B.5 | Generated test file follows the convention of `tests/test_utils.py` | PASS (carried forward) |
| B.6 | `compileall -q codebuddy_generated` reports no error | PASS (carried forward) |
| G | The guard returns `'permissionDecision': 'deny'` for `rm -rf /` | PASS (carried forward) |

## Notes

### Step 6 checks 2 and 3 - the MCP defect is fixed.

The discovery lines from `transcripts/explore-run.txt`, lines 1 and 2:

```
[mcp-discovery] servers: fs=connected
[mcp-discovery] tool schemas: ['mcp__fs__create_directory', 'mcp__fs__directory_tree',
'mcp__fs__edit_file', 'mcp__fs__get_file_info', 'mcp__fs__list_allowed_directories',
'mcp__fs__list_directory', 'mcp__fs__list_directory_with_sizes', 'mcp__fs__move_file',
'mcp__fs__read_file', 'mcp__fs__read_media_file', 'mcp__fs__read_multiple_files',
'mcp__fs__read_text_file', 'mcp__fs__search_files', 'mcp__fs__write_file']
```

One server. Fourteen tool schemas, every one of them `mcp__fs__`. The previous run named 33
servers and about 190 tool names. `strict_mcp_config=True` confines the run to the servers
passed in `mcp_servers`, and `setting_sources=[]` loads no settings file, so the machine's
own MCP configuration never enters the run.

### Step 6 check 4 - FAIL. One `ToolSearch` call remains, and the spec's premise was wrong.

The transcript still holds one `ToolSearch` call, at lines 21 to 23:

```
[stream] tool_use ToolSearch
-> [builtin] ToolSearch query=select:mcp__fs__list_directory max_results=1
<- ToolSearch 7ms ok 111 chars
```

The task predicted that this call would disappear with the foreign servers, on the reasoning
that the agent reaches for `ToolSearch` only when the tool list is large. That reasoning does
not hold. The tool list is now 14 names, all from one server, and the call still happened.
The CLI defers MCP tool schemas by default, whatever their number, so the agent must fetch a
schema through `ToolSearch` before it can call the tool. The query proves it: it is a direct
`select:` for the single tool the agent had already decided to use, not a keyword search
through a crowded list.

So the call is a property of deferred MCP tool loading, not a symptom of context bloat. The
context defect that this task set out to fix is fixed, and checks 2 and 3 are the evidence for
that. Check 4 measured the wrong thing. I did not re-run `explore` to chase it, because the
task allows one run.

### Step 7 check 4 - PASS. This is the check that failed twice before.

```
$ .venv/Scripts/python.exe -m black --check sample-legacy-app/handlers.py sample-legacy-app/utils.py
All done!
2 files would be left unchanged.
BLACK_EXIT=0
```

The fix was to stop depending on `PATH`. `chores.py` now computes
`Path(sys.executable).as_posix()`, puts that absolute interpreter in the prompt, and passes it
to `permissions.for_chores`, which builds the matching allow rule. The earlier `PATH` overlay
in `config.sdk_env()` was deleted; it never reached the shell that the `Bash` tool starts.

### Step 7 check 5 - PASS, with the transcript truncated.

The transcript does not hold the literal text `-m black`, because
`observability` truncates a logged command at about 110 characters and the absolute
interpreter path is longer than that. Line 43 shows:

```
-> [builtin] Bash command=C:/Users/lcare/orca/workspaces/claude-certification/Developer-Productivity-Agent-with-the-Claude-Agent... description=Run black on sample-legacy-app
<- Bash 1509ms ok 715 chars
```

Three facts settle what the truncated command was. The permission mode is `dontAsk`, and the
only two shell rules that mention black are `Bash(<absolute interpreter> -m black:*)` and
`Bash(python -m black:*)`, so an approved call must have matched one of them by prefix. The
visible prefix is the absolute interpreter, so it matched the first. The call returned `ok`,
the phrase `No module named black` appears zero times in the transcript, and `black --check`
now exits 0 on both files.

### The `git diff --stat` check - NOT APPLICABLE.

`projects/codebuddy/` is untracked, and `git diff` reports tracked files only, so it prints
nothing here whatever the command changes. The CRLF byte counts are the evidence instead:
`handlers.py` 23 pairs and `utils.py` 10 pairs before the run, 0 and 0 after it. The agent
reached the same conclusion inside the run and said so in its summary.

### API spend

Two runs in this task: `explore` 0.542284 USD and `chores` 0.266184 USD. Total 0.808468 USD.
`boilerplate` was not re-run.
