"""Tests for `agents_loader.py`.

Two kinds of test live here.

The first kind reads the real `agents/` directory and pins the crew's actual
configuration: four agents, one of which can reach the web, one of which runs
Opus. These are contract tests on the design, not on the parser. If someone adds
`Bash` to the analyst, a test fails and names the risk.

The second kind builds throwaway Markdown in `tmp_path` and pins parser
behaviour that the real files cannot express, above all the difference between
an absent `tools` key and an empty one. That difference is invisible in output
and turns a no-tool agent into a full-filesystem agent, so it gets a dedicated
test rather than a comment.

No test here calls a model. `load_agents` builds `AgentDefinition` objects; it
never runs an agent, which is exactly why the whole loader is testable offline.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from research_crew.agents_loader import load_agents, parse_agent_file, strip_html_comments  # noqa: E402

AGENTS_DIR = _ROOT / "agents"


@pytest.fixture(scope="module")
def crew() -> dict:
    return load_agents(AGENTS_DIR)


# ---------------------------------------------------------------------------
# The real crew: what the design actually claims
# ---------------------------------------------------------------------------


def test_loads_exactly_the_four_named_agents(crew: dict) -> None:
    """Criterion 3. Keyed by the frontmatter `name`, which is the string the
    coordinator passes to the Agent tool - not by filename."""
    assert set(crew) == {"searcher", "analyst", "synthesizer", "reporter"}


def test_searcher_can_reach_the_web_and_nothing_else(crew: dict) -> None:
    """Criterion 4. One agent touches the outside world, and only one.

    Provenance in this system means "a URL the searcher actually retrieved". A
    second agent with fetch access would make the origin of a fact unknowable.
    Note the absences too: no Read or Grep, so the searcher cannot 'find' a fact
    inside this repository and report it in the shape of a web result.
    """
    assert crew["searcher"].tools == ["WebSearch"]


@pytest.mark.parametrize("name", ["analyst", "synthesizer", "reporter"])
def test_downstream_agents_have_no_tools_at_all(crew: dict, name: str) -> None:
    """Criterion 5. An empty list, and it must stay an empty list.

    `[]` makes each of these agents a pure function of the string it is handed:
    same input, same output, no hidden channel. That is what makes the recorded
    input file a complete explanation of what the agent did.

    The assertion is deliberately `== []` and not `not tools`. `None` is also
    falsy, and `None` means the exact opposite - inherit every tool.
    """
    assert crew[name].tools == []


def test_only_the_synthesizer_pays_the_opus_rate(crew: dict) -> None:
    """Criterion 6. Per-agent model choice is a concrete saving of the split.

    Retrieval, extraction, and formatting are Sonnet work. Deciding whether two
    differently worded claims are the same claim, or genuinely opposed, is the
    one judgment call in the pipeline. A single mega-prompt cannot make this
    distinction: it runs the whole task at the strongest model any phase needs.
    """
    assert crew["synthesizer"].model == "opus"
    assert [crew[n].model for n in ("searcher", "analyst", "reporter")] == ["sonnet"] * 3


@pytest.mark.parametrize("name", ["searcher", "analyst", "synthesizer", "reporter"])
def test_design_notes_never_reach_the_prompt(crew: dict, name: str) -> None:
    """Criterion 7. The rationale ships in the file and is stripped at load.

    If this fails, every call to that agent pays tokens for a block of prose
    written for a human, and the agent is additionally being told at length
    about behaviour it must avoid - which is a poor way to prevent it.
    """
    prompt = crew[name].prompt
    assert "<!--" not in prompt
    assert "-->" not in prompt
    assert "DESIGN NOTES" not in prompt


@pytest.mark.parametrize("name", ["searcher", "analyst", "synthesizer", "reporter"])
def test_every_prompt_survives_stripping_and_opens_with_a_role(crew: dict, name: str) -> None:
    """Criterion 8. A prompt emptied by an over-greedy regex would still load.

    The agent would run and answer as a generic assistant, which is a failure
    that produces plausible output. Checking the opening line catches it.
    """
    assert crew[name].prompt.startswith("You are the")


def test_descriptions_are_present_because_they_drive_delegation(crew: dict) -> None:
    """`description` tells the caller when to use an agent. An empty one is a
    silent routing failure, so the loader refuses to build such an agent."""
    for definition in crew.values():
        assert len(definition.description.strip()) > 20


# ---------------------------------------------------------------------------
# The trap: absent `tools` versus empty `tools`
# ---------------------------------------------------------------------------

_INHERITS = """---
name: inherits
description: No tools key at all, so this agent inherits every subagent tool.
model: sonnet
---

You are the inheriting agent.
"""

_RESTRICTED = """---
name: restricted
description: An explicitly empty tools list, so this agent gets nothing.
tools: []
model: sonnet
---

You are the restricted agent.
"""


def test_absent_tools_differs_from_empty_tools(tmp_path: Path) -> None:
    """Criterion 9. The two cases must not collapse into one.

        tools key absent  -> AgentDefinition.tools is None
                          -> the SDK grants every subagent tool: Read, Write,
                             Bash, Grep, WebSearch, everything.
        tools: []         -> AgentDefinition.tools == []
                          -> the SDK grants none.

    Both values are falsy in Python. A loader written as `tools or None`, or one
    guarded by `if tools:`, passes every other test in this file while handing
    the analyst, the synthesizer, and the reporter shell and filesystem access.
    Nothing in the output would show it. That is why this is a test and not a
    comment.
    """
    (tmp_path / "inherits.md").write_text(_INHERITS, encoding="utf-8")
    (tmp_path / "restricted.md").write_text(_RESTRICTED, encoding="utf-8")

    loaded = load_agents(tmp_path)

    assert loaded["inherits"].tools is None
    assert loaded["restricted"].tools == []
    assert loaded["inherits"].tools != loaded["restricted"].tools
    # Both are falsy. That is the whole trap, stated as an assertion.
    assert not loaded["inherits"].tools and not loaded["restricted"].tools


def test_model_key_is_optional(tmp_path: Path) -> None:
    """Omitting `model` leaves it unset, so the SDK default applies."""
    (tmp_path / "a.md").write_text(
        "---\nname: a\ndescription: An agent with no model pin.\n---\n\nYou are the a agent.\n",
        encoding="utf-8",
    )
    assert load_agents(tmp_path)["a"].model is None


# ---------------------------------------------------------------------------
# Comment stripping
# ---------------------------------------------------------------------------


def test_strips_several_multi_line_comments_without_eating_the_text_between() -> None:
    """A greedy regex would swallow from the first `<!--` to the last `-->`.

    That deletes the prompt text sitting between two comment blocks and leaves a
    file that still loads. Non-greedy plus DOTALL is the required combination:
    non-greedy for the several-comments case, DOTALL for the many-lines case.
    """
    body = "<!--\nfirst\nblock\n-->\nKEEP ONE\n<!-- second -->\nKEEP TWO\n"
    result = strip_html_comments(body)
    assert "KEEP ONE" in result and "KEEP TWO" in result
    assert "first" not in result and "second" not in result


def test_a_horizontal_rule_in_the_body_is_not_read_as_frontmatter(tmp_path: Path) -> None:
    """The frontmatter regex is anchored to the start of the file on purpose.

    Agent prompts contain Markdown, and Markdown uses `---` as a horizontal
    rule. An unanchored pattern would cut the prompt in half at the first rule.
    """
    path = tmp_path / "r.md"
    path.write_text(
        "---\nname: r\ndescription: An agent whose body contains a rule.\ntools: []\n---\n\n"
        "You are the r agent.\n\n---\n\nStill part of the prompt.\n",
        encoding="utf-8",
    )
    _, definition = parse_agent_file(path)
    assert "Still part of the prompt." in definition.prompt


# ---------------------------------------------------------------------------
# Failure modes: refuse to start rather than half-load
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "content", "needle"),
    [
        ("no_front.md", "You are the agent with no frontmatter.\n", "frontmatter"),
        ("no_name.md", "---\ndescription: Has no name.\n---\n\nYou are the nameless agent.\n", "name"),
        ("empty_name.md", "---\nname: ''\ndescription: Blank name.\n---\n\nYou are the agent.\n", "name"),
        ("no_desc.md", "---\nname: n\n---\n\nYou are the undescribed agent.\n", "description"),
        ("empty_body.md", "---\nname: n\ndescription: Body is only a comment.\n---\n\n<!-- all of it -->\n", "body"),
        ("bad_yaml.md", '---\nname: n\ndescription: "unterminated\n---\n\nYou are the agent.\n', "YAML"),
        ("bad_tools.md", "---\nname: n\ndescription: Tools is a string.\ntools: WebSearch\n---\n\nYou are it.\n", "tools"),
    ],
)
def test_broken_files_raise_a_value_error_naming_the_file(
    tmp_path: Path, filename: str, content: str, needle: str
) -> None:
    """Loading must fail loudly, and the message must say which file.

    A crew that half-loads is worse than one that refuses to start: an agent
    that lost its prompt still runs and still answers, just as a generic
    assistant, and the resulting report looks ordinary.
    """
    path = tmp_path / filename
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        parse_agent_file(path)

    message = str(excinfo.value)
    assert filename in message
    assert needle.lower() in message.lower()


def test_duplicate_agent_names_are_rejected(tmp_path: Path) -> None:
    """Two files claiming one name would silently drop one agent from the crew."""
    text = "---\nname: dup\ndescription: A duplicated name.\ntools: []\n---\n\nYou are the dup agent.\n"
    (tmp_path / "one.md").write_text(text, encoding="utf-8")
    (tmp_path / "two.md").write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_agents(tmp_path)


def test_an_empty_directory_loads_to_an_empty_crew(tmp_path: Path) -> None:
    assert load_agents(tmp_path) == {}
