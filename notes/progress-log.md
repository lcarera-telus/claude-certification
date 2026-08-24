# CCA-F Progress Log

Chronological log of full mock exams and diagnostics only. Newest entry on top. Each entry: source, date, per-domain score, and what it implies for study priority. Task-statement-level drill notes live under `notes/<domain-folder>/<task-folder>/notes.md`, mirroring the folder structure in `projects/claudecertificationguide/`.

**EXAM SCHEDULED: Thursday 2026-09-03, 15:00** (booked as of 2026-08-24 — 10 days out). Delivered by Pearson VUE, 60 items / 120 min, cut score 720/1000.

**The official Exam Guide was read on 2026-08-24** — see `notes/official-exam-guide.md`. Two findings change how this log should be read: (1) the scenario bank is **6, not 8** — the long-tracked "Scenario 8 / agentic AI tools" blind spot does not exist; (2) the guide states that **per-domain percentages are informational and do not determine pass/fail**, only the total scaled score does — which independently confirms the 2026-08-18 conclusion that per-domain bars should not drive study priority. The remaining window is for repeated-misconception review and the multiple-response item format (new, previously unknown), not for adding practice volume.

**Current focus (as of 2026-08-18, updated after Udemy mock exam #3/6):** Third Udemy exam passed at 93% (56/60), tied with exam #1; the three Udemy exams sit in a tight 90-93% band (~902-936/1000 weighted). **The D2/D3 dip flagged on exam #2 did not repeat** — D2 recovered 82%→100%, D3 83%→92%, and D1 hit 100% for the first time. The misses instead moved to **D4 (83%, first Udemy dip)** and **D5 (89%, after two 100%s)**, both 1-2 question deltas. No domain has dipped on two consecutive exams: the aggregate is stable while the decomposition rotates, which is small-sample noise, not a knowledge gap. Next: stop re-prioritising domains off single-exam percentages; hunt for *repeated* misconceptions across exams instead, and spend the time on the two genuinely unmeasured risks — Scenario 8 (agentic AI tools, the CLAUDE.md blind spot) and the unread official Exam Guide.

**Study strategy (decided 2026-07-31; diagnostic loop revised 2026-08-18):** Domain-by-domain, task-statement by task-statement, with periodic full mock exams. As of exam #3/6, per-domain percentages on 9-16 question samples have proven too noisy to set priority — the loop is now "which misconception recurs across exams," reviewed from the missed questions themselves, plus closing known content blind spots (Scenario 8, official Exam Guide) rather than adding practice volume.

---

## 2026-08-18 — Udemy "Anthropic Claude Certified Architect – 3 Full Practice Exams" mock exam #3/6 (Exam mode, 60 questions)

**93% correct (56/60) — PASSED** (72% required to pass). 1 hour 2 minutes — the fastest of the three Udemy attempts (1h07m, 1h11m, 1h02m).

| Domain | Score | % |
|---|---|---|
| D1 Agentic Architecture & Orchestration | 16/16 | 100% |
| D2 Tool Design & MCP Integration | 11/11 | 100% |
| D3 Claude Code Configuration & Workflows | 11/12 | 92% |
| D4 Prompt Engineering & Structured Output | 10/12 | 83% |
| D5 Context Management & Reliability | 8/9 | 89% |

Hand-computed weighted equivalent (same method as the 2026-08-13 and 2026-08-15 entries, using CLAUDE.md's domain weights): ~933/1000 — essentially tied with exam #1 (~936) and above exam #2 (~902).

**The exam #2 prediction resolved in favour of noise.** The previous entry said: "watch D2 and D3 for a third consecutive dip, which would upgrade 'noise' to 'real gap'." Neither dipped — **D2 recovered from 82% to 100%** (its best result on any mock) and **D3 recovered from 83% to 92%**. D1 also hit **100% for the first time** on any 60-question mock.

**Instead, the misses moved to D4 and D5.** D4 fell to 83% (10/12) — its first sub-90% on Udemy after 92% and 92%. D5 fell to 89% (8/9) after two straight 100%s. Both are 1-2 question deltas.

**The three-exam pattern is now the most useful signal in this log, and it is a pattern about the measurement, not about the knowledge.** Across Udemy #1/#2/#3:

| Domain | #1 | #2 | #3 |
|---|---|---|---|
| D1 | 94% | 94% | 100% |
| D2 | 91% | 82% | 100% |
| D3 | 92% | 83% | 92% |
| D4 | 92% | 92% | 83% |
| D5 | 100% | 100% | 89% |
| **Total** | **93%** | **90%** | **93%** |

**No domain has dipped on two consecutive exams.** The total sits in a tight 90-93% band while the 4-6 misses rotate between domains from attempt to attempt. On 9-16 question samples, a single missed question is 6-11 percentage points, so a domain "dropping to 83%" means two wrong answers. That is what small-sample noise looks like: stable aggregate, unstable decomposition. This retires the question that has been open in this log since 2026-07-31 — **the per-domain swings (D2 especially, six swings across two sources) were never a knowledge signal**, and the log's discipline of waiting for ≥2-3 consecutive same-source dips was the right call, because that condition has now been tested three times and never once been met.

**Takeaway:** Three independent 60-question exams at 90-93%, weighted equivalents ~902-936/1000 against a 720 cut, with every domain having scored ≥91% at least once. Readiness is no longer the open question. Per-domain percentages on 9-16 question samples should stop driving study priority — only a domain that dips twice in a row, or a specific repeated misconception found by reviewing the actual missed questions, is worth acting on.

**Next actions:**
- Stop re-prioritising domains off single-exam percentages. Switch the diagnostic loop from "which domain scored lowest" to "which misconception recurs" — review the 4 missed questions here (2× D4, 1× D3, 1× D5) and check whether any of them repeats a miss from exams #1 or #2. A repeat across exams is worth more than any domain bar in this table.
- Continue Udemy exams #4-6 primarily to hunt for repeated misconceptions, not to re-measure readiness — that is now well established.
- Scenario 8 (agentic AI tools) is still the known content blind spot from CLAUDE.md and has never been isolated by any mock's breakdown. It is a bigger unmeasured risk than any 83% domain bar here.
- The official Exam Guide PDF remains unread (CLAUDE.md open question). With scores this consistent, closing that gap and Scenario 8 is a better use of time than more practice volume.

---

## 2026-08-15 — Udemy "Anthropic Claude Certified Architect – 3 Full Practice Exams" mock exam #2/6 (Exam mode, 60 questions)

**90% correct (54/60) — PASSED** (72% required to pass). 1 hour 11 minutes.

| Domain | Score | % |
|---|---|---|
| D1 Agentic Architecture & Orchestration | 15/16 | 94% |
| D2 Tool Design & MCP Integration | 9/11 | 82% |
| D3 Claude Code Configuration & Workflows | 10/12 | 83% |
| D4 Prompt Engineering & Structured Output | 11/12 | 92% |
| D5 Context Management & Reliability | 9/9 | 100% |

Hand-computed weighted equivalent (same method as the 2026-08-13 entry, using CLAUDE.md's domain weights): ~902/1000 — comfortably above the 720 cut.

**D2 dropped back to 82% (9/11)** right after its strongest-ever showing (91%) on Udemy exam #1 two days prior. Across both sources, D2 has now swung 80%→60%→100%→64%→91%→82% over six mocks — always on a small (5-11 question) sample. The pattern still doesn't clearly resolve to "real gap" vs. "noise," but the swing happening *within the same source* just two exams apart is new information: it argues against "different question bank" being the whole explanation for the earlier cyberskill dip, since Udemy alone just showed the same volatility.

**D3 dropped to 83% (10/12)**, a new weak point — its first sub-90% result on Udemy after 92% on exam #1, and its first sub-90% mock result of any kind since 2026-08-04 (92%). One data point; not yet worth treating as a trend, but worth tracking on exam #3.

**D1 (94%), D4 (92%), and D5 (100%) held steady**, consistent with prior mocks — no new signal there.

**Takeaway:** Still comfortably passing, but this exam muddies rather than confirms the "D2 was just noise" read from exam #1. D3 is a new, small flag. Neither is enough yet to redirect study priority — the discipline established in this log is to wait for a pattern across ≥2-3 same-source data points before treating a domain as a real gap, and D2/D3 are each only 1-2 data points into a possible pattern within Udemy specifically.

**Next actions:**
- Continue through Udemy exams #3-6; specifically watch D2 and D3 for a third consecutive dip, which would upgrade "noise" to "real gap worth a dedicated drill pass."
- Review the 6 missed questions (D2 and D3 heaviest) via "Review questions" for the specific misconception, not just the domain tally.
- Hold off on re-prioritizing study time based on a single dip in either domain — consistent with how this log has treated D2 swings on cyberskill in the past.

---

## 2026-08-13 — Udemy "Anthropic Claude Certified Architect – 3 Full Practice Exams" mock exam #1/6 (Exam mode, 60 questions)

**93% correct (56/60) — PASSED** (72% required to pass). 1 hour 7 minutes.

| Domain | Score | % |
|---|---|---|
| D1 Agentic Architecture & Orchestration | 15/16 | 94% |
| D2 Tool Design & MCP Integration | 10/11 | 91% |
| D3 Claude Code Configuration & Workflows | 11/12 | 92% |
| D4 Prompt Engineering & Structured Output | 11/12 | 92% |
| D5 Context Management & Reliability | 9/9 | 100% |

**New source, different scoring scheme:** this Udemy course reports raw overall % against a flat 72% pass mark, not a domain-weighted /1000 score like practice.cyberskill.world. Applying CLAUDE.md's domain weights (D1 27%, D2 18%, D3 20%, D4 20%, D5 15%) to this breakdown by hand gives an equivalent weighted score of ~936/1000 — comfortably above the 720 cut under either scoring scheme.

**All five domains scored ≥91%, the best across-the-board showing to date.** D2 in particular — flagged as "of concern" after the 2026-08-11 cyberskill mock (64%, its third swing in four attempts, never drilled) — came in at 91% here, its strongest showing yet and further evidence the cyberskill volatility was small-sample noise from that specific question bank rather than a real knowledge gap. Caveat: different question source than the dip, so this is a weaker like-for-like comparison than a same-source retake would be — the two banks may simply test D2 differently.

**Takeaway:** Comfortably passing on a new, independent question bank with no domain below 91% is a good signal of broad readiness. This is exam 1 of 6 in the Udemy course.

**Next actions:**
- Review the 4 missed questions ("Review questions") for the specific misconception behind each, not just which domain they fell in.
- Work through the remaining 5 Udemy practice exams as the next diagnostic layer, to see if the strong D2 showing holds up on a larger independent sample and whether any domain-specific weak spot emerges that cyberskill didn't surface.
- If a domain dips on a later Udemy exam, weight that signal more heavily than a cyberskill dip — Udemy's per-domain samples here (9-16 questions) are larger than cyberskill's (5-11).

---

## 2026-08-11 — practice.cyberskill.world mock exam #4 (60 questions, taken while multitasking / "in the background")

**822/1000 — PASSED** (pass mark 720). 49/60 correct (82%).

| Domain | Score | % | Weighted pts |
|---|---|---|---|
| D1 Agentic Architecture & Orchestration | 12/14 | 86% | 231 |
| D2 Tool Design & MCP Integration | 7/11 | 64% | 115 |
| D3 Claude Code Configuration & Workflows | 12/12 | 100% | 200 |
| D4 Prompt Engineering & Structured Output | 10/12 | 83% | 167 |
| D5 Context Management & Reliability | 8/11 | 73% | 109 |

**D1 and D4 — the two domains flagged as priority after 2026-08-04 — both improved** (D1: 71%→86%, D4: 67%→83%), consistent with the D1/D4 drilling done in between. This is a decent signal the domain-by-domain approach is translating into actual score gains, not just task-statement recognition.

**D2 dropped sharply again (100%→64%) and D5 also dropped (91%→73%).** D2 has now swung 80%→60%→100%→64% across four domain-weighted mocks, always on a small 5-11 question sample and never followed by a dedicated drill pass — the swings are as consistent with "no real signal yet" as with a genuine gap. D5's drop is a new, single data point with no prior volatility to compare against.

**Caveat — this mock was taken while multitasking**, unlike the fully-focused 2026-07-31/08-04 attempts. Divided attention is a plausible confound specifically for the D2/D5 dips (careless-error pattern), while the D1/D4 gains holding up *despite* less focus is arguably a stronger signal than it would be under full attention — if drilled domains improved anyway, the improvement is more likely real knowledge, not just careful test-taking.

**Takeaway:** Comfortably above pass mark. Read this as confirmation that the D1/D4 drill pass is working, and as a reason to finally give D2 the same dedicated treatment rather than continuing to write it off as noise after every dip.

**Next actions:**
- Do a dedicated D2 task-statement drill pass — it's the only domain never drilled despite three mock-to-mock swings.
- Retake under full attention (no multitasking) to get a clean read on whether D1/D4 gains hold and whether D2/D5 dips were distraction-driven or real.
- Keep D1/D4 in lighter consolidation rotation rather than must-fix, given two consecutive improvements.

---

## 2026-08-05 — practice.cyberskill.world mock exam ("exam" mode, scenario breakdown, 60 questions)

**71.67% (43/60)** — no /1000 weighted score shown in this mode (unlike the "practice" mode used on 2026-08-04, which converts to a domain-weighted /1000 score).

| Category | Score | % |
|---|---|---|
| code_exploration | 15/18 | 83% |
| extraction_pipeline | 10/13 | 77% |
| research_pipeline | 10/15 | 67% |
| customer_support | 8/14 | 57% |

**Different breakdown scheme than previous entries:** this mode groups questions by exam *scenario* rather than by the five weighted *domains* used elsewhere in this log. Mapping to CLAUDE.md's eight scenarios: `customer_support` ≈ Scenario 1, `research_pipeline` ≈ Scenario 3, `code_exploration` ≈ Scenario 4, `extraction_pipeline` ≈ Scenario 6. Scenarios cut across multiple domains (e.g. `customer_support` tests both D1 orchestration and D2 tool/MCP design), so this table isn't directly comparable to the D1-D5 table in the 2026-08-04 entry — treat it as a complementary signal, not a replacement.

**Directionally consistent with the existing D1 concern:** `customer_support` (57%) and `research_pipeline` (67%) are the two weakest categories, and both are D1-heavy scenarios (agent orchestration, multi-agent coordination) — this lines up with D1 already being flagged as a priority from the 2026-08-04 domain-level mock. `code_exploration` staying strong (83%) also lines up with D3 being solid. `extraction_pipeline` (77%) is harder to read against the earlier D4 finding (67%) since it likely blends D4 (structured output) with D2 (tool design) — not a clean comparison.

**Takeaway:** No pass/fail score is shown in this mode, but 71.67% sits almost exactly at the passing threshold on the 1000-point scale (720/1000 = 72%) — no clear improvement since the 2026-08-04 mock. `customer_support` is now the single weakest category seen across any mock so far, which sharpens (without changing) the existing D1/D4 priority.

**Next actions:**
- Continue the D1/D4 task-statement drill pass already queued from 2026-08-04.
- Within D1, specifically review Scenario 1 (customer support agent) content — escalation policy and the `get_customer`/`lookup_order`/`process_refund`/`escalate_to_human` MCP tool set — since it's now the weakest category by a clear margin.
- Prefer the site's domain-weighted "practice" mode over this scenario-based "exam" mode when tracking progress against the CLAUDE.md D1-D5 weighting; use "exam" mode as a secondary, scenario-level check.

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
