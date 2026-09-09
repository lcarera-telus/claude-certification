"""Tests for `observability.py`.

The recorder is the debugging surface of the whole system. The two things worth
pinning are the filenames, because a later reader navigates by them, and the
refusal to reuse a run directory, because an audit trail that a later run can
overwrite is not an audit trail.

Every test writes into `tmp_path`. Nothing touches the real `runs/` directory
and nothing calls a model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from research_crew.observability import RunRecorder  # noqa: E402
from research_crew.state import RunState, Source  # noqa: E402


def test_constructor_creates_the_run_directory(tmp_path: Path) -> None:
    recorder = RunRecorder(tmp_path / "runs", "20260830-113500")
    assert recorder.run_dir.is_dir()
    # parents=True: the runs root need not exist beforehand, so the first run on
    # a fresh clone works without a setup step.
    assert recorder.run_dir == tmp_path / "runs" / "20260830-113500"


def test_reusing_a_run_id_raises(tmp_path: Path) -> None:
    """Criterion 12. Never overwrite an existing run directory.

    The run you least want to lose is the one that failed. Refusing here costs
    an error message on a rerun; not refusing costs the evidence.
    """
    RunRecorder(tmp_path, "20260830-113500")
    with pytest.raises(FileExistsError):
        RunRecorder(tmp_path, "20260830-113500")


def test_records_input_and_output_under_their_documented_names(tmp_path: Path) -> None:
    """The input file is the *complete* context the agent received.

    Subagents share no memory, so this file is not a partial log - it is
    everything that reached the agent. That is what turns 'which phase got it
    wrong' into a bisection: if a bad claim is already in the input, this agent
    passed on someone else's error; if it is not, this agent invented it.
    """
    recorder = RunRecorder(tmp_path, "run")
    payload = {"prompt": "Search for: multi-agent cost", "model": "sonnet", "round": 1}

    recorder.record_input(1, "searcher", payload)
    recorder.record_output(1, "searcher", "```json\n{\"sources\": []}\n```")

    input_path = recorder.run_dir / "01-searcher.input.json"
    output_path = recorder.run_dir / "01-searcher.output.md"
    assert json.loads(input_path.read_text(encoding="utf-8")) == payload
    # The output is stored verbatim. JSON extraction is itself a step that can
    # fail, and when it does this file is the only record of what was actually
    # said.
    assert output_path.read_text(encoding="utf-8").startswith("```json")


def test_sequence_numbers_are_zero_padded(tmp_path: Path) -> None:
    """Two digits so the directory listing sorts in execution order.

    Unpadded, `10-reporter` would sort before `2-analyst` and the trail would
    read out of order at exactly the point a long run gets hard to follow.
    """
    recorder = RunRecorder(tmp_path, "run")
    recorder.record_input(2, "analyst", {})
    recorder.record_output(10, "reporter", "text")
    recorder.record_state(3, "synthesize", "{}")

    names = sorted(p.name for p in recorder.run_dir.iterdir())
    assert names == ["02-analyst.input.json", "10-reporter.output.md", "state-after-03-synthesize.json"]


def test_state_snapshot_round_trips_back_into_a_run_state(tmp_path: Path) -> None:
    """A snapshot is only useful if it reloads as the same run.

    This is the join between `state.py` and this module: the recorder stores the
    text `to_json()` produced, and `from_dict()` must give the run back.
    """
    recorder = RunRecorder(tmp_path, "run")
    state = RunState.new("Does the trail replay?")
    state.sources.append(Source(id=1, url="https://a", title="A", snippet="s", query="q"))

    recorder.record_state(1, "search", state.to_json())

    written = (recorder.run_dir / "state-after-01-search.json").read_text(encoding="utf-8")
    assert RunState.from_dict(json.loads(written)) == state


def test_records_cost_and_report(tmp_path: Path) -> None:
    recorder = RunRecorder(tmp_path, "run")
    summary = {"total_usd": 0.42, "phases": [{"agent": "synthesizer", "cost_usd": 0.30}]}

    recorder.record_cost(summary)
    recorder.record_report("# Report\n\nA finding [1].\n")

    assert json.loads((recorder.run_dir / "cost.json").read_text(encoding="utf-8")) == summary
    # The report sits beside its own evidence on purpose: a reader who doubts a
    # citation finds the searcher's collected sources one file away.
    assert (recorder.run_dir / "report.md").read_text(encoding="utf-8").startswith("# Report")


def test_everything_is_written_as_utf8(tmp_path: Path) -> None:
    """Snippets are quoted verbatim from arbitrary web pages.

    This code runs on Windows, where the default text encoding is still the ANSI
    codepage. An encoding guess would either raise at write time or corrupt the
    evidence, so the encoding is set explicitly and pinned here.
    """
    recorder = RunRecorder(tmp_path, "run")
    text = "Émile Borel — 15× more tokens — 结论"

    recorder.record_output(1, "searcher", text)
    recorder.record_input(1, "analyst", {"snippet": text})

    assert (recorder.run_dir / "01-searcher.output.md").read_bytes().decode("utf-8") == text
    # ensure_ascii=False, so the JSON stays readable to a human rather than
    # turning every non-ASCII character into an escape.
    raw = (recorder.run_dir / "01-analyst.input.json").read_bytes().decode("utf-8")
    assert "15×" in raw


def test_writers_return_the_path_they_wrote(tmp_path: Path) -> None:
    recorder = RunRecorder(tmp_path, "run")
    path = recorder.record_report("# R\n")
    assert path.exists() and path.name == "report.md"
