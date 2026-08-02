# CCA-F Progress Log

Chronological log of full mock exams and diagnostics only. Newest entry on top. Each entry: source, date, per-domain score, and what it implies for study priority. Task-statement-level drill notes live under `notes/<domain-folder>/<task-folder>/notes.md`, mirroring the folder structure in `projects/claudecertificationguide/`.

**Current focus (as of 2026-07-31, updated after second mock):** Domain 2 — Tool Design & MCP Integration is now the clear weakest domain (60%, 3/5) and the priority gap. D3 and D4, previously flagged weak, both recovered strongly (100% and 83%) under slower, unhurried exam conditions — reinforcing that pacing/pressure, not just knowledge gaps, was part of the earlier D3/D4 misses.

**Study strategy (decided 2026-07-31):** Domain-by-domain, task-statement by task-statement, with periodic full mock exams to check whether drilling is translating into domain-level gains (not just task-statement recognition — see the mock exam entries below). Next priority: Domain 2 task statements, drilling the specific MCP/tool-design questions missed on 2026-07-31's second mock.

---

## 2026-07-31 — Full mock exam #2 (28 questions), taken slower and unhurried

**895/1000 — PASSED** (pass mark 720). 25/28 correct (89%).

| Domain | Score | % | Weighted pts |
|---|---|---|---|
| D1 Agentic Architecture & Orchestration | 6/6 | 100% | 270 |
| D2 Tool Design & MCP Integration | 3/5 | 60% | 108 |
| D3 Claude Code Configuration & Workflows | 6/6 | 100% | 200 |
| D4 Prompt Engineering & Structured Output | 5/6 | 83% | 167 |
| D5 Context Management & Reliability | 5/5 | 100% | 150 |

**Major turnaround vs. the 2026-07-31 first mock (536/1000):** D1 went 50% → 100%, D3 went 50% → 100%, D4 went 33% → 83%. The one variable explicitly changed was pace — this attempt was taken "more focused and without hurrying." Strong evidence that the first mock's D1/D3/D4 misses were driven significantly by rushing, not pure knowledge gaps, though the intervening task-statement drilling (3.1, 3.2) likely also contributed to the D3 gain specifically.

**New signal: D2 dropped from 80% (first mock) to 60% (this mock)** — the only domain that got worse. D2 hadn't been targeted by any drilling in between, so this is likely just normal variance in a small (5-question) sample rather than a real regression — but it's now the lowest-scoring domain and hasn't had a dedicated task-statement drill pass yet (unlike D3/D4, which have already had 3.1/3.2 drills).

**Takeaway:** Score is comfortably above the 720 pass mark, and the "slow down" adjustment mattered a lot. Don't over-index on a single 5-question D2 sample as proof of a deep gap, but it's the natural next place to focus since it's both the weakest showing here and the least-drilled domain so far.

**Next actions:**
- Review the specific D2 (Tool Design & MCP Integration) questions missed on this mock to distinguish "unlucky sample" from "real gap."
- Do a dedicated D2 task-statement drill pass (analogous to the D3 3.1/3.2 drills) before writing D2 off as noise.
- Given the score is well above pass mark, remaining prep can shift from "must-fix" urgency to consolidation — a good point to consider scheduling the real exam.

---

## 2026-07-31 — Full mock exam (28 questions)

**536/1000 — NOT PASSED** (pass mark 720). 15/28 correct (54%).

| Domain | Score | % | Weighted pts |
|---|---|---|---|
| D1 Agentic Architecture & Orchestration | 3/6 | 50% | 135 |
| D2 Tool Design & MCP Integration | 4/5 | 80% | 144 |
| D3 Claude Code Configuration & Workflows | 3/6 | 50% | 100 |
| D4 Prompt Engineering & Structured Output | 2/6 | 33% | 67 |
| D5 Context Management & Reliability | 3/5 | 60% | 90 |

**Important discrepancy to flag:** D3 came in at 50% here, *below* the 2026-07-29 diagnostic's 60% — despite Task Statements 3.1 and 3.2 both going 5/5 in dedicated drills the same day. Reading: narrow task-statement drills test recognition within a tightly scoped topic; a domain-wide mock pulls in other D3 task statements (3.3+) that haven't been drilled yet, plus applies pressure/variety a single-topic drill doesn't. **5/5 on a task-statement drill is not evidence the whole domain is solid — don't let it create false confidence.**

D4 is now the clear weakest domain (33%, down from the diagnostic's 60% — again likely a broader/harder question set), and D1 dropped in with D3 at 50%. D2 remains consistently strong (80-100% across both attempts).

**Takeaway:** Passing individual task-statement drills is necessary but not sufficient — full mock exams are the real signal for domain readiness. Don't mark a domain "closed out" until it holds up under mock-exam conditions, not just a task-statement drill.

**Next actions:**
- Continue D3 task-statement coverage (3.3+) before assuming D3 is done.
- D4 (Prompt Engineering & Structured Output) needs a fresh full pass — it's now the single biggest gap and carries 20% weight.
- Retake a full mock after the next study block to check whether task-statement drilling is actually translating to domain-level gains.

---

## 2026-07-29 — claudecertificationguide.com diagnostic test

| Domain | Score | % |
|---|---|---|
| D1 Agentic Architecture & Orchestration | 4/5 | 80% |
| D2 Tool Design & MCP Integration | 5/5 | 100% |
| D3 Claude Code Configuration & Workflows | 3/5 | 60% |
| D4 Prompt Engineering & Structured Output | 3/5 | 60% |
| D5 Context Management & Reliability | 4/5 | 80% |

Overall: 19/25 (76%)

**Takeaway:** D3 and D4 are the weakest (60% each) and, per CLAUDE.md, together they're 40% of the real exam's weighting — more than D1 alone (27%). These two are the priority for the next study pass, ahead of D1 despite D1 having the single highest domain weight.

**Next actions:**
- Re-read `claude-certified-architect/guide_en.md` sections on Claude Code config/workflows (D3) and prompt engineering/structured output (D4).
- Work through claudecertificationguide.com exercises tagged D3 (×5) and D4 (×6).
- Retake the diagnostic after that pass to confirm improvement before moving to D1/D5 polish.
