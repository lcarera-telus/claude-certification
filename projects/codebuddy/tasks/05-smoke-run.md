# Task 05 — Install, run all three commands, capture transcripts

Implement this specification exactly. Do not read the other files in `tasks/`.
This specification is the complete contract. Ask no questions.

All paths below are relative to `projects/codebuddy/`.

## Goal

Prove that `codebuddy` works end to end. Capture the real console output of each command
into `transcripts/`. The coordinator turns the `explore` transcript into an annotated
walkthrough in the README, so the transcript must be complete and unedited.

**This task calls the Claude API. It costs real money.** Keep the run count low. Do not
re-run a command that already succeeded. If a command fails, read the error, fix only the
cause, and try once more. Report a second failure instead of trying a third time.

## Write no new source code

This task installs dependencies, runs commands, and saves output. You may edit an existing
file under `codebuddy/` **only** to fix a defect that a run exposes. Record every such
edit in your final report with the file, the line, and the reason. Create no new module.

---

## Step 1 — Create the environment

```bash
cd projects/codebuddy
python -m venv .venv
.venv/Scripts/python.exe -m pip install --quiet --upgrade pip
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m pip show claude-agent-sdk
```

Record the installed `claude-agent-sdk` version in your report. Use
`.venv/Scripts/python.exe` for every later command in this task.

## Step 2 — Complete the check deferred from an earlier task

Run:

```bash
.venv/Scripts/python.exe -m black --check sample-legacy-app/handlers.py sample-legacy-app/utils.py
```

This must **fail** with a nonzero exit code. It proves the formatter has real work to do.
Record the exit code and the output. Do not fix the formatting. The `chores` command fixes
it in step 5.

## Step 3 — Confirm the prerequisites

```bash
claude --version
node --version
npx --version
```

Record all three. If `npx` is missing, the `explore` command must still run and must print
a warning about MCP being unavailable. Note that in your report.

## Step 4 — Run `explore`

```bash
.venv/Scripts/python.exe -m codebuddy explore sample-legacy-app 2>&1 | tee transcripts/explore-run.txt
```

Then check, and record each result:

1. The exit code is `0`.
2. `sample-legacy-app/EXPLORATION.md` now exists.
3. The transcript contains a line reporting the MCP server named `fs` and its status.
4. The transcript lists at least one discovered tool name starting with `mcp__fs__`.
5. The transcript shows at least one call to each of `Glob`, `Grep`, and `Read`.
6. The transcript shows at least one call whose tool name starts with `mcp__fs__`.
7. The transcript shows a write of `EXPLORATION.md`.
8. The transcript ends with a summary line giving the tool-call counts.
9. `EXPLORATION.md` names `legacy_pricing.py` as the confusing module.
10. `EXPLORATION.md` reports the `TODO` and the `FIXME` from `legacy_pricing.py`.
11. `EXPLORATION.md` has a Conventions section naming the test file pattern.
12. `EXPLORATION.md` notes that the sample README disagrees with the source code.

If check 6 fails but check 3 shows the server connected, record it as a partial result.
The model chooses its own tools, so a missing MCP call is a prompt weakness, not a crash.
In that case, and only in that case, you may strengthen the wording of the MCP instruction
in the prompt constant inside `codebuddy/commands/explore.py` and run `explore` once more.

## Step 5 — Run `boilerplate`

```bash
.venv/Scripts/python.exe -m codebuddy boilerplate invoice_formatter --path sample-legacy-app 2>&1 | tee transcripts/boilerplate-run.txt
```

Then check, and record each result:

1. The exit code is `0`.
2. `codebuddy_generated/invoice_formatter.py` exists.
3. `codebuddy_generated/tests/test_invoice_formatter.py` exists.
4. The transcript shows at least two `Write` calls.
5. The generated test file follows the convention set by
   `sample-legacy-app/tests/test_utils.py`. It has a module docstring, test names in the
   form `test_<function>_<case>`, plain `assert` statements, no test class, and no fixture.
   Quote the generated test file in your report.
6. `.venv/Scripts/python.exe -m compileall -q codebuddy_generated` reports no error.

## Step 6 — Run `chores`

First, record the state before the run:

```bash
git -C ../.. status --porcelain -- projects/codebuddy/sample-legacy-app
```

Then run:

```bash
.venv/Scripts/python.exe -m codebuddy chores --path sample-legacy-app 2>&1 | tee transcripts/chores-run.txt
```

Then check, and record each result:

1. The exit code is `0`.
2. `sample-legacy-app/handlers.py` and `sample-legacy-app/utils.py` no longer contain any
   CRLF byte pair. Verify each file with
   `.venv/Scripts/python.exe -c "print(open('sample-legacy-app/utils.py','rb').read().count(b'\r\n'))"`,
   which must print `0`.
3. `.venv/Scripts/python.exe -m black --check sample-legacy-app/handlers.py sample-legacy-app/utils.py`
   now **passes** with exit code `0`.
4. `git -C ../.. diff --stat -- projects/codebuddy/sample-legacy-app` is not empty.
5. The transcript shows at least one `Bash` call.
6. The transcript shows the summary of what changed, per file.
7. `.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'sample-legacy-app'); import app; app.main()"`
   still runs without raising. The chore must not have broken the app.

## Step 7 — Test the safety guard, without spending money

Confirm that the destructive-command guard denies a command, using a direct call rather
than an agent run:

```bash
.venv/Scripts/python.exe -c "import asyncio, codebuddy.permissions as p; print(asyncio.run(p._deny_destructive_bash({'hook_event_name':'PreToolUse','tool_name':'Bash','tool_input':{'command':'rm -rf /'}}, None, None)))"
```

The output must contain `'permissionDecision': 'deny'`. Record it.

## Step 8 — Confirm the size constraint

```bash
cat $(find codebuddy -name '*.py') | grep -vE '^[[:space:]]*(#|$)' | wc -l
```

Record the number. It must be at most `500`.

Also record the per-file counts:

```bash
for f in $(find codebuddy -name '*.py'); do echo -n "$f "; grep -vE '^[[:space:]]*(#|$)' "$f" | wc -l; done
```

## Step 9 — Save a machine-readable result

Write `transcripts/smoke-results.md`. Use one table with three columns: Step, Check,
Result. One row per numbered check in steps 2 through 8. Put `PASS`, `FAIL`, or `PARTIAL`
in the Result column. Add a short Notes section below the table for anything that needed a
retry or an edit.

---

## Acceptance criteria

The reviewer checks all of the following.

1. `transcripts/explore-run.txt`, `transcripts/boilerplate-run.txt`, and
   `transcripts/chores-run.txt` all exist and are not empty.
2. `transcripts/smoke-results.md` exists and covers every numbered check.
3. `sample-legacy-app/EXPLORATION.md` exists.
4. `codebuddy_generated/invoice_formatter.py` and
   `codebuddy_generated/tests/test_invoice_formatter.py` exist.
5. Neither `sample-legacy-app/handlers.py` nor `sample-legacy-app/utils.py` contains CRLF.
6. `black --check` on those two files passes.
7. The sample app still runs.
8. The package line count is at most 500.
9. The transcripts are unedited console output. Do not reformat them, do not remove lines,
   and do not add commentary inside them.

## Out of scope

Do not create any new module.
Do not create `README.md`, `DECISIONS.md`, or `COORDINATION.md`.
Do not run `git add` or `git commit`.
Do not commit the `.venv` directory. It is already in `.gitignore`.

## When you finish

Report, in this order:

1. The installed `claude-agent-sdk` version and the three prerequisite versions.
2. The full contents of `transcripts/smoke-results.md`.
3. Every file you edited to fix a defect, with the reason.
4. The per-file and total line counts.
5. The total number of Claude API runs you performed.

Then stop.
