# CCAR-P Progress Log

Chronological log of CCAR-P mock exams and diagnostics. Newest entry on top. Same conventions as `notes/progress-log.md` (the CCAR-F record). Blueprint and weights: `official-exam-guide.md`.

**EXAM SCHEDULED: Thursday 2026-10-22** (booked 2026-10-14, 8 days out).

**Current focus:** close three repeated misconceptions before the exam: soft vs hard controls, per-task model selection, RAG chunking. Then one more mock with full attention. claudearchitectguide gave 986 (62/63); Timo Labs, a second source, gave 80% (16/20). Both are above the pass line, but the second margin is much smaller.

---

## 2026-10-14 — Timo Labs free mock (20 questions) — SECOND-SOURCE CHECK

**80% — 16/20 correct.** Timo treats 72% as a practice pass. Not an official result.

| Domain | Weight | Score |
|---|---|---|
| D1 Solution Design & Architecture | 17% | 2/3 |
| D2 Claude Models, Prompting & Context Engineering | 13% | 2/3 |
| D3 Integration | 19% | 2/3 |
| D4 Evaluation, Testing & Optimization | 16% | 3/3 |
| D5 Governance, Safety & Risk Management | 14% | **1/2** |
| D6 Stakeholder Communication & Lifecycle | 14% | 3/3 |
| D7 Developer Productivity & Enablement | 7% | 3/3 |

**What it shows:**
- This is the check against a second source that the 2026-10-14 claudearchitectguide entry asked for. The gap is large: 98% there, 80% here. This supports the view that the claudearchitectguide bank is easier than the real exam.
- The 4 misses are spread over 4 domains, one each. With 2-3 items per domain, the per-domain bars are noise (same lesson as the CCAR-F log, 2026-08-18).
- 20 items is a small sample: one item is 5 points. 80% is still above the 72% line, and above the ~70% raw (44/63) that claudearchitectguide maps to 720.
- D5 governance is the only domain below 67%. The Reddit report names governance and security trade-offs as the least intuitive area. One miss is not a pattern, but the two signals point the same way.

**Attention caveat:** I took this mock with less focus and read it less carefully than the claudearchitectguide mock. Part of the gap is attention, not knowledge. But the misses below are not random. 3 of 4 repeat a misconception that already appeared elsewhere.

### The 4 misses

**Q6 — D1, objective 1.6 (business value pillars).** A university assistant answers course-planning questions to free advisor time. Students with complex or sensitive issues must still reach an advisor. Which success measure?
- Picked A: "increase the share resolved without any advisor by 30%". **Correct B: cut advisor prep time by 30%, with floors on escalation accuracy and satisfaction.**
- A can be gamed: the share rises when students who needed an advisor do not get one. C (cost per conversation, one annual average) hides missed escalations. D (satisfaction only) measures neither advisor time nor escalation.
- **Misconception:** I took the deflection rate as the goal. The right measure is the business gain *plus guardrail floors* that protect the stated constraint. A metric with no floor rewards the failure the stem warns about.

**Q7 — D5, objective 5.1 (guardrails).** A procurement assistant has tools that accept contract terms and send purchase orders. It must never use them without an employee's explicit approval of that action.
- Picked A: "state the restriction in the system prompt and have Claude ask first". **Correct C: the tools require the employee's approval of the exact terms and recipient before they run.**
- A is advisory: nothing stops the tool if Claude does not follow the prompt. B (daily digest) detects after the fact. D (second model agrees) is not employee approval.
- **Misconception — the same one as the CCAR-F 0% objective (3.1, CLAUDE.md vs hooks/permissions).** A prompt is not an enforcement mechanism. A "must never" rule belongs in the application or tool layer, at the point where the action takes effect. This is now the second exam where this gap cost points.

**Q15 — D3, objective 3.5 (RAG chunking/indexing), select TWO.** A RAG system over maintenance manuals: short fault-code tables plus multi-page procedures. Technicians search by equipment family and revision. An outdated revision is unsafe.
- Picked B + D. **Correct B + C.** B: filter by equipment family and revision, keep section metadata. C: small self-contained chunks that link to the full parent procedure.
- D (boost the newest revision) is a soft ranking: outdated revisions can still appear, and older equipment may need an earlier revision. A (whole manual as one chunk) is too coarse for a single table row.
- **Misconception, two parts.** (1) A safety requirement needs a *hard filter*, not a ranking boost. This is the same soft-vs-hard error as Q7. (2) Small chunks for search precision plus a parent link for full context (small-to-big retrieval). Second miss on objective 3.5, after d3-30 on 2026-10-09.

**Q18 — D2, objective 2.1 (model selection).** One fast model does extraction (meets target) and reputational-risk summaries (miss indirect effects). Do not add cost to any task that already meets its target.
- Picked A: "raise max output length for both tasks and monitor". **Correct C: test a more capable model on the summaries only, and route only those summaries to it if it passes.**
- A: a longer output does not fix a reasoning gap, and it adds cost to extraction. B (move both, compare a combined average) adds cost and hides per-task change. D (random split, overall rating) is the same flaw.
- **Misconception:** when one task type hits the limits of a model, evaluate a stronger model *on that task* and route by task type. Second miss on objective 2.1, after d2-01 on the claudearchitectguide mock: in both, the answer is "measure per task, pay for capability only where the data says it is needed".

### Pattern across all CCAR-P misses (6 total, 2 sources)

| Theme | Misses |
|---|---|
| Soft control where a hard one is needed (prompt, ranking boost) | Q7, Q15 D — plus the CCAR-F 0% on 3.1 |
| Model selection: measure per task, route per task | d2-01, Q18 |
| RAG chunking for mixed tables and long prose | d3-30, Q15 C |
| Success metric without guardrail floors | Q6 |

**Next actions:**
1. Review the three repeated themes above before scheduling. The study is small: one rule each.
   - A "must never" requirement → enforce it in code, tool, or filter. Never in a prompt or a ranking.
   - Model choice → evaluate per task, route per task, smallest model that meets the target.
   - Mixed corpora → structure-aware chunks (whole tables, small-to-big with parent links) plus hard metadata filters.
2. Take the next mock with full attention, so the result is comparable.
3. Then schedule the exam.

---

## 2026-10-14 — claudearchitectguide.com Practice Exam (63 questions, timed exam mode) — FIRST FULL CCAR-P MOCK

**986/1000 — PASS** (cut 720). 62/63 correct (98%); 44 correct needed for 720. Exam mode, the same shape as the real exam (63 items). Duration 78m 52s of 120m. Results: https://claudearchitectguide.com/results?id=dd4f55b6-27e7-42df-955f-00343debbfdc (works only in the browser that took it; the site stores attempts in `localStorage` key `ccarp.v2.ccar-p.attempts`).

| Domain | Weight | Score |
|---|---|---|
| D1 Solution Design & Architecture | 17% | 11/11 |
| D2 Models, Prompting & Context Engineering | 13% | **7/8** |
| D3 Integration | 19% | 12/12 |
| D4 Evaluation, Testing & Optimization | 16% | 10/10 |
| D5 Governance, Safety & Risk Management | 14% | 9/9 |
| D6 Stakeholder Communication & Lifecycle | 14% | 9/9 |
| D7 Developer Productivity & Enablement | 7% | 4/4 |

Several items were multi-response (select TWO) and two were matching items. All of them were correct.

**Calibration against CCAR-F:** the last CCAR-F mock was 939 and the real exam was 865, about 75 points lower. This bank's distractors are also easier than real-exam distractors. Even a 150-point discount on 986 leaves a wide margin above 720.

**The only miss: d2-01, objective 2.1 (select Claude models based on trade-offs).**
- Stem: a router classifies 350,000 short messages per day into eight queues. Accuracy on a labelled test set is comparable across the model family. The business is sensitive to latency and cost.
- Correct: **use the smallest model that meets the accuracy target, validated by ongoing evaluation.**
- Distractors: "most capable model, errors always cost more than compute" puts an assumption in place of measurement. "Mid-tier as a compromise, no formal evaluation" skips the evaluation that must drive the choice. "Alternate randomly between models" makes behavior impossible to debug.
- Misconception to fix: when the stem says accuracy is *comparable* and volume is high, the measured data has already made the decision. Pick the cheapest model that meets the target, and keep the evaluation running. The pattern is the same as the official sample answers: measurement beats assumption.
- Which distractor I picked is not certain: the export gave the selected index, but the option-order array for d2-01 was cut off.

**The 2026-10-09 D3 miss, now identified: d3-30, objective 3.5 (RAG chunking and indexing).** A corpus mixes long prose with numeric tables. A uniform 512-token window splits tables. Correct (select TWO): **index each table as a single unit with a text serialisation of rows and headers**, and **attach the section heading path to each chunk's metadata and prepend it to the chunk text**. Smaller windows split tables more often. Converting tables to prose loses the exact figures. Indexing only tables discards most of the corpus. This item was not in the 2026-10-14 mock, so it is not re-tested yet.

**What it shows:**
- Two diagnostics from one source, 82/84 correct in total. Each miss is a single item in a different objective. No pattern repeats.
- Timing is not a risk: 79 minutes for 63 items leaves 40 minutes spare.
- Source caveat stays: one third-party bank. A second source (Timo Labs) would reduce the risk of a bank that is easier than the real exam.

**Next actions:**
1. Optional: sit the Timo Labs 20-question mock as a check from a second source.
2. Schedule the CCAR-P on Partner Academy ($175).
3. Before the exam, review RAG chunking/indexing (3.5) and model selection (2.1), the two objectives with a miss.

---

## 2026-10-09 — claudearchitectguide.com Quick Quiz (21 questions) — FIRST CCAR-P DIAGNOSTIC

**957/1000 — PASS** (cut 720). 20/21 correct (95%); 15 correct needed for 720. Results: https://claudearchitectguide.com/results?id=190df107-d7f0-455b-b171-51c07c64f61e

**Not a score projection.** Quick-quiz mode shows each answer after you submit it. The site itself says to sit a timed mock for a projection. The 128m 6s duration is not meaningful for 21 items; the clock ran while the page stayed open.

| Domain | Weight | Score |
|---|---|---|
| D1 Solution Design & Architecture | 17% | 4/4 |
| D2 Models, Prompting & Context Engineering | 13% | 3/3 |
| D3 Integration | 19% | **3/4** |
| D4 Evaluation, Testing & Optimization | 16% | 3/3 |
| D5 Governance, Safety & Risk Management | 14% | 3/3 |
| D6 Stakeholder Communication & Lifecycle | 14% | 3/3 |
| D7 Developer Productivity & Enablement | 7% | 1/1 |

Objective coverage: 21 of 38 sampled, 1 not clean (the D3 miss). Clean objectives visible in the screenshot: 4.5 cost & latency, 4.6 logging & monitoring, 3.2 authn/authz gaps, 3.8 progressive discovery, 1.4 multi-agent orchestration.

**What it shows:**
- The CCAR-F base transfers. D1, D2, and D7 overlap heavily with CCAR-F and were clean.
- The "new" domains (D4, D5, D6) were also clean, 9/9. This is the first evidence against the expectation that governance and stakeholder items would be the weak area. Three items per domain is a small sample.
- The only miss is in D3, the heaviest domain (19%). Identified 2026-10-14 as d3-30, objective 3.5 (RAG chunking/indexing of tables); see the entry above.
- Source caveat: third-party, unofficial bank. The Reddit poster warns that most CCAR-P prep material is Claude-generated (see `resources.md`).

**Next actions:**
1. Record the missed D3 question: the misconception, not only the correct answer.
2. Sit a timed full mock on claudearchitectguide.com, Timo Labs, or both, to get a real projection.
3. If the timed mock is also well above 720, decide on scheduling the exam.
