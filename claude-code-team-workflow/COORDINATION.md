# Coordination log

Every work package dispatched to an implementation worker, with its spec, review verdict,
iteration count, and what changed.

**Protocol.** The coordinator writes specs, reviews, and documentation, and no source code.
All source, tests, settings, and command files come from a worker dispatched through the
`orca` CLI. The coordinator reviews by **running commands**, not by reading the worker's
report. One revision task per failure; two failures escalate to the user.

**Worker.** Codex was specified originally but is unavailable here — absent from `PATH` under
both shells, `orca account list --json` reports `codex.accounts: []` with `hasAuth: false`,
and a live probe returned `bash: codex: command not found`. A Claude worker was substituted
through the same `orca` dispatch path, with the user's approval, before any work started. See
ADR-004.

## Dispatch table

| # | Spec | Dispatch style | Produced | Iterations | Verdict |
|---|---|---|---|---|---|
| 01 | `tasks/01-sample-app.md` | Full spec (~140 lines) | `package.json`, `src/app.js`, `src/server.js`, `test/app.test.js`, `.gitignore` | 1 | **ACCEPT**, with one flagged deviation |
| 02 | `tasks/02-claude-config.md` | Full spec (~260 lines, doc excerpts inline) | `.claude/settings.json`, `.claude/settings.local.example.json`, 4 × `SKILL.md`, `.claude/commands/adr-legacy.md` | 1 | **ACCEPT** |
| 03 | *none — one sentence* | Minimal, no spec | one-line `\|\|` → `??` fix in `src/app.js`, plus one test | 1 | **ACCEPT** |

No package required a revision task. The escalation threshold was never reached.

## Dispatch commands

The real commands, so the log matches what was run:

```bash
orca terminal create --worktree active --title "worker-01" \
  --command 'claude --permission-mode acceptEdits' --json
orca terminal wait  --terminal <handle> --for tui-idle --timeout-ms 120000 --json
orca terminal send  --terminal <handle> --text "Read the file tasks/01-sample-app.md and
  implement it completely and exactly as specified..." --enter --json
orca terminal wait  --terminal <handle> --for tui-idle --timeout-ms 600000 --json
orca terminal read  --terminal <handle> --json
```

**Operational note.** `--permission-mode acceptEdits` covers file edits but **not** Bash
commands, and not writes into `.claude/`. Both workers stalled on approval prompts. Task 01's
worker was switched to auto mode so it could run its own `npm test`; task 02's seven
`.claude/` files were approved individually, then the worker was switched to auto mode for its
verification pass. Anyone repeating this should start the worker in auto mode.

---

## Task 01 — sample application

**Spec:** `tasks/01-sample-app.md`. Self-contained: goal, five files, exact parsing logic,
commenting requirements, seven acceptance criteria, and an explicit instruction not to
"improve" the seeded fallback line.

**Coordinator verification** — run directly, not taken from the worker's report:

```
$ npm test
# tests 5
# pass 5
# fail 0

$ grep -n "parsed || DEFAULT_LIMIT" src/app.js
76:  const limit = parsed || DEFAULT_LIMIT;

$ cat src/app.js src/server.js | grep -v -E '^\s*(//|/\*|\*|$)' | wc -l
28
```

Seeded-bug behaviour captured before any fix, by driving the live endpoint:

```
GET /items (none)  -> 200 items=3 limit=3
GET /items?limit=0 -> 200 items=3 limit=3     # wrong: asked for 0, got 3
GET /items?limit=2 -> 200 items=2 limit=2
GET /items?limit=abc -> 400
```

All seven criteria pass. `src/` is 28 non-comment lines against a 150 budget.

**Flagged deviation — accepted.** The spec required `"test": "node --test test/"`. The worker
reported that this fails on Node 22 and changed it to `node --test "test/**/*.test.js"`,
reporting the change rather than hiding it. The coordinator reproduced the failure before
accepting:

```
$ node --test test/
# pass 0
# fail 1
```

Node 22 treats positional `--test` arguments as globs matching *files*; directory recursion
for an explicit path argument was removed. **The spec was stale, not the implementation.**
Recorded as ADR-005.

**Verdict: ACCEPT.** 1 iteration.

---

## Task 02 — configuration layer

**Spec:** `tasks/02-claude-config.md`. Includes a reference section of documentation excerpts
fetched during planning, pasted inline, with an instruction that the excerpts override the
worker's training data where they differ.

**Why the excerpts were necessary.** The worker sees only the spec file — never the
coordinator's conversation or its research. Two spec requirements sit exactly where training
data is most likely to be stale: `$0` vs. `$1` for the first argument, and whether
`.claude/commands/` is deprecated. Without the excerpts, plausible and wrong output was the
likely result.

**Coordinator verification:**

```
$ for f in <the seven paths>; do [ -f "$f" ] && echo "OK  $f"; done
OK  .claude/settings.json
OK  .claude/settings.local.example.json
OK  .claude/skills/review/SKILL.md
OK  .claude/skills/test-gen/SKILL.md
OK  .claude/skills/adr/SKILL.md
OK  .claude/skills/standup/SKILL.md
OK  .claude/commands/adr-legacy.md

$ node -e "JSON.parse(...)"          settings.json OK / example OK
$ head -1 on each SKILL.md           all five: [---]
$ grep '\$[0-9]' test-gen/SKILL.md   $0 only; $1 appears solely as a named counter-example
$ grep 'arguments:' adr/SKILL.md     arguments: [title, status], body uses $title / $status
$ grep '[^[:space:]]!`' skills/*     none — every injection is at a valid position
```

Injection sites matched against their grants:

| Skill | Injects | `allowed-tools` | Covered |
|---|---|---|---|
| `/review` | `git diff --staged --name-only`, `git diff --staged` | `Bash(git diff *)` | yes |
| `/standup` | `git log --oneline -15`, `git status --short` (fenced) | `Bash(git log *)`, `Bash(git status *)` | yes |

All ten criteria pass. Skill bodies are 43–50 lines against a 60-line ceiling.

**Verdict: ACCEPT.** 1 iteration.

---

## Task 03 — one-line fix, dispatched directly

**No spec file.** This is the deliberate contrast with 01 and 02: the delegation-level version
of direct execution versus planning. The entire dispatch was one sentence:

> In claude-code-team-workflow/src/app.js, change the limit fallback on line 76 from || to ??
> so that ?limit=0 returns zero items instead of the default, and add a test for that case.

**Coordinator verification:**

```
$ grep -n "DEFAULT_LIMIT" src/app.js
76:  const limit = parsed ?? DEFAULT_LIMIT;

$ npm test
# pass 6
# fail 0

GET /items (none)  -> 200 items=3 limit=3
GET /items?limit=0 -> 200 items=0 limit=0     # fixed
GET /items?limit=2 -> 200 items=2 limit=2
```

The worker additionally ran its new test against the pre-fix code to prove it discriminates —
it failed with `||` and passes with `??`. That is the right instinct: a regression test that
passes against the broken code tests nothing.

Elapsed: 1m 33s, against roughly 5 minutes for each spec-driven package.

**Worker-raised issue — actioned.** The worker reported that `docs/claude-md-annotated.md`
still described the bug in the present tense, and that the plan-mode guide would need past
tense. It correctly declined to edit files it did not own. The coordinator fixed both
references in `CLAUDE.md` and `docs/claude-md-annotated.md`.

**Verdict: ACCEPT.** 1 iteration.

---

## Coordinator-authored files

Written by the coordinator, never dispatched, per the role constraint:

`CLAUDE.md`, `README.md`, `DECISIONS.md`, `COORDINATION.md`, `docs/claude-md-annotated.md`,
`docs/plan-mode-guide.md`, `docs/team-adoption.md`, `tasks/01-sample-app.md`,
`tasks/02-claude-config.md`.

## What the review loop actually caught

Both findings came from the worker pushing back against written criteria, not from complying
with them:

1. **A defective spec** (task 01) — surfaced and explained rather than silently worked around.
2. **A stale cross-reference** (task 03) — in a file the worker was not permitted to edit, so
   it reported instead of fixing.

Neither is available to a process that dispatches vague instructions. A worker told to "make
it work" has nothing to disagree with, and a coordinator who reviews by reading the worker's
summary would have accepted both problems.
