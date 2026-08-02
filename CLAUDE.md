# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A personal study workspace for the **Claude Certified Architect – Foundations (CCA-F)** certification. It is not an application — there is no build, no test suite, and no dependency manifest.

Current contents:

- `CLAUDE.md` — this file
- `claude-certified-architect/` — a clone of https://github.com/paullarionov/claude-certified-architect (~124 MB, its own git repo; the parent directory is not under version control)

Work here is study artifacts: notes, worked exercises, practice-exam post-mortems. Treat exercise code as disposable learning material — the goal is understanding the tradeoff being tested, not a polished implementation.

## Exam facts

From the official Skilljar listing:

- **$125** per attempt, proctored via Skilljar
- Scope: Claude Code, Claude Agent SDK, Claude API, MCP
- Tests judgment about **tradeoffs** in real-world Claude solutions, not API trivia
- Access is gated to Anthropic Partner Network members with a verified partner-company email; free for the first 5,000, then $99. Request access: https://anthropic.skilljar.com/claude-certified-architect-foundations-access-request

From `claude-certified-architect/guide_en.md`, which states it is based on the official Exam Guide:

| Parameter | Value |
|---|---|
| Question type | Multiple choice, 1 correct of 4 |
| Scoring | 100–1000 scale, **720 to pass** |
| Guessing penalty | None — answer every question |
| Scenarios | **4 of 8, randomly selected** |

Third-party guides add **60 questions / 120 minutes / closed-book**. The community guide's format table does not confirm this — treat as unverified.

## The five domains

Weights are consistent across the community guide and third-party sources:

| # | Domain | Weight |
|---|--------|--------|
| 1 | Agent architecture & orchestration | **27%** |
| 3 | Claude Code configuration & workflows | 20% |
| 4 | Prompt engineering & structured output | 20% |
| 2 | Tool design & MCP integration | 18% |
| 5 | Context management & reliability | 15% |

Scoring is domain-weighted, so accuracy in Domain 1 moves the total more than equal accuracy in Domain 5. Domains 3 + 4 together (40%) outweigh Domain 1 alone.

## The eight scenarios

The exam draws 4 of these 8 at random, so none can be safely skipped:

1. Customer support agent — Agent SDK, MCP tools (`get_customer`, `lookup_order`, `process_refund`, `escalate_to_human`), escalation policy
2. Code generation with Claude Code — slash commands, CLAUDE.md config, when to use plan mode
3. Multi-agent research — coordinator delegating to specialized subagents, citations
4. Developer productivity — codebase exploration, built-in tools (Read/Write/Bash/Grep/Glob), MCP servers
5. Claude Code in CI/CD — automated review, test generation, minimizing false positives
6. Structured data extraction — JSON schema validation, edge cases
7. Conversational architecture — context window management, instruction persistence, memory, ambiguous input
8. Agentic AI tools — **content missing from the community guide.** Reported by candidates but not covered. Known blind spot; cover it from other resources.

## Primary study resource: `claude-certified-architect/`

`guide_en.md` (~3,400 lines) is the substantive artifact. Read it directly rather than the PDF/EPUB renders. Structure:

- **Part I — Theory foundations**, 13 chapters: Claude API basics → `tool_use` → Agent SDK (agentic loop, `AgentDefinition`, hub-and-spoke, `Task` tool, hooks) → MCP → Claude Code config → prompt engineering → Batches API → task decomposition → escalation/HITL → multi-agent error handling → context management → provenance → built-in tools
- **Part II — Domain notes**, one section per weighted domain
- Then: worked exam questions with explanations, a **practice test** (line ~2141), **practical exercises** (line ~3304), appendix, **out-of-scope topics** (line ~3387), preparation recommendations

The "Out-of-Scope Topics" section is worth reading early — it bounds what you can safely ignore.

15 language translations exist (`guide_*.md`); `guide_en.md` is the reference. PDF/EPUB under `pdf/` and `epub/` are CI-generated from the markdown by `.github/workflows/` — never edit those, and don't edit the markdown either since this is a read-only upstream clone. `anki/*.apkg` decks are built from `practical_test_*.html` by `utils/build_anki_deck.py`.

## Other resources

- **claudecertificationguide.com/learn/exercises** — 24 hands-on build exercises mapped to the five domains: D1 ×7, D2 ×5, D3 ×6, D4 ×6, D5 ×6. Primary source of practice *work*.
- **practice.cyberskill.world** (was `ccaf.cyberskill.world`, 301) — free 60q/120min mock at the 720/1000 cut score, 15 questions each across research pipelines, extraction pipelines, support agents, code exploration. Independent, not Anthropic-affiliated.
- **Udemy: "Anthropic Claude Certified Architect – 3 Full Practice Exams"** — timed practice volume.

Only the official Skilljar material is authoritative. Where sources conflict, note the discrepancy rather than averaging them.

## Conventions

Keep study notes and exercise work outside `claude-certified-architect/` — that directory is an upstream clone and should stay pristine so it can be pulled. Own work lives under `notes/`; `notes/progress-log.md` is a chronological log (newest entry first) of diagnostic tests and mock-exam results, one entry per attempt with per-domain scores and a takeaway on what to study next.

Because the exam scores tradeoff judgment, a note explaining *why each distractor is wrong* is worth more than one restating the correct answer. For a missed practice question, record the misconception, not just the fix.

## Open questions

- The official Exam Guide PDF sits behind Skilljar enrollment and has not been read. Everything above is from the community guide and third-party sites. Verify and correct this file once you have it.
- Question count and time limit are unconfirmed.
- Whether partner-tier access works with a `@gm2dev.com` address is untested.
