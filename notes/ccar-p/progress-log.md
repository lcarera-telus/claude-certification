# CCAR-P Progress Log

Chronological log of CCAR-P mock exams and diagnostics. Newest entry on top. Same conventions as `notes/progress-log.md` (the CCAR-F record). Blueprint and weights: `official-exam-guide.md`.

**Current focus:** find out if the CCAR-P is worth a $175 attempt without more study. The first diagnostic says the CCAR-F knowledge transfers. A timed full mock is the next data point.

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
- The only miss is in D3, the heaviest domain (19%). The specific objective is not recorded yet.
- Source caveat: third-party, unofficial bank. The Reddit poster warns that most CCAR-P prep material is Claude-generated (see `resources.md`).

**Next actions:**
1. Record the missed D3 question: the misconception, not only the correct answer.
2. Sit a timed full mock on claudearchitectguide.com, Timo Labs, or both, to get a real projection.
3. If the timed mock is also well above 720, decide on scheduling the exam.
