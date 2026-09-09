# Task 01 - Foundation: run state, agent loader, observability

You are implementing part of `research-crew`, a teaching artifact for the Claude Certified
Architect exam. Read this whole spec before you write code. It is self-contained. Do not
look for other task files, and do not ask for more context.

## What research-crew is

A CLI. It takes a research question and produces a cited Markdown report. A coordinator
written in Python delegates to four specialised subagents through the Claude Agent SDK:

```
question
 -> searcher     (tools: WebSearch)  -> sources with URLs
 -> analyst      (tools: none)       -> atomic claims, each tied to a source
 -> synthesizer  (tools: none)       -> merged claims + explicit conflicts
 -> reporter     (tools: none)       -> Markdown with [n] citations + References
 -> verify.py    (no model)          -> citation integrity check
```

This task builds the three foundation modules only. Another task builds the coordinator.
Do not write the coordinator, the CLI, or the verifier here.

## Audience

The reader is studying agent orchestration. Comment the architecture at least as much as
the code. Explain *why* a boundary exists, not what a line does. Assume the reader knows
Python and does not know the Agent SDK.

## Current SDK facts - code against these, not against memory

The Agent SDK documentation moved hosts. It is now at `code.claude.com/docs/en/agent-sdk/`.
The older `docs.anthropic.com/en/docs/claude-code/sdk` path, and anything on
`platform.claude.com` describing "Managed Agents", are a **different product**. Ignore both.

- Reference: https://code.claude.com/docs/en/agent-sdk/subagents
- Reference: https://code.claude.com/docs/en/agent-sdk/python

Install with `pip install claude-agent-sdk` (current version 0.2.148).

`AgentDefinition` is imported from `claude_agent_sdk` and takes these fields:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `description` | str | yes | Natural language description of when to use this agent |
| `prompt` | str | yes | The agent's system prompt |
| `tools` | list[str] | no | Allowed tool names. **Omitting this inherits every tool available to subagents. Passing an empty list grants none.** These are different. |
| `model` | str | no | opus, sonnet, haiku, inherit, or a full model id |
| `disallowedTools` | list[str] | no | camelCase on purpose, see note below |
| `mcpServers` | list | no | camelCase on purpose |

Note from the docs: "In the Python SDK, multi-word field names such as `disallowedTools`
and `mcpServers` keep their camelCase spelling to match the wire format rather than
following Python's snake_case convention." Single-word fields are lowercase, as shown.

Quote from the same page, which drives this whole design: "A tool you leave out isn't in
the subagent's session at all: Claude works without it, with no permission prompt or error."

## Files to create

Work only inside `research-crew/`. Create exactly these files:

```
research-crew/
  requirements.txt
  src/research_crew/__init__.py
  src/research_crew/state.py
  src/research_crew/agents_loader.py
  src/research_crew/observability.py
  tests/test_state.py
  tests/test_agents_loader.py
  tests/test_observability.py
```

Do not create or edit anything else. The directory `research-crew/agents/` already exists
and holds four Markdown files. They are an input to your work. Read them. Do not modify them.

### requirements.txt

List `claude-agent-sdk`, `PyYAML`, and `pytest`. Nothing else.

Do **not** add `python-dotenv`, and do not load a `.env` file anywhere in this project. The
Agent SDK drives the locally installed `claude` CLI and uses its ambient authentication. A
stray `ANTHROPIC_BASE_URL` from a `.env` file would silently misroute every call to a
gateway that does not serve this API. Record this reason in a comment in `requirements.txt`.

### src/research_crew/state.py

The run-state object. The learner watches context flow by reading these snapshots, so
clarity beats cleverness.

Define frozen dataclasses:

- `Source` with `id: int`, `url: str`, `title: str`, `snippet: str`, `query: str`
- `Claim` with `id: str`, `text: str`, `source_id: int`, `evidence: str`, `confidence: str`
- `MergedClaim` with `id: str`, `text: str`, `source_ids: list[int]`, `support: str`
- `Conflict` with `id: str`, `topic: str`, `position_a: dict`, `position_b: dict`,
  `kind: str`, `explanation: str`
- `PhaseRecord` with `phase: str`, `agent: str`, `round: int`, `cost_usd: float | None`,
  `duration_s: float`, `subtype: str`

Define a mutable `RunState` holding:

- `question: str`
- `run_id: str`, a UTC timestamp in the format `YYYYMMDD-HHMMSS`
- `search_round: int`, which starts at 1
- `sources: list[Source]`
- `claims: list[Claim]`
- `merged_claims: list[MergedClaim]`
- `conflicts: list[Conflict]`
- `coverage_sufficient: bool | None`
- `coverage_gaps: list[str]`
- `report_md: str | None`
- `phases: list[PhaseRecord]`

Provide these methods:

- `RunState.new(question: str) -> RunState` builds the initial state with a fresh `run_id`.
- `to_dict() -> dict` and `to_json() -> str` give a full, human-readable serialisation.
- `RunState.from_dict(d) -> RunState` is the exact inverse of `to_dict()`.
- `citation_map() -> dict[int, Source]` maps a citation number to its `Source`, keyed by
  `Source.id`.
- `total_cost_usd() -> float` sums the `cost_usd` values that are not `None`.

Write a module docstring explaining that this object is the *only* thing that crosses a
phase boundary. Subagents share no memory. Anything the next phase needs must be read out
of this object by the coordinator and written into a prompt string by hand.

### src/research_crew/agents_loader.py

This module turns the four Markdown design files into `AgentDefinition` objects.

Signature: `load_agents(agents_dir: Path) -> dict[str, AgentDefinition]`

For each `*.md` file in the directory:

1. Parse the YAML frontmatter delimited by `---` lines at the top of the file. The keys are
   `name`, `description`, `tools`, and `model`.
2. **Strip every HTML comment from the body.** A comment may span many lines, and one file
   may hold several. Use a non-greedy, DOTALL regular expression.
3. Take the remaining body text, stripped of surrounding whitespace, as the agent `prompt`.
4. Build an `AgentDefinition`.
5. Key the returned dictionary by the frontmatter `name`.

Rules that the tests must pin down:

- If the `tools` key is **absent** from the frontmatter, do not pass `tools` to
  `AgentDefinition` at all. The agent then inherits every subagent tool.
- If the `tools` key is **present and an empty list**, pass an empty list. The agent then
  gets no tools. The analyst, synthesizer, and reporter all depend on this.
- Confusing these two cases silently grants a no-tool agent full filesystem access. Comment
  this trap at the point where the code handles it.
- Raise a clear `ValueError` that names the file when frontmatter is missing, when `name` or
  `description` or the body is empty, or when the YAML fails to parse.

Explain in comments why stripping HTML comments matters. The design rationale must ship with
the artifact, but it must never reach the model's context window, where it would cost tokens
on every call and could distract the agent.

### src/research_crew/observability.py

This module writes one directory per execution, so that a bad report can be debugged later.

Define `class RunRecorder` with the constructor `RunRecorder(runs_root: Path, run_id: str)`.

It creates `runs_root/<run_id>/` and writes:

- `record_input(seq: int, agent: str, payload: dict)` writes `NN-<agent>.input.json`
- `record_output(seq: int, agent: str, text: str)` writes `NN-<agent>.output.md`
- `record_state(seq: int, phase: str, state_json: str)` writes `state-after-NN-<phase>.json`
- `record_cost(summary: dict)` writes `cost.json`
- `record_report(markdown: str)` writes `report.md`

Zero-pad `seq` to two digits. Create parent directories as needed. Write UTF-8. Never
overwrite an existing run directory silently: raise if `run_id` already exists.

Comment on why the *input* to each agent is recorded separately from its output. The input
file is the complete context that the agent received. When a claim in the final report is
wrong, that file answers one question in a single step: was the error already present in
what this agent was given, or did this agent introduce it?

## Acceptance criteria

Your work is reviewed against this list. Every item must hold.

1. `pip install -r research-crew/requirements.txt` succeeds.
2. `pytest research-crew/tests/` passes. No test makes a network call or an API call.
3. `load_agents()` run against the real `research-crew/agents/` directory returns exactly
   four entries, keyed `searcher`, `analyst`, `synthesizer`, and `reporter`.
4. The loaded `searcher` has `tools` equal to `["WebSearch"]`.
5. The loaded `analyst`, `synthesizer`, and `reporter` each have `tools` equal to `[]`.
6. The loaded `synthesizer` has `model` equal to `"opus"`. The other three are `"sonnet"`.
7. No loaded `prompt` contains the text `<!--` or the text `DESIGN NOTES`.
8. Every loaded `prompt` is non-empty and starts with `You are the`.
9. A test proves that the absent-`tools` case differs from the empty-list case. Build two
   temporary Markdown files in `tmp_path` and assert the difference.
10. `RunState.from_dict(s.to_dict())` reproduces an equal `RunState`, including the nested
    dataclasses. Test with at least one populated `Source`, `Claim`, `MergedClaim`,
    `Conflict`, and `PhaseRecord`.
11. `total_cost_usd()` ignores `None` entries, and does not raise when every entry is `None`.
12. `RunRecorder` raises when it is asked to reuse an existing `run_id`.
13. Every module has a docstring that explains its role in the pipeline.
14. `state.py`, `agents_loader.py`, and `observability.py` together stay under 260 lines,
    excluding comments, docstrings, and blank lines. The comments themselves are not capped.

## Constraints

- Target Python 3.10 or later. Use the standard library plus the three listed dependencies.
- Add a type hint to every public function.
- Do not call `print()` in a library module.
- Do not write `coordinator.py`, `cli.py`, or `verify.py`. A later task covers them.
- Do not modify any file in `research-crew/agents/`.

## When you are done

Reply with these four items:

1. The list of files you created.
2. The exact `pytest` command you ran, and its full output.
3. The line count for each of the three modules, excluding comments and blank lines.
4. Anything in this spec that you found ambiguous or wrong.
