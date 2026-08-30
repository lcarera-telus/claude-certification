# Task 02 - The coordinator pipeline and the CLI

You are implementing part of `research-crew`, a teaching artifact for the Claude Certified
Architect exam. Read this whole spec before you write code. It is self-contained.

## What already exists

Task 01 built and tested these modules. Read them before you start. Reuse them. Do not
rewrite them and do not modify them.

- `src/research_crew/state.py` — `RunState`, `Source`, `Claim`, `MergedClaim`, `Conflict`,
  `PhaseRecord`. `RunState` carries `question`, `run_id`, `search_round`, `sources`,
  `claims`, `merged_claims`, `conflicts`, `coverage_sufficient`, `coverage_gaps`,
  `report_md`, and `phases`. It offers `RunState.new()`, `to_dict()`, `to_json()`,
  `from_dict()`, `citation_map()`, and `total_cost_usd()`.
- `src/research_crew/agents_loader.py` — `load_agents(agents_dir: Path) -> dict[str, AgentDefinition]`.
- `src/research_crew/observability.py` — `RunRecorder(runs_root, run_id)` with
  `record_input`, `record_output`, `record_state`, `record_cost`, and `record_report`.
- `research-crew/agents/*.md` — the four subagent definitions. Do not modify these.

Your job is `coordinator.py` and `cli.py`. Do not write `verify.py`; a later task covers it.

## Audience

The reader is studying agent orchestration. Comment the architecture at least as heavily as
the code. Explain *why* a boundary exists. Assume the reader knows Python and does not know
the Agent SDK.

## Current SDK facts - code against these, not against memory

Docs are at `code.claude.com/docs/en/agent-sdk/`. Anything on `platform.claude.com` about
"Managed Agents" is a **different product**; ignore it.

- https://code.claude.com/docs/en/agent-sdk/subagents
- https://code.claude.com/docs/en/agent-sdk/python
- https://code.claude.com/docs/en/agent-sdk/agent-loop
- https://code.claude.com/docs/en/env-vars

The shape of a call:

```python
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

async for message in query(
    prompt="Use the searcher agent to ...",
    options=ClaudeAgentOptions(
        agents=AGENTS,                     # dict[str, AgentDefinition] from load_agents()
        allowed_tools=["Agent", "WebSearch"],
        max_budget_usd=3.0,
        env={
            "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
            "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "4",
        },
    ),
):
    ...
```

Facts that will cost you a debugging session if you miss them:

1. **`allowed_tools` must contain `"Agent"`.** Claude invokes a subagent through the `Agent`
   tool. Leave it out and the invocation falls through to a permission callback or is denied,
   and Claude silently answers the question itself instead of delegating.
2. **`Task` was renamed to `Agent`** in Claude Code v2.1.63. `tool_use` blocks now carry
   `"Agent"`, but `system:init` and `permission_denials[].tool_name` still say `"Task"`. When
   you detect a subagent invocation, match **both** names.
3. **The parent may summarise the subagent's output.** From the docs: "The parent receives
   the subagent's final message as the Agent tool result, but may summarize it in its own
   response." You need the subagent's output **verbatim**, because it is JSON you must parse.
   Handle this two ways, both required:
   - Prefer reading the `Agent` tool's result block from the message stream. That is the
     subagent's actual final message.
   - Also instruct the coordinator, in every phase prompt, to reproduce the agent's output
     exactly and add no commentary.
4. **The subagent sees only the prompt string you write.** It gets no parent history, no
   parent system prompt, no sibling output. Everything it needs must be inside that string.
5. **`env` is merged into the inherited environment** by the Python SDK. It does not replace
   it, so `PATH` survives.
6. `ResultMessage` carries `subtype`, `total_cost_usd`, `usage`, and `session_id`.
7. Messages produced inside a subagent carry a `parent_tool_use_id`.

## Files to create

```
research-crew/
  src/research_crew/coordinator.py
  src/research_crew/cli.py
  tests/test_coordinator.py
```

Create nothing else. Do not modify Task 01 modules or `agents/*.md`.

## src/research_crew/coordinator.py

### Constants, at module level, each with a comment explaining the number

- `MAX_SEARCH_ROUNDS = 2` — the initial search plus at most one re-search.
- `DEFAULT_MAX_BUDGET_USD = 3.0`
- `SUBAGENT_SPAWN_DEPTH = "1"` — our four agents may not spawn subagents of their own.
- `MAX_CONCURRENT_SUBAGENTS = "4"`

### The phase runner

Write one helper that every phase goes through:

```python
async def run_phase(
    *, agent_name: str, phase: str, prompt: str, state: RunState,
    recorder: RunRecorder, seq: int, agents: dict, max_budget_usd: float,
) -> str:
```

It must:

1. Record the input with `recorder.record_input(seq, agent_name, {...})`. Include the full
   prompt string. That file is the complete context the agent received, so it must be complete.
2. Run `query()` with the options shown above, naming `agent_name` explicitly in the prompt.
3. Collect the subagent's verbatim final message, per fact 3 above.
4. Detect the `Agent` (or `Task`) tool invocation and confirm delegation actually happened.
   If no subagent was invoked, raise. Answering directly is a silent failure of the whole
   architecture, and it must be loud.
5. Branch on `ResultMessage.subtype` **explicitly**:
   - `"success"` — continue.
   - `"error_max_budget_usd"` — raise `BudgetExceeded` with the cost.
   - `"error_max_turns"` — raise `TurnLimitExceeded`.
   - anything else — raise `PhaseFailed` naming the subtype.
   Never treat "not an error I named" as success. Comment on why: an unrecognised subtype
   returned as success produces a truncated or empty result that flows downstream and looks
   like a real answer. This is the SDK-level form of the rule in
   `.claude/rules/agentic-loop-stop-reason.md`.
6. Append a `PhaseRecord` to `state.phases` with the cost, duration, and subtype.
7. Record the output with `recorder.record_output(seq, agent_name, text)`.
8. Record the state with `recorder.record_state(seq, phase, state.to_json())`.
9. Return the verbatim text.

### Parsing a subagent's reply

Every agent returns exactly one fenced JSON block. Write one helper that extracts and parses
it, and raises a clear error carrying the offending text when the block is missing or invalid.
Do not use `eval`. Comment on why this contract exists: a fenced block is easy for a model to
produce reliably and easy for code to find, and it keeps the coordinator free of model calls.

### The pipeline

```python
async def run_research(question: str, *, agents_dir: Path, runs_root: Path,
                       max_budget_usd: float = DEFAULT_MAX_BUDGET_USD) -> RunState:
```

Phases, in order:

**Phase 1 — search (seq 1).** Prompt the `searcher` with the question and 3 to 5 queries you
derive from it in Python, not with a model call. Parse `sources`, assign each a sequential
integer `id` starting at 1, and store them on `state.sources`.

**Phase 2 — analyse (seq 2).** Marshal `state.sources` into the prompt as a numbered list
with URL, title, and snippet. The analyst has no tools, so anything absent from this string
does not exist for it. Parse `claims` and `coverage`. Store claims, `coverage_sufficient`,
and `coverage_gaps`.

**The bounded re-search gate.** After phase 2, if `coverage_sufficient` is false **and**
`state.search_round < MAX_SEARCH_ROUNDS`:

- increment `state.search_round`
- run the searcher again (seq 3) with queries built from `state.coverage_gaps`
- append the new sources, continuing the `id` numbering, and never renumbering an existing id
- re-run the analyst (seq 4) over the combined source set, replacing `state.claims`

This may happen **at most once**. Enforce it with the `search_round` check, not with a prompt
instruction. Write a comment explaining why an unbounded version is dangerous: the component
judging sufficiency is the same kind of component that produces the work, so a model that is
never satisfied loops forever, and every iteration is a billable API call. Nothing raises,
because nothing is failing — it is working, expensively, without end.

**Phase 3 — synthesise.** Marshal `state.claims` into the prompt. Parse `merged_claims` and
`conflicts`. Store both.

**Phase 4 — report.** Build the citation map in Python from `state.citation_map()` and pass
it to the reporter as a fixed `number -> (title, url)` table. The reporter must use those
numbers exactly. Comment on why the coordinator owns the numbering: it is a step needing no
judgment, and a model that renumbers produces a well-formed report in which every citation is
off by one. Store the Markdown on `state.report_md`.

Use sequence numbers that keep the run directory readable when a re-search happens. Number
phases in execution order and record the real phase name in each filename.

Finally, write `recorder.record_report(state.report_md)` and `recorder.record_cost({...})`
with per-phase cost, duration, subtype, and the run total from `state.total_cost_usd()`.

Return the `RunState`.

## src/research_crew/cli.py

An `argparse` entry point runnable as `python -m research_crew.cli "<question>"`.

- positional `question`
- `--max-budget-usd`, float, default `DEFAULT_MAX_BUDGET_USD`
- `--runs-root`, path, default `research-crew/runs`
- `--agents-dir`, path, default `research-crew/agents`

Run the pipeline with `asyncio.run`. Print a short progress line per phase to stderr, and the
final report path plus total cost to stdout. Exit non-zero on `BudgetExceeded`,
`TurnLimitExceeded`, or `PhaseFailed`, printing the error clearly.

Resolve the default paths relative to the package, so the command works from any directory.

## tests/test_coordinator.py

**No test may make a network or API call.** Monkeypatch `query`.

Cover at least:

1. The JSON-block parser: a valid block, a missing block, and malformed JSON.
2. Each `ResultMessage.subtype` branch raises the right exception, and `success` does not.
3. An unrecognised subtype raises rather than passing.
4. The re-search gate fires when coverage is insufficient and `search_round` is 1.
5. The re-search gate does **not** fire when `search_round` has reached `MAX_SEARCH_ROUNDS`,
   even when coverage is still insufficient. This is the important one — assert the searcher
   is invoked exactly twice across the whole run, never three times.
6. The gate does not fire when coverage is sufficient.
7. Source ids stay stable across a re-search. Ids assigned in round 1 keep their values.
8. A phase where no `Agent` or `Task` invocation appears raises.

## Acceptance criteria

1. `pytest research-crew/tests/` passes, including the Task 01 tests, with no network calls.
2. `allowed_tools` includes `"Agent"`.
3. Subagent detection matches both `"Agent"` and `"Task"`.
4. `ResultMessage.subtype` is branched explicitly, with an else that raises.
5. `MAX_SEARCH_ROUNDS` bounds the loop in code. A test proves the searcher runs at most twice.
6. `max_budget_usd` is passed on every `query()` call.
7. `env` sets both `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` and `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`.
8. `record_input`, `record_output`, and `record_state` are called for every phase.
9. The citation map is built in Python and passed to the reporter.
10. No `.env` file is loaded and `python-dotenv` is not imported.
11. `coordinator.py` and `cli.py` together stay under 300 lines, excluding comments,
    docstrings, and blank lines. Comments are not capped.
12. Every module and public function has a docstring.

## Constraints

- Python 3.10+, `asyncio`, no new dependencies.
- Type-hint every public function.
- Do not write `verify.py`.
- Do not modify Task 01 modules or `agents/*.md`.

## When you are done

Reply with:

1. The files you created.
2. The exact `pytest` command and its full output.
3. Line counts excluding comments and blanks.
4. How you captured the subagent's verbatim output, and how you proved delegation happened.
5. Anything in this spec that was ambiguous or wrong.
