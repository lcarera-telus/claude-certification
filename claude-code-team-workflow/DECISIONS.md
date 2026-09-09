# Architecture decision records

Short ADRs for `claude-code-team-workflow`. Each records a decision that had real
alternatives, so a reader can tell what was chosen deliberately from what is incidental.

---

## ADR-001 — Express on Node, not FastAPI on Python

**Status:** Accepted

**Context.** The repo needs a trivial HTTP service as a substrate. The configuration layer is
the actual product, so the substrate must not introduce toolchain work. Either Express or
FastAPI was acceptable in principle.

The environment decided it. Node v22.14.0 and npm 10.9.2 are installed, and `npm view express
version` resolves against the registry. The installed Python 3.13 has **neither `fastapi` nor
`pytest`**, so the Python route needs two installs before a single test can run.

**Decision.** Express 5 with the built-in `node:test` runner. One runtime dependency, one
`npm install`, no test framework, no build step.

**Consequences.** `/test-gen` and `/review` operate on a suite that actually runs, which is
the point — the commands are demonstrated against something real, not described. The cost is
that a Python-first reader must translate the app; that is acceptable because the app is 28
lines and nothing in the configuration layer is language-specific.

---

## ADR-002 — Commands ship as skills, with one legacy command file kept

**Status:** Accepted

**Context.** The current documentation states that custom commands have been merged into
skills: `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both create
`/deploy`. Existing command files keep working, skills are recommended, and a skill wins if
both share a name.

Shipping only skills would be cleanest. But most engineers reading this repo learned the
`.claude/commands/*.md` form, and a repo that silently omits it leaves them unsure whether
their existing setup is broken.

**Decision.** All four working commands are skills under `.claude/skills/<name>/SKILL.md`. One
extra file, `.claude/commands/adr-legacy.md`, is kept in the older format and named so it does
not collide, with a header explaining the relationship.

**Consequences.** The repo demonstrates both formats and the precedence rule instead of
asserting them. The cost is one file that exists purely to teach; its header says so, so
nobody mistakes it for a live command someone forgot to migrate.

---

## ADR-003 — A seeded bug, disclosed

**Status:** Accepted

**Context.** `docs/plan-mode-guide.md` must contain two worked examples that were actually
performed: one task that should be planned first, and one that should just be executed. The
direct-execution example needs a genuine one-line bug. Waiting for a real bug to appear was
the alternative, but nothing guarantees a suitably one-line defect shows up on schedule.

**Decision.** The bug was **deliberately seeded**, and this ADR is the disclosure.
`tasks/01-sample-app.md` specified the fallback as `const limit = parsed || DEFAULT_LIMIT;`
and instructed the implementer not to improve it. Because `0` is falsy, `?limit=0` skips the
caller's value and returns `DEFAULT_LIMIT` items.

Measured before the fix:

```
GET /items?limit=0 -> 200 items=3 limit=3     # wrong: asked for 0, got 3
```

This is the `||` vs `??` class of bug, which is real and common: `??` falls back only on
`null` and `undefined`, so a meaningful `0` survives it.

**Consequences.** The teaching repo stays honest — a reader is told the bug was planted rather
than being shown a staged discovery. `CLAUDE.md` warns Claude not to fix it as a drive-by
change, which doubles as a demonstration of a "things Claude gets wrong here" entry earning
its place. After the fix, `?limit=0` correctly returns zero items.

---

## ADR-004 — Codex was unavailable; a Claude worker was substituted

**Status:** Accepted

**Context.** The build protocol requires the coordinator to write no implementation code, and
originally named Codex as the implementing worker dispatched through the `orca` CLI. Codex is
not usable in this environment. Three independent checks agree:

- `codex` is absent from `PATH` under both Git Bash and PowerShell
- `orca account list --json` reports `codex.accounts: []` and `hasAuth: false`
- a live probe, `orca terminal create --command "codex --version"`, returned
  `bash: codex: command not found`

**Decision.** Dispatch a **Claude worker** through the same `orca` CLI, via
`orca terminal create --worktree active --command 'claude --permission-mode acceptEdits'`,
then `terminal send` / `terminal wait` / `terminal read`. The coordinator protocol is
unchanged: a separate agent, context transferred only through the spec file, and every output
reviewed against written acceptance criteria.

**Consequences.** What the exercise teaches — coordinator/worker separation, self-contained
specs, review loops — is preserved, since none of it depends on which model implements. The
substitution was approved before any dispatch. `COORDINATION.md` records the real dispatch
commands, so the log matches what was actually run.

---

## ADR-005 — `npm test` uses a quoted glob, not a directory argument

**Status:** Accepted

**Context.** `tasks/01-sample-app.md` specified `"test": "node --test test/"`. The worker
reported this fails on the installed Node 22 and changed it, flagging the deviation rather
than hiding it. The coordinator reproduced the failure independently before accepting:

```
$ node --test test/
# pass 0
# fail 1
```

Node 22 treats positional `--test` arguments as glob patterns matching **files**. Directory
recursion for an explicit path argument was removed, so `test/` matches the directory entry
and Node tries to execute it as a module.

**Decision.** Keep the worker's form: `"test": "node --test \"test/**/*.test.js\""`. The spec
was stale, not the implementation.

**Consequences.** `npm test` passes 5/5 on Node 22. The `engines` field still says `>=18`,
where the original form also worked, and the quoted glob is portable across both. This is
recorded because it is the one place the delivered repo departs from its own written spec —
and because a worker that surfaces a spec defect instead of silently working around it is the
behaviour the review loop is meant to produce.
