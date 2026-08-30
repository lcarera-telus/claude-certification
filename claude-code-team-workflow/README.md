# claude-code-team-workflow

A reference repository for how a team configures Claude Code and folds it into an existing
development workflow. Built as CCFA exam-prep material.

It is two things at once: a working example you can clone and run, and a teaching document.
The Express service is a substrate — 28 lines, deliberately boring. **The configuration layer
and the docs are the product.**

## Quick start

```bash
npm install
npm test                                                  # 6 tests, all passing
cp .claude/settings.local.example.json .claude/settings.local.json
claude
```

Then try `/review`, `/test-gen src/app.js`, `/adr "Some decision" Accepted`, or `/standup`.

## Layout

```
claude-code-team-workflow/
├── CLAUDE.md                       project instructions — a teaching artifact
├── DECISIONS.md                    5 ADRs, including one disclosure
├── COORDINATION.md                 the build log: every dispatch, verdict, iteration
├── src/app.js                      2 endpoints, exported without listen()
├── src/server.js                   the only file that binds a port
├── test/app.test.js                6 tests on the built-in node:test runner
├── .claude/
│   ├── settings.json               shared, committed, code-reviewed
│   ├── settings.local.example.json template for personal overrides
│   ├── skills/{review,test-gen,adr,standup}/SKILL.md
│   └── commands/adr-legacy.md      the older format, kept to show it still works
├── docs/
│   ├── claude-md-annotated.md      CLAUDE.md with commentary on every section
│   ├── plan-mode-guide.md          decision table + two performed examples
│   └── team-adoption.md            shared vs. personal, reviewing config, habits
└── tasks/                          the work-package specs used to build this repo
```

## The application

Two endpoints, so the commands have something real to run against.

| Method | Path | Behaviour |
|---|---|---|
| `GET` | `/health` | `200 {"status":"ok"}` |
| `GET` | `/items?limit=N` | `200 {"items":[...],"limit":N}`; `400` if `limit` is not a non-negative integer |

The app is exported without calling `listen()`, so tests import it directly and bind port `0`.
No test hardcodes a port, so runs never collide.

## The four commands

| Command | Demonstrates | Try it |
|---|---|---|
| `/review` | Dynamic context injection — the staged diff is injected before the prompt is sent | Stage something, run `/review` |
| `/test-gen` | Positional arguments. **`$0` is the first argument**, not `$1` | `/test-gen src/app.js` |
| `/adr` | Named arguments via `arguments:` frontmatter | `/adr "Use node:test" Accepted` |
| `/standup` | Multi-line fenced injection (` ```! `) | `/standup` |

All four set `disable-model-invocation: true`: they run when you ask, never on their own.

`.claude/commands/adr-legacy.md` is a fifth command in the **older single-file format**. It
still works. It is kept, and named so it does not collide, because custom commands have now
been merged into skills and most engineers learned the older form.

## Documentation pages used

Everything here was checked against the current docs during the build rather than written from
memory. That mattered — see the next section.

| Page | URL |
|---|---|
| Docs map | https://code.claude.com/docs/en/claude_code_docs_map.md |
| Skills (and custom commands) | https://code.claude.com/docs/en/skills.md |
| Memory / CLAUDE.md | https://code.claude.com/docs/en/memory.md |
| Permission modes / plan mode | https://code.claude.com/docs/en/permission-modes.md |
| Settings | https://code.claude.com/docs/en/settings.md |

Fetched 2026-08-30.

## What the docs check turned up

Four findings that contradict widely-held assumptions. Each one would have produced
plausible-looking but wrong configuration if written from memory:

1. **`docs.anthropic.com/en/docs/claude-code/...` is stale.** It 301-redirects to
   `code.claude.com/docs/en/...`. The old `slash-commands` page no longer exists.

2. **Custom commands have been merged into skills.** `.claude/commands/deploy.md` and
   `.claude/skills/deploy/SKILL.md` both create `/deploy`. Command files keep working; skills
   are recommended and win on a name collision.

3. **`$0` is the first argument, not `$1`.** Indices are zero-based. `$1` is a silent
   off-by-one that expands to the second argument — usually empty, so the command appears to
   do nothing rather than failing loudly.

4. **`@path` imports do not save context.** Imported files load at launch, so splitting a long
   CLAUDE.md into imports is organizational only. The mechanisms that actually reduce loaded
   context are path-scoped rules (`.claude/rules/` with `paths:`) and skills.

## CCFA concept checklist

Every artifact here maps to a certification topic.

### Domain 3 — Claude Code configuration and workflows (20%)

| Concept | Where to look |
|---|---|
| CLAUDE.md as project memory | `CLAUDE.md` |
| Why each CLAUDE.md section exists; what breaks without it | `docs/claude-md-annotated.md` |
| Memory hierarchy: managed → user → project → local | `docs/claude-md-annotated.md` |
| The 200-line target, and that over-length *reduces adherence* | `docs/claude-md-annotated.md` |
| Imports organize but do not save context | `docs/claude-md-annotated.md` |
| Free maintainer notes — HTML comments are stripped before injection | `CLAUDE.md` |
| Custom commands as skills; the `.claude/commands/` merge | `.claude/skills/*/`, `.claude/commands/adr-legacy.md` |
| Skill frontmatter: `allowed-tools`, `argument-hint`, `arguments`, `disable-model-invocation` | all four `SKILL.md` files |
| Frontmatter is read only when `---` is line 1 | every `SKILL.md` |
| Argument passing, indexed (`$0`) and named (`$title`) | `.claude/skills/test-gen/`, `.claude/skills/adr/` |
| Dynamic context injection, inline and fenced | `.claude/skills/review/`, `.claude/skills/standup/` |
| Settings precedence and shared vs. personal | `docs/team-adoption.md`, both settings files |
| Permission rules: `allow` / `ask` / `deny` | `.claude/settings.json` |
| Plan mode, all six permission modes, `defaultMode` | `docs/plan-mode-guide.md`, `.claude/settings.json` |
| When to plan vs. execute directly | `docs/plan-mode-guide.md` |
| Config as reviewable code | `docs/team-adoption.md` |

### Domain 1 — Agent architecture and orchestration (27%)

| Concept | Where to look |
|---|---|
| Coordinator/worker separation, enforced | `COORDINATION.md`, `tasks/` |
| Task decomposition into work packages | `tasks/01-sample-app.md`, `tasks/02-claude-config.md` |
| Context transfer via self-contained specs — the worker sees only the spec | `tasks/02-claude-config.md` and its pasted doc excerpts |
| Review loops with written acceptance criteria | `COORDINATION.md` |
| Escalation policy — two failures stop the loop | `COORDINATION.md` |
| Matching dispatch weight to task weight | `docs/plan-mode-guide.md`, final section |

### Domain 5 — Context management and reliability (15%)

| Concept | Where to look |
|---|---|
| Always-loaded vs. on-demand context | `docs/claude-md-annotated.md` |
| Token budgeting as a design decision | `docs/claude-md-annotated.md` |
| Context is not enforcement — hooks and `deny` rules are | `docs/team-adoption.md`, `docs/plan-mode-guide.md` |
| Verifying what actually loaded (`/context` vs. `/memory`) | `docs/claude-md-annotated.md` |

## How this repo was built

Under a coordinator/worker split, logged in `COORDINATION.md`. A coordinator wrote the specs,
docs, and this README; a separate agent dispatched through the `orca` CLI wrote all source,
tests, settings, and command files. The coordinator wrote no source code, and reviewed every
output against written criteria by running commands rather than reading claims.

Two moments are worth reading in `COORDINATION.md`, because both came from the worker pushing
back rather than complying:

- It **rejected a defective spec.** `node --test test/` fails on Node 22, which treats
  positional arguments as file globs. The worker flagged the deviation instead of silently
  routing around it; the coordinator reproduced the failure before accepting (ADR-005).
- It **caught a stale cross-reference** the coordinator had written, where a doc described the
  seeded bug in the present tense after it had been fixed.

Written acceptance criteria are what make that possible. A worker told to "make it work" has
nothing to push back against.
