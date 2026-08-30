"""Coordinator: the hub of a hub-and-spoke research crew.

WHAT THIS MODULE IS
===================
Four subagents do the work of this system. None of them talks to another. Each
one is handed a single string, answers it once, and is gone. This module is the
only thing that knows all four exist, and it is therefore the only place where a
fact can travel from one of them to the next.

That shape has a name. The coordinator is the hub; the four agents are spokes.
The rule that makes it a hub-and-spoke and not a tree is that no spoke may call
another spoke, which is enforced here in one line of environment configuration
(`SUBAGENT_SPAWN_DEPTH`) rather than by asking the agents nicely.

WHY THE HUB IS CODE AND NOT A MODEL
===================================
A tempting alternative is to give one clever agent the four tools and let it
decide the order. It reads as simpler, and it is worse, because the ordering
decisions in this pipeline have exactly one correct answer each and no judgment
in them:

    * search before analysing              - there is nothing to analyse first
    * analyse before synthesising          - there are no claims to merge first
    * number the citations 1, 2, 3, ...    - counting is not an opinion
    * search at most twice                 - the budget is finite

Every one of those is a step a program takes correctly every time and a model
takes incorrectly some of the time. So the hub is a Python function. What the
hub does *not* do is anything requiring judgment: it never decides whether a
source is good, whether two claims agree, or whether coverage is sufficient. It
asks an agent, and it obeys the answer. Read the whole module through that
split, because it is the point of the exercise: **judgment goes to models,
bookkeeping stays in code.**

THE THREE FAILURES THIS MODULE IS BUILT TO MAKE LOUD
====================================================
A multi-agent pipeline fails quietly by default. Three failures matter here, and
each one gets a named exception rather than a log line, because each produces
output that *looks correct* to a reader:

  1. **Delegation did not happen.** Claude answered the question itself instead
     of calling a subagent. The reply is fluent and plausible, carries no URL it
     actually retrieved, and every architectural property this system claims -
     provenance, per-agent tooling, per-agent model choice - is gone. Nothing in
     the text says so. See `NoDelegation`.

  2. **The run stopped early and the SDK said so in a field nobody read.** See
     the long comment above the subtype branch in `run_phase`.

  3. **The re-search loop never ended.** See the comment above the gate in
     `run_research`. This one does not raise, because nothing is failing. It
     works, expensively, forever.

WHY EVERY PHASE PROMPT IS ASSEMBLED BY HAND
===========================================
A subagent receives the prompt string and nothing else. No parent conversation,
no parent system prompt, no sibling output, no memory of a previous round. This
is the property that makes the crew debuggable, and it is also why a third of
this module is string assembly: if the analyst's claims are not written into the
synthesizer's prompt, the synthesizer does not know they exist. There is no
implicit channel to fall back on. The `_*_prompt` helpers below are that
marshalling step, and the recorder writes each assembled string to disk, because
that file is not a log of the context - it *is* the context.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition, ClaudeAgentOptions, ResultMessage, TextBlock, ToolResultBlock, ToolUseBlock, query,
)

from .agents_loader import load_agents
from .observability import RunRecorder
from .state import Claim, Conflict, MergedClaim, PhaseRecord, RunState, Source
from .verify import validate_conflicts, verify_report

# ---------------------------------------------------------------------------
# Constants. Each number is a policy decision, so each one carries its reason.
# ---------------------------------------------------------------------------

# The initial search plus at most one re-search. Two, not three, because the
# second round is already the expensive half of the run: it pays for a searcher
# call and a full re-analysis of the *combined* source set. A third round costs
# more than the first two together and, in practice, adds sources the analyst
# has already told us are peripheral. The real reason the number is small is in
# the comment above the gate in `run_research`: this number is the only thing
# standing between this pipeline and an unbounded bill.
MAX_SEARCH_ROUNDS = 2

# A ceiling for one whole research run, in US dollars. It is a *run* budget, and
# what the SDK enforces is a *call* budget, so `run_research.delegate` subtracts
# the run's spend so far and hands each `query()` only the remainder. That
# conversion is the whole point, and the comment there explains what happened
# when it was missing. Three dollars is roomy for four Sonnet-and-one-Opus phases
# and tight enough that a runaway loop trips it in minutes rather than hours.
DEFAULT_MAX_BUDGET_USD = 3.0

# Our four agents may not spawn subagents of their own. Depth 1 means the
# coordinator may delegate and the delegates may not. This is what keeps the
# topology a hub-and-spoke instead of a tree: at depth 2 the analyst could spawn
# its own searcher, and a source could then enter the run without ever passing
# through `state.sources`, which breaks provenance silently. It is set as an
# environment variable, not as a prompt rule, because a prompt rule is a request
# and this is a constraint.
SUBAGENT_SPAWN_DEPTH = "1"

# At most four subagents alive at once - one per agent in the crew. This
# pipeline is strictly sequential, so the value is a guard rail rather than a
# throughput setting: it bounds what a misbehaving parent can start in parallel,
# and it bounds concurrent spend, which is the same thing measured in dollars.
MAX_CONCURRENT_SUBAGENTS = "4"

# The session-level tool allow-list, and the single most common way to break
# this architecture by omission.
#
#   "Agent"      - Claude invokes a subagent *through a tool*, and this is that
#                  tool. Leave it out and the invocation is denied or falls
#                  through to a permission callback, and Claude then answers the
#                  question itself. No error is raised. The output looks fine.
#                  `NoDelegation` exists because this failure has no other
#                  symptom.
#   "WebSearch"  - the searcher's one tool. It appears here even though the
#                  coordinator never searches, because a subagent runs *inside*
#                  this session: a tool the session forbids is not restored by
#                  granting it in the subagent's own definition.
#
# Nothing else is listed. The absent entries are the load-bearing part: no Read,
# no Write, no Bash. The coordinator owns every disk write in this system and
# does them through `RunRecorder`, so a file appearing in a run directory can
# only have come from code.
ALLOWED_TOOLS = ["Agent", "WebSearch"]

# Passed as `env`. The Python SDK *merges* this into the inherited environment
# rather than replacing it, so PATH and the ambient authentication the `claude`
# CLI relies on both survive. That merge is why it is safe to set two variables
# here and nothing else.
SUBAGENT_ENV = {
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": SUBAGENT_SPAWN_DEPTH,
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": MAX_CONCURRENT_SUBAGENTS,
}

# Claude Code v2.1.63 renamed the delegation tool from `Task` to `Agent`.
# `tool_use` blocks now carry "Agent", but `system:init` and
# `permission_denials[].tool_name` still say "Task". Detection therefore matches
# both names. Matching only the new name means that on a slightly older CLI
# every phase raises `NoDelegation` even though delegation worked perfectly;
# matching only the old name means detection never fires and `NoDelegation`
# never raises even when nothing was delegated. The second failure is the
# dangerous one, and accepting both names costs nothing.
DELEGATION_TOOL_NAMES = frozenset({"Agent", "Task"})

# One fenced block, optionally tagged `json`. Non-greedy, so two blocks in one
# reply are two matches rather than one span swallowing the text between them.
_FENCED_JSON_RE = re.compile(r"```(?:json)?[ \t]*\r?\n(.*?)```", re.DOTALL)

# The two trailers Claude Code appends to an `Agent` tool result: an `agentId:`
# resume hint, and a `<usage>` block that spans several lines.
#
# `\Z` and not `$`, which under MULTILINE would match at every line ending and
# let a `<usage>` block in the middle of a reply truncate everything after it.
# Only a *trailing* run of these is transport framing; the same characters
# elsewhere are the agent's own content. `^` under MULTILINE so the newline that
# ended the agent's last line stays with the agent's text.
_HARNESS_TRAILER_RE = re.compile(
    r"^[ \t]*(?:agentId:[ \t]*\S+[ \t]*(?:\([^)\n]*\))?|<usage>.*?</usage>)[ \t]*(?:\r?\n)*\Z", re.S | re.M)

# An opening or closing fence, used only to tell whether a candidate trailer is
# really inside a code block the agent wrote.
_FENCE_LINE_RE = re.compile(r"^[ \t]*```", re.MULTILINE)


# ---------------------------------------------------------------------------
# Exceptions
#
# One class per distinct cause, all under one base, so a caller can catch the
# family and still tell the cases apart. A single generic RuntimeError would
# force the CLI to match on message text, and would lose the distinction between
# "you ran out of money" (raise the budget) and "an agent returned nonsense"
# (fix the prompt) - two problems with completely different fixes.
# ---------------------------------------------------------------------------


class CoordinatorError(RuntimeError):
    """Base class for every way a research run can fail."""


class BudgetExceeded(CoordinatorError):
    """The SDK stopped the run because it reached `max_budget_usd`."""


class TurnLimitExceeded(CoordinatorError):
    """The SDK stopped the run because it reached its turn limit."""


class PhaseFailed(CoordinatorError):
    """A phase ended on a result subtype that is not a success."""


class NoDelegation(CoordinatorError):
    """A phase completed without ever invoking a subagent.

    Raised loudly because it is the one failure with no visible symptom: the
    coordinator answered from its own weights, the text reads well, and every
    guarantee this architecture makes is gone.
    """


class MalformedAgentReply(CoordinatorError):
    """An agent's reply held no parsable fenced JSON block.

    Carries the offending text, because the fix is always to read what the model
    actually said - which is also why `RunRecorder.record_output` stores the
    unparsed reply next to this failure.
    """


def _progress(message: str) -> None:
    """Write one progress line to stderr.

    stderr, not stdout, so a caller can pipe the machine-readable result of a
    run without a progress line landing in the middle of it.
    """
    print(message, file=sys.stderr, flush=True)


def parse_agent_json(text: str) -> dict:
    """Extract and parse the single fenced JSON block in an agent's reply.

    WHY THE CONTRACT IS A FENCED BLOCK
    ----------------------------------
    Every agent in this crew is told to answer with exactly one fenced JSON
    block and nothing else. The fence does real work at both ends. A model
    produces one reliably, because a code fence is among the most heavily
    practised structures in its training data and it needs no schema-following
    machinery. Code finds one reliably, because the delimiters are unambiguous
    and survive the leading pleasantry a model sometimes adds anyway.

    The alternative - asking a model to look at the reply and pull the data out
    - would put a model call inside the plumbing. The coordinator could then no
    longer fail loudly, because its own error handling would be a thing that can
    hallucinate. Parsing here keeps the hub deterministic.

    The last block wins when there are several: a coordinator told to reproduce
    its agent's output verbatim occasionally prefixes it with an echo of its own
    instructions, and the payload is the part at the end.

    Raises `MalformedAgentReply`, carrying the offending text, when the block is
    missing or is not valid JSON. `json.loads` and never `eval`: this string
    came from a model that read arbitrary web pages, so it is untrusted input,
    and `eval` on untrusted input executes it.
    """
    blocks = _FENCED_JSON_RE.findall(text)
    if not blocks:
        raise MalformedAgentReply(f"no fenced JSON block in agent reply:\n{text}")
    try:
        parsed = json.loads(blocks[-1])
    except json.JSONDecodeError as exc:
        raise MalformedAgentReply(f"fenced block is not valid JSON ({exc}):\n{text}") from exc
    if not isinstance(parsed, dict):
        raise MalformedAgentReply(f"fenced block is not a JSON object:\n{text}")
    return parsed


def _tool_result_text(block: ToolResultBlock) -> str:
    """Flatten an `Agent` tool result into the subagent's final message text.

    `ToolResultBlock.content` is `str | list[dict] | None`, so all three shapes
    are handled here rather than at the call site.
    """
    content = block.content
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return "\n".join(str(part.get("text", "")) for part in content if isinstance(part, dict))


def strip_harness_trailers(text: str) -> str:
    """Remove Claude Code's own trailers from the end of an `Agent` tool result.

    WHY THIS FUNCTION HAD TO BE WRITTEN
    -----------------------------------
    `run_phase` reads the tool-result block verbatim, and verbatim is the right
    instinct: it is the one place the subagent's bytes exist without having gone
    through the parent's generation step. But the block is not only the agent's
    reply. The harness appends its own framing to it - an `agentId:` line so the
    agent can be resumed, and a `<usage>` block of token counts - and a verbatim
    read copies the framing as faithfully as it copies the payload.

    In run 20260830-152235 that framing reached `report.md`, four lines of it, at
    the bottom of the References section. The citation verifier caught all four
    as malformed References lines and the artifact was corrupted anyway, because
    a verifier reports and a report is already written by the time it runs.

    The lesson generalises past this SDK: reading raw bytes off a channel does
    not mean every byte on that channel is payload. A transport that adds framing
    needs the framing removed at the point of reading, once, in a named place -
    not guessed at by each downstream consumer.

    WHAT IT WILL NOT TOUCH
    ----------------------
    Only a trailing run of trailers, and only outside a fenced code block. An
    agent that quotes an `agentId:` line inside triple backticks - which a
    searcher summarising harness output could legitimately do - keeps it. When a
    result carries neither trailer it is returned byte for byte.
    """
    # Looped, because the two trailers arrive together and removing the last one
    # exposes the one before it. It stops as soon as the tail is clean.
    while True:
        match = _HARNESS_TRAILER_RE.search(text)
        # An odd number of fences before the match means the match opened inside
        # a code block the agent wrote, so it is content and the text is done.
        if match is None or len(_FENCE_LINE_RE.findall(text, 0, match.start())) % 2:
            return text
        text = text[: match.start()]


def _delegation_header(agent_name: str) -> str:
    """Build the instruction that opens every phase prompt.

    Two jobs in five lines.

    It names the agent, because `allowed_tools` makes delegation *possible* and
    this line makes it *happen*. And it demands a verbatim reproduction, which
    is the prompt-side half of the defence described in `run_phase`: the parent
    receives the subagent's final message as the Agent tool result but *may
    summarise it in its own response*, and a summarised JSON block is not JSON.
    """
    return (
        f"Use the `{agent_name}` agent to carry out the task below. Do not carry it out\n"
        f"yourself, and do not answer from your own knowledge.\n"
        f"Then reproduce the `{agent_name}` agent's output exactly as it returned it.\n"
        f"Add no commentary, no summary, no preamble, and no closing remark. Its reply is\n"
        f"a fenced JSON block that a program parses, so any edit to it breaks the caller."
    )


async def run_phase(
    *,
    agent_name: str,
    phase: str,
    prompt: str,
    state: RunState,
    recorder: RunRecorder,
    seq: int,
    agents: dict[str, AgentDefinition],
    max_budget_usd: float,
) -> str:
    """Run one delegated phase and return the subagent's verbatim reply.

    Every phase in the pipeline goes through this one function, which is what
    makes the guarantees below properties of the *system* rather than of four
    separately written call sites: recorded input, recorded output, a recorded
    `PhaseRecord`, proven delegation, and an explicitly branched terminal
    subtype. The state snapshot is the caller's, for the reason given at the
    bottom of this function.
    """
    # The input file is written before the call, and it holds the entire prompt.
    # This is not a log line. The subagent sees this string and nothing else, so
    # this file is a complete record of the context that produced the output
    # beside it. Truncating the prompt here would destroy the one property that
    # makes debugging a bisection: "is the wrong fact already in the input?"
    recorder.record_input(seq, agent_name, {
        "seq": seq, "phase": phase, "agent": agent_name, "search_round": state.search_round,
        "allowed_tools": ALLOWED_TOOLS, "max_budget_usd": max_budget_usd, "env": SUBAGENT_ENV,
        "prompt": prompt,
    })
    _progress(f"[{seq:02d}] {phase} -> {agent_name} agent")
    started = time.monotonic()

    # Delegation evidence, collected as the stream arrives.
    delegated_tool_use_ids: set[str] = set()
    subagent_text: str | None = None
    parent_text: list[str] = []
    result: ResultMessage | None = None

    options = ClaudeAgentOptions(
        agents=agents, allowed_tools=ALLOWED_TOOLS, max_budget_usd=max_budget_usd, env=SUBAGENT_ENV,
    )
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message
            continue
        content = getattr(message, "content", None)
        if not isinstance(content, list):
            # A SystemMessage carries `data`, not `content`. Nothing to read.
            continue
        for block in content:
            if isinstance(block, ToolUseBlock) and block.name in DELEGATION_TOOL_NAMES:
                # Proof that a subagent was actually invoked. Recorded as an id
                # rather than a boolean, so the matching result block below can
                # be identified as *this* delegation's output.
                delegated_tool_use_ids.add(block.id)
            elif isinstance(block, ToolResultBlock) and block.tool_use_id in delegated_tool_use_ids:
                # THE VERBATIM CAPTURE. This block is the subagent's actual
                # final message, moved by the SDK. It has not passed through the
                # parent's generation step, so it is bytes rather than a
                # paraphrase. Preferring it over the parent's own text is the
                # structural half of the defence; the prompt instruction in
                # `_delegation_header` is the behavioural half. Both are needed:
                # the prompt cannot be trusted, because a model decides whether
                # to obey it, and the block cannot be assumed, because the
                # message shape is the SDK's to change.
                #
                # Stripped, because the block carries the harness's own trailers
                # as well as the agent's reply and a verbatim read copies both.
                # See `strip_harness_trailers`.
                subagent_text = strip_harness_trailers(_tool_result_text(block)) or subagent_text
            elif isinstance(block, TextBlock) and getattr(message, "parent_tool_use_id", None) is None:
                # Text from the parent itself. Messages produced *inside* a
                # subagent carry a `parent_tool_use_id`, so filtering on its
                # absence keeps the subagent's own narration out of the fallback
                # and leaves only what the coordinator said in its own voice.
                parent_text.append(block.text)

    duration_s = time.monotonic() - started
    if result is None:
        raise PhaseFailed(f"phase {phase!r} ({agent_name}): the stream ended with no ResultMessage")

    # -----------------------------------------------------------------------
    # THE TERMINAL SUBTYPE, BRANCHED EXPLICITLY, WITH AN ELSE THAT RAISES.
    #
    # This is the most important branch in the module. `ResultMessage` arrives
    # whether the run finished or was cut off, and the difference lives entirely
    # in `subtype`. A phase that hit the budget ceiling mid-sentence still
    # yields a well-formed message object; what it does not yield is a complete
    # answer.
    #
    # The failure mode being prevented is not "an error was ignored". It is
    # worse than that. Treating an unrecognised subtype as success sends a
    # truncated or empty result downstream, where it is marshalled into the next
    # agent's prompt and read as fact. The pipeline then completes, produces a
    # report, and the report is short by whatever the cut-off removed - with
    # nothing anywhere saying so. A run that stopped early and a run that
    # finished are told apart here or they are never told apart at all.
    #
    # Hence the `else` that raises. "Not an error I happened to name" is not a
    # synonym for "success"; it is the set of outcomes this code has never seen,
    # which is exactly the set that deserves a stop. This is the SDK-level form
    # of the rule in `.claude/rules/agentic-loop-stop-reason.md`, which says the
    # same thing one layer down about `stop_reason` in a manual tool-use loop.
    #
    # The subtype is checked before the delegation check on purpose. When the
    # budget runs out before the Agent tool is ever called, both conditions hold
    # and only one of them is the cause. Reporting `NoDelegation` there would
    # name the symptom and send the reader to inspect `allowed_tools` instead of
    # their budget.
    # -----------------------------------------------------------------------
    subtype = result.subtype
    if subtype == "success":
        pass
    elif subtype == "error_max_budget_usd":
        # `max_budget_usd` is what was left of the *run's* budget when this phase
        # started - see `run_research.delegate`. So this now reads "the phase
        # exhausted the remainder", which is the run-level failure the caller
        # wants named, rather than "one call went over a ceiling six calls share".
        raise BudgetExceeded(f"phase {phase!r} ({agent_name}) hit the ${max_budget_usd:.2f} remaining budget; "
                             f"the SDK reported ${result.total_cost_usd or 0.0:.4f} spent")
    elif subtype == "error_max_turns":
        raise TurnLimitExceeded(f"phase {phase!r} ({agent_name}) hit the SDK turn limit")
    else:
        raise PhaseFailed(f"phase {phase!r} ({agent_name}) ended on unhandled result subtype {subtype!r}")

    if not delegated_tool_use_ids:
        raise NoDelegation(f"phase {phase!r}: no Agent/Task tool use appeared, so the {agent_name!r} agent "
                           f"never ran and the coordinator answered from its own weights")

    text = subagent_text if subagent_text else "\n".join(parent_text).strip()
    if not text:
        raise PhaseFailed(f"phase {phase!r} ({agent_name}) produced no text at all")

    state.phases.append(PhaseRecord(phase=phase, agent=agent_name, round=state.search_round,
                                    cost_usd=result.total_cost_usd, duration_s=duration_s, subtype=subtype))
    recorder.record_output(seq, agent_name, text)
    # No `record_state` here, and that omission is deliberate. The parsed payload
    # is folded into `RunState` by the caller, *after* this function returns, so
    # a snapshot written on this line would be the state before this phase
    # contributed anything - a file named after a phase whose result it does not
    # contain. The caller writes it instead, immediately after each fold. See
    # `run_research`, where the invariant is stated.
    #
    # `record_input`, `record_output` and the `PhaseRecord` append stay here.
    # They record what this function alone knows: the exact prompt sent, the
    # exact text returned, and the cost, duration and subtype off the
    # `ResultMessage`. None of those survive the return.
    return text


# ---------------------------------------------------------------------------
# Prompt assembly. Marshalling, not judgment - see the module docstring.
# ---------------------------------------------------------------------------


def _sections(*parts: str) -> str:
    """Join prompt sections with a blank line between them."""
    return "\n\n".join(part for part in parts if part)


def _fence(rows: list) -> str:
    """Render a list of payload dataclasses as one fenced JSON block."""
    return "```json\n" + json.dumps([asdict(r) for r in rows], indent=2, ensure_ascii=False) + "\n```"


def derive_queries(question: str) -> list[str]:
    """Turn a research question into 3-5 search queries, in Python.

    Deliberately mechanical, and deliberately not a model call. Asking a model
    to expand a question into queries would add a fifth billable phase, a fifth
    chance to drift off the question, and a step whose output nobody can
    predict, all to produce four strings a template produces for free. A model
    call is worth its price when there is judgment to buy. There is none here.
    """
    core = " ".join(question.split()).rstrip("?").strip()
    return [core, f"{core} evidence study data", f"{core} criticism limitations", f"{core} 2026 latest"]


def queries_from_gaps(question: str, gaps: list[str]) -> list[str]:
    """Turn the analyst's named coverage gaps into re-search queries.

    The gaps are the whole reason a second round is being paid for, so they, and
    not the original question, drive it. Repeating round one's queries would
    spend the single retry the budget allows on the sources we already have.
    Falls back to the original queries only when the analyst called coverage
    insufficient without naming a single gap.
    """
    queries = [" ".join(g.split()).strip() for g in gaps if g and g.strip()]
    return queries[:5] if queries else derive_queries(question)


def _search_prompt(question: str, queries: list[str]) -> str:
    """Assemble the searcher's prompt: the question plus an explicit query list."""
    listed = "\n".join(f"{i}. {q}" for i, q in enumerate(queries, start=1))
    return _sections(_delegation_header("searcher"), "## Research question", question,
                     "## Run exactly these queries, one search each", listed,
                     "Return one fenced JSON block in the shape your instructions define.")


def _analyse_prompt(question: str, sources: list[Source]) -> str:
    """Assemble the analyst's prompt: the question plus every source, in full.

    The analyst has no tools. It cannot fetch a page, re-run a search, or look
    anything up. Whatever is absent from this string does not exist for it, so
    this function writes out every source's id, url, title and snippet rather
    than a selection. A source omitted here is a source that silently cannot be
    cited later.
    """
    listed = "\n\n".join(f"[{s.id}] {s.title}\n    url: {s.url}\n    query: {s.query}\n    snippet: {s.snippet}"
                         for s in sources)
    return _sections(_delegation_header("analyst"), "## Research question", question,
                     "## Sources\n\nUse these source ids exactly. Do not renumber them.", listed,
                     "Return one fenced JSON block with `claims` and `coverage`.")


def _synthesise_prompt(question: str, claims: list[Claim]) -> str:
    """Assemble the synthesizer's prompt: the question plus the claims as JSON."""
    return _sections(_delegation_header("synthesizer"), "## Research question", question,
                     "## Claims extracted by the analyst", _fence(claims),
                     "Return one fenced JSON block with `merged_claims`, `conflicts` and `summary`.")


def _report_prompt(state: RunState) -> str:
    """Assemble the reporter's prompt, including the fixed citation map.

    WHY THE COORDINATOR OWNS THE NUMBERING
    --------------------------------------
    The citation numbers are computed here, in Python, from
    `state.citation_map()`, and handed to the reporter as a finished table it
    may not change.

    Numbering is counting. There is no judgment in it, nothing a model knows
    that the code does not, and therefore nothing to buy by delegating it. What
    delegating it costs is the worst failure this system can produce. A model
    that renumbers - drops a source it judges weak, sorts the references
    alphabetically, starts at zero - emits a report that is well-formed, fluent,
    correctly structured, and in which every citation points one row off. There
    is no error. The prose reads as authoritative. The only reader who finds out
    is the one who follows a link, and by then the report has been believed.

    The reporter still needs judgment for grouping, wording and structure. It
    just does not need any for arithmetic.
    """
    table = "\n".join(f"[{n}] {s.title} - {s.url}" for n, s in sorted(state.citation_map().items()))
    gaps = "\n".join(f"- {g}" for g in state.coverage_gaps) or "- None reported."
    return _sections(_delegation_header("reporter"), "## Research question", state.question,
                     "## Citation map - fixed. Use these numbers exactly and renumber nothing.", table,
                     "## Merged claims", _fence(state.merged_claims),
                     "## Conflicts", _fence(state.conflicts),
                     "## Coverage gaps for the Limitations section", gaps,
                     "Return the report as Markdown, in the section order your instructions define.")


# ---------------------------------------------------------------------------
# Folding an agent's payload back into the run state.
# ---------------------------------------------------------------------------


def _append_sources(state: RunState, payload: dict, queries: list[str]) -> None:
    """Fold a searcher payload into `state.sources`, assigning ids in Python.

    The id the searcher put in its own JSON is discarded. It has to be: on a
    re-search the agent starts counting at 1 again, because it never saw round
    one and cannot know what is already numbered. Assigning ids here, from the
    highest id already in state, is what keeps round one's citations pointing at
    round one's sources. Nothing is ever renumbered, because a number already
    written into a recorded state snapshot is a number a reader may already have
    followed.
    """
    next_id = max((s.id for s in state.sources), default=0) + 1
    fallback_query = queries[0] if queries else ""
    for raw in payload.get("sources", []):
        state.sources.append(Source(id=next_id, url=str(raw.get("url", "")), title=str(raw.get("title", "")),
                                    snippet=str(raw.get("snippet", "")),
                                    query=str(raw.get("query", fallback_query))))
        next_id += 1


def _apply_analysis(state: RunState, payload: dict) -> None:
    """Replace `state.claims` and the coverage verdict from an analyst payload.

    Replace rather than append. After a re-search the analyst has seen the
    *combined* source set, so its new claim list supersedes the old one; keeping
    both would duplicate every claim the second pass re-extracted.
    """
    state.claims = [
        Claim(id=str(r.get("id", "")), text=str(r.get("text", "")), source_id=int(r.get("source_id", 0)),
              evidence=str(r.get("evidence", "")), confidence=str(r.get("confidence", "")))
        for r in payload.get("claims", [])
    ]
    coverage = payload.get("coverage") or {}
    state.coverage_sufficient = bool(coverage.get("sufficient", False))
    state.coverage_gaps = [str(g) for g in coverage.get("gaps", [])]


def _apply_synthesis(state: RunState, payload: dict) -> None:
    """Fold a synthesizer payload into `state.merged_claims` and `state.conflicts`.

    Conflicts are stored, never resolved. A disagreement between sources is a
    finding, and the reporter is required to print it; averaging it away here
    would delete the most useful thing the run produced.
    """
    state.merged_claims = [
        MergedClaim(id=str(r.get("id", "")), text=str(r.get("text", "")), support=str(r.get("support", "")),
                    source_ids=[int(i) for i in r.get("source_ids", [])])
        for r in payload.get("merged_claims", [])
    ]
    state.conflicts = [
        Conflict(id=str(r.get("id", "")), topic=str(r.get("topic", "")), kind=str(r.get("kind", "")),
                 position_a=dict(r.get("position_a") or {}), position_b=dict(r.get("position_b") or {}),
                 explanation=str(r.get("explanation", "")))
        for r in payload.get("conflicts", [])
    ]


async def run_research(
    question: str,
    *,
    agents_dir: Path,
    runs_root: Path,
    max_budget_usd: float = DEFAULT_MAX_BUDGET_USD,
) -> RunState:
    """Run the full four-phase pipeline and return the finished `RunState`.

    Phases run in a fixed order - search, analyse, synthesise, report - with one
    optional bounded re-search between the second and the third. The order is
    fixed in code because it is not a decision (see the module docstring).
    """
    agents = load_agents(Path(agents_dir))
    state = RunState.new(question)
    recorder = RunRecorder(Path(runs_root), state.run_id)

    # A single counter, incremented per phase in execution order, so a run with
    # a re-search still reads top to bottom on disk: the re-search is 03 and 04,
    # and synthesis is 05 rather than colliding with the first analysis. The
    # phase name goes in each filename too, so a file says which of the two
    # searches it is without the reader having to count.
    seq = 1

    async def delegate(agent_name: str, phase: str, prompt: str) -> str:
        """Run one phase at the current sequence number, then advance it.

        A thin wrapper over `run_phase`, holding the arguments that are the same
        for every phase of a run. It exists so that each call site below reads as
        the pipeline step it is, and so the sequence number cannot be advanced in
        one branch and forgotten in another.

        THE BUDGET IS CONVERTED FROM PER-CALL TO PER-RUN HERE
        ----------------------------------------------------
        `ClaudeAgentOptions.max_budget_usd` bounds one `query()`. It has to: the
        SDK sees one call and cannot know a pipeline is wrapped around it. This
        function passed the same ceiling to all six phases of run
        20260830-152235, so the cap reset on each one. The phases cost $0.78,
        $0.59, $0.60, $0.97, $0.85 and $0.82 - not one of them approached $3.00
        alone, the SDK never fired, every phase reported `subtype: "success"`,
        and the run spent $4.59 against a stated ceiling of $3.00. The real
        bound was 6 x $3.00.

        That is worse than having no cap at all. A run with no ceiling is
        obviously unbounded and gets watched. A run displaying `max_budget_usd:
        3.0` in its cost artifact looks bounded, and the number is a lie that
        nobody checks until the invoice arrives. **A limit enforced at the wrong
        scope is indistinguishable from a limit enforced at the right one, right
        up to the moment it matters.**

        The fix is two lines and neither of them is in the SDK. Subtract what the
        run has already spent, refuse to start a phase with nothing left, and
        hand the *remainder* to `query()` so the SDK's own enforcement stays
        armed and now guards the run instead of one call. This is the same shape
        as `MAX_SEARCH_ROUNDS` above: the component that knows the pipeline has
        six calls in it is the application layer, so the application layer is
        where the pipeline-wide bound has to live.
        """
        nonlocal seq
        if (remaining := max_budget_usd - state.total_cost_usd()) <= 0:
            raise BudgetExceeded(f"phase {phase!r} ({agent_name}) not started: the ${max_budget_usd:.2f} run "
                                 f"budget is spent (${state.total_cost_usd():.4f} already)")
        text = await run_phase(agent_name=agent_name, phase=phase, prompt=prompt, state=state,
                               recorder=recorder, seq=seq, agents=agents, max_budget_usd=remaining)
        seq += 1
        return text

    def snapshot() -> None:
        """Write `state-after-NN-<phase>.json` for the phase that just finished.

        THE INVARIANT: the file named after a phase is the run state **including**
        that phase's parsed result. Called after each fold below, never inside
        `run_phase`, because the fold happens out here.

        Both arguments are read back out of what the finished phase already left
        behind - `seq - 1` because `delegate` has advanced the counter, and the
        phase name off the `PhaseRecord` that `run_phase` appended - so a call
        site cannot name the file after the wrong phase. Filenames and numbering
        are unchanged; only the moment of writing moved.
        """
        recorder.record_state(seq - 1, state.phases[-1].phase, state.to_json())

    # ---- Phase 1: search --------------------------------------------------
    queries = derive_queries(question)
    reply = await delegate("searcher", "search", _search_prompt(question, queries))
    _append_sources(state, parse_agent_json(reply), queries)
    snapshot()

    # ---- Phase 2: analyse -------------------------------------------------
    reply = await delegate("analyst", "analyze", _analyse_prompt(question, state.sources))
    _apply_analysis(state, parse_agent_json(reply))
    snapshot()

    # -----------------------------------------------------------------------
    # THE BOUNDED RE-SEARCH GATE
    #
    # The analyst reports whether the sources answer the question. When they do
    # not, one more search round is worth paying for. The bound is the whole
    # design of this block, and it is a `while` with a counter rather than a
    # sentence in a prompt.
    #
    # WHY AN UNBOUNDED VERSION IS DANGEROUS
    # The component judging sufficiency is the same *kind* of component that
    # produces the work. A model that is never satisfied - because the question
    # is genuinely hard, or because "be thorough" reads to it as "ask again" -
    # answers `sufficient: false` on round three exactly as readily as on round
    # one. Each iteration is a searcher call plus a full re-analysis of a source
    # set that grew, so the rounds get *more* expensive as they go.
    #
    # And nothing raises. No exception, no timeout, no error subtype, no
    # degraded output. The pipeline is working - doing precisely what it was
    # built to do, correctly, forever, at a few cents a turn, until somebody
    # notices the bill. That is why the stopping condition cannot be delegated
    # to the same component whose dissatisfaction is what continues the loop.
    # `MAX_SEARCH_ROUNDS` is enforced here, in the loop header, where no model
    # can reach it.
    #
    # `is False` and not `not ...`: `coverage_sufficient` is None until the
    # analyst reports, and "not yet known" must never spend the retry.
    # -----------------------------------------------------------------------
    while state.coverage_sufficient is False and state.search_round < MAX_SEARCH_ROUNDS:
        state.search_round += 1
        gap_queries = queries_from_gaps(question, state.coverage_gaps)
        # Appended, never renumbered: round one's ids keep their values.
        reply = await delegate("searcher", "search", _search_prompt(question, gap_queries))
        _append_sources(state, parse_agent_json(reply), gap_queries)
        snapshot()
        # Re-analysed over the *combined* set, so the synthesizer receives one
        # claim list drawn from every source rather than two it must reconcile.
        reply = await delegate("analyst", "analyze", _analyse_prompt(question, state.sources))
        _apply_analysis(state, parse_agent_json(reply))
        snapshot()

    # ---- Phase 3: synthesise ----------------------------------------------
    reply = await delegate("synthesizer", "synthesize", _synthesise_prompt(question, state.claims))
    _apply_synthesis(state, parse_agent_json(reply))
    snapshot()

    # ---- Phase 4: report --------------------------------------------------
    # The reporter returns Markdown, not JSON, so its reply is stored whole. It
    # is the only phase whose output is the deliverable rather than an input to
    # the next phase, which is why it is the only one that is not parsed.
    state.report_md = await delegate("reporter", "report", _report_prompt(state))
    # The fold for this phase is the assignment on the line above, so the
    # snapshot still comes after it and `state-after-06-report.json` carries the
    # report rather than a null.
    snapshot()

    recorder.record_report(state.report_md)

    # ---- Phase 5, and no model runs in it ---------------------------------
    #
    # WHY THIS RUNS AFTER THE REPORT IS ALREADY ON DISK
    # `record_report` above is deliberately the line before this block. A failed
    # verification must not be able to stop the report reaching the run
    # directory: the report of a run that failed its citation check is the most
    # informative artifact that run produced, and deleting it would leave the
    # reader with a verdict and no way to see what provoked it. So this block
    # never raises and never unwinds anything. It writes a second artifact
    # beside the first and lets the CLI decide the exit code.
    #
    # WHY THE VERIFIER IS NOT AN AGENT
    # Every other phase in this pipeline asks a model, because every other phase
    # needs judgment. This one needs none: "does this URL string appear in the
    # source set" has one correct answer and no opinion in it. Handing it to a
    # model would make the last line of defence subject to the same failure mode
    # it exists to catch. See the split stated in the module docstring -
    # judgment to models, bookkeeping to code.
    # The citation map is passed as well as the source list. The two answer
    # different questions - "was this URL collected at all" and "was it collected
    # under *this* number" - and only the second one catches a renumbering.
    citation_report = verify_report(state.report_md, state.sources, state.citation_map())
    conflict_problems = validate_conflicts(state.conflicts, state.citation_map())
    # A direct write rather than a new `RunRecorder` method, because
    # `observability.py` is out of scope for this task. It lands in the same
    # directory as the report and its evidence, so a reader who doubts the
    # verdict has both one file away.
    (recorder.run_dir / "citation-report.json").write_text(
        json.dumps({"run_id": state.run_id, "ok": citation_report.ok and not conflict_problems,
                    "citations": asdict(citation_report), "conflict_problems": conflict_problems},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    # Attached to the returned state rather than added as a `RunState` field:
    # `state.py` is fixed for this task, and changing the return type of
    # `run_research` would break every existing caller for the sake of one
    # value. `RunState` is a plain (unfrozen) dataclass, so an added attribute
    # costs nothing and is invisible to `to_dict()` - which is correct, because
    # the verdict is an artifact *about* a run rather than part of its state.
    state.citation_report = citation_report  # type: ignore[attr-defined]
    state.conflict_problems = conflict_problems  # type: ignore[attr-defined]

    # Cost is a separate artifact because it answers a different question from
    # the rest of the directory: not "is this report right" but "what did this
    # architecture cost". The per-phase breakdown is the evidence for the claim
    # that splitting the work pays - only the synthesize row runs on Opus.
    recorder.record_cost({
        "run_id": state.run_id, "question": state.question, "search_rounds": state.search_round,
        "max_budget_usd": max_budget_usd, "phases": [asdict(p) for p in state.phases],
        "total_cost_usd": state.total_cost_usd(),
    })
    return state
