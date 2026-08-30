# Task 04 - Four fixes found by the first live run

Live run `20260830-152235` completed all six phases and produced a good report. It also
exposed four defects. Three of them are defects in earlier **specs**, not in the code that
implemented them, so do not treat any of this as cleaning up after a careless predecessor.

Read this whole spec before you change anything. Keep every diff surgical. **No live run is
needed or permitted for this task** — every fix here is provable offline.

---

## Fix 1 (most serious) - `max_budget_usd` does not bound the run

### Evidence

`runs/20260830-152235/cost.json`:

```
"max_budget_usd": 3.0,
"total_cost_usd": 4.59486355
```

Every phase reported `subtype: "success"`. Nothing raised. The run overspent its stated
ceiling by 53% and reported complete success.

### Cause

`max_budget_usd` is a **per-`query()`** ceiling. `run_phase` passes the same
`max_budget_usd` value to every phase, so the cap resets on each one. The six phases cost
$0.78, $0.59, $0.60, $0.97, $0.85, and $0.82 — none came close to $3.00 alone, so the SDK
never fired. With six phases the real ceiling is roughly `6 x 3.0 = $18`, not `$3.00`.

This is worse than having no cap. A reader trusts the number and it is not true.

### The fix

Make the ceiling a **run-level** budget while keeping the SDK's per-call enforcement.

1. Before each phase, compute `remaining = max_budget_usd - state.total_cost_usd()`.
2. If `remaining <= 0`, raise `BudgetExceeded` **before** making the call. Name the phase
   that was about to run, the ceiling, and the amount already spent.
3. Pass `max_budget_usd=remaining` to that phase's `query()` call, so the SDK's own
   enforcement stays armed and now bounds the run rather than one phase.
4. Keep the existing `error_max_budget_usd` branch. It is still correct and now it means
   "this phase exhausted what was left of the run's budget".

Add a comment explaining what happened here. The general lesson is the one the README makes
about bounded loops: a limit enforced at the wrong scope reads exactly like a limit enforced
at the right one, right up until the invoice arrives. The application layer must convert a
per-call cap into a per-run cap; the SDK cannot know your pipeline has six calls in it.

### Tests

- Phases whose costs sum past the ceiling: the run raises `BudgetExceeded` before the phase
  that would cross it, and that phase's `query()` is never called.
- The value passed to each `query()` decreases as spend accumulates.
- A run that stays under the ceiling still completes, and nothing raises.

---

## Fix 2 - SDK trailer text leaks into the report

### Evidence

The last four lines of `runs/20260830-152235/report.md`, inside the References section:

```
agentId: ad337dd3c386c9a66 (use SendMessage with to: 'ad337dd3c386c9a66', summary: '<5-10 word recap>' to continue this agent)
<usage>subagent_tokens: 18671
tool_uses: 0
duration_ms: 45769</usage>
```

`citation-report.json` caught all four as `malformed_references`. The verifier did its job.
The artifact is still corrupted.

### Cause

`run_phase` reads the `Agent` tool's `ToolResultBlock` to get the subagent's output verbatim.
That block contains more than the agent's message: Claude Code appends an `agentId:` trailer
so the agent can be resumed, plus a `<usage>...</usage>` block. Reading the block verbatim
therefore captures harness metadata along with the agent's reply, and it flowed through the
reporter into the finished report.

### The fix

Strip the harness trailers from the tool-result text before treating it as the agent's
output. Remove at minimum:

- a line matching `agentId: <id>`, including any parenthetical `SendMessage` hint after it
- a `<usage>...</usage>` block, which may span several lines

Strip only trailing metadata. Do not touch the agent's own content, and do not strip inside a
fenced code block. Put this in one small, named, unit-tested helper.

Comment on why this exists. "Verbatim" is the right instinct for a machine-parsed reply, but
the transport adds its own framing, and a verbatim read faithfully copies the framing too.
Reading raw bytes off a channel does not mean every byte on that channel is payload.

### Tests

- A tool result carrying an `agentId:` trailer yields text without it.
- A tool result carrying a `<usage>` block yields text without it.
- Both together are removed.
- A result with neither is returned unchanged, byte for byte.
- Content that legitimately contains the word `usage` in prose is not damaged.

---

## Fix 3 - `numbering_gaps` fires on every correct run

### Evidence

`citation-report.json` reports `ok: false` with 23 `numbering_gaps`, while
`unmapped_citations`, `uncollected_urls`, and `orphan_references` are all empty. That is a
report with no citation defect at all, marked as failing.

### Cause

A spec defect in `tasks/03-verification.md`, and the WP3 review flagged it precisely. The
coordinator hands the reporter the full citation map — 46 sources in this run — and
`agents/reporter.md` instructs it to "List every cited number in the References section. List
no others." The reporter cited the 21 sources it had claims for. **A subset of an integer
range is never contiguous**, so the check must fire on every correct run of this system.

### The fix

Replace the contiguity check with the check it was actually meant to be: **renumbering
detection**.

- Drop `numbering_gaps` from `CitationReport`.
- Add `misnumbered_references: list[tuple[int, str, str]]`, holding
  `(number, url_in_report, url_in_citation_map)` for any References entry whose number maps
  to a different URL than the coordinator's citation map says it should.
- `verify_report` needs the citation map to do this. Add a parameter for it. Keep the
  existing `sources` parameter working, since `uncollected_urls` still needs the collected set.
- `ok` stays true only when every list is empty.

Comment on what changed and why. The original check punished selective citation, which the
reporter is explicitly told to do. The real risk was always a reporter that renumbers, and a
number-to-URL comparison against the coordinator's map catches that directly.

Update the module docstring and `README.md` is not yours to edit — just make the code and
its comments correct.

### One observation worth preserving in a comment

The WP3 review noticed that the 23 flagged numbers were exactly the sources the searcher
returned with no snippet text. The check was accidentally informative: it surfaced a phase-1
data-quality issue while claiming to detect a phase-4 renumbering issue. Record that in a
comment, because "my check fired for a reason unrelated to what it tests" is a good thing for
a reader to see once.

### Tests

- A report citing a strict subset of the collected sources **passes**. This is the
  regression test for the whole fix.
- A References entry pointing at the wrong URL for its number lands in
  `misnumbered_references`.
- An entry matching the citation map does not.

---

## Fix 4 - `state-after-NN-<phase>.json` lags one phase

### Evidence

- `state-after-01-search.json` has `sources: []` though the searcher returned 28.
- `state-after-02-analyze.json` has `claims: 0` and `coverage_sufficient: null`, though the
  analyst had run and its `false` verdict is what triggered the re-search.
- `state-after-06-report.json` has `report_md: null`.

### Cause

Another spec defect, this one in `tasks/02-pipeline.md`. `run_phase` writes the snapshot as
its last step, but the reply is parsed and folded into `RunState` by the caller, after
`run_phase` returns. Every snapshot is therefore written one step early.

This matters because these files exist so a reader can watch state accumulate across phase
boundaries. A snapshot that omits the phase it is named after teaches the wrong thing.

### The fix

Move the `record_state` call so it happens **after** the parsed payload is folded into
`RunState`.

- `record_input` and `record_output` stay inside `run_phase`. They are correct there.
- Move only `record_state`. Either have the caller invoke it after each fold, or pass
  `run_phase` a callback. Prefer whichever keeps the signature simplest.
- Keep filenames and `NN` sequence numbers exactly as they are.
- The `PhaseRecord` append stays inside `run_phase`; cost, duration, and subtype are known
  only there.

Replace the comment that documents the current lag with one stating the new invariant:
`state-after-NN-<phase>.json` is the run state **including** that phase's parsed result.

### Tests

- After a scripted search phase, the snapshot contains the parsed sources.
- After a scripted analyse phase, the snapshot contains the claims **and** the coverage verdict.
- A snapshot exists for every phase that ran.
- Mutation check: revert the ordering and confirm at least one new test fails. Report which,
  and do not leave the mutation in place.

---

## Acceptance criteria

1. `pytest research-crew/tests/` passes in full, offline. All 93 existing tests still pass.
2. No existing assertion is weakened to make something pass.
3. Run-level budget: a test proves the run raises before the phase that would cross the
   ceiling, and that the per-call value shrinks as spend accumulates.
4. Trailer stripping: `agentId:` and `<usage>` blocks are removed; clean content is unchanged.
5. `numbering_gaps` is gone; `misnumbered_references` replaces it; a subset-citing report passes.
6. Snapshots contain their own phase's payload.
7. Mutation checks reported for fixes 1 and 4.
8. `verify.py` stays under 140 code lines; `coordinator.py` plus `cli.py` stay under 320.
9. No changes to `state.py`, `agents_loader.py`, `observability.py`, or `agents/*.md`.
10. **No live run.** Prove all four offline.

## Constraints

- Python 3.10+, no new dependencies.
- Keep diffs surgical. Do not restructure the pipeline or rename anything not named here.
- Do not run `git commit`.

## When you are done

Reply with:

1. The files you edited and a precise description of each diff.
2. The exact `pytest` command and its full output.
3. The mutation-check results for fixes 1 and 4.
4. Final line counts excluding comments and blanks.
5. Anything in this spec that was ambiguous or wrong.
