"""Tests for `verify.py`, the mechanical citation check.

WHAT THIS SUITE IS FOR
======================
`verify.py` is the layer of the no-new-facts rule that does not depend on a
model choosing to cooperate, so it is the layer that has to be right. Everything
here runs offline, against `Source` objects built by hand: the module imports
nothing from the SDK, and a test that needed the network would be testing the
network.

The suite is also written to teach the check's boundary. The last test asserts
that a fabricated claim carrying a *real* citation **passes**, because that is
true and a reader who does not know it will over-trust the verdict. A test suite
that quietly avoided the case would leave the limitation for someone to discover
in production.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# See the note in `tests/test_state.py`: the spec fixes the set of files each
# task may create and a `conftest.py` is not among them, so every test module
# puts `src/` on the path itself.
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from research_crew import verify  # noqa: E402
from research_crew.state import Conflict, Source  # noqa: E402
from research_crew.verify import (  # noqa: E402
    CitationReport,
    describe,
    normalise_url,
    validate_conflicts,
    verify_report,
)


# ---------------------------------------------------------------------------
# Fixtures, built by hand. No network, no model, no run directory.
# ---------------------------------------------------------------------------

SOURCE_ONE = Source(id=1, url="https://a.example/one", title="Source One",
                    snippet="Crews beat solos on broad questions.", query="multi-agent")
SOURCE_TWO = Source(id=2, url="https://b.example/two?id=17", title="Source Two",
                    snippet="Single agents win on narrow tasks.", query="single-agent")
SOURCES = [SOURCE_ONE, SOURCE_TWO]
# What `RunState.citation_map()` hands the verifier: the number the coordinator
# assigned, paired with the source it assigned it to. `verify_report` needs this
# and not just the source list, because the renumbering check is about the
# pairing rather than about membership.
CITATION_MAP = {s.id: s for s in SOURCES}


def report(body: str, references: str) -> str:
    """Assemble a report in the shape `agents/reporter.md` specifies."""
    return f"# Title\n\n## Summary\n{body}\n\n## References\n{references}\n"


CLEAN = report(
    "Crews cover more ground [1]. Narrow tasks favour one agent [2].",
    "[1] Source One - https://a.example/one\n[2] Source Two - https://b.example/two?id=17",
)


# ---------------------------------------------------------------------------
# 1. The happy path.
# ---------------------------------------------------------------------------


def test_a_clean_report_passes_and_counts_its_citations() -> None:
    """`ok` is the conjunction of five empty lists, and the count is of markers."""
    result = verify_report(CLEAN, SOURCES, CITATION_MAP)
    assert result.ok is True
    assert result.checked_citations == 2
    assert isinstance(result, CitationReport)
    assert (result.unmapped_citations, result.uncollected_urls, result.orphan_references) == ([], [], [])
    assert (result.misnumbered_references, result.malformed_references) == ([], [])


def test_a_repeated_marker_is_counted_once_per_occurrence() -> None:
    """`checked_citations` counts what was scanned, not how many numbers exist.

    Cited three times, [1] was checked three times. The problem lists stay keyed
    on the distinct number, so this cannot inflate a failure into three.
    """
    md = report("A [1]. B [1]. C [1].", "[1] Source One - https://a.example/one")
    result = verify_report(md, SOURCES)
    assert result.checked_citations == 3
    assert result.ok is True


# ---------------------------------------------------------------------------
# 2-5. The four checks: unmapped, uncollected, orphan, misnumbered.
# ---------------------------------------------------------------------------


def test_a_citation_with_no_references_entry_is_unmapped() -> None:
    """`[2]` is cited, and the References block never defines it.

    The reader cannot follow the citation at all, which is why this is a
    failure and not a warning.
    """
    md = report("A [1]. B [2].", "[1] Source One - https://a.example/one")
    result = verify_report(md, SOURCES)
    assert result.unmapped_citations == [2]
    assert result.ok is False


def test_a_references_url_the_searcher_never_collected_is_reported() -> None:
    """THE CENTRAL TEST: the reporter invented a source.

    Layer 1 (the prompt) told it not to. Layer 2 (`tools: []`) stopped it
    *fetching* one, but not recalling one from pre-training and typing the URL
    into the References block. This is the failure that only code catches, and
    the reason `verify.py` exists.
    """
    md = report(
        "Crews cover more ground [1]. Crews are twice as fast [3].",
        "[1] Source One - https://a.example/one\n"
        "[3] Plausible Paper - https://arxiv.example/2401.99999",
    )
    result = verify_report(md, SOURCES)
    assert result.uncollected_urls == [(3, "https://arxiv.example/2401.99999")]
    assert result.ok is False


def test_a_references_entry_never_cited_is_an_orphan() -> None:
    """Source 2 is listed and no sentence uses it.

    This test is also what proves the body/references split happened. Without
    it, the `[2]` on the reference line itself would read as a citation of
    source 2, this list would come back empty, and the check would silently
    pass on every report ever written.
    """
    result = verify_report(report("Only the first [1].", CLEAN.split("## References\n")[1].strip()), SOURCES)
    assert result.orphan_references == [2]
    assert result.ok is False


def test_a_reference_pointing_at_the_wrong_url_for_its_number_is_misnumbered() -> None:
    """The renumbering failure, caught by comparing against the citation map.

    Reference [1] carries source *two's* URL. Both URLs were genuinely collected,
    so `uncollected_urls` is empty and every citation resolves to a line; the
    report is well-formed, fluent, and sends the reader who follows [1] to a page
    about something else. Only the number-to-URL pairing gives it away, and only
    the coordinator's map knows what that pairing was supposed to be.
    """
    md = report("A [1].", "[1] Source One - https://b.example/two?id=17")
    result = verify_report(md, SOURCES, CITATION_MAP)
    assert result.misnumbered_references == [(1, "https://b.example/two?id=17", "https://a.example/one")]
    assert result.uncollected_urls == []  # both URLs really were collected
    assert result.ok is False

    # `describe` renders the verdict for the CLI, and it is the only place a
    # human reads this list. A three-tuple where the other lists hold ints or
    # pairs is exactly the shape that unpacks wrongly and raises on the failure
    # path, which is the one path nobody exercises by hand.
    assert describe(result) == [
        "misnumbered reference [1] https://b.example/two?id=17: "
        "the citation map assigns 1 to https://a.example/one"
    ]


def test_a_reference_matching_the_citation_map_is_not_misnumbered() -> None:
    """The pairing is what is compared, and cosmetic URL differences do not count.

    The reference is written with a shouted scheme and a trailing slash, which is
    the same page. Flagging it would be the sort of false alarm that teaches a
    reader to skip the verdict.
    """
    md = report("A [1].", "[1] Source One - HTTPS://A.Example/one/")
    assert verify_report(md, SOURCES, CITATION_MAP).misnumbered_references == []


def test_a_report_citing_a_subset_of_the_collected_sources_passes() -> None:
    """THE REGRESSION TEST for the check this replaced.

    `agents/reporter.md` tells the reporter to list every number it cited and no
    others, while the coordinator hands it the whole citation map. So the
    References block is a *subset* of the map on every correct run - here 1 out
    of 2, and 21 out of 46 in run 20260830-152235.

    The old `numbering_gaps` check tested that block for contiguity. A subset of
    an integer range is essentially never contiguous, so that check reported a
    failure on every correct run of this system and could not do otherwise. It
    punished the reporter for obeying its instructions. This test fails if
    anything like it comes back.
    """
    md = report("Only the first source had a usable claim [1].", "[1] Source One - https://a.example/one")
    result = verify_report(md, SOURCES, CITATION_MAP)
    assert result.ok is True
    assert result.misnumbered_references == []


def test_without_a_citation_map_the_renumbering_check_is_skipped() -> None:
    """The map is optional, and omitting it silently drops one check.

    Same shape as `validate_conflicts`. Worth pinning, because "the verdict was
    `ok` and the map was never passed" is a much weaker statement than "the
    verdict was `ok`", and a caller has to be able to tell them apart.
    """
    md = report("A [1].", "[1] Source One - https://b.example/two?id=17")
    assert verify_report(md, SOURCES).misnumbered_references == []
    assert verify_report(md, SOURCES, CITATION_MAP).misnumbered_references != []


# ---------------------------------------------------------------------------
# 6-8. Parsing.
# ---------------------------------------------------------------------------


def test_a_malformed_references_line_is_recorded_and_does_not_raise() -> None:
    """The verifier reports bad input; it does not crash on it.

    A crash names one bad line and hides every other problem behind it. This
    function's contract is the fullest description of what is wrong, in one
    pass, so the reader fixes everything before re-running.
    """
    md = report("A [1].", "[1] Source One - https://a.example/one\nsee the appendix for the rest")
    result = verify_report(md, SOURCES)
    assert result.malformed_references == ["see the appendix for the rest"]
    assert result.unmapped_citations == []  # the good line still parsed
    assert result.ok is False


def test_a_run_of_markers_parses_as_separate_citations() -> None:
    """`[2][5]` is two citations, not one token.

    `MergedClaim.source_ids` is a list, so a sentence resting on several sources
    is the normal output of the synthesizer, not an edge case.
    """
    md = report("A merged claim [2][5].",
                "[2] Source Two - https://b.example/two?id=17\n[5] Five - https://e.example/five")
    result = verify_report(md, SOURCES)
    assert result.checked_citations == 2
    assert result.unmapped_citations == []
    assert 5 in [n for n, _ in result.uncollected_urls]


def test_a_markdown_link_is_not_a_citation() -> None:
    """`[see here](https://x.com)` is a link, and `[1](url)` is a link too.

    Both are legitimate Markdown. Counting either as a citation would raise an
    alarm about a document that is fine, and a check that cries wolf is a check
    the reader learns to skip.
    """
    md = report("Background reading is [see here](https://x.com) and [1](https://y.com). A fact [1].",
                "[1] Source One - https://a.example/one")
    result = verify_report(md, SOURCES)
    assert result.checked_citations == 1
    assert result.ok is True


# ---------------------------------------------------------------------------
# 9-10. URL comparison.
# ---------------------------------------------------------------------------


def test_cosmetic_url_differences_compare_equal() -> None:
    """A trailing slash, a shouted scheme, a default port, a fragment.

    The URL was retyped by a model twice on its way here. None of these
    differences means the citation points somewhere else, and treating them as
    citation errors would bury the real ones.
    """
    assert normalise_url("https://a.example/one/") == normalise_url("https://a.example/one")
    assert normalise_url("HTTPS://A.Example/one") == normalise_url("https://a.example/one")
    assert normalise_url("https://a.example:443/one") == normalise_url("https://a.example/one")
    assert normalise_url("https://a.example/one#results") == normalise_url("https://a.example/one")
    md = report("A [1].", "[1] Source One - HTTPS://A.Example/one/")
    assert verify_report(md, SOURCES).ok is True


def test_a_different_query_string_is_a_different_page() -> None:
    """The query string is kept, because it is often the page's identity.

    `?id=17` and `?id=18` are two records. Normalising the query away would let
    an invented source pass by resembling a real one, which is exactly the
    failure this module is here to catch.
    """
    assert normalise_url("https://b.example/two?id=17") != normalise_url("https://b.example/two?id=18")
    md = report("A [2].", "[2] Source Two - https://b.example/two?id=18")
    assert verify_report(md, SOURCES).uncollected_urls == [(2, "https://b.example/two?id=18")]


def test_an_unparsable_url_does_not_raise() -> None:
    """A bad port makes `urlsplit(...).port` raise. Nothing here may raise."""
    assert normalise_url("https://a.example:notaport/one") == "https://a.example:notaport/one"


# ---------------------------------------------------------------------------
# 11. Conflict shape.
# ---------------------------------------------------------------------------


def conflict(position_a: object, position_b: object) -> Conflict:
    """A `Conflict` with arbitrary positions, which the type `dict` permits."""
    return Conflict(id="x1", topic="Whether crews win.", position_a=position_a,  # type: ignore[arg-type]
                    position_b=position_b, kind="apparent", explanation="Different workloads.")  # type: ignore[arg-type]


def test_validate_conflicts_accepts_a_well_formed_conflict() -> None:
    """Both positions carry a non-empty text and ids that were really collected."""
    good = conflict({"text": "Crews win.", "source_ids": [1]}, {"text": "Solos win.", "source_ids": [2]})
    assert validate_conflicts([good], {s.id: s for s in SOURCES}) == []
    assert validate_conflicts([]) == []


def test_validate_conflicts_reports_a_malformed_conflict_without_raising() -> None:
    """Four different shape failures, each named, and no exception.

    A conflict whose position cites source 9 serialises happily into the state
    snapshot and surfaces much later as a Disagreements section citing a number
    the References block does not contain. Naming it here names the phase that
    produced it.
    """
    problems = validate_conflicts(
        [
            conflict({"text": "  ", "source_ids": [1]}, {"text": "Fine.", "source_ids": "1"}),
            conflict("not a dict", {"text": "Fine.", "source_ids": [9]}),
        ],
        {s.id: s for s in SOURCES},
    )
    assert all(isinstance(p, str) for p in problems)
    assert any("no non-empty 'text'" in p for p in problems)
    assert any("no 'source_ids' list" in p for p in problems)
    assert any("position_a is not a dict" in p for p in problems)
    assert any("cites source 9" in p for p in problems)


def test_validate_conflicts_without_a_citation_map_checks_shape_only() -> None:
    """The optional map is what turns a shape check into a provenance check."""
    citing_nine = conflict({"text": "A.", "source_ids": [9]}, {"text": "B.", "source_ids": [1]})
    assert validate_conflicts([citing_nine]) == []
    assert validate_conflicts([citing_nine], {s.id: s for s in SOURCES}) != []


# ---------------------------------------------------------------------------
# 12. The limitation, stated as a passing test.
# ---------------------------------------------------------------------------


def test_referential_check_cannot_detect_a_false_claim() -> None:
    """DOCUMENTS A KNOWN LIMITATION. This is not a bug, and not a TODO.

    The report below cites source 1 - genuinely retrieved by the searcher, with
    a snippet about coverage - for the claim that multi-agent systems are 900%
    faster and were banned in Belgium in 1997. Every citation resolves. Every
    URL was collected. The numbering is contiguous. `ok` is True.

    That is the boundary of a *referential* check: it verifies that a pointer
    points at something real, and it has no way to read what is at the other end
    or to judge whether the sentence follows from it. Closing this gap needs an
    entailment model or a human, both of which cost per claim and can be wrong.

    The test exists so the boundary is visible in the suite rather than
    discovered in production. If a future change makes this test fail, the check
    has become semantic, and this docstring is what should be rewritten.
    """
    fabricated = report(
        "Multi-agent systems are 900% faster [1]. Belgium banned them in 1997 [1].",
        "[1] Source One - https://a.example/one",
    )
    result = verify_report(fabricated, SOURCES)
    assert result.ok is True
    assert result.checked_citations == 2


# ---------------------------------------------------------------------------
# Module-level invariants for this task's acceptance criteria.
# ---------------------------------------------------------------------------


def _code_line_count(path: Path) -> int:
    """Count lines that are neither blank, nor a comment, nor part of a docstring."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    docstring_lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            docstring_lines.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return sum(
        1
        for number, line in enumerate(source.splitlines(), start=1)
        if number not in docstring_lines and line.strip() and not line.strip().startswith("#")
    )


def test_verify_stays_inside_its_line_budget() -> None:
    """Criterion 13: under 140 code lines. The rationale above it is uncapped."""
    assert _code_line_count(_SRC / "research_crew" / "verify.py") < 140


def test_the_verifier_involves_no_model() -> None:
    """Criterion 3. The value of this check is that it cannot be talked around.

    An import of the SDK here would mean the last line of defence was itself a
    model call, and therefore subject to the same failure mode it is guarding
    against.
    """
    source = (_SRC / "research_crew" / "verify.py").read_text(encoding="utf-8")
    assert "claude_agent_sdk" not in source
    assert "import requests" not in source and "urlopen" not in source


def test_the_report_is_written_before_it_is_verified() -> None:
    """Criteria 10 and 11, checked on the wiring rather than by running the pipeline.

    Read as source text on purpose. Importing the coordinator would drag the
    SDK into this module, and the one property worth pinning here is an
    *ordering*: `record_report` comes before `verify_report`, and nothing in
    the tail raises. A verifier that could unwind the run before its report
    reached disk would destroy exactly the evidence a failed run exists to
    leave behind.
    """
    source = (_SRC / "research_crew" / "coordinator.py").read_text(encoding="utf-8")
    assert source.index("recorder.record_report(") < source.index("verify_report(")
    assert "citation-report.json" in source
    tail = source.split("recorder.record_report(")[1]
    assert re.search(r"^\s*raise", tail, re.MULTILINE) is None


def test_the_module_docstring_states_the_limitation() -> None:
    """Criterion 8. An over-trusted check is more dangerous than no check.

    Pinned as a test because the docstring is the only place a future reader
    learns that `ok: true` does not mean the report is true.
    """
    doc = verify.__doc__ or ""
    assert "referential" in doc and "semantic" in doc
    assert "passes this check" in doc
