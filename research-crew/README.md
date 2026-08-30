# research-crew

A CLI that takes a research question and produces a cited Markdown report. A coordinator
delegates to four specialised subagents through the Claude Agent SDK.

It is a **teaching artifact** for the Claude Certified Architect exam, Domain 1 (agent
architecture and orchestration). The code works, but the comments are the product. Read
`agents/*.md` and `DECISIONS.md` before you read the Python.

```bash
cd research-crew
pip install -r requirements.txt
PYTHONPATH=src python -m research_crew.cli "Do multi-agent LLM systems outperform single-agent systems?"
```

`PYTHONPATH=src` is required. The package lives under `src/` and there is no `pyproject.toml`,
because the task specs that built this listed the exact files to create and adding one would
have broken that constraint. An editable install would be the normal fix in a real project.

It needs a working, authenticated `claude` CLI on the PATH — the SDK drives it. This project
deliberately loads **no** `.env` file: `projects/claudecertificationguide/.env` in this
repository points `ANTHROPIC_BASE_URL` at a gateway that does not serve this API, and picking
it up would silently misroute every call.

## Source documentation

Verified against the live docs while building this, not recalled from memory. Two facts
here surprise people, so both are called out.

| Topic | URL |
|---|---|
| Subagents in the SDK | https://code.claude.com/docs/en/agent-sdk/subagents |
| Python SDK reference | https://code.claude.com/docs/en/agent-sdk/python |
| Subagent files, built-ins, nesting | https://code.claude.com/docs/en/sub-agents |
| Agent loop, turns and budget | https://code.claude.com/docs/en/agent-sdk/agent-loop |
| Environment variables (the caps) | https://code.claude.com/docs/en/env-vars |
| Managed Agents — the road not taken | https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration.md |

**The Agent SDK docs moved hosts.** They are on `code.claude.com`, not `platform.claude.com`.
The API docs site map contains no Agent SDK section at all. Its multi-agent story is
**Managed Agents**, a separate server-hosted product. Conflating the two is the most common
way to end up coding against an API that does not exist. `DECISIONS.md` ADR-002 compares them.

**`Task` was renamed to `Agent`** in Claude Code v2.1.63. Current SDKs emit `"Agent"` in
`tool_use` blocks, but still say `"Task"` in the `system:init` tool list and in
`result.permission_denials[].tool_name`. Detection code must match both. Study material
written before that rename will show you `Task`.

## Architecture

```
                                 ┌──────────────────────────────────────┐
   question ──▶ cli.py ─────────▶│          coordinator.py              │
                                 │  owns: sequence, RunState, budget    │
                                 │  the ONLY component that sees        │
                                 │  the whole run                       │
                                 └───┬───────────┬────────┬─────────┬───┘
             one prompt string ──────┘           │        │         │
             one final message ◀─────┐           │        │         │
                                 ┌───▼───┐  ┌────▼───┐ ┌──▼─────┐ ┌─▼──────┐
                                 │searcher│  │analyst │ │synthes.│ │reporter│
                                 │        │  │        │ │        │ │        │
                    tools:       │WebSearch│  │  none  │ │  none  │ │  none  │
                    model:       │ sonnet │  │ sonnet │ │  opus  │ │ sonnet │
                                 └────────┘  └────────┘ └────────┘ └────────┘
                                  ╎ separate context window each, no shared memory ╎

   coordinator ──▶ verify.py (pure Python, no model) ──▶ report.md + runs/<id>/
```

Each dashed box is a **separate context window**. They cannot see each other, and they
cannot see the coordinator's reasoning.

### What actually crosses a boundary

This is the fact the whole design rests on. From the subagents documentation:

> The only content you pass from parent to subagent is the Agent tool's prompt string, so
> include any file paths, error messages, or decisions the subagent needs directly in that
> prompt.

So the channel is **one string in, one string out**:

| The subagent receives | The subagent does not receive |
|---|---|
| its own system prompt (`AgentDefinition.prompt`) | the parent's conversation history |
| the `Agent` tool's prompt string | the parent's tool results |
| project `CLAUDE.md`, if `settingSources` loads it | the parent's system prompt |
| its tool definitions (the subset in `tools`) | any sibling agent's output |

The parent gets back **only the subagent's final message**. Every intermediate tool call and
result stays inside the subagent and never reaches the coordinator's context.

This is why `coordinator.py` marshals state by hand. It reads `RunState`, formats the next
prompt string, and sends it. There is no "pass the context along" shortcut, because there is
no shared context to pass.

### Two tool gates, and a tool needs both

Easy to conflate, and conflating them produces a system that looks like it works.

| Gate | Scope | Question it answers |
|---|---|---|
| `AgentDefinition.tools` | one agent | which tools does *this* agent have at all? |
| `ClaudeAgentOptions.allowed_tools` | the whole session | which tool calls are auto-approved? |

`tools` **narrows**. `allowed_tools` **admits**. A tool must clear both gates to be usable.

Two consequences fall out, and both are easy to get wrong:

- **`"WebSearch"` must be in `allowed_tools` even though the coordinator never searches.** The
  searcher subagent runs inside that same session, so its one granted tool has to be permitted
  at session level too.
- **`"Agent"` must be in `allowed_tools` or delegation does not happen.** Claude invokes a
  subagent *through* the `Agent` tool. Leave it out and the call falls through to a permission
  callback or is denied, and Claude simply answers the question itself. No error is raised.
  The hub-and-spoke design collapses into one prompt and the only symptom is a worse report.
  `coordinator.py` therefore raises `NoDelegation` when a phase completes with no `Agent` or
  `Task` tool use — a silent architectural failure made loud.

## One run, in sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant CLI as cli.py
    participant Coord as coordinator.py
    participant Rec as runs/&lt;id&gt;/
    participant Sea as searcher<br/>tools: WebSearch
    participant Ana as analyst<br/>tools: none
    participant Syn as synthesizer<br/>tools: none
    participant Rep as reporter<br/>tools: none
    participant Ver as verify.py

    User->>CLI: research question
    CLI->>Coord: RunState.new(question)

    rect rgb(238, 246, 255)
    note over Coord,Sea: Phase 1 — collect evidence (round 1)
    Coord->>Rec: 01-searcher.input.json
    Coord->>Sea: Agent tool prompt: question + queries
    Sea-->>Sea: WebSearch (tool calls stay inside)
    Sea->>Coord: final message only — sources + URLs
    Coord->>Rec: 01-searcher.output.md, state-after-01
    end

    rect rgb(238, 255, 242)
    note over Coord,Ana: Phase 2 — extract claims
    Coord->>Ana: sources marshalled from RunState
    Ana->>Coord: claims + coverage verdict
    Coord->>Rec: 02-analyst.*, state-after-02
    end

    alt coverage insufficient AND search_round < 2
        note over Coord,Sea: Bounded re-search — fires at most ONCE
        Coord->>Sea: gap-targeted queries (round 2)
        Sea->>Coord: additional sources
        Coord->>Ana: re-analyse combined set
        Ana->>Coord: updated claims
    else coverage sufficient OR retry already used
        note over Coord: proceed — no further searching
    end

    rect rgb(255, 248, 235)
    note over Coord,Syn: Phase 3 — merge and flag conflicts
    Coord->>Syn: claims marshalled from RunState
    Syn->>Coord: merged claims + explicit conflicts
    Coord->>Rec: 03-synthesizer.*, state-after-03
    end

    rect rgb(252, 240, 255)
    note over Coord,Rep: Phase 4 — format (cannot search)
    Coord->>Rep: merged claims + FIXED citation map
    Rep->>Coord: Markdown with [n] + References
    Coord->>Rec: 04-reporter.*, state-after-04
    end

    Coord->>Ver: report + collected source set
    Ver->>Coord: CitationReport (no model involved)
    Coord->>Rec: report.md, cost.json
    Coord->>User: report + citation verdict
```

## Why multi-agent instead of one big prompt?

The honest answer first: **for a task this size, one big prompt would probably work, and it
would be cheaper and faster.** Anyone who tells you multi-agent is free is selling something.
Here is the real ledger.

### Cost — worse

Multi-agent **increases** token cost for this task. One prompt is one call. We make at least
five, and explicit invocation (ADR-003) adds a router turn to each. The four agent system
prompts are re-sent every phase.

Measured, from run `20260830-152235` (the demo question, with the re-search round firing):

| Phase | Agent | Model | Cost | Duration |
|---|---|---|---|---|
| 1 search | searcher | sonnet | $0.779 | 112s |
| 2 analyse | analyst | sonnet | $0.586 | 93s |
| 3 search (re-search) | searcher | sonnet | $0.598 | 118s |
| 4 analyse (re-run) | analyst | sonnet | $0.968 | 216s |
| 5 synthesise | synthesizer | **opus** | $0.848 | 162s |
| 6 report | reporter | sonnet | $0.816 | 167s |
| | | | **$4.59** | **868s (14.5 min)** |

$4.59 and fifteen minutes for one research question. Budget accordingly, and note that the
re-search round is a third of the cost.

One genuine saving pushes back: **per-agent model selection**. Only the synthesizer runs
Opus, because conflict resolution is the only phase needing that judgment. Searching,
extracting, and formatting run Sonnet. A single prompt has one model for the whole task, so
it must run everything at the strongest model any part requires — here, Opus for all six
phases. Whether that saving covers the extra calls depends on the run, so measure it in
`runs/<id>/cost.json` rather than assume it.

### Latency — worse, and we get none of the usual mitigation

Our four phases run **strictly in series**. The analyst needs the searcher's output; the
reporter needs the synthesizer's. Total latency is the sum of every phase plus router hops,
against one round trip for a single prompt. The table above shows what that costs: **868
seconds, every one of them sequential.**

Parallelism is the standard answer to this, and it does not apply. It pays when subtasks are
independent — three reviewers reading the same diff finish in the time of the slowest. A
research pipeline is a dependency chain. We pay the full latency cost of splitting and
collect none of the parallelism benefit. That is a real loss, and it is the price of the
three wins below.

### Context isolation — genuinely better

This is the first real win. The searcher may pull twenty sources with long verbatim snippets.
In a single prompt, all of that stays in the context window for the rest of the task, and the
model is still carrying raw search noise while it formats the final Markdown. Long contexts
degrade attention and cost tokens on every subsequent turn.

With subagents, only the final message crosses. The reporter's context holds merged claims
and a citation map — nothing else. It never sees a search result. Each agent works in a
context sized to its own job.

### Debuggability — genuinely better

The second real win, and the one you feel at 2am. A bad citation in the report is one
question: **which phase introduced it?** Open `runs/<id>/` and bisect. See the walkthrough
below. In a single prompt, the whole task is one opaque call. There is no intermediate state
to inspect, because none was ever written down.

### Enforceability — the argument that actually justifies the split

The third win, and the most underrated. **You cannot give different tools to different parts
of the same prompt.** A single agent that must both search the web and write a report that
introduces no new facts has WebSearch available the entire time. "Do not search while
writing the report" is a request.

Split them, and `reporter` gets `tools: []`. WebSearch is not in its session at all. The
constraint stops being a request and becomes a property of the architecture.

If citation integrity matters, this alone justifies the split — and it is the reason
`research-crew` is multi-agent rather than one careful prompt.

### When to use one prompt instead

Use a single prompt when the task fits comfortably in one context window, when no part needs
capabilities another part must be denied, and when you do not need to attribute failures to
stages. That covers most tasks. Reach for multi-agent when isolation, tool scoping, or
per-stage debugging buys you something specific — and be able to name what.

## Two layers of delegation, and they mirror each other

This repository was itself built by delegation. The architect (Claude Opus 5) wrote the
specs and reviewed the work; a separate worker agent, dispatched through the `orca` CLI,
wrote the implementation. `COORDINATION.md` logs every dispatch.

So the same pattern runs at both levels, and comparing them is the fastest way to internalise it:

| | Build time (`COORDINATION.md`) | Run time (`runs/<id>/`) |
|---|---|---|
| Coordinator | the architect agent | `coordinator.py` |
| Workers | one worker agent per package | four specialised subagents |
| **The whole context channel** | the spec file in `tasks/` | the `Agent` tool prompt string |
| Hand-back | the worker's reply | the subagent's final message |
| Worker sees the coordinator's reasoning? | no | no |
| Bounded retry | 1 revision, then escalate | 1 re-search, `MAX_SEARCH_ROUNDS = 2` |
| Verification | review against acceptance criteria | `verify.py` against collected sources |
| Audit trail | `COORDINATION.md` | `runs/<id>/` |

The lesson that transfers: **a spec file and an `Agent` prompt string are the same object.**
Both are the entire context a worker gets. Anything the author knows and does not write down
is lost. Writing `tasks/01-foundation.md` meant restating the docs-host move, the
`Task`/`Agent` rename, and the `tools: []` trap by hand — because the worker could not see
the research that produced them. `coordinator.py` does exactly this work when it formats the
next subagent's prompt from `RunState`.

The layers differ in one important way, and `COORDINATION.md` records it honestly: the
subagents are isolated by **enforcement** (a tool absent from the session cannot be used),
while the build-time worker is isolated only by **instruction** (it runs in the same worktree
and is asked not to read other files). That gap is exactly the ADR-004 argument, seen from
the outside.

## Bounded loops, and why unbounded ones are dangerous

The coordinator may run a second search round when the analyst reports insufficient
coverage. It may **never** run a third. `MAX_SEARCH_ROUNDS = 2` is a constant in
`coordinator.py`, checked in an `if` statement.

An unbounded "search until satisfied" loop is dangerous for a reason worth stating precisely:
**the agent judging sufficiency is the same kind of component as the agent producing the
work.** A model that is never satisfied will search forever, and every iteration is a real
API call against a real invoice. Nothing in the system raises an error, because nothing is
failing. It is working, expensively, without end. Traditional infinite loops burn CPU and
show up as a hung process. Agent loops burn money and look like progress.

Three independent layers bound this run. Independence is the point — each catches what the
others miss:

| Layer | Mechanism | Catches |
|---|---|---|
| Application | `MAX_SEARCH_ROUNDS = 2` in `coordinator.py` | the loop we designed |
| SDK spend | `max_budget_usd` → `error_max_budget_usd` result subtype | runaway cost **within a single `query()` call** |
| Environment | `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | a subagent spawning its own subagents |

### A limit at the wrong scope: what the first live run taught us

Read that middle row carefully, because the first version of this system got it wrong and the
run proved it.

`max_budget_usd` bounds **one `query()` call**. ADR-003 makes one `query()` per phase, so the
cap **reset on every phase**. Run `20260830-152235` was configured with
`max_budget_usd = 3.0` and cost **$4.59**, and every phase returned `subtype: "success"`.
Nothing raised, because no single phase came near $3.00 — the largest was $0.97. With six
phases the real ceiling was about **$18**, not $3.

Nothing was broken in the SDK. The cap did exactly what it documents. The design assumed it
applied at a scope it never claimed.

The fix is to convert the per-call cap into a per-run one in the application layer: track
cumulative spend on `RunState`, pass `remaining = ceiling - spent` to each phase, and raise
before starting a phase that has nothing left. The SDK cannot know your pipeline contains six
calls; only your code knows that.

The lesson generalises past this bug, and it is worth carrying into the exam. **A limit
enforced at the wrong scope is indistinguishable from a limit enforced at the right one,
until it matters.** It appears in dashboards, it passes review, and it produces a number that
readers trust. That makes it more dangerous than no limit at all, because no limit at least
prompts caution. When you see a cap, ask what unit it counts and whether that unit is the one
you care about.

Note which layer did hold. `MAX_SEARCH_ROUNDS` worked perfectly: the analyst reported
insufficient coverage, the re-search fired exactly once, and a third round was impossible.
That bound is an `if` statement in code we own, at the scope we chose. The bound we borrowed
from the framework was the one that surprised us.

The third matters more than it looks. Subagents can spawn subagents, up to three levels by
default, so one prompt can grow into a tree of agents. Setting depth to `1` stops our four
agents from spawning any of their own. The docs note that Opus 5 delegates more readily than
earlier models, which makes the cap more necessary, not less.

Related: `coordinator.py` branches explicitly on `ResultMessage.subtype`. `success`,
`error_max_budget_usd`, and `error_max_turns` are handled; anything else raises. It never
treats "not an error I recognise" as success. That is the SDK-level form of the rule in
`.claude/rules/agentic-loop-stop-reason.md`.

## Citation integrity, and its limits

`verify.py` runs after the reporter. It uses no model. It checks three things:

1. every `[n]` in the report body resolves to a References entry (`unmapped_citations`);
2. every References URL is in the set the **searcher** actually collected (`uncollected_urls`);
3. no References entry goes uncited in the body (`orphan_references`);
4. no number maps to a different URL than the coordinator's citation map says
   (`misnumbered_references`);
5. every References line parses (`malformed_references`).

Failures are reported per citation, so a bad report names its own bad citations.

Check 4 replaced an earlier contiguity check that looked for gaps in the numbering. That
check was wrong, and the first live run proved it: the coordinator hands the reporter the
whole citation map, and `agents/reporter.md` tells it to list only the numbers it cited. A
report citing 21 of 46 sources is behaving correctly, and a subset of an integer range is
never contiguous — so the gap check fired on every correct run. It reported 23 "gaps" on a
report with no citation defect at all. The risk was never a gap; it was a reporter that
renumbers, and comparing number-to-URL against the coordinator's map catches that directly.

Two design choices make this check cheap and deterministic. The coordinator fixes the
citation numbers before the reporter runs and passes them in as a map, so the reporter never
renumbers anything. And the searcher is the only agent with web access, so "the set of legal
URLs" is unambiguous.

### What it does not check — read this part

**It does not verify that the cited source supports the claim.**

The check is referential, not semantic. It proves citation `[4]` points at a URL the searcher
really retrieved. It proves nothing about whether the sentence carrying `[4]` is supported by
what is at that URL. A report that attaches a real source to a fabricated claim **passes this
check**.

Closing that gap needs either an entailment model comparing each sentence to its source text,
or a human reader. Both are out of scope here. The check is a cheap guard against the most
common failure — invented or drifted citation numbers — and it is not a truth oracle. Treat a
passing `CitationReport` as "the citations are well-formed", never as "the report is correct".

**And the evidence chain has a soft link earlier than that.** The design assumes the
searcher's `snippet` is verbatim source text, and the analyst is told its `evidence` quote
must appear in that snippet. Run `20260830-152235` showed the assumption does not always
hold. The searcher reported honestly in its `notes` field:

> The WebSearch tool returned an AI-generated summary paragraph plus a links list for each
> query, rather than per-link verbatim snippets. For several links, no direct quoted snippet
> text was available from the tool output; these are marked accordingly rather than
> fabricated.

So for some sources the "verbatim quote" is a quote from a **summary of** the page, not from
the page. The URL is real and the claim traces to it, but one link in the chain is a
paraphrase produced by a model rather than text copied from a document. Every downstream
check still passes, because every check verifies structure rather than provenance depth.

Worth noting what went right: the searcher's prompt tells it that an honest gap beats a
filler source, and under pressure it did exactly that — flagged the shortfall instead of
inventing snippets to satisfy the schema. The system reported its own weakest point. That
only worked because something asked it to, which is an argument for writing that instruction
into every agent that collects evidence.

Fixing this properly means fetching each URL and extracting real text, which is a `WebFetch`
tool grant to the searcher and a different design. Recorded here rather than hidden.

## Debugging a bad report with `runs/<id>/`

Every execution writes:

```
runs/20260830-143012/
  01-searcher.input.json       exact prompt string the searcher received
  01-searcher.output.md        its final message, verbatim
  02-analyst.input.json        exact prompt string the analyst received
  02-analyst.output.md
  03-synthesizer.input.json
  03-synthesizer.output.md
  04-reporter.input.json
  04-reporter.output.md
  state-after-01-search.json   RunState snapshot after each phase
  state-after-02-analyze.json
  state-after-03-synthesize.json
  state-after-04-report.json
  cost.json                    per-phase cost, duration, and result subtype
  report.md
```

Recording each agent's **input** separately from its output is what makes this work. The
input file is the complete context that agent received — the entire string, since that is the
entire channel. So for any bad claim you can ask "was it already wrong in what this agent was
given, or did this agent introduce it?" and get an answer from one file.

**Worked example.** The report says "multi-agent systems cut latency by 90%", cited `[3]`,
and that number looks invented. Bisect backwards:

1. **`04-reporter.input.json`** — is the claim there? If **no**, the reporter invented it.
   That is an ADR-004 failure: the prompt rule held, the tool scoping held, and the model
   still produced a fact from pre-training. Tighten `verify.py`, not the prompt.
2. If **yes**, open **`03-synthesizer.output.md`**. Did the synthesizer merge two claims into
   something neither source said? Merges that overreach show up here.
3. If the claim is already in **`02-analyst.output.md`**, check its `evidence` field against
   the snippet in **`01-searcher.output.md`**. If the quote is not in the snippet, the analyst
   fabricated evidence.
4. If the quote **is** in the snippet, the pipeline behaved correctly and the source itself is
   wrong. Not a bug — a sourcing problem. Judge the source, not the code.

Four files, and the failure is attributed to one component. Note that step 4 is a real
possible outcome: a correct pipeline can faithfully report a bad source. Knowing the
difference between "my system broke" and "my source was wrong" is most of what these
artifacts buy you.

`cost.json` answers the other common question — which phase spent the money. It carries
`total_cost_usd` and the result subtype per phase, taken from the SDK's `ResultMessage`.

## Known issues and things left undone

Recorded rather than hidden. Several of these are more instructive than the parts that work.

| Issue | Impact | Why it is still here |
|---|---|---|
| `PYTHONPATH=src` needed to run the CLI | annoying | The package is under `src/` with no `pyproject.toml`. The task specs listed exact files to create and adding one would have broken that constraint. An editable install is the normal fix. |
| Searcher snippets are not always verbatim source text | weakens the evidence chain | WebSearch returns AI summaries for some results. A real fix means granting the searcher `WebFetch` and extracting page text — a different design. Documented above. |
| The verifier is referential, not semantic | a real URL on a false claim passes | Needs an entailment check or a human. Out of scope, and stated wherever the check is described. |
| `run_id` has second resolution | two runs starting in the same second collide | `RunRecorder` refuses the second, which is correct behaviour surfaced by the wrong module. |
| No parallelism anywhere | latency is the sum of all phases | The pipeline is a genuine dependency chain. Parallelism would need a different task shape, not a different implementation. |
| The build-time worker is isolated by instruction, not enforcement | a worker could read files it was told to skip | See `COORDINATION.md`. The contrast with the run-time layer's `tools: []` is the point. |

Four further defects were found by the first live run and **fixed** — the run-level budget
cap, harness trailers leaking into the report, the citation-numbering false positive, and the
off-by-one state snapshots. `COORDINATION.md` dispatch 4 has the details. They are worth
reading precisely because the offline test suite passed while every one of them was present.

## Repository layout

```
research-crew/
  README.md              this file
  DECISIONS.md           four ADRs
  COORDINATION.md        the build-time delegation log
  agents/                the four subagent prompts — design artifacts, heavily commented
    searcher.md          tools: [WebSearch]   the only agent that reaches the outside world
    analyst.md           tools: []            extracts claims, cannot search
    synthesizer.md       tools: []  model: opus  merges and flags conflicts
    reporter.md          tools: []            formats, introduces no new facts
  tasks/                 specs dispatched to the worker agent
  src/research_crew/
    state.py             RunState — the only thing crossing a phase boundary
    agents_loader.py     agents/*.md -> AgentDefinition (strips the design comments)
    observability.py     writes runs/<id>/
    coordinator.py       the pipeline, the bounded re-search, the budget caps
    verify.py            citation integrity, no model
    cli.py               entry point
  tests/
  runs/                  one directory per execution
```

### On `agents/*.md` and the stripped comments

Each agent file has YAML frontmatter (`name`, `description`, `tools`, `model`) and a body.
The body carries the system prompt **and** the design rationale, the rationale in HTML
comments.

`agents_loader.py` strips every HTML comment before building the `AgentDefinition`. So the
reasoning ships with the artifact, sits next to the constraint it explains, and never enters
the model's context window — no token cost at run time, and no chance of the commentary
confusing the agent reading it.

The frontmatter holds one trap worth repeating, because it fails silently. In
`AgentDefinition`, **omitting `tools` inherits every tool available to subagents; passing an
empty list grants none.** A loader that treats a missing key like an empty list hands a
supposedly tool-less reporter full filesystem and web access, and nothing errors. A test pins
the difference.
