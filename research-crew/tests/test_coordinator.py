"""Tests for `coordinator.py`.

WHY THERE IS A FAKE SDK AND NOT A RECORDED CASSETTE
===================================================
No test in this file makes a network or API call. `coordinator.query` is
monkeypatched with `ScriptedQuery`, which hands back a list of SDK message
objects the test wrote by hand.

The objects are the real `AssistantMessage`, `UserMessage`, `ToolUseBlock`,
`ToolResultBlock` and `ResultMessage` classes from `claude_agent_sdk`, not
stand-ins. That matters: `run_phase` detects delegation with `isinstance`
checks, so a duck-typed fake would let a genuine type mismatch pass here and
fail only against the live SDK. Building the real objects means these tests
break if the SDK's message shapes change, which is the correct outcome - that is
the interface under test.

What is being tested is the *control flow*, which is the part of this system
that a model does not do and therefore the part that must be right every time:
the re-search bound, the terminal-subtype branch, the delegation check, and the
stability of citation numbers. None of those need a model to exercise, and none
of them should ever be validated by a run that costs money.

THE ONE TEST THAT MATTERS MOST
==============================
`test_gate_does_not_fire_a_third_time_even_when_coverage_stays_insufficient`.
An unbounded re-search loop raises nothing, times out on nothing, and produces
no degraded output - it works, correctly and expensively, until somebody reads
the bill. There is no runtime symptom to detect, so a test is the only place the
bound can be observed at all.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from research_crew import coordinator  # noqa: E402
from research_crew.agents_loader import load_agents  # noqa: E402
from research_crew.coordinator import (  # noqa: E402
    MAX_SEARCH_ROUNDS,
    BudgetExceeded,
    MalformedAgentReply,
    NoDelegation,
    PhaseFailed,
    TurnLimitExceeded,
    parse_agent_json,
    run_phase,
    run_research,
    strip_harness_trailers,
)
from research_crew.observability import RunRecorder  # noqa: E402
from research_crew.state import RunState  # noqa: E402

AGENTS_DIR = _ROOT / "agents"
QUESTION = "Does a bounded re-search loop beat an unbounded one?"


# ---------------------------------------------------------------------------
# The fake SDK
# ---------------------------------------------------------------------------

# A paraphrase in the parent's own voice, placed in every scripted stream after
# the tool result. Fact 3 of the brief: "The parent receives the subagent's
# final message as the Agent tool result, but may summarize it in its own
# response." This string is that summary. If `run_phase` ever returns it instead
# of the tool-result block, the coordinator is parsing a paraphrase of JSON, and
# `test_verbatim_tool_result_beats_the_parents_paraphrase` says so.
PARENT_PARAPHRASE = "The searcher found several relevant sources about the topic."


def fenced(payload: dict) -> str:
    """Wrap a payload the way an agent does: prose, then one fenced JSON block."""
    return "Here is the result.\n\n```json\n" + json.dumps(payload, indent=2) + "\n```\n"


def stream(
    *,
    reply: str,
    subtype: str = "success",
    tool_name: str = "Agent",
    delegate: bool = True,
    cost: float | None = 0.01,
) -> list:
    """Build one phase's worth of SDK messages.

    `delegate=False` models the silent failure the whole architecture rests on:
    Claude answers the question itself and never touches the Agent tool. The
    stream still ends in a perfectly ordinary `success` ResultMessage, which is
    exactly why the check cannot be "did the run succeed".
    """
    messages: list = []
    if delegate:
        tool_id = "toolu_01test"
        messages.append(
            AssistantMessage(
                content=[ToolUseBlock(id=tool_id, name=tool_name, input={"prompt": "..."})],
                model="claude-sonnet-5",
            )
        )
        # The subagent's final message, arriving as the Agent tool's result.
        messages.append(UserMessage(content=[ToolResultBlock(tool_use_id=tool_id, content=reply)]))
        # ... and then the parent talking about it in its own words.
        messages.append(AssistantMessage(content=[TextBlock(text=PARENT_PARAPHRASE)], model="claude-sonnet-5"))
    else:
        messages.append(AssistantMessage(content=[TextBlock(text=reply)], model="claude-sonnet-5"))
    messages.append(
        ResultMessage(
            subtype=subtype,
            duration_ms=1200,
            duration_api_ms=900,
            is_error=subtype != "success",
            num_turns=2,
            session_id="session-test",
            total_cost_usd=cost,
        )
    )
    return messages


class ScriptedQuery:
    """A stand-in for `claude_agent_sdk.query` that replays scripted streams.

    Records every prompt and every `ClaudeAgentOptions` it was handed, so a test
    can assert on what the coordinator asked for as well as on what it did with
    the answer. Running out of script is an assertion failure rather than a
    `StopIteration`, because "the coordinator called the model more times than
    the test allowed" is precisely the bug the re-search tests hunt for, and it
    should read as that and not as a plumbing error.
    """

    def __init__(self, scripts: list[list]) -> None:
        self._scripts = list(scripts)
        self.prompts: list[str] = []
        self.options: list = []

    def __call__(self, *, prompt: str, options):  # noqa: ANN001 - SDK options type
        self.prompts.append(prompt)
        self.options.append(options)
        assert self._scripts, f"query() was called {len(self.prompts)} times; the test scripted fewer"
        messages = self._scripts.pop(0)

        async def generate():
            for message in messages:
                yield message

        return generate()

    @property
    def call_count(self) -> int:
        return len(self.prompts)


# ---------------------------------------------------------------------------
# Payload fixtures. Two sources per search round, so ids are easy to follow.
# ---------------------------------------------------------------------------

# Note the ids: the searcher numbers from 1 every time, because it never sees a
# previous round. The coordinator is expected to throw these away.
SEARCH_ROUND_1 = {
    "sources": [
        {"id": 1, "url": "https://a.example/one", "title": "Source One", "snippet": "s1", "query": "q1"},
        {"id": 2, "url": "https://b.example/two", "title": "Source Two", "snippet": "s2", "query": "q1"},
    ],
    "queries_run": ["q1"],
    "notes": "",
}
SEARCH_ROUND_2 = {
    "sources": [
        {"id": 1, "url": "https://c.example/three", "title": "Source Three", "snippet": "s3", "query": "gap"},
        {"id": 2, "url": "https://d.example/four", "title": "Source Four", "snippet": "s4", "query": "gap"},
    ],
    "queries_run": ["gap"],
    "notes": "",
}
ANALYSIS_INSUFFICIENT = {
    "claims": [{"id": "c1", "text": "A claim.", "source_id": 1, "evidence": "s1", "confidence": "medium"}],
    "coverage": {"sufficient": False, "gaps": ["no source gives a cost comparison"]},
}
ANALYSIS_SUFFICIENT = {
    "claims": [{"id": "c1", "text": "A claim.", "source_id": 1, "evidence": "s1", "confidence": "high"}],
    "coverage": {"sufficient": True, "gaps": []},
}
SYNTHESIS = {
    "merged_claims": [{"id": "m1", "text": "A merged claim.", "source_ids": [1, 2], "support": "strong"}],
    "conflicts": [
        {
            "id": "x1",
            "topic": "Whether the bound helps.",
            "position_a": {"text": "Yes.", "source_ids": [1]},
            "position_b": {"text": "Only sometimes.", "source_ids": [2]},
            "kind": "apparent",
            "explanation": "The two measured different workloads.",
        }
    ],
    "summary": "A short summary.",
}
REPORT_MD = "# Title\n\n## Summary\nA sentence [1].\n\n## References\n[1] Source One - https://a.example/one\n"


def scripted_run(
    scripts: list[list],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    max_budget_usd: float = 1.5,
) -> tuple[RunState, ScriptedQuery]:
    """Run the whole pipeline against a scripted fake SDK."""
    fake = ScriptedQuery(scripts)
    monkeypatch.setattr(coordinator, "query", fake)
    state = asyncio.run(
        run_research(QUESTION, agents_dir=AGENTS_DIR, runs_root=tmp_path / "runs", max_budget_usd=max_budget_usd)
    )
    return state, fake


def one_round_scripts() -> list[list]:
    """A run in which the analyst is satisfied the first time: four phases."""
    return [
        stream(reply=fenced(SEARCH_ROUND_1)),
        stream(reply=fenced(ANALYSIS_SUFFICIENT)),
        stream(reply=fenced(SYNTHESIS)),
        stream(reply=REPORT_MD),
    ]


def two_round_scripts(second_verdict: dict) -> list[list]:
    """A run in which the analyst is unsatisfied the first time: six phases.

    `second_verdict` is what the analyst says *after* the re-search, which is the
    knob that separates "the gate fired once" from "the gate must refuse to fire
    again".
    """
    return [
        stream(reply=fenced(SEARCH_ROUND_1)),
        stream(reply=fenced(ANALYSIS_INSUFFICIENT)),
        stream(reply=fenced(SEARCH_ROUND_2)),
        stream(reply=fenced(second_verdict)),
        stream(reply=fenced(SYNTHESIS)),
        stream(reply=REPORT_MD),
    ]


@pytest.fixture
def phase_kit(tmp_path: Path):
    """A `RunState`, a `RunRecorder` and the real crew, for single-phase tests."""
    state = RunState.new(QUESTION)
    recorder = RunRecorder(tmp_path / "runs", state.run_id)
    return state, recorder, load_agents(AGENTS_DIR)


def run_one_phase(phase_kit, messages: list, monkeypatch: pytest.MonkeyPatch) -> str:
    """Drive `run_phase` once against a single scripted stream."""
    state, recorder, agents = phase_kit
    monkeypatch.setattr(coordinator, "query", ScriptedQuery([messages]))
    return asyncio.run(
        run_phase(
            agent_name="searcher",
            phase="search",
            prompt="a prompt",
            state=state,
            recorder=recorder,
            seq=1,
            agents=agents,
            max_budget_usd=1.0,
        )
    )


# ---------------------------------------------------------------------------
# 1. The fenced-JSON parser
# ---------------------------------------------------------------------------


def test_parser_reads_a_valid_fenced_block() -> None:
    """The block is found even though the agent wrapped it in prose."""
    assert parse_agent_json(fenced(SEARCH_ROUND_1))["sources"][0]["url"] == "https://a.example/one"


def test_parser_reads_an_untagged_fence() -> None:
    """The `json` language tag is optional; models drop it often enough to matter."""
    assert parse_agent_json('```\n{"a": 1}\n```') == {"a": 1}


def test_parser_raises_when_the_block_is_missing() -> None:
    """A reply with no fence is a contract violation, not an empty result.

    Returning `{}` here would send an empty source list downstream, and the run
    would finish with a report built on nothing at all.
    """
    with pytest.raises(MalformedAgentReply) as excinfo:
        parse_agent_json("I searched and found some interesting things.")
    # The offending text travels with the error, because the fix always starts
    # with reading what the model actually said.
    assert "interesting things" in str(excinfo.value)


def test_parser_raises_on_malformed_json() -> None:
    """A fence containing broken JSON names the parse error and shows the text."""
    with pytest.raises(MalformedAgentReply) as excinfo:
        parse_agent_json('```json\n{"sources": [ }\n```')
    assert "not valid JSON" in str(excinfo.value)


def test_parser_rejects_a_non_object_payload() -> None:
    """Every agent contract in this crew is a JSON *object*, so a bare list fails."""
    with pytest.raises(MalformedAgentReply):
        parse_agent_json("```json\n[1, 2, 3]\n```")


# ---------------------------------------------------------------------------
# 2 and 3. The terminal subtype branch
# ---------------------------------------------------------------------------


def test_success_subtype_returns_the_text(phase_kit, monkeypatch: pytest.MonkeyPatch) -> None:
    state, _, _ = phase_kit
    text = run_one_phase(phase_kit, stream(reply=fenced(SEARCH_ROUND_1)), monkeypatch)
    assert parse_agent_json(text)["sources"][0]["title"] == "Source One"
    assert state.phases[-1].subtype == "success"


def test_budget_subtype_raises_budget_exceeded(phase_kit, monkeypatch: pytest.MonkeyPatch) -> None:
    """The cost travels with the exception, because it is what the reader needs."""
    messages = stream(reply=fenced(SEARCH_ROUND_1), subtype="error_max_budget_usd", cost=1.23)
    with pytest.raises(BudgetExceeded) as excinfo:
        run_one_phase(phase_kit, messages, monkeypatch)
    assert "1.23" in str(excinfo.value)


def test_turn_limit_subtype_raises_turn_limit_exceeded(phase_kit, monkeypatch: pytest.MonkeyPatch) -> None:
    messages = stream(reply=fenced(SEARCH_ROUND_1), subtype="error_max_turns")
    with pytest.raises(TurnLimitExceeded):
        run_one_phase(phase_kit, messages, monkeypatch)


@pytest.mark.parametrize("subtype", ["error_during_execution", "aborted", "", "success_partial"])
def test_an_unrecognised_subtype_raises_rather_than_passing(
    phase_kit, monkeypatch: pytest.MonkeyPatch, subtype: str
) -> None:
    """The `else` branch. This is the test the whole subtype section exists for.

    Every subtype here is one this code has never seen. The tempting handling -
    "it is not an error I named, so carry on" - would send a truncated or empty
    reply into the next phase's prompt, and the run would finish and produce a
    plausible report that is quietly missing whatever was cut off. An unknown
    outcome is an unknown outcome, so it stops the run.
    """
    with pytest.raises(PhaseFailed) as excinfo:
        run_one_phase(phase_kit, stream(reply=fenced(SEARCH_ROUND_1), subtype=subtype), monkeypatch)
    assert repr(subtype) in str(excinfo.value)


def test_a_stream_with_no_result_message_raises(phase_kit, monkeypatch: pytest.MonkeyPatch) -> None:
    """No ResultMessage means no terminal outcome to check, which is not success."""
    messages = [m for m in stream(reply=fenced(SEARCH_ROUND_1)) if not isinstance(m, ResultMessage)]
    with pytest.raises(PhaseFailed):
        run_one_phase(phase_kit, messages, monkeypatch)


# ---------------------------------------------------------------------------
# 8. Delegation actually happened
# ---------------------------------------------------------------------------


def test_a_phase_with_no_agent_invocation_raises(phase_kit, monkeypatch: pytest.MonkeyPatch) -> None:
    """The silent failure of the whole architecture, made loud.

    The stream here is a perfectly successful run: `subtype == "success"`, real
    text, no error anywhere. The only thing missing is the delegation, and the
    text is exactly the kind of well-formed JSON that would sail through the
    parser and into a report. Nothing downstream could tell that the four-agent
    crew never ran, so the check has to be here.
    """
    messages = stream(reply=fenced(SEARCH_ROUND_1), delegate=False)
    with pytest.raises(NoDelegation):
        run_one_phase(phase_kit, messages, monkeypatch)


@pytest.mark.parametrize("tool_name", ["Agent", "Task"])
def test_delegation_is_detected_under_both_tool_names(
    phase_kit, monkeypatch: pytest.MonkeyPatch, tool_name: str
) -> None:
    """`Task` was renamed to `Agent` in v2.1.63 and both names are still in flight.

    Matching only one of them breaks in a way that depends on the installed CLI
    version rather than on this code, which is the hardest kind of bug to place.
    """
    text = run_one_phase(phase_kit, stream(reply=fenced(SEARCH_ROUND_1), tool_name=tool_name), monkeypatch)
    assert "Source One" in text


def test_verbatim_tool_result_beats_the_parents_paraphrase(
    phase_kit, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The subagent's bytes, not the parent's summary of them.

    The scripted stream contains both: the tool result holds the JSON, and the
    parent then describes it in prose. Returning the prose would mean parsing a
    model's summary of a data structure, which fails as a `MalformedAgentReply`
    on a good day and as silently wrong data on a bad one.
    """
    text = run_one_phase(phase_kit, stream(reply=fenced(SEARCH_ROUND_1)), monkeypatch)
    assert PARENT_PARAPHRASE not in text
    assert parse_agent_json(text) == SEARCH_ROUND_1


# ---------------------------------------------------------------------------
# 4, 5 and 6. The bounded re-search gate
# ---------------------------------------------------------------------------


def test_gate_fires_when_coverage_is_insufficient_in_round_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Insufficient coverage plus an unspent retry buys exactly one more round."""
    state, fake = scripted_run(two_round_scripts(ANALYSIS_SUFFICIENT), tmp_path, monkeypatch)
    assert state.search_round == 2
    assert [p.phase for p in state.phases] == ["search", "analyze", "search", "analyze", "synthesize", "report"]
    assert fake.call_count == 6
    # The re-search queries come from the analyst's named gap, not from a repeat
    # of round one - the retry is spent on what is missing.
    assert "no source gives a cost comparison" in fake.prompts[2]


def test_gate_does_not_fire_a_third_time_even_when_coverage_stays_insufficient(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """THE IMPORTANT ONE. The searcher runs exactly twice, never three times.

    The analyst reports `sufficient: false` after the re-search as well, so the
    model-supplied half of the condition is asking for a third round. The bound
    is what refuses. If `MAX_SEARCH_ROUNDS` were enforced by a sentence in a
    prompt instead of by the loop header, this run would continue - and it would
    continue without raising anything, because a loop that keeps working is not
    an error condition. `ScriptedQuery` runs out of script on the seventh call
    and fails the test, which is the only symptom an unbounded version has.
    """
    state, fake = scripted_run(two_round_scripts(ANALYSIS_INSUFFICIENT), tmp_path, monkeypatch)

    searcher_phases = [p for p in state.phases if p.agent == "searcher"]
    assert len(searcher_phases) == 2, "the searcher must run at most twice in a whole run"
    assert state.search_round == MAX_SEARCH_ROUNDS
    assert fake.call_count == 6

    # Coverage is *still* insufficient at the end. The run finished anyway, with
    # a report, because thin sources are a documented limitation rather than a
    # failure - and the reporter is handed the gaps for its Limitations section.
    assert state.coverage_sufficient is False
    assert "no source gives a cost comparison" in fake.prompts[5]


def test_gate_does_not_fire_when_coverage_is_sufficient(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A satisfied analyst ends the search. The retry is not spent out of habit."""
    state, fake = scripted_run(one_round_scripts(), tmp_path, monkeypatch)
    assert state.search_round == 1
    assert len([p for p in state.phases if p.agent == "searcher"]) == 1
    assert fake.call_count == 4


# ---------------------------------------------------------------------------
# 7. Citation numbers survive a re-search
# ---------------------------------------------------------------------------


def test_source_ids_are_stable_across_a_re_search(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Round one's ids keep their values when round two appends to the list.

    Both scripted searcher payloads number their own sources 1 and 2, because a
    subagent has no memory of a previous round and cannot do otherwise. The
    coordinator therefore discards those ids and assigns its own. Round two's
    sources become 3 and 4; round one's stay 1 and 2.

    A renumber here would not raise anything. It would produce a report in which
    [1] points at a page that says something else entirely, and the prose around
    it would still read as authoritative.
    """
    state, _ = scripted_run(two_round_scripts(ANALYSIS_SUFFICIENT), tmp_path, monkeypatch)

    assert [s.id for s in state.sources] == [1, 2, 3, 4]
    assert state.sources[0].url == "https://a.example/one"
    assert state.sources[1].url == "https://b.example/two"
    assert state.sources[2].url == "https://c.example/three"
    assert state.citation_map()[1].title == "Source One"


# ---------------------------------------------------------------------------
# The run-level budget
#
# `max_budget_usd` is a per-`query()` ceiling. Handing the same value to every
# phase resets the cap on each one, so a six-phase run stating a $3.00 ceiling
# is really bounded at 6 x $3.00. Run 20260830-152235 did exactly that and spent
# $4.59 while every phase reported `subtype: "success"`. Nothing raises, nothing
# looks wrong, and the number in `cost.json` is false - which is why these tests
# assert on the value handed to the SDK and not only on the outcome.
# ---------------------------------------------------------------------------


def costly_scripts(cost: float) -> list[list]:
    """A four-phase run in which every phase reports the same cost."""
    return [
        stream(reply=fenced(SEARCH_ROUND_1), cost=cost),
        stream(reply=fenced(ANALYSIS_SUFFICIENT), cost=cost),
        stream(reply=fenced(SYNTHESIS), cost=cost),
        stream(reply=REPORT_MD, cost=cost),
    ]


def test_the_per_call_budget_shrinks_as_the_run_spends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each `query()` is handed what is *left* of the run budget, not the ceiling.

    Six phases at one cent each against a $1.50 run ceiling. The first call gets
    the whole 1.50 because nothing has been spent; every call after it gets less.
    Handing 1.50 to all six - the old behaviour - would arm the SDK's enforcement
    at a threshold no single phase can reach, which is a cap that cannot fire.
    """
    _, fake = scripted_run(two_round_scripts(ANALYSIS_SUFFICIENT), tmp_path, monkeypatch)
    budgets = [options.max_budget_usd for options in fake.options]

    assert budgets == pytest.approx([1.50, 1.49, 1.48, 1.47, 1.46, 1.45])
    assert budgets == sorted(budgets, reverse=True)
    assert all(a > b for a, b in zip(budgets, budgets[1:])), "the remainder must strictly decrease"


def test_the_run_raises_before_the_phase_that_would_cross_the_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The run stops, and the phase that would have overspent is never called.

    Two phases at $0.60 against a $1.00 ceiling puts the run at $1.20 with
    nothing left. The third phase is refused *before* `query()`, which is the
    only place a run-level bound can be enforced: once the call is made, the
    money is spent whatever the SDK reports afterwards.

    `call_count == 2` is the assertion that matters. A version that checked the
    budget after the call would also raise, and would also have paid for phase 3.
    """
    fake = ScriptedQuery(costly_scripts(0.6))
    monkeypatch.setattr(coordinator, "query", fake)

    with pytest.raises(BudgetExceeded) as excinfo:
        asyncio.run(
            run_research(QUESTION, agents_dir=AGENTS_DIR, runs_root=tmp_path / "runs", max_budget_usd=1.0)
        )

    assert fake.call_count == 2, "the third phase must never reach the SDK"
    message = str(excinfo.value)
    # The message names the phase that was refused, the ceiling, and the spend,
    # because those three are what a reader needs to decide whether to raise the
    # budget or to fix the pipeline.
    assert "'synthesize'" in message
    assert "1.00" in message and "1.2000" in message


def test_a_run_that_stays_under_the_ceiling_completes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bound must not fire on a run it should not fire on.

    Four phases at $0.20 is $0.80 against a $1.00 ceiling. Nothing raises, the
    report is produced, and the last call still carries a positive remainder.
    """
    state, fake = scripted_run(costly_scripts(0.2), tmp_path, monkeypatch, max_budget_usd=1.0)

    assert state.report_md == REPORT_MD
    assert fake.call_count == 4
    assert state.total_cost_usd() == pytest.approx(0.8)
    assert fake.options[-1].max_budget_usd == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# Harness trailers on the tool result
#
# `run_phase` reads the Agent tool result verbatim, and the harness appends its
# own framing to that block. In run 20260830-152235 four lines of it reached the
# bottom of `report.md`. The verifier flagged all four and the artifact was
# corrupted regardless, because a verifier runs after the report is written.
# ---------------------------------------------------------------------------

# The exact trailer from run 20260830-152235, copied off the tool result.
AGENT_ID_TRAILER = (
    "agentId: ad337dd3c386c9a66 (use SendMessage with to: 'ad337dd3c386c9a66', "
    "summary: '<5-10 word recap>' to continue this agent)"
)
USAGE_TRAILER = "<usage>subagent_tokens: 18671\ntool_uses: 0\nduration_ms: 45769</usage>"
REPLY_BODY = "# Title\n\n## Summary\nA sentence [1].\n\n## References\n[1] Source One - https://a.example/one\n"


def test_an_agent_id_trailer_is_stripped() -> None:
    """The resume hint is transport framing, not the agent's reply."""
    assert strip_harness_trailers(REPLY_BODY + AGENT_ID_TRAILER) == REPLY_BODY


def test_a_usage_block_is_stripped_even_though_it_spans_lines() -> None:
    """`<usage>` is multi-line, so a line-at-a-time strip would leave two thirds."""
    assert strip_harness_trailers(REPLY_BODY + USAGE_TRAILER) == REPLY_BODY


def test_both_trailers_together_are_stripped() -> None:
    """The shape the live run actually produced: the id line, then the usage block."""
    corrupted = REPLY_BODY + AGENT_ID_TRAILER + "\n" + USAGE_TRAILER
    assert strip_harness_trailers(corrupted) == REPLY_BODY
    assert "agentId" not in strip_harness_trailers(corrupted)
    assert "<usage>" not in strip_harness_trailers(corrupted)


def test_a_result_with_no_trailer_is_returned_byte_for_byte() -> None:
    """The common case, and the one where a helper like this does damage.

    Byte for byte, so no trailing newline is added or removed. A stripper that
    also tidied whitespace would silently rewrite every clean reply in the run.
    """
    for text in (REPLY_BODY, fenced(SEARCH_ROUND_1), "", "no trailer here", "trailing space   \n\n"):
        assert strip_harness_trailers(text) == text


def test_prose_about_usage_is_not_damaged() -> None:
    """The word `usage` in a sentence is content. Only the `<usage>` tag is framing.

    The word appears in the last line, which is where the trailers live, so a
    stripper matching on the word rather than on the tag would truncate a real
    report here.
    """
    prose = REPLY_BODY + "\nToken usage rose sharply, and usage of the term varies across sources.\n"
    assert strip_harness_trailers(prose) == prose
    assert strip_harness_trailers(prose + USAGE_TRAILER) == prose


def test_a_trailer_inside_a_fenced_code_block_is_content() -> None:
    """An agent quoting harness output in a code fence keeps every byte of it.

    A searcher summarising what a tool returned can legitimately paste an
    `agentId:` line into a fence. Stripping it there would edit the agent's
    reply, which is the one thing the verbatim capture exists to prevent.
    """
    quoted = "Here is what the harness printed:\n\n```\n" + AGENT_ID_TRAILER + "\n"
    assert strip_harness_trailers(quoted) == quoted


def test_the_stripper_runs_on_the_real_tool_result_path(
    phase_kit, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wired in, not merely written. The helper is useless if nothing calls it.

    The scripted tool result carries both trailers, exactly as the live one did.
    What `run_phase` returns must parse, and must not contain either trailer.
    """
    reply = fenced(SEARCH_ROUND_1) + AGENT_ID_TRAILER + "\n" + USAGE_TRAILER
    text = run_one_phase(phase_kit, stream(reply=reply), monkeypatch)

    assert "agentId" not in text and "<usage>" not in text
    assert parse_agent_json(text) == SEARCH_ROUND_1


# ---------------------------------------------------------------------------
# The options handed to the SDK, and the artifacts left on disk
# ---------------------------------------------------------------------------


def test_every_query_call_carries_the_delegation_tool_and_the_guard_rails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Criteria 2, 6 and 7, asserted on every call rather than on the first.

    `"Agent"` is the one that matters most: without it Claude cannot delegate,
    falls back to answering directly, and produces output that reads correctly
    while the entire architecture is bypassed.
    """
    _, fake = scripted_run(two_round_scripts(ANALYSIS_SUFFICIENT), tmp_path, monkeypatch)
    assert fake.call_count == 6
    for options in fake.options:
        assert "Agent" in options.allowed_tools
        # A live, armed budget on every call. It is no longer the run ceiling of
        # 1.5 on every call, because that is exactly the defect fix 1 removed -
        # see `test_the_per_call_budget_shrinks_as_the_run_spends`, which pins
        # the shrinking values.
        assert 0 < options.max_budget_usd <= 1.5
        assert options.env["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "1"
        assert options.env["CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS"] == "4"
        assert set(options.agents) == {"searcher", "analyst", "synthesizer", "reporter"}


def test_every_phase_leaves_an_input_an_output_and_a_state_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Criterion 8, and the reason a failed run can be bisected at all.

    The sequence numbers run 01..06 in execution order, and each filename
    carries the real phase name, so a directory containing a re-search still
    reads top to bottom without the reader counting rounds.
    """
    state, _ = scripted_run(two_round_scripts(ANALYSIS_SUFFICIENT), tmp_path, monkeypatch)
    run_dir = tmp_path / "runs" / state.run_id
    names = sorted(p.name for p in run_dir.iterdir())

    assert len([n for n in names if n.endswith(".input.json")]) == 6
    assert len([n for n in names if n.endswith(".output.md")]) == 6
    assert len([n for n in names if n.startswith("state-after-")]) == 6
    assert "report.md" in names and "cost.json" in names

    assert "01-searcher.input.json" in names
    assert "03-searcher.input.json" in names
    assert "state-after-03-search.json" in names
    assert "06-reporter.output.md" in names

    # The recorded input is the whole prompt, because it is the whole context
    # the agent had - not a summary of it.
    recorded = json.loads((run_dir / "02-analyst.input.json").read_text(encoding="utf-8"))
    assert "https://a.example/one" in recorded["prompt"]
    assert recorded["allowed_tools"] == ["Agent", "WebSearch"]

    costs = json.loads((run_dir / "cost.json").read_text(encoding="utf-8"))
    assert len(costs["phases"]) == 6
    assert costs["total_cost_usd"] == pytest.approx(0.06)


# ---------------------------------------------------------------------------
# What is inside a state snapshot
#
# THE INVARIANT: `state-after-NN-<phase>.json` is the run state *including* that
# phase's parsed result.
#
# It did not hold. `run_phase` wrote the snapshot as its last step, but the reply
# is parsed and folded into `RunState` by the caller, after `run_phase` returns -
# so every file was written one step early. Run 20260830-152235 left
# `state-after-01-search.json` with `sources: []` after the searcher returned 28,
# and `state-after-06-report.json` with `report_md: null`. These files exist so a
# reader can watch state accumulate across phase boundaries, and a snapshot that
# omits the phase it is named after teaches the opposite of what it is for.
# ---------------------------------------------------------------------------


def snapshot(run_dir: Path, name: str) -> dict:
    """Read one `state-after-NN-<phase>.json` back off disk."""
    return json.loads((run_dir / f"state-after-{name}.json").read_text(encoding="utf-8"))


def test_the_search_snapshot_contains_the_sources_that_phase_returned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`state-after-01-search.json` holds the parsed sources, not an empty list.

    The searcher's two sources, with the ids the coordinator assigned rather than
    the ones the agent numbered itself.
    """
    state, _ = scripted_run(two_round_scripts(ANALYSIS_SUFFICIENT), tmp_path, monkeypatch)
    after_search = snapshot(tmp_path / "runs" / state.run_id, "01-search")

    assert [s["id"] for s in after_search["sources"]] == [1, 2]
    assert after_search["sources"][0]["url"] == "https://a.example/one"
    # The re-search snapshot shows the accumulation these files exist to show.
    assert len(snapshot(tmp_path / "runs" / state.run_id, "03-search")["sources"]) == 4


def test_the_analyse_snapshot_contains_the_claims_and_the_coverage_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The verdict especially: it is what decides whether a re-search happens.

    `coverage_sufficient` was `null` in the live run's `state-after-02-analyze`
    even though the analyst's `false` is what triggered phase 3. A reader
    bisecting that run would have found no record of the decision in the file
    named after the phase that made it.
    """
    state, _ = scripted_run(two_round_scripts(ANALYSIS_SUFFICIENT), tmp_path, monkeypatch)
    after_analyse = snapshot(tmp_path / "runs" / state.run_id, "02-analyze")

    assert [c["id"] for c in after_analyse["claims"]] == ["c1"]
    assert after_analyse["coverage_sufficient"] is False
    assert after_analyse["coverage_gaps"] == ["no source gives a cost comparison"]


def test_every_phase_that_ran_left_a_snapshot_holding_its_own_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One file per phase, each carrying the thing its phase produced.

    The report phase is the one that used to be impossible to check by reading
    the directory: its snapshot held `report_md: null`, so the run's deliverable
    appeared in no state file at all.
    """
    state, _ = scripted_run(two_round_scripts(ANALYSIS_SUFFICIENT), tmp_path, monkeypatch)
    run_dir = tmp_path / "runs" / state.run_id

    assert sorted(p.name for p in run_dir.glob("state-after-*.json")) == [
        "state-after-01-search.json", "state-after-02-analyze.json",
        "state-after-03-search.json", "state-after-04-analyze.json",
        "state-after-05-synthesize.json", "state-after-06-report.json",
    ]
    assert [m["id"] for m in snapshot(run_dir, "05-synthesize")["merged_claims"]] == ["m1"]
    assert snapshot(run_dir, "06-report")["report_md"] == REPORT_MD


def test_the_reporter_receives_a_citation_map_built_in_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Criterion 9. The numbers are fixed before the reporter ever sees them.

    Every id in `state.sources` appears in the reporter's prompt paired with its
    title and url, and the prompt forbids renumbering. Handing the reporter a
    finished table removes the only decision in the report that has a single
    correct answer and no way to notice a wrong one.
    """
    state, fake = scripted_run(two_round_scripts(ANALYSIS_SUFFICIENT), tmp_path, monkeypatch)
    report_prompt = fake.prompts[5]

    for source in state.sources:
        assert f"[{source.id}] {source.title} - {source.url}" in report_prompt
    assert "renumber nothing" in report_prompt
    assert state.report_md == REPORT_MD


def test_no_dotenv_anywhere_in_the_pipeline() -> None:
    """Criterion 10, pinned as a test because the failure it prevents is remote.

    The SDK spawns the local `claude` CLI and inherits its ambient
    authentication, so this project needs no key of its own. A sibling project
    in this workspace keeps a `.env` that points `ANTHROPIC_BASE_URL` at a
    gateway. Loading it here would export that variable into the environment the
    SDK hands the subprocess, and every call would be misrouted - surfacing as
    an auth error from an agent, four layers from the cause.
    """
    assert "dotenv" not in sys.modules
    for name in ("coordinator.py", "cli.py"):
        assert "dotenv" not in (_SRC / "research_crew" / name).read_text(encoding="utf-8")
