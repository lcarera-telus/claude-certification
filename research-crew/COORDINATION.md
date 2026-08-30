# COORDINATION.md — the build-time delegation log

This file records the **outer** delegation layer: the architect (Claude Opus 5) dispatching
implementation work to a separate worker agent, reviewing the result, and iterating.

The system being built, `research-crew`, is itself a delegation system. So this log is a
worked example of the subject matter. Read it next to the run-time log in `runs/<id>/` and
the two layers line up. `README.md` has the side-by-side table.

## Protocol

1. Write one self-contained spec per work package in `tasks/NN-<name>.md`.
2. Dispatch it to a fresh worker agent through the `orca` CLI.
3. Read the worker's output. Review it against the spec's acceptance criteria.
4. On failure, send **one** revision task. After a second failure, escalate to the user.
5. Log every dispatch, verdict, and iteration below.

## Why the worker is `claude` and not `codex`

The original brief named Codex as the implementer. Codex is not installed on this machine.
Checked before dispatching anything:

- no `codex` on the PATH, in Git Bash or in PowerShell
- no npm global, bun, pnpm, or volta shim
- no `~/.codex` directory
- `orca account list --json` reports zero Codex accounts

`claude` is installed at `C:\Users\lcare\.local\bin\claude.exe`, version **2.1.251**. The
user chose to delegate to a separate `claude` agent instead. The delegation structure is
unchanged: a separate process, its own context window, briefed only by a spec file.

## An honest note on how tight the isolation really is

The run-time subagents are isolated by **enforcement**. `tools: []` means a tool is absent
from the session, so the agent cannot use it. There is nothing to disobey.

The build-time worker is isolated by **instruction**. It runs in the same worktree, so it
*could* read this file, the other task specs, or the plan. It is told not to. Nothing stops
it.

That gap is the point, and it is worth carrying into the exam. A boundary you enforce with
tool scoping holds. A boundary you request in a prompt holds only while the agent
cooperates. The same distinction drives the `reporter` design in `agents/reporter.md`.

## Dispatch log

| # | Work package | Worker handle | Verdict | Iterations |
|---|---|---|---|---|
| 1 | WP1 — foundation | `term_258ea5cf` | **accepted** | 0 |
| 2 | WP2 — pipeline | `term_dcbcf1ca` | **accepted** | 0 |
| 3 | WP3 — verification + live run | `term_42d2de86` | **accepted** | 0 |
| 4 | WP4 — four post-run fixes | `term_0ac836f2` | **accepted** | 0 |

---

### Dispatch 1 — WP1: run state, agent loader, observability

**Spec:** `tasks/01-foundation.md`
**Dispatched:** worker terminal `term_258ea5cf-4df7-4ff3-abe4-ac546f7672f1`, title `WORKER-WP1`

Commands used:

```bash
orca terminal create --worktree active --title "WORKER-WP1" --command "claude" --json
orca terminal wait   --terminal term_258ea5cf... --for tui-idle --timeout-ms 120000 --json
orca terminal send   --terminal term_258ea5cf... --text "<brief>" --enter --json
```

The `wait --for tui-idle` step is not optional. Send a prompt to an agent TUI before it
finishes starting and the input is dropped, which looks exactly like an agent that ignored
its instructions. This is the build-time twin of a race that also bites at run time.

**Scope handed over:** `state.py`, `agents_loader.py`, `observability.py`, their tests, and
`requirements.txt`. Explicitly withheld: `coordinator.py`, `cli.py`, `verify.py`.

**Context deliberately restated in the spec.** The worker cannot see the research that
produced this design, so anything discovered here had to be written into the spec by hand:

- the Agent SDK docs moved to `code.claude.com/docs/en/agent-sdk/`
- Managed Agents on `platform.claude.com` is a different product, and is not what we use
- `AgentDefinition` field names, including the camelCase exceptions
- the `tools` absent versus `tools: []` distinction, which is the trap in this package

Marshalling that by hand is the same work `coordinator.py` does when it writes a prompt
string for the next subagent. Neither layer gets to just "pass the context along".

**Verdict: accepted, 0 iterations.**

Reviewed by re-running everything rather than trusting the worker's report. A worker
reporting its own success is exactly the case where independent verification matters.

| Criterion | Result | How it was checked |
|---|---|---|
| 1 — install succeeds | pass | `claude-agent-sdk` 0.2.148 installed |
| 2 — tests pass, offline | pass | re-ran `pytest`: **47 passed in 1.40s** |
| 3 — four agents, right keys | pass | `load_agents()` on the real directory |
| 4 — `searcher.tools == ["WebSearch"]` | pass | direct assertion |
| 5 — other three `tools == []` | pass | direct assertion |
| 6 — synthesizer is `opus`, rest `sonnet` | pass | direct assertion |
| 7 — no `<!--` or `DESIGN NOTES` in prompts | pass | prompts are 1.6–2.2 KB against 4.7–5.5 KB source files |
| 8 — prompts start `You are the` | pass | direct assertion |
| 9 — absent `tools` differs from `[]` | pass | absent gives `None`, empty gives `[]` |
| 10 — `RunState` round-trips | pass | covered by the suite |
| 11 — `total_cost_usd` handles `None` | pass | all-`None` gives `0.0` as a `float` |
| 12 — recorder refuses a reused `run_id` | pass | raises `FileExistsError` |
| 13 — module docstrings | pass | read |
| 14 — under 260 code lines | pass | **161** lines, with a test enforcing the budget |

The important check was criterion 9, and the worker improved on the spec here. It read the
installed SDK source and found `tools: list[str] | None = None`, then pointed out something
my spec did not say: **`None` and `[]` are both falsy in Python.** So `if tools:` or
`tools or []` silently collapses the restrictive case into the permissive one, and a
supposedly tool-less reporter would receive full filesystem and web access with no error
anywhere. The loader branches on `"tools" in front` — key presence, never truthiness.

Verified empirically, not just by reading the code:

```
absent tools key -> tools = None   (inherit every subagent tool)
tools: []        -> tools = []     (grant none)
both falsy in Python (the trap): True
```

It also handled a third spelling the spec never mentioned. YAML `tools:` with no value parses
to `None`, not to a list. Rather than guess between "inherit everything" and "grant nothing",
it raises `ValueError`. Guessing silently there is precisely the wrong move, so this is the
right call and it goes beyond what was asked.

**Seven spec defects the worker reported.** All accurate, and worth recording because a spec
is the only channel to a worker — every defect here is a defect in my half of the work:

1. The exact-file list forbids `conftest.py`, so each test file must patch `sys.path` itself.
   Conforming but not what a real project would do. My constraint was too tight.
2. Criterion 11 is under-specified: `sum()` over an empty sequence returns `int` `0`, which
   contradicts the `-> float` annotation. Fixed with an explicit `float()`.
3. The spec said "raise" for a reused `run_id` without naming the exception. `FileExistsError`
   chosen, which fits the condition.
4. `Conflict.position_a` and `position_b` are typed as bare `dict`, so a malformed position
   serialises happily. **Carried into `tasks/03-verification.md`** — the verifier must catch it.
5. YAML `tools:` with no value — the third spelling, above.
6. `run_id` has second resolution, so two runs starting in the same second collide, and the
   failure then surfaces in `RunRecorder` rather than in `RunState.new()`. Accepted: correct
   behaviour reported by the wrong module. Not worth a revision for a study artifact.
7. The `AgentDefinition` field table in my spec was incomplete though not wrong. 0.2.148 also
   accepts `skills`, `memory`, `initialPrompt`, `maxTurns`, `background`, `effort`, and
   `permissionMode`. It also noted that passing `"Skill"` inside `tools` is now deprecated in
   favour of the `skills` field. Nothing in this crew does that.

One test failed on the worker's first run: `total_cost_usd()` returned
`0.15000000000000002` for `0.10 + 0.05`. It changed the assertion to `pytest.approx` rather
than rounding inside the sum, on the grounds that a cost report which silently rounds cannot
be audited. Correct instinct — fix the test, not the number.

Result: **161 code lines against a 260 budget, with comments outnumbering code about 2.4 to
1**, which is what a teaching artifact should look like.

---

### Dispatch 2 — WP2: coordinator pipeline and CLI

**Spec:** `tasks/02-pipeline.md`
**Dispatched:** fresh worker terminal, title `WORKER-WP2`

A **new** worker, not the one that built WP1. That worker's context is full of WP1's
implementation detail, and none of it is needed here. Starting fresh is the same reasoning
the run-time pipeline uses: each subagent gets a clean context holding only what its own job
requires. Reusing the WP1 worker would have been the build-time equivalent of skipping
context isolation because the history happened to be lying around.

The cost is the same one the run-time layer pays. Everything the new worker needs about
Task 01 must be restated in the spec, by hand, because it cannot see the previous
conversation. `tasks/02-pipeline.md` opens with a summary of the modules WP1 produced for
exactly that reason.

**Context deliberately restated:** the `RunState` field list and method signatures, the
`RunRecorder` API, `load_agents()`, the `Task`/`Agent` rename, the requirement that
`allowed_tools` contain `"Agent"`, and the warning that a parent may summarise a subagent's
output when the coordinator needs it verbatim.

**Verdict: accepted, 0 iterations.**

Re-verified independently: **72 passed in 2.07s**, and every criterion checked against the
source rather than against the worker's summary.

| Criterion | Result | Evidence |
|---|---|---|
| 1 — full suite passes offline | pass | 72 passed, WP1's 47 included |
| 2 — `allowed_tools` has `"Agent"` | pass | `ALLOWED_TOOLS = ["Agent", "WebSearch"]` |
| 3 — matches `Agent` and `Task` | pass | `DELEGATION_TOOL_NAMES = frozenset({"Agent", "Task"})` |
| 4 — explicit subtype branch with a raising else | pass | four-way branch; unhandled subtype raises `PhaseFailed` |
| 5 — the loop is bounded in code | pass | `MAX_SEARCH_ROUNDS = 2`; a test asserts the searcher never runs a third time |
| 6 — `max_budget_usd` on every call | pass | passed in the shared options |
| 7 — both env caps set | pass | `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`, `..._MAX_CONCURRENT_SUBAGENTS=4` |
| 8 — input, output, state recorded per phase | pass | dedicated test |
| 9 — citation map built in Python | pass | dedicated test |
| 10 — no `.env` loaded | pass | grep finds nothing; a test asserts it too |
| 11 — under 300 code lines | pass | **276** (`coordinator.py` 223 + `cli.py` 53) |
| 12 — docstrings | pass | read |

**The worker mutation-tested its own guards.** Rather than assert the tests pass, it broke
each guard in turn and confirmed a test caught it. This is the difference between "my tests
pass" and "my tests would notice". Its results:

| Mutation applied | Tests that failed |
|---|---|
| remove the `search_round < MAX_SEARCH_ROUNDS` check | 1 — the searcher ran a third time |
| let an unknown subtype pass as success | 4 |
| disable the delegation check | 1 |
| drop the `"Task"` alias | 1 |
| remove `"Agent"` from `allowed_tools` | 2 |
| renumber source ids on re-search | 2 |
| remove verbatim capture | 11 |

It also refused to assert "no network calls" without proving it. Its first guard blocked all
sockets and produced 19 failures, including WP1 tests that had passed. Instead of loosening
the tests, it diagnosed the guard: on Windows, `asyncio.run` builds a loopback socketpair as
the event loop's self-pipe, which is local plumbing rather than network access. It re-scoped
the guard to outbound connections, DNS, and process spawning, and all 72 tests then passed
under it. Correct instinct — when a new check fails, first ask whether the check is wrong.

Its first draft was 368 code lines, over the 300 cap. It compacted the code and kept every
comment, which is the right way round for this artifact.

**Two insights from the worker worth keeping**, both sharper than my spec:

- **`allowed_tools` is session-level, not per-agent.** `"WebSearch"` must appear there even
  though the coordinator itself never searches, because the searcher subagent runs inside
  that session and its one granted tool must also be permitted at session level. Per-agent
  `tools` narrows; `allowed_tools` admits. Both must allow a tool for it to be usable.
- **Verbatim capture has the same two-layer split as everything else here.** Reading the
  `ToolResultBlock` off the stream is *structural* — those are bytes the SDK moved. The
  "reproduce the output exactly" line in the prompt is *behavioural* — bytes the model chose.
  Only the first is trustworthy; the second is the fallback. The same reasoning as ADR-004,
  arrived at independently.

**Four spec defects reported.** All fair:

1. **Per-phase progress cannot come from `cli.py`.** I asked for it there, but I also fixed
   `run_research`'s signature with no callback, and the CLI makes exactly one `asyncio.run`
   call, so it cannot observe a phase boundary. The worker put `_progress()` in
   `coordinator.py` rather than change a signature I had spelled out. My spec was internally
   inconsistent.
2. **`record_state` timing contradicts WP1's recorder docstring.** My step order has
   `run_phase` write the snapshot, but parsing happens in the caller, so
   `state-after-01-search.json` does not yet contain the sources. The worker followed the
   explicit order and commented the consequence. **Genuine wart, listed under Known issues.**
3. `python -m research_crew.cli` still needs `src` importable. A `pyproject.toml` would have
   fixed it but "create nothing else" forbade it. My constraint again.
4. `BudgetExceeded` — I did not say which cost to report. It reports both the ceiling and
   the actual, since the gap is what a reader wants.

It also noted that the `claude-api` skill triggered on this task but states it does not
generate Agent SDK code, so it worked from the spec and verified every shape against the
installed `claude-agent-sdk` 0.2.148 instead.

---

### Dispatch 3 — WP3: citation integrity and the live run

**Spec:** `tasks/03-verification.md`
**Dispatched:** fresh worker terminal, title `WORKER-WP3`

Third fresh worker, same reasoning as before.

This package carries forward defect 4 from the WP1 review. `Conflict.position_a` and
`position_b` are typed as bare `dict`, so a malformed position serialises without complaint.
WP1's worker spotted it and it was out of scope there, so `tasks/03-verification.md` asks for
a `validate_conflicts()` function. A defect found in one package and fixed in the next is
what the review step is for; without a written log it would simply have been forgotten.

This is also the only package that spends real money. It runs the demo question once, under
the `max_budget_usd` ceiling, and the spec says explicitly: if the run fails, diagnose from
`runs/<id>/` and run once more, do not loop. The instruction the coordinator enforces in code
is the same one the build layer has to state in prose.

#### Interruption: the coordinator was wrong, and the worker refused the instruction

Worth recording in full, because the lesson runs opposite to the usual one.

Mid-run, I told the worker its live run had died: no `python` process on the machine, and
only `01-searcher.input.json` in the run directory. I instructed it to diagnose the failure
before spending its second run.

**All three claims were false.** The worker checked rather than complied, and answered with
evidence:

| My claim | What was actually true |
|---|---|
| no `python` process running | PID 28480 alive since 12:22:34 |
| only `01-searcher.input.json` exists | four files, including a 13,994-byte searcher output |
| the run died in phase 1 | captured output showed `[01] search` then `[02] analyze` |

My error was a bad check, not a bad inference. The process is named **`python3.13.exe`**, so
`Get-Process python` matched nothing and returned empty. Empty looked like absence. Re-run as
`Get-CimInstance Win32_Process -Filter "Name LIKE '%python%'"`, it appears immediately. My
directory listing was simply early: the searcher wrote its output at 12:24:28, moments after
I looked.

Two things worth taking from this.

**A coordinator's instructions deserve the same scepticism as a worker's reports.** The
standard warning is not to take an agent's self-reported success at face value, and this log
applies it — every work package was re-verified independently. The reverse holds equally. Had
the worker complied, it would have "diagnosed" a failure that never happened and possibly
burned its one remaining live run re-running a working pipeline. It was told to act on a
false premise by the component with authority over it, and the correct response was to check
the premise. Delegation is not obedience.

**The worker read the run directory the way the artifacts were designed to be read, and got
more out of them than I did.** Its observation:

> `02-analyst.input.json` exists but `02-analyst.output.md` does not, which localises the run
> to "inside phase 2" with no guessing. Log only outputs and a mid-flight run is
> indistinguishable from a dead one.

The recorder writes input, then output, then state, in that order per phase. So the highest
complete triple names the last finished phase, and a dangling `.input.json` names the phase
in flight. `README.md` presents `runs/<id>/` as a post-mortem tool. This is the same
directory read as a **progress** record, which is a property we got for free by recording
inputs separately from outputs and did not design for deliberately.

**Verdict: accepted, 0 iterations.**

Re-verified: **93 passed in 2.44s**. `verify.py` imports only `re`, `urllib.parse`,
`dataclasses`, `collections.abc`, and `.state` — no `claude_agent_sdk`, no model, so the
check really is code rather than judgment. The referential-versus-semantic limitation is in
the module docstring, and `test_referential_check_cannot_detect_a_false_claim` keeps it
visible.

**The live run completed all six phases.** `runs/20260830-152235/`:

| Phase | Agent | Model | Cost | Duration | Subtype |
|---|---|---|---|---|---|
| 1 search | searcher | sonnet | $0.779 | 112s | success |
| 2 analyse | analyst | sonnet | $0.586 | 93s | success |
| 3 search (re-search) | searcher | sonnet | $0.598 | 118s | success |
| 4 analyse (re-run) | analyst | sonnet | $0.968 | 216s | success |
| 5 synthesise | synthesizer | **opus** | $0.848 | 162s | success |
| 6 report | reporter | sonnet | $0.816 | 167s | success |
| | | | **$4.59** | **868s** | |

**The bounded re-search fired, exactly once.** The analyst reported insufficient coverage
after round 1, the coordinator ran a second search round, and a third was impossible.
28 sources became 46; the report cites 21 of them across 70 citations.

**The report is good.** The Disagreements section found four conflicts, marked three
*apparent* and one *real*, and named the separating condition each time. The headline finding
— that the multi-agent advantage largely disappears once reasoning-token budgets are held
equal, while surviving on breadth-first parallelisable tasks — is exactly the kind of result
that averaging would have destroyed. The synthesizer's "never resolve by averaging" rule did
real work here.

**The run also exposed four defects**, which became `tasks/04-post-run-fixes.md`. Three were
defects in my specs, not in anyone's implementation. Details in dispatch 4.

Two spec problems the worker raised that are worth keeping:

- **The documented run command did not work.** `python -m research_crew.cli` fails with
  `ModuleNotFoundError` because the package is under `src/` with no `pyproject.toml`, which
  earlier "create exactly these files" constraints ruled out. `PYTHONPATH=src` is required.
  `README.md` carried the broken command and has been corrected.
- **`validate_conflicts` had an incomplete signature.** I specified
  `validate_conflicts(conflicts) -> list[str]` and then required it to check `source_ids`
  against "the citation map passed alongside" — which no parameter provided. It added an
  optional `citation_map` parameter satisfying both readings.

---

### Dispatch 4 — WP4: four fixes found by the live run

**Spec:** `tasks/04-post-run-fixes.md`
**Dispatched:** fresh worker terminal `term_0ac836f2`, title `WORKER-WP4`

Not a revision for poor work. Three of the four defects were mine, and only a real run could
have surfaced them. Offline tests all passed while the system carried them.

| # | Defect | Origin |
|---|---|---|
| 1 | `max_budget_usd` bounded a phase, not the run — $4.59 spent against a $3.00 ceiling, every phase `success` | my ADR-003 + spec 02 |
| 2 | Harness trailers (`agentId:`, `<usage>`) leaked into `report.md` | spec 02's verbatim-capture instruction |
| 3 | `numbering_gaps` fired on every correct run | my spec 03 |
| 4 | `state-after-NN` snapshots lagged one phase | my spec 02 |

**Defect 1 is the one to remember.** `max_budget_usd` is a per-`query()` ceiling, and
ADR-003 makes one `query()` per phase, so the cap reset six times. No phase came near $3.00 —
the largest was $0.97 — so nothing raised, and the true ceiling was about $18. A limit at the
wrong scope reads exactly like a limit at the right one. The fix converts it to a run-level
cap in the application layer: `remaining = ceiling - state.total_cost_usd()`, passed to each
phase, with a raise before any phase that has nothing left. `README.md` now teaches this.

**Defect 2 came directly from doing the right thing.** Spec 02 required reading the `Agent`
tool's `ToolResultBlock` for the subagent's output verbatim, precisely because a parent may
paraphrase. That is correct — but the block carries the harness's own framing as well, and a
verbatim read copies the framing too. Reading raw bytes off a channel does not make every
byte on that channel payload.

**Verdict: accepted, 0 iterations.**

Re-verified: **108 passed in 2.13s**. Both mutation checks confirmed:

| Fix | Mutation | Result |
|---|---|---|
| 1 | remove the guard, pass the full budget to every phase | 3 tests failed |
| 4 | restore `record_state` as `run_phase`'s last step | 3 tests failed |

Neither mutation was left in the tree.

**The decisive check was against the real artifact, not the test suite.** Running the fixed
code over the actual corrupted `runs/20260830-152235/report.md`:

```
bytes removed by strip_harness_trailers : 196
last line after                         : [44] Specialists or Generalists? ...
re-verified against the real 46-source citation map:
  ok=True, checked_citations=70
  unmapped=[] uncollected=[] orphan=[] misnumbered=[] malformed=[]
recorded verdict was: ok=False, numbering_gaps=23, malformed=4
```

A report the original verifier failed for 27 reasons passes cleanly, and the 70 real
citations still check out. That is the difference between "the tests pass" and "the defect is
gone".

**One spec contradiction the worker was right to override.** Criterion 1 said "all 93
existing tests still pass", which cannot hold alongside fixes 1 and 3: deleting
`numbering_gaps` invalidates assertions whose only purpose was testing the deleted check, and
the run-level budget breaks a test asserting the old per-phase value. It treated criterion 2
("no assertion weakened to make something pass") as binding, retargeted the assertions to the
newly specified behaviour, replaced the two dead tests with the regression test I had asked
for, and added 17 more. That is the correct reading of two criteria in conflict.

It also caught that my acceptance wording for fix 1 overstated the behaviour. "Raises before
the phase that would cross the ceiling" is not what the steps describe: they raise before the
first phase with *nothing left*, which is the phase after the one that crossed. The SDK's own
per-call enforcement bounds the crossing phase. Its test asserts what the code does rather
than what my prose claimed.
