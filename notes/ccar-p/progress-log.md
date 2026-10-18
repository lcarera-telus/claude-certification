# CCAR-P Progress Log

Chronological log of CCAR-P mock exams and diagnostics. Newest entry on top. Same conventions as `notes/progress-log.md` (the CCAR-F record). Blueprint and weights: `official-exam-guide.md`.

**EXAM SCHEDULED: Thursday 2026-10-22** (booked 2026-10-14, 8 days out).

**Current focus:** review D5 governance (preventive vs detective controls, LLM-specific failure modes) and 4.4 diagnosis by layer before the exam. The second full mock (2026-10-18) gave 943 (59/63). Earlier: claudearchitectguide 986 (62/63), Timo Labs 80% (16/20).

---

## 2026-10-18 — claudearchitectguide.com Practice Exam (63 questions, timed exam mode) — SECOND FULL CCAR-P MOCK

**943/1000 — PASS** (cut 720). 59/63 correct (94%); 44 correct needed for 720. Duration 68m 11s of 120m.

| Domain | Weight | Score |
|---|---|---|
| D1 Solution Design & Architecture | 17% | 11/11 |
| D2 Models, Prompting & Context Engineering | 13% | 8/8 |
| D3 Integration | 19% | 12/12 |
| D4 Evaluation, Testing & Optimization | 16% | **8/10** |
| D5 Governance, Safety & Risk Management | 14% | **7/9** |
| D6 Stakeholder Communication & Lifecycle | 14% | 9/9 |
| D7 Developer Productivity & Enablement | 7% | 4/4 |

D2 and D3 are clean. Both domains had misses in earlier sessions (2.1 model selection, 3.2 and 3.5).

### The 4 misses

**Item 2 — D5.** At design review, list the realistic failure modes of an LLM system. Which framing is the best starting point?
- Picked A: infrastructure risks (provider outages, rate limits, timeout cascades). **Correct C: hallucination, prompt injection, context truncation, stale knowledge, tool misuse, inconsistent handling of ambiguous input.**
- Why A is wrong: the risks are real, but standard engineering already covers them. A misses every failure mode that is specific to the model. B (a tested prompt makes other risks negligible) ignores that injection, staleness, and truncation occur with any prompt. D (alignment training handles safety) gives safety to a vendor that does not know this application's stakes.
- **Misconception:** I listed the risks of any distributed system. A risk register for an LLM system must start with the failure modes of the technology itself, so each one gets an owner and a mitigation.

**Item 36 — D4, select TWO.** Record which fields for each model call, so that cost and behavior can be attributed later without stored payloads?
- Picked A + D. **Correct C + D.** C: token counts split by cached input, uncached input, and output. D: the stop reason.
- Why A is wrong: every log line already has a timestamp, and a timestamp attributes nothing. B (client library version) matters only at upgrade time. E (characters) is a weak proxy for the output token count.
- **Misconception:** I did not see that cost attribution needs the token *split*. The split lets you rebuild a bill and check if caching works. The stop reason catches silent truncation and unresolved tool loops, two failures that look like successes.

**Match item (item number not in the screenshot) — D4, objective 4.4.** For each production symptom, select the layer to investigate first.
- Statements 1, 4, 5 correct: wrong answers after a content refresh → retrieval and indexing. A section order stated twice in different words → prompt and instructions. A small model loses detail on 40-page documents → model capability fit.
- Statement 2: the assistant apologizes instead of calling its lookup, and the logs show no call. Picked tool integration. **Correct: prompt and instructions.**
- Statement 3: the agent reports success, the record is unchanged, and the integration returned a non-2xx status. Picked prompt and instructions. **Correct: tool integration.**
- **Misconception:** I swapped the two. The rule: if the model never attempts the call, the defect is in what the model was told. If the call failed and the agent still reports success, the integration swallowed the error. Use the logs: "no call attempted" puts the integration out of scope.

**Item 49 — D5, select TWO.** A payments assistant must never emit a full card number, with no tolerated failure rate.
- Picked D + E. **Correct A + E.** A: tokenise card numbers upstream, so the full value never enters the context. E: a deterministic pattern check on every response that blocks display.
- Why D is wrong: a daily audit finds the breach after the customer saw it. It detects, it does not prevent. B (scoring model) and C (system-prompt rule) are probabilistic, so "no tolerated failure rate" excludes them as the guarantee.
- **Misconception:** the soft-vs-hard rule held (I did not pick B or C). But I picked a detective control in place of a preventive one. The strongest control removes the data from the model's context. If the value never reaches the model, the model cannot emit it.

### What it shows

- 43 points below the first mock from the same bank (986). The 4 misses are in D4 and D5 only, two each.
- 3 of 4 misses are multi-response or match items. Each time I selected the correct count, so these are knowledge misses, not format errors.
- Item 49 extends the repeated soft-vs-hard theme. Order of strength for a "must never" rule: keep the data out of the context, then a deterministic block, then probabilistic layers, then detection after the fact.
- Items 2 and 49 are in D5. The Reddit report and Timo Q7 also point at D5. D5 is the area to review before the exam.
- Timing is not a risk: 68 minutes for 63 items.

**Next actions (4 days to the exam):**
1. Review D5: the LLM-specific failure-mode list (item 2), and the preventive-vs-detective order of controls (item 49).
2. Review 4.4 diagnosis by layer. Map each symptom to the evidence that rules layers out.
3. Learn the per-call log fields: split token counts (cached, uncached, output) and stop reason.

---

## 2026-10-17 — claudearchitectguide.com domain drill: D1 Solution Design & Architecture (34 questions, checked as I went)

**974 — 33/34 (97%).** Not a projection: I saw each answer before the next item. Duration 131m 58s (not timed).

| Objective | Score |
|---|---|
| 1.1 Business problem to solution | 6/6 |
| 1.2 End-to-end architecture | **5/6** |
| 1.3 Architectural pattern choice | 6/6 |
| 1.4 Multi-agent orchestration | 5/5 |
| 1.5 Decomposition | 5/5 |
| 1.6 Business value alignment | 6/6 |

### The 1 miss

**Item 9 — 1.2, match each.** For each weakness in a deployed solution, pick the end-to-end stage that is missing or underspecified. Options: input handling, processing, output contract, feedback loop.
- Statements 1–4 correct: rotated scans → input handling. No one knows if quality changed → feedback loop. A required field is sometimes absent → output contract. Reviewer corrections are saved and never used → feedback loop.
- Statement 5: good answers for short documents, incomplete answers for long ones. Picked input handling. **Correct: processing.**
- Why input handling is wrong: the input is valid. Nothing is malformed or rotated. The design has no strategy for inputs above a certain size (chunking, map-reduce, multi-pass).
- **Rule:** if the input is *invalid*, the fix is input handling. If the input is valid but the quality degrades with *size*, the fix is processing. Quality that tracks document length is a processing problem.

### What it shows

- D1 is solid. The only miss is one statement in a match item, and it was a stage-boundary error, not a gap.
- 1.2 also had Round 2 Q3 correct (feedback loops). The feedback-loop pattern held twice in this item.

---

## 2026-10-15 — claudearchitectguide.com domain drill: D3 Integration (38 questions, checked as I went)

**882 — 33/38 (87%).** The site marks a domain drill as *not* a projection: I saw each answer before the next item. It still counts for coverage and the mistakes deck. Duration 279m 55s (not timed).

| Objective | Score |
|---|---|
| 3.1 Capability bloat | 5/5 |
| 3.2 Authn & authz gaps | **3/5** |
| 3.3 Accuracy-latency trade-offs | 5/5 |
| 3.4 Observability at scale | 5/5 |
| 3.5 RAG chunking & indexing | 4/5 |
| 3.6 Retrieval strategy | 4/5 |
| 3.7 Integration protocol choice | 3/4 |
| 3.8 Progressive discovery | 4/4 |

### The 5 misses

**Item 7 — 3.2, select TWO.** The agent writes to the CRM with one integration account. Compliance cannot tell which employee made a change.
- Picked D only. **Correct B + D.** D: propagate the end user's identity to the CRM. B: session traces with the user id and a correlation id carried into every downstream call.
- **Format error, not knowledge.** I did not select the second option. D was right.
- C (model writes the name in a free-text note) is unauthenticated and forgeable. E (longer retention) keeps more entries that all say "integration account". A (rotate credentials) does not show who did what.

**Item 10 — 3.2.** A payroll assistant uses one service account with organisation-wide read access. The system prompt tells the model to return only the requester's data.
- Picked D ("service accounts cannot legally be used with AI"). **Correct C: authorisation sits in prompt instructions, not in the access-control layer.**
- **Real miss, and the repeated theme.** This is soft vs hard control again: Timo Q7, Timo Q15, and the CCAR-F 0% on 3.1. The model must not be able to retrieve what the user may not see. Fix it with per-user scoped credentials or pass-through auth. D is not a real rule. A widens the blast radius. B (store raw user passwords) is a credential anti-pattern.

**Item 18 — 3.7, match each.** Connection mechanism per integration need.
- Statement 5: a microservice calls the model once to classify a document inside its own controlled pipeline. Picked MCP server. **Correct: direct API integration.**
- **Translation error.** I read statement 5 wrong. The rule: MCP is for standard, reusable, discoverable access by many consumers. A single owned pipeline call needs no discovery layer.

**Item 20 — 3.5, select TWO.** A RAG assistant sometimes answers from superseded content after the nightly refresh.
- Picked C only. **Correct C + E.** C: version metadata in the index, filter out superseded versions at query time. E: automated re-index pipeline that validates completeness and embedding consistency after each refresh.
- **Format error, not knowledge.** C was right.
- B (prompt: prefer the newest source) only works when the model sees a conflict. The usual failure is one stale chunk with nothing against it. Again soft vs hard. D (larger window) retrieves more stale content. A (weekly spot-check) is too slow.

**Item 35 — 3.6, match each.** Retrieval strategy per need. Two statements wrong.
- Statement 3: invoices above 10,000 euros in the last quarter. Picked lexical/exact-match. **Correct: structured query over metadata.** A threshold and a date range are field filters, not text matches.
- Statement 5: clauses that mean the same as a given paragraph, in any wording. Picked structured query. **Correct: semantic vector search.**
- Rule: meaning and paraphrase → semantic. Exact string → lexical. Thresholds, dates, fields → structured. Natural text *and* exact codes → hybrid.

### What it shows

- 3 of 5 misses are format or reading errors (items 7, 18, 20). On the real exam, each item states how many responses to select. **Count the selections before Next.**
- Item 10 is the fourth soft-vs-hard miss across CCAR-F and CCAR-P. It is still the top risk. Rule: if the stem says "only", "never", or "must", find the option that enforces it below the model.
- 3.2 at 3/5 is the only objective below 80%. One of the two misses is a format error.

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
