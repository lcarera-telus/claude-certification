# Plan mode vs. direct execution

When to make Claude propose before it acts, and when planning is pure overhead.

## What plan mode actually is

> Plan mode tells Claude to research and propose changes without making them. Claude reads
> files, runs shell commands to explore, and writes a plan, but does not edit your source.
> Except in sessions with bypass permissions available, edits stay blocked until you approve
> the plan.

The block is enforced by the harness, not by Claude's good intentions. That is the difference
between plan mode and typing "please plan first" — the latter is a request, the former is a
constraint.

Plan mode is one of six permission modes:

| Mode | Runs without asking | Best for |
|---|---|---|
| `default` (shown as **Manual**) | Reads only | Reviewing every action yourself |
| `acceptEdits` | Reads, file edits, common filesystem commands | Iterating on code you're reviewing |
| `plan` | Reads, plus classifier-approved commands when auto mode is available | Exploring before changing |
| `auto` | Everything, with background safety checks | Long tasks, reducing prompt fatigue |
| `dontAsk` | Only pre-approved tools | Locked-down CI and scripts |
| `bypassPermissions` | Everything | Isolated containers and VMs only |

### Entering and leaving

- `Shift+Tab` cycles modes. From `auto` the first press goes to `default`, then the cycle runs
  `default` → `acceptEdits` → `plan` → back to `default`.
- `/plan` prefixed to a single prompt applies plan mode to that prompt only.
- `claude --permission-mode plan` starts a session in it.
- `"defaultMode": "plan"` in `.claude/settings.json` makes it the default for the project.
  This repo does exactly that — see `.claude/settings.json`.
- `Shift+Tab` again leaves plan mode without approving anything.

Approving a plan exits plan mode and switches the session to whichever mode the approve option
names, so Claude starts editing immediately.

## Decision table

| Task type | Mode | Why |
|---|---|---|
| **Multi-file refactor** | **Plan** | Cost of a wrong approach scales with the number of files. You want to argue about the target shape while it is still a paragraph, not a diff across nine files. Plan mode also surfaces files you forgot were coupled. |
| **One-line bugfix** | **Direct** | The diff *is* the plan. A plan for a one-line change is longer than the change, and reviewing the plan costs more than reviewing the line. Only plan if you cannot yet name the line. |
| **Dependency upgrade** | **Plan** | The blast radius is unknown until something reads the changelog and the lockfile. Breaking changes hide in transitive deps. You want the migration listed before anything touches `package.json`. |
| **Exploratory "how does X work"** | **Neither — just ask** | There is nothing to approve. Plan mode's output is a proposal for changes you are not making. It adds a step and produces a plan you will discard. Ask the question in a normal session. |
| **Destructive operations** (`rm -rf`, history rewrites, dropping data, force pushes) | **Plan, plus a hard block** | Plan mode is necessary but *not sufficient*. It shapes behaviour; it does not enforce it. Back it with `permissions.deny` or a `PreToolUse` hook, which apply regardless of what Claude decides. Note that no mode auto-approves `rm`/`rmdir` against a critical path — not even `bypassPermissions`. |

### The rule underneath the table

Plan when **the cost of the wrong approach exceeds the cost of describing the approach**.

That ratio, not the size of the change, is the deciding factor. A one-line change to a
migration that runs against production deserves a plan. A fifty-line change to a test fixture
does not.

---

## Worked example 1 — a task that should be planned

**The task:** scaffold this entire repository. A sample app, tests, a settings layer, four
commands, and the docs, with a hard constraint that the coordinator writes no source code.

**What was done:** planned first, in plan mode. The plan is at
`~/.claude/plans/lucky-forging-micali.md`.

**What planning caught, before any file was written:**

1. **The named implementation worker did not exist.** The original brief specified Codex as
   the implementer. Three checks during planning disagreed: `codex` was absent from `PATH`
   under both shells, `orca account list --json` reported `codex.accounts: []` with
   `hasAuth: false`, and a live probe returned `bash: codex: command not found`. Executing
   directly would have burned the first dispatch discovering this. Planning surfaced it while
   the cost was one question.

2. **The documentation URL in the brief was stale.** `docs.anthropic.com/en/docs/claude-code/`
   now 301-redirects to `code.claude.com/docs/en/`. Fetching the current pages first turned up
   a change that would have poisoned every command file: **custom commands have been merged
   into skills**, and `$0` — not `$1` — is the first argument. Writing from memory would have
   produced four plausible, subtly wrong command files.

3. **The substrate choice had an evidence-based answer.** Express or FastAPI were both
   allowed. Checking the machine settled it: Node 22 and npm present and resolving, Python
   3.13 with neither `fastapi` nor `pytest` installed. Recorded as ADR-001.

**Verdict:** planning was clearly correct. Each finding would have been more expensive to
discover mid-implementation, and the third one would have been invisible — a working FastAPI
repo that simply took longer to set up, with nobody noticing the choice was never justified.

---

## Worked example 2 — a task that should just be executed

**The task:** fix the `||` vs `??` bug in `src/app.js`. Because `0` is falsy,
`parsed || DEFAULT_LIMIT` discards an explicit `?limit=0` and returns the default.

**What was done:** executed directly. No plan, no spec — a single sentence to the worker:

> In claude-code-team-workflow/src/app.js, change the limit fallback on line 76 from || to ??
> so that ?limit=0 returns zero items instead of the default, and add a test for that case.

**Measured before:**

```
GET /items (none)  -> 200 items=3 limit=3
GET /items?limit=0 -> 200 items=3 limit=3     # wrong: asked for 0, got 3
GET /items?limit=2 -> 200 items=2 limit=2
```

**Measured after:**

```
GET /items (none)  -> 200 items=3 limit=3
GET /items?limit=0 -> 200 items=0 limit=0     # correct
GET /items?limit=2 -> 200 items=2 limit=2
```

Suite went from 5 tests to 6, all passing. Total elapsed: 1m 33s.

**Why planning would have been waste:** the file was known, the line was known, the fix was
known, and a test proves it. A plan would have restated all four and then been approved
unread. The verification — run the endpoint before and after — is stronger evidence than any
plan could have been.

> **Disclosure:** this bug was seeded deliberately so the example would be real rather than
> hypothetical. `tasks/01-sample-app.md` specified the `||` form and told the implementer not
> to improve it. See ADR-003.

---

## The same decision, one level up: how you delegate

The plan-vs-execute choice repeats when you hand work to another agent. The two dispatches
above used deliberately different styles.

| | Tasks 01 and 02 | Task 03 |
|---|---|---|
| **Dispatch** | A written spec file, 150+ lines, with acceptance criteria and pasted documentation excerpts | One sentence, no spec |
| **Prompt** | "Read `tasks/01-sample-app.md` and implement it exactly as specified" | The whole task, inline |
| **Review** | Ten numbered criteria, each checked by command | Run the endpoint before and after |
| **Elapsed** | ~5 min each | 1m 33s |

**What the heavy style bought.** The worker cannot see the coordinator's conversation. Task 02
needed current skill syntax that contradicts training data, so the spec carried the doc
excerpts inline. It worked: the worker wrote `$0`, used named `arguments:`, and matched every
injection against `allowed-tools` — none of which it would reliably have done from memory.

**What the light style bought.** Speed, and nothing lost. The single sentence contained the
file, the line, the change, and the expected behaviour. A spec would have added ceremony
around information already complete.

**The symmetry:** a full spec is plan mode for delegation. A one-line dispatch is direct
execution. The deciding ratio is identical — how expensive is the wrong approach, compared to
describing the right one.

### Two things the heavy style also bought

Both dispatches produced pushback that a rubber-stamp process would have missed:

- **The worker rejected a defective spec.** `tasks/01-sample-app.md` specified
  `"test": "node --test test/"`. The worker reported this fails on Node 22, which treats
  positional `--test` arguments as globs matching *files*; directory recursion for explicit
  path arguments was removed. It changed the script to a quoted glob and **flagged the
  deviation** instead of silently working around it. The coordinator reproduced the failure
  independently before accepting. See ADR-005.

- **The worker caught a documentation inconsistency the coordinator created.** After fixing
  the bug, it noted that `docs/claude-md-annotated.md` still described the bug in the present
  tense, and that the plan-mode guide would need to present it in the past tense. It correctly
  declined to edit files it did not own, and reported instead. Both lines were then corrected.

Written acceptance criteria are what make that possible. A worker told to "make it work" has
nothing to push back against.
