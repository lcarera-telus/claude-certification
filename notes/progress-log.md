# CCA-F Progress Log

Chronological log of full mock exams and diagnostics only. Newest entry on top. Each entry: source, date, per-domain score, and what it implies for study priority. Task-statement-level drill notes live under `notes/<domain-folder>/<task-folder>/notes.md`, mirroring the folder structure in `projects/claudecertificationguide/`.

**Current focus (as of 2026-08-04, updated after 60-question mock):** D2 fully recovered to 100%, confirming the 2026-07-31 dip was sample noise, not a real gap. **D4 (67%) and D1 (71%) are now the weakest domains** and the priority — together they carry 47% of the real exam's weight, so gains here move the total score more than any other pair.

**Study strategy (decided 2026-07-31, still in effect):** Domain-by-domain, task-statement by task-statement, with periodic full mock exams to check whether drilling is translating into domain-level gains (not just task-statement recognition — see the mock exam entries below). Next priority: review the specific D1 and D4 questions missed on this mock, then a dedicated drill pass on both before the next mock.

---

## 2026-08-04 — practice.cyberskill.world mock exam (60 questions)

**826/1000 — PASSED** (pass mark 720). 50/60 correct (83%).

| Domain | Score | % | Weighted pts |
|---|---|---|---|
| D1 Agentic Architecture & Orchestration | 10/14 | 71% | 193 |
| D2 Tool Design & MCP Integration | 11/11 | 100% | 180 |
| D3 Claude Code Configuration & Workflows | 11/12 | 92% | 183 |
| D4 Prompt Engineering & Structured Output | 8/12 | 67% | 133 |
| D5 Context Management & Reliability | 10/11 | 91% | 136 |

**D2 fully recovered (60% → 100%)** — confirms the 2026-07-31 mock #2 reading that the 60% dip was noise from a small 5-question sample, not a real gap. No dedicated D2 drill pass was done in between, so this is further evidence D2 doesn't need must-fix urgency.

**D4 dropped back down (83% → 67%)** — after recovering on 2026-07-31 mock #2 under slower pacing, it's regressed again on a larger, harder 12-question sample. This is the first mock with double-digit D4 questions, so it's a more reliable signal than the earlier 5-6 question samples. **D1 also came in soft at 71%** (10/14) — its first sub-100% showing since the pacing fix on 2026-07-31. Both are now below the other three domains.

**Takeaway:** Comfortably above pass mark (826 vs. 720), and the D2 recovery is a good sign that earlier domain volatility was mostly small-sample noise rather than real gaps. D1 and D4 are the two domains that still show real misses on a reasonably sized sample (14 and 12 questions respectively) — these are the priority now, not D2.

**Next actions:**
- Review the specific D1 and D4 questions missed on this mock (source: practice.cyberskill.world, "SHOW DETAIL" view) to identify the misconception behind each, not just the correct answer.
- D1 hadn't had a dedicated task-statement drill pass yet (only 1.1 and 1.2 have notes so far per `notes/01-*`) — continue through remaining D1 task statements.
- D4 has had a full task-statement drill pass already per earlier notes; a repeat regression suggests either genuine edge cases in prompt engineering/structured output, or this domain's question pool is just harder/more varied than the drills covered — worth comparing missed questions against existing D4 drill notes.
- Retake a full mock after the D1/D4 drill pass to confirm whether it moves the domain scores.

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
