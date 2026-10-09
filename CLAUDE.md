# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A personal study workspace for the **Claude Certified Architect – Foundations (CCA-F)** certification. It is not an application — there is no build or test suite; the only dependency manifest is `projects/claudecertificationguide/requirements.txt` for the practice exercises.

Current contents:

- `CLAUDE.md` — this file
- `claude-certified-architect/` — a clone of https://github.com/paullarionov/claude-certified-architect (~124 MB, its own git repo; the parent directory is not under version control)
- `notes/` — own study notes and progress log (see Conventions), including `notes/official-exam-guide.md`, the distilled official Exam Guide
- `notes/ccar-p/` — prep for the next exam, **Claude Certified Architect – Professional (CCAR-P)**: distilled official guide (`official-exam-guide.md`, authoritative) and collected resources plus the only first-hand report found (`resources.md`). CCAR-F was passed (865/1000); see `notes/progress-log.md`
- `projects/claudecertificationguide/` — worked exercises from claudecertificationguide.com, one folder per task statement across the five domains
- `.claude/rules/agentic-loop-stop-reason.md` — path-scoped rule for exercise code (stop-reason handling in manual tool-use loops)

Work here is study artifacts: notes, worked exercises, practice-exam post-mortems. Treat exercise code as disposable learning material — the goal is understanding the tradeoff being tested, not a polished implementation.

## Exam facts

**Authoritative source: the official Exam Guide** (v1.0, effective July 2026), read 2026-08-24. Distilled into `notes/official-exam-guide.md`; original PDF at `~/Downloads/claude certification exam.pdf`. Everything below is from that guide and supersedes the community/third-party numbers this file previously carried.

| Parameter | Value |
|---|---|
| Credential / exam code | Claude Certified Architect – Foundations / **CCAR-F** |
| Number of items | **60** |
| Item format | Multiple-choice **and multiple-response**; each item states how many responses to select |
| Exam structure | **4 scenarios drawn from a bank of 6** |
| Time limit | **120 minutes** |
| Delivery | **Pearson VUE** — online proctored or test center |
| Passing score | Scaled **720** on a 100–1,000 scale |
| Fee | **$125 USD** per attempt |
| Validity | **12 months** from award date |
| Result reporting | Pass/fail + scaled score, plus percent-correct by domain |

Scope: Claude Code, Claude Agent SDK, Claude API, MCP. Tests practical judgment about architecture, configuration, and **tradeoffs**, not API trivia.

**Scoring is criterion-referenced** — measured against a fixed standard set by a standard-setting study, not against other candidates. Critically: **per-domain percentages on the score report are informational only and do not determine pass/fail** — only the total scaled score does. Do not optimise study time against a single mock's domain bars.

**Logistics:** registration through the Anthropic Partner Academy, scheduling through Pearson VUE. Cancel/reschedule up to **24 hours** before, or forfeit the fee. Valid unexpired government-issued photo ID required, name matching the registration exactly. Closed-book and closed-room: no notes, books, phones, smart watches, headphones, or secondary monitors; stay in webcam view throughout. A confidentiality/NDA must be accepted before the exam starts. Retakes: 14 days after a first fail, 30 after a second, 90 after a third; max 4 attempts per rolling 12 months, fee each time.

The guide does **not** mention a guessing penalty (the community guide claimed there is none). Unstated either way — but with no evidence of one, answering every item remains correct.

## The five domains

Weights confirmed against the official blueprint:

| # | Domain | Weight |
|---|--------|--------|
| 1 | Agentic Architecture & Orchestration | **27%** |
| 3 | Claude Code Configuration & Workflows | 20% |
| 4 | Prompt Engineering & Structured Output | 20% |
| 2 | Tool Design & MCP Integration | 18% |
| 5 | Context Management & Reliability | 15% |

Weights are the *approximate proportion of scored items* per domain. Domains 3 + 4 together (40%) outweigh Domain 1 alone. The official guide breaks each domain into numbered task statements (D1 ×7, D2 ×5, D3 ×6, D4 ×6, D5 ×6) with explicit "Knowledge of" / "Skills in" bullets — these are what items are written against. Full list in `notes/official-exam-guide.md`.

## The six scenarios

The exam presents **4 of these 6** at random, so none can be safely skipped:

1. **Customer Support Resolution Agent** — Agent SDK, MCP tools (`get_customer`, `lookup_order`, `process_refund`, `escalate_to_human`), 80%+ first-contact resolution target, escalation. *Primary domains: 1, 2, 5*
2. **Code Generation with Claude Code** — slash commands, CLAUDE.md config, plan mode vs direct execution. *Primary domains: 3, 5*
3. **Multi-Agent Research System** — coordinator delegating to search/analysis/synthesis/report subagents, cited reports. *Primary domains: 1, 2, 5*
4. **Developer Productivity with Claude** — codebase exploration, built-in tools (Read/Write/Bash/Grep/Glob), MCP servers. *Primary domains: 2, 3, 1*
5. **Claude Code for Continuous Integration** — automated review, test generation, minimizing false positives. *Primary domains: 3, 4*
6. **Structured Data Extraction** — JSON schema validation, edge cases, downstream integration. *Primary domains: 4, 5*

**Correction (2026-08-24):** this file previously listed *eight* scenarios, adding "Conversational architecture" and "Agentic AI tools" from the community guide, and flagged the latter as a known blind spot. **Neither exists in the official guide.** The bank is 6. That blind spot was an artifact of an unofficial source, not a gap in preparation.

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

Only the official Exam Guide is authoritative (`notes/official-exam-guide.md`). Where sources conflict, the official guide wins — note the discrepancy rather than averaging them.

## Running exercises

Exercises live under `projects/claudecertificationguide/<NN-domain>/<N.N-task>/main.py` and share `common/client.py`, which reads `.env` at the project root.

```bash
cd projects/claudecertificationguide
pip install -r requirements.txt
cp .env.example .env   # then set ANTHROPIC_AUTH_TOKEN
python 01-agentic-architecture-orchestration/1.1-agentic-loops/main.py
```

`.env` points at a FuelIX gateway (`ANTHROPIC_BASE_URL=https://api.fuelix.ai`) with `ANTHROPIC_AUTH_TOKEN`, not a first-party `ANTHROPIC_API_KEY`. `ANTHROPIC_MODEL` overrides the default model.

## Conventions

Keep study notes and exercise work outside `claude-certified-architect/` — that directory is an upstream clone and should stay pristine so it can be pulled. Own work lives under `notes/`:

- `notes/progress-log.md` — chronological log (newest entry first) of full mock exams and diagnostics only, one entry per attempt with per-domain scores and a takeaway on what to study next.
- `notes/<NN-domain-name>/<N.N-task-name>/notes.md` — task-statement-level drill notes, one folder per task statement, mirroring the numbering and naming used in `projects/claudecertificationguide/`. Numbering must match; names have drifted in places (e.g. notes `1.2-coordinator-subagent-orchestration` vs project `1.2-multi-agent-orchestration`) — match on the `N.N` prefix, not the slug.

Because the exam scores tradeoff judgment, a note explaining *why each distractor is wrong* is worth more than one restating the correct answer. For a missed practice question, record the misconception, not just the fix.

## Open questions

- Resolved 2026-08-24: the official Exam Guide has been read; the exam facts, domain, and scenario sections above now reflect it. Where the community guide (`claude-certified-architect/guide_en.md`) conflicts, the official guide wins — notably scenario count (6, not 8) and item format (multiple-response items exist).
- Per-domain item counts are not published; only approximate weights.
- Community and third-party sources remain useful for *practice volume*, but every factual claim they make about format should now be checked against `notes/official-exam-guide.md`.
