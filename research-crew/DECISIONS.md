# Architecture Decision Records

Four decisions shaped `research-crew`. Each one had a real alternative. This file records
what we chose, why, and what the choice costs us.

---

## ADR-001 — Coordinator-per-pipeline, not free-form agent-to-agent chatter

**Status:** accepted

### Context

Four specialised agents must cooperate to answer one research question. Two shapes are
available.

**A coordinator pipeline.** One coordinator owns the sequence. It calls each agent in turn,
holds all shared state, and decides what the next agent sees. Agents never address each
other.

**Free-form chatter.** Agents message each other directly and settle the work between
themselves. The searcher tells the analyst when new sources land. The analyst asks the
searcher for more. The work ends when the agents agree it has ended.

The second option is not a strawman. The SDK supports it today through the `SendMessage`
tool. Per the subagents documentation, "a subagent that has the `SendMessage` tool starts
with a list of the other named agents running in the session, so it knows which names it can
send messages to." Chatter is one tool grant away. We are declining a capability we have.

### Decision

Use a coordinator pipeline. `coordinator.py` runs the four phases in a fixed order. No agent
receives `SendMessage`.

### Why

**Termination is decidable.** The pipeline ends after four phases and at most one re-search.
You can prove that from reading the code. In a chatter system, termination is an emergent
property of agents agreeing to stop. Two agents can each wait for the other. Two agents can
politely hand work back and forth until the budget runs out. Neither failure raises an
exception. Both burn real money.

**Cost is boundable in advance.** A fixed pipeline has a known call count, so you can price a
run before you make it. Chatter has no such bound: message paths between N agents grow
quadratically, and each message is an API call.

**One owner of state means the run can be snapshotted.** `RunState` is written to disk after
every phase, so `runs/<id>/` reconstructs the whole execution. When state is spread across
several agents' private conversations, there is no moment at which anything holds the whole
picture, and so there is nothing to log.

**Failure is attributable.** In a pipeline, a bad claim in the report came from a specific
phase, and the input file for that phase is on disk. In a chatter system, a bad claim is the
product of a conversation, and "which message introduced this" is often unanswerable.

**Replay is possible.** Fixed order plus recorded inputs means a run can be re-executed and
compared. Chatter runs are non-deterministic in their ordering, so two runs of the same
question are not comparable artifacts.

### What this costs us

Be honest about the trade. A pipeline is rigid.

- **The shape is fixed at design time.** If a question needs analysis before searching, this
  pipeline cannot express that. It would need a code change.
- **The coordinator is a bottleneck.** Every hand-off is routed through it, including ones
  where two agents could have settled the matter directly in one message.
- **Adaptation is limited to what we anticipated.** The one bounded re-search loop is the
  only feedback path in the system. A chatter system could improvise a recovery that we
  never designed.

Chatter is the better choice when the task shape is genuinely unknown until run time, or
when subtasks are interdependent in ways that cannot be ordered in advance.

Research is not such a task. Collect, extract, merge, format — the dependency graph is known
before the question is asked, and it never changes. When the shape is known at design time,
encode it in code. Chatter's flexibility buys nothing here and costs every property listed
above.

---

## ADR-002 — Claude Agent SDK, not Managed Agents

**Status:** accepted

### Context

Anthropic ships two supported multi-agent mechanisms. They live in different documentation
sets, and a stale mental model will conflate them.

| | Claude Agent SDK | Managed Agents |
|---|---|---|
| Docs | `code.claude.com/docs/en/agent-sdk/` | `platform.claude.com/docs/en/managed-agents/` |
| Runs | locally, driving the installed `claude` CLI | on Anthropic's servers |
| Define a subagent | `AgentDefinition` in the `agents` option | `client.beta.agents.create(...)` |
| Delegation primitive | the `Agent` tool | `agent_toolset_20260401` |
| Isolation unit | subagent conversation | session thread |
| Requires | `claude` installed and authenticated | API key plus `managed-agents-2026-04-01` beta header |

Both give real context isolation and per-agent tool scoping. Either would satisfy the brief.

### Decision

Use the Claude Agent SDK.

### Why

**It runs on what is installed.** `claude` v2.1.251 is on this machine and authenticated.
Managed Agents needs a first-party API key with beta access, which this environment does not
have.

**The repository's existing credentials point the wrong way.** `projects/claudecertificationguide/.env`
sets `ANTHROPIC_BASE_URL=https://api.fuelix.ai`, a gateway. That gateway does not serve
`/v1/agents` or `/v1/sessions`. Managed Agents would need new credentials before the demo
could run at all. This is why `research-crew` deliberately loads no `.env` file — see the
note in `requirements.txt`.

**Local execution is better for study.** Every subagent call is observable on this machine,
and the run artifacts land in `runs/<id>/`. Server-side threads would have to be read back
through the event-stream API.

### What this costs us

- No persistent threads. Managed Agents keeps a thread alive so the coordinator can send a
  follow-up to an agent it called earlier, and that agent keeps its history. The Agent SDK
  can resume a subagent, but only within the same session and only by passing `resume` plus
  the `agentId`. Our pipeline does not need this, so we do not use it.
- Managed Agents caps a coordinator at one level of delegation and rejects a nested roster at
  create time. The Agent SDK permits nesting by default, so we must cap it ourselves with
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`. A guarantee we get for free there is our job here.
- The demo is bound to a correctly configured local `claude`. It is not portable to CI
  without one.

---

## ADR-003 — Explicit named invocation, not model-chosen auto-delegation

**Status:** accepted

### Context

With all four agents passed in the `agents` option, delegation can happen two ways.

**Auto-delegation.** Give the coordinator one prompt describing the whole job. Claude reads
each agent's `description` and picks which to call, and when.

**Explicit invocation.** The coordinator runs one `query()` per phase, and each prompt names
exactly one agent. The docs support this directly: "To guarantee Claude uses a specific
subagent, mention it by name in your prompt."

### Decision

Use explicit named invocation, one `query()` per phase, sequenced by Python.

### Why

Auto-delegation moves the orchestration inside the model's reasoning. Three things we need
become impossible.

1. **State cannot be logged between phases**, because there are no phase boundaries in the
   host program. The run is one opaque call.
2. **The re-search loop cannot be bounded in code.** "At most one retry" becomes a request in
   a prompt rather than an `if` statement. Objective 3 asks us to demonstrate a bounded loop.
   A bound the model can talk itself out of is not a bound.
3. **The order is not guaranteed.** Nothing stops Claude calling the reporter before the
   synthesizer if it judges that reasonable.

There is also a teaching reason. This artifact exists so a reader can see orchestration. If
the orchestration lives in the model's head, there is nothing to read.

### What this costs us

One extra router hop per phase. Each `query()` starts a coordinator turn that does nothing
but invoke the named subagent, so we pay a small amount of latency and tokens four to five
times per run that auto-delegation would not spend. Real cost, measured in `runs/<id>/cost.json`.

We accept it. Determinism and observability are worth more here than four cheap turns.

**A consequence we did not anticipate, and it cost us.** One `query()` per phase means the
SDK's `max_budget_usd` — which bounds a single call — resets on every phase. The first live
run was configured with a $3.00 ceiling, cost **$4.59**, and reported `success` on all six
phases, because no individual phase came near $3.00. The real ceiling was about $18.

Auto-delegation would not have had this problem. One `query()` for the whole run means one
budget for the whole run, enforced by the SDK for free. Choosing explicit invocation moved
that guarantee out of the framework and into our hands, and we did not notice we had taken
delivery of it. `coordinator.py` now tracks cumulative spend and passes the remaining budget
to each phase.

The general form is worth more than the specific bug: **when you take control of a loop from
a framework, you inherit every invariant the framework was maintaining inside it** — not just
the one you wanted to change. Ask what else that loop was holding.

Note also that Opus 5 delegates more eagerly than earlier models. The docs point this out and
recommend the depth, concurrency, and spend caps precisely because prompt-level steering is
unreliable. That reinforces the same conclusion: put the control in code.

---

## ADR-004 — Empty tool lists as enforcement, not prompt instructions

**Status:** accepted

### Context

The brief requires that the `reporter` may not introduce new facts. The same class of
constraint applies to the analyst and the synthesizer, neither of which may search.

### Decision

Enforce it with `tools: []`, then verify the result mechanically in `verify.py`. The prompt
states the rule too, but the prompt is the weakest of the three layers.

### Why

There are three ways to stop an agent doing something, and they are not equally strong.

1. **Ask it in the prompt.** Advisory. It usually works. Under pressure — a thin claim set,
   an awkward transition — a model will helpfully fill the gap. Every hallucinated citation
   ever shipped got past a prompt that said not to do that.
2. **Remove the capability.** Structural. Per the docs, "a tool you leave out isn't in the
   subagent's session at all: Claude works without it, with no permission prompt or error."
   There is no instruction to disobey, because there is no tool.
3. **Check the output in code.** `verify.py` reads the finished report and matches every
   `[n]` against the sources the searcher actually collected. No model judgment is involved,
   so no amount of fluent prose talks its way past it.

Prefer the layer that does not depend on the model choosing to cooperate.

### An implementation trap this creates

In `AgentDefinition`, omitting `tools` and passing `tools=[]` do opposite things. Omitting it
inherits **every** tool available to subagents. Passing an empty list grants **none**. A
loader that treats a missing key and an empty list alike would hand a supposedly tool-less
reporter full filesystem and web access, and nothing would error. `agents_loader.py` keeps
the two cases apart, and a test in `tests/test_agents_loader.py` pins the difference.

### What this costs us

- Rigidity. A tool-less agent that turns out to need one tool needs a design change, not a
  prompt tweak.
- Incomplete coverage. `tools: []` closes the *retrieval* channel. It does not stop a model
  reciting something from pre-training. Only layer 3 catches that, and only partly — see the
  next point.
- **The verifier is weaker than it sounds.** It proves that citation `[4]` points at a URL
  the searcher really retrieved. It does **not** prove the sentence carrying `[4]` is
  supported by what is at that URL. A report that cites a real source for a fabricated claim
  passes. Closing that gap needs an entailment check or a human reader. `README.md` states
  this limitation in the same words.
