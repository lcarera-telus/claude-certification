"""Tests for `state.py`, plus the two project-wide invariants.

The state object is the only thing that crosses a phase boundary and the only
thing the recorder snapshots, so the property that matters most here is not that
a field exists. It is that a snapshot written to disk and read back is the same
run. Everything else in the audit trail rests on that.

The cross-module invariants (every module documented, all three modules inside
the line budget) live at the end of this file because `state.py` is the module
the other two are written around.
"""

from __future__ import annotations

import ast
import dataclasses
import json
import sys
from pathlib import Path

import pytest

# The spec fixes the exact set of files this task may create, and a conftest.py
# is not among them. So each test module puts `src/` on the path itself. In a
# packaged project this would be a `pip install -e .` instead.
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from research_crew import agents_loader, observability, state  # noqa: E402
from research_crew.state import (  # noqa: E402
    Claim,
    Conflict,
    MergedClaim,
    PhaseRecord,
    RunState,
    Source,
)


def _populated_state() -> RunState:
    """A run state with one of every nested dataclass, and no default left over.

    Round-tripping an empty state proves almost nothing: every list would be
    empty in both directions whether or not `from_dict` rebuilt the dataclasses.
    Each collection here holds a real object so the reconstruction is exercised.
    """
    s = RunState.new("Do multi-agent systems beat single agents?")
    s.search_round = 2
    s.sources.append(
        Source(
            id=1,
            url="https://example.com/a",
            title="A Study",
            snippet="Multi-agent systems used about 15x more tokens.",
            query="multi-agent token cost",
        )
    )
    s.claims.append(
        Claim(
            id="c1",
            text="Multi-agent systems use roughly 15x more tokens than chat.",
            source_id=1,
            evidence="Multi-agent systems used about 15x more tokens.",
            confidence="high",
        )
    )
    s.merged_claims.append(
        MergedClaim(id="m1", text="Token use rises sharply.", source_ids=[1], support="moderate")
    )
    s.conflicts.append(
        Conflict(
            id="x1",
            topic="Whether multi-agent beats single-agent",
            position_a={"text": "It wins on breadth-first search.", "source_ids": [1]},
            position_b={"text": "It fails on stateful engineering.", "source_ids": [2]},
            kind="apparent",
            explanation="The two reports measured different task shapes.",
        )
    )
    s.coverage_sufficient = False
    s.coverage_gaps.append("No source gives a cost comparison.")
    s.report_md = "# Report\n\nA sentence [1].\n"
    s.phases.append(
        PhaseRecord(
            phase="search",
            agent="searcher",
            round=1,
            cost_usd=0.0412,
            duration_s=8.5,
            subtype="success",
        )
    )
    return s


def test_new_builds_a_utc_run_id_and_starts_at_round_one() -> None:
    s = RunState.new("question?")
    assert s.question == "question?"
    assert s.search_round == 1
    # YYYYMMDD-HHMMSS. Checked by shape, not by value, so the test does not race
    # the clock. The format has to stay filesystem-safe: it names a directory.
    assert len(s.run_id) == 15
    assert s.run_id[8] == "-"
    assert s.run_id.replace("-", "").isdigit()


def test_new_state_has_independent_collections() -> None:
    """Two runs must not share a list. A mutable default would make them."""
    a, b = RunState.new("q1"), RunState.new("q2")
    a.sources.append(Source(id=1, url="u", title="t", snippet="s", query="q"))
    assert b.sources == []


def test_round_trip_reproduces_an_equal_state() -> None:
    """Criterion 10: `from_dict(to_dict(s))` is the same run, nested types included."""
    original = _populated_state()
    restored = RunState.from_dict(original.to_dict())

    assert restored == original
    # Equality alone could pass on plain dicts if the dataclasses compared loose,
    # so pin the reconstructed types directly.
    assert isinstance(restored.sources[0], Source)
    assert isinstance(restored.claims[0], Claim)
    assert isinstance(restored.merged_claims[0], MergedClaim)
    assert isinstance(restored.conflicts[0], Conflict)
    assert isinstance(restored.phases[0], PhaseRecord)
    assert restored.conflicts[0].position_a == {
        "text": "It wins on breadth-first search.",
        "source_ids": [1],
    }


def test_round_trip_survives_json_text() -> None:
    """The recorder stores text, not a dict, so the trip through JSON must hold."""
    original = _populated_state()
    assert RunState.from_dict(json.loads(original.to_json())) == original


def test_to_json_is_readable() -> None:
    text = _populated_state().to_json()
    assert "\n" in text and '  "question"' in text


def test_frozen_payloads_reject_mutation() -> None:
    """Evidence is immutable: a later phase must not be able to edit a snippet."""
    src = Source(id=1, url="u", title="t", snippet="s", query="q")
    with pytest.raises(dataclasses.FrozenInstanceError):
        src.snippet = "rewritten"  # type: ignore[misc]


def test_citation_map_keys_on_source_id() -> None:
    s = RunState.new("q")
    s.sources.extend(
        [
            Source(id=1, url="https://a", title="A", snippet="sa", query="q"),
            Source(id=4, url="https://d", title="D", snippet="sd", query="q"),
        ]
    )
    cmap = s.citation_map()
    # Keyed by Source.id, not by list position. The reporter is handed these
    # numbers and forbidden to renumber, so a gap in the sequence must survive.
    assert set(cmap) == {1, 4}
    assert cmap[4].url == "https://d"


def _phase(cost: float | None) -> PhaseRecord:
    return PhaseRecord(phase="p", agent="a", round=1, cost_usd=cost, duration_s=1.0, subtype="success")


def test_total_cost_ignores_none_entries() -> None:
    """Criterion 11, first half: `None` means 'not reported', never zero."""
    s = RunState.new("q")
    s.phases.extend([_phase(0.10), _phase(None), _phase(0.05)])
    # approx, not ==: 0.10 + 0.05 is 0.15000000000000002 in binary floating
    # point. The rounding belongs in whatever displays the figure, not in the
    # sum - a cost report that quietly rounds is a cost report you cannot audit.
    assert s.total_cost_usd() == pytest.approx(0.15)


def test_total_cost_is_zero_when_nothing_was_reported() -> None:
    """Criterion 11, second half: an all-`None` run must not raise.

    A partial run is exactly the run whose cost you want to see.
    """
    s = RunState.new("q")
    s.phases.extend([_phase(None), _phase(None)])
    assert s.total_cost_usd() == 0.0
    assert RunState.new("q").total_cost_usd() == 0.0
    # A float, not the int that a bare `sum([])` would return. The cost report
    # formats this value, and formatting is where an int would show up.
    assert isinstance(RunState.new("q").total_cost_usd(), float)


# ---------------------------------------------------------------------------
# Project-wide invariants
# ---------------------------------------------------------------------------

_MODULES = [state, agents_loader, observability]


def test_every_module_has_a_docstring() -> None:
    """Criterion 13. This artifact is read to be learned from, so the docstring
    explaining a module's role in the pipeline is part of the deliverable."""
    for module in _MODULES:
        doc = module.__doc__ or ""
        assert len(doc.strip()) > 200, f"{module.__name__} lacks a substantive module docstring"


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

    count = 0
    for number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if number in docstring_lines or not stripped or stripped.startswith("#"):
            continue
        count += 1
    return count


def test_three_modules_stay_inside_the_line_budget() -> None:
    """Criterion 14: under 260 code lines across the three modules.

    The cap is on code, not on comments. The point of the budget is that a
    reader can hold the foundation layer in their head; explaining it costs
    nothing at run time, so the rationale is deliberately uncapped.
    """
    counts = {
        name: _code_line_count(_SRC / "research_crew" / f"{name}.py")
        for name in ("state", "agents_loader", "observability")
    }
    assert sum(counts.values()) < 260, counts
