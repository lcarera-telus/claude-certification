# Official Exam Guide — distilled

Source: **Claude Certified Architect – Foundations Exam Guide, Version 1.0, effective July 2026** (exam code CCAR-F). PDF at `~/Downloads/claude certification exam.pdf`, 39 pages, read 2026-08-24. This is the authoritative reference; where `claude-certified-architect/guide_en.md` or any third-party source disagrees, **this wins**.

## What this corrected

Four claims carried in `CLAUDE.md` from unofficial sources turned out to be wrong or incomplete:

| Was believed | Official |
|---|---|
| Scenarios: **4 of 8** | **4 of 6.** "Conversational architecture" and "Agentic AI tools" do not exist |
| Item format: multiple choice, **1 correct of 4** | Multiple-choice **and multiple-response**; each item states how many to select |
| Proctored via **Skilljar** | Delivered by **Pearson VUE** (online proctored or test center); registration via Anthropic Partner Academy |
| 60 questions / 120 min — **unverified** | **Confirmed**: 60 items, 120 minutes |

The "Scenario 8 blind spot" that this workspace tracked for weeks was an artifact of the community guide. There is nothing to cover there.

## Format and scoring

60 items · 120 minutes (2 min/item) · 4 scenarios drawn from a bank of 6 · scaled score 100–1,000, **cut score 720** · $125/attempt · credential valid 12 months.

**Criterion-referenced**: measured against a fixed standard from a formal standard-setting study, not a curve. The score report shows percent-correct per domain, but the guide states plainly that **section percentages are informational and are not used to determine pass/fail** — only the total scaled score is. Scaled scoring exists to equate across exam forms of differing difficulty.

No guessing penalty is mentioned anywhere in the guide (the community guide asserted there is none). Unstated, but nothing suggests one.

## Logistics and exam-day rules

- Cancel/reschedule up to **24 hours** before; inside 24 hours the fee is forfeited. No-show forfeits the fee.
- Valid, unexpired, **government-issued photo ID**, name matching registration **exactly**. Name corrections go to certifications-support@anthropic.com *before* scheduling.
- Closed book, closed room: no notes, books, phones, smart watches, headphones, secondary monitors, or recording devices. Stay in webcam view the whole session if testing online. Only scratch paper provided by the proctor, if any.
- An NDA must be accepted before the exam starts; declining ends the session with no refund.
- Retakes: **14 days** after a first fail, **30** after a second, **90** after a third. Max **4 attempts per rolling 12 months**, full fee each time.
- Appeals within 14 days, via Pearson VUE. Item content and the standard-setting outcome are not appealable.

## The 6 scenarios

| # | Scenario | Primary domains |
|---|---|---|
| 1 | Customer Support Resolution Agent — Agent SDK, MCP tools `get_customer`/`lookup_order`/`process_refund`/`escalate_to_human`, 80%+ first-contact resolution target | 1, 2, 5 |
| 2 | Code Generation with Claude Code — slash commands, CLAUDE.md, plan mode vs direct execution | 3, 5 |
| 3 | Multi-Agent Research System — coordinator + web-search / document-analysis / synthesis / report subagents, cited reports | 1, 2, 5 |
| 4 | Developer Productivity with Claude — codebase exploration, built-in tools, MCP servers | 2, 3, 1 |
| 5 | Claude Code for Continuous Integration — automated review, test generation, minimizing false positives | 3, 4 |
| 6 | Structured Data Extraction — JSON schema validation, edge cases, downstream integration | 4, 5 |

## The 30 task statements

Items are written directly against these. **The 30 exercise folders under `projects/claudecertificationguide/` map 1:1 onto this list** — that third-party exercise set is aligned to the official blueprint, which raises its value considerably.

**Domain 1 — Agentic Architecture & Orchestration (27%)**
1.1 Design and implement agentic loops for autonomous task execution
1.2 Orchestrate multi-agent systems with coordinator-subagent patterns
1.3 Configure subagent invocation, context passing, and spawning
1.4 Implement multi-step workflows with enforcement and handoff patterns
1.5 Apply Agent SDK hooks for tool call interception and data normalization
1.6 Design task decomposition strategies for complex workflows
1.7 Manage session state, resumption, and forking

**Domain 2 — Tool Design & MCP Integration (18%)**
2.1 Design effective tool interfaces with clear descriptions and boundaries
2.2 Implement structured error responses for MCP tools
2.3 Distribute tools appropriately across agents and configure tool choice
2.4 Integrate MCP servers into Claude Code and agent workflows
2.5 Select and apply built-in tools (Read, Write, Edit, Bash, Grep, Glob) effectively

**Domain 3 — Claude Code Configuration & Workflows (20%)**
3.1 Configure CLAUDE.md files with appropriate hierarchy, scoping, modular organization
3.2 Create and configure custom slash commands and skills
3.3 Apply path-specific rules for conditional convention loading
3.4 Determine when to use plan mode vs direct execution
3.5 Apply iterative refinement techniques for progressive improvement
3.6 Integrate Claude Code into CI/CD pipelines

**Domain 4 — Prompt Engineering & Structured Output (20%)**
4.1 Design prompts with explicit criteria to improve precision and reduce false positives
4.2 Apply few-shot prompting to improve output consistency and quality
4.3 Enforce structured output using tool use and JSON schemas
4.4 Implement validation, retry, and feedback loops for extraction quality
4.5 Design efficient batch processing strategies
4.6 Design multi-instance and multi-pass review architectures

**Domain 5 — Context Management & Reliability (15%)**
5.1 Manage conversation context to preserve critical information across long interactions
5.2 Design effective escalation and ambiguity resolution patterns
5.3 Implement error propagation strategies across multi-agent systems
5.4 Manage context effectively in large codebase exploration
5.5 Design human review workflows and confidence calibration
5.6 Preserve information provenance and handle uncertainty in multi-source synthesis

## Recurring judgment patterns

The same tradeoffs surface across the objectives and all 12 sample questions. These are effectively the answer key's reasoning:

- **Deterministic enforcement beats prompt instruction** whenever compliance must be guaranteed. Hooks and programmatic prerequisite gates over "the system prompt says to always...". Prompt compliance has a non-zero failure rate; that is unacceptable before financial operations.
- **Fix the root cause at the cheapest layer first.** Thin tool descriptions → write better descriptions, not a routing classifier. Unclear escalation boundaries → explicit criteria + few-shot, not an ML classifier or sentiment analysis. Over-engineered options are the most common distractor.
- **Self-reported confidence is not calibrated.** An agent already wrong-and-confident on hard cases will not fix itself with a 1-10 score. Same for sentiment as a proxy for complexity.
- **Least privilege for subagents.** Scope tools to the role; 18 tools degrade selection vs 4-5. Add one narrow cross-role tool for a high-frequency need rather than handing over the whole toolset.
- **Never hide error information.** Structured error context (failure type, attempted query, partial results, alternatives) upward. Empty-result-as-success and workflow-wide termination are both anti-patterns. Distinguish access failures from valid empty results.
- **Attention dilutes across many files.** Split into per-file passes plus a cross-file integration pass; a bigger context window does not fix attention quality.
- **Independent review beats self-review.** The instance that generated the code retains its reasoning and will not question itself.
- **Schemas eliminate syntax errors, not semantic ones.** Line items that don't sum still need validation. Nullable/optional fields prevent fabrication when the source lacks the data; retries can't recover information that was never in the document.
- **Match the API to the latency requirement.** Batches API = 50% cheaper, up to 24h, no SLA, no multi-turn tool calling → fine for overnight reports, disqualified for blocking pre-merge checks.
- **Coordinator decomposition is where coverage failures originate.** If subagents each succeed but the report misses whole subtopics, blame the decomposition, not the downstream agents.

## Appendix: in-scope technologies

Agent SDK (agent definitions, agentic loops, `stop_reason`, hooks incl. PostToolUse and tool-call interception, subagent spawning via `Task`, `allowedTools`) · MCP (servers, tools, resources, `isError`, `.mcp.json`, env var expansion) · Claude Code (CLAUDE.md hierarchy, `.claude/rules/` YAML path-scoping, `.claude/commands/`, `.claude/skills/` SKILL.md frontmatter `context: fork` / `allowed-tools` / `argument-hint`, plan mode, `/memory`, `/compact`, `--resume`, `fork_session`, Explore subagent) · CLI (`-p`/`--print`, `--output-format json`, `--json-schema`) · Claude API (`tool_use` + JSON schemas, `tool_choice` auto/any/forced, `stop_reason` values, `max_tokens`, system prompts) · Message Batches API (`custom_id`, polling) · JSON Schema · Pydantic · built-in tools · few-shot · prompt chaining · context management · session management · confidence scoring.

## Appendix: explicitly out of scope

Fine-tuning or training · API auth, billing, account management · language/framework implementation detail beyond tool and schema config · deploying or hosting MCP servers (infra, networking, containers) · Claude's internal architecture, training, weights · Constitutional AI, RLHF, safety training · embeddings and vector DB internals · **computer use** · **vision/image analysis** · **streaming / SSE** · rate limits, quotas, pricing math · OAuth, key rotation, auth protocols · cloud provider configuration · benchmarking and model comparison · **prompt caching implementation detail** (beyond knowing it exists) · token counting and tokenization internals.
