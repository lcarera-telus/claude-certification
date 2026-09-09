# Task 03 - Citation integrity and the live demo run

You are implementing the last part of `research-crew`, a teaching artifact for the Claude
Certified Architect exam. Read this whole spec before you write code. It is self-contained.

## What already exists

Tasks 01 and 02 built and tested these. Read them before you start. Reuse them.

- `src/research_crew/state.py` — `RunState`, `Source`, `Claim`, `MergedClaim`, `Conflict`,
  `PhaseRecord`. `RunState.citation_map()` returns `dict[int, Source]`.
- `src/research_crew/agents_loader.py` — `load_agents()`.
- `src/research_crew/observability.py` — `RunRecorder`.
- `src/research_crew/coordinator.py` — `run_research()`, the four-phase pipeline with a
  bounded re-search.
- `src/research_crew/cli.py` — the `argparse` entry point.
- `agents/*.md` — the four subagent definitions. Do not modify these.

## Audience

The reader is studying agent orchestration. Comment the architecture at least as heavily as
the code. Explain *why*, not *what*.

## Background: what this check is for, and what it is not for

The `reporter` agent must not introduce new facts. It is constrained three ways, in
increasing order of strength:

1. Its prompt says so. Advisory only.
2. It has `tools: []`, so it cannot search. Structural.
3. **This module checks the output in code.** No model is involved, so no fluent prose talks
   its way past it.

You are building layer 3. It is the only layer that does not depend on a model choosing to
cooperate.

**Be honest in the code and the docstrings about what this cannot do.** The check is
*referential*, not *semantic*. It proves that citation `[4]` points at a URL the searcher
really retrieved. It proves nothing about whether the sentence carrying `[4]` is supported by
what is at that URL. A report attaching a real source to a fabricated claim **passes**.
Closing that gap needs an entailment model or a human. Say this plainly in the module
docstring. Do not imply the check is stronger than it is.

## Files

```
research-crew/
  src/research_crew/verify.py       (new)
  tests/test_verify.py              (new)
  src/research_crew/coordinator.py  (edit: call the verifier, minimally)
  src/research_crew/cli.py          (edit: print the verdict, minimally)
```

Keep the edits to `coordinator.py` and `cli.py` small and additive. Do not restructure the
pipeline.

## src/research_crew/verify.py

### The report object

```python
@dataclass(frozen=True)
class CitationReport:
    ok: bool
    checked_citations: int
    unmapped_citations: list[int]      # [n] in the body with no References entry
    uncollected_urls: list[tuple[int, str]]  # References URL the searcher never collected
    orphan_references: list[int]       # References entry never cited in the body
    numbering_gaps: list[int]          # missing numbers in an otherwise contiguous range
    malformed_references: list[str]    # References lines that do not parse
```

`ok` is true only when every list is empty.

### The entry point

```python
def verify_report(report_md: str, sources: Sequence[Source]) -> CitationReport:
```

Steps:

1. Split the report into the body and the `## References` section. Everything from the
   `## References` heading onward is the references block. Comment on why the body and the
   references must be split before counting markers: `[1]` appears in both, and counting a
   reference line as a citation would make every orphan reference look cited.
2. Extract every `[n]` marker from the **body**. Support `[1]` and runs such as `[1][3]`.
   Ignore Markdown links of the form `[text](url)`, which are not citations.
3. Parse each references line into a number, an optional title, and a URL. Accept the format
   `[1] Title - https://example.com/page`. Record a line that does not parse in
   `malformed_references` rather than raising. A verifier that crashes on bad input tells you
   less than one that reports precisely what was bad.
4. Run the four checks and fill the lists.

### URL comparison

Compare **normalised** URLs, not raw strings. Normalise by lowercasing the scheme and host,
removing a default port, removing a trailing slash from the path, and dropping a `#fragment`.
Do **not** drop the query string, because it often carries the identity of the page.

Comment on why normalisation is needed at all: the reporter copies a URL through two agents
by hand, and a trailing slash difference is not a citation error. Being strict here would
produce false alarms that train the reader to ignore the check, which is worse than a slightly
loose check.

### One extra validator, carried over from a Task 01 review

`Conflict.position_a` and `position_b` are typed as bare `dict`. Nothing yet checks their
shape, so a malformed position serialises happily and surfaces much later as a confusing
report. Add:

```python
def validate_conflicts(conflicts: Sequence[Conflict]) -> list[str]:
```

It returns a list of human-readable problems. Each position must be a `dict` carrying a
non-empty `text` string and a `source_ids` list of integers. Each `source_ids` entry must
exist in the citation map passed alongside. Return an empty list when everything is well
formed. Do not raise.

## Wiring it in

In `coordinator.py`, after phase 4, call `verify_report()` with `state.report_md` and
`state.sources`, and call `validate_conflicts()`. Write the result to the run directory as
`citation-report.json` via the recorder or a direct write, and keep it on the returned state
or return it alongside. Do **not** raise on a failed verification: a failing report is still
an artifact the reader must be able to inspect. Report the failure; do not delete the evidence.

In `cli.py`, print a clear verdict. On success print the count of citations checked. On
failure print each problem on its own line, and exit non-zero.

## tests/test_verify.py

No network calls. Build `Source` objects directly. Cover at least:

1. A clean report passes, and `checked_citations` is correct.
2. A body citation with no References entry lands in `unmapped_citations`.
3. A References URL the searcher never collected lands in `uncollected_urls`. **This is the
   central test.** It is the case where the reporter invented a source.
4. A References entry never cited in the body lands in `orphan_references`.
5. A gap in the numbering is reported.
6. A malformed references line is recorded, and does not raise.
7. A run such as `[2][5]` is parsed as two separate citations.
8. A Markdown link `[see here](https://x.com)` is **not** counted as a citation.
9. URLs differing only by a trailing slash, or by scheme case, compare equal.
10. A URL differing by query string does **not** compare equal.
11. `validate_conflicts` accepts a well-formed conflict and reports a malformed one.
12. A report citing a real collected URL for an absurd claim **passes**. Name this test
    something like `test_referential_check_cannot_detect_a_false_claim`, and write a docstring
    saying it documents a known limitation rather than a bug. The test suite should teach the
    limitation, not hide it.

## The live demo run

After the tests pass, run the pipeline once, for real:

```bash
cd research-crew
python -m research_crew.cli "Do multi-agent LLM systems outperform single-agent systems?"
```

The budget cap is real, so this should cost only a few dollars at most. Run it **once**. If it
fails, read `runs/<id>/` to diagnose, fix, and run once more. Do not loop.

Then report what happened. Include:

- the run id and the total cost from `cost.json`
- whether the re-search round fired, and how you can tell from the artifacts
- the `CitationReport` verdict
- the first 40 lines of the generated `report.md`
- whether the `Disagreements Between Sources` section contains a real conflict

## Acceptance criteria

1. `pytest research-crew/tests/` passes in full, including the Tasks 01 and 02 tests.
2. No test in the suite makes a network or API call.
3. `verify_report` uses no model and imports nothing from `claude_agent_sdk`.
4. All four checks are implemented, and `ok` is true only when every list is empty.
5. URL comparison is normalised as described, and the query string is significant.
6. A Markdown link is not counted as a citation.
7. `validate_conflicts` exists, returns a list of strings, and never raises.
8. The module docstring states the referential-versus-semantic limitation plainly.
9. A test documents that limitation rather than hiding it.
10. The verifier's result is written into the run directory.
11. A failed verification does not delete or suppress the report.
12. The live run completed, and `runs/<id>/` holds the per-phase inputs, outputs, state
    snapshots, `cost.json`, and `report.md`.
13. `verify.py` stays under 140 lines excluding comments, docstrings, and blanks.

## Constraints

- Python 3.10+, standard library only in `verify.py`.
- Type-hint every public function.
- Do not modify `agents/*.md`, `state.py`, `agents_loader.py`, or `observability.py`.
- Keep the `coordinator.py` and `cli.py` edits minimal and additive.
- Do not run `git commit`.

## When you are done

Reply with:

1. The files you created and the files you edited.
2. The exact `pytest` command and its full output.
3. The live-run report described above.
4. The `verify.py` line count excluding comments and blanks.
5. Anything in this spec that was ambiguous or wrong.
