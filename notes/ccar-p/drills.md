# CCAR-P drills

Hard-drill rounds on the three heaviest domains (D3 19%, D1 17%, D4 16%), before the 2026-10-22 exam. Questions written by Claude in the exam's style. They are not from an exam bank, so a score here is not a projection. The value is the misconception record. Newest round on top.

---

## Round 2 — 2026-10-14 — 4/6

(Q6 first recorded as A+E. I meant A+D and typed E by mistake. Counted as correct. The cost-at-volume note below stays useful.)

Harder than round 1: distractors that are partly right, and "what first" items.

| Q | Domain / objective | My answer | Correct |
|---|---|---|---|
| 1 | D3 3.8 progressive discovery vs monolithic context | A | **D** |
| 2 | D3 3.2 authn/authz gaps | C | C |
| 3 | D1 1.2 end-to-end with feedback loops | A+C | A+C |
| 4 | D1 1.1 translate business problem | C | C |
| 5 | D4 4.4 diagnose failures | D | **C** |
| 6 | D4 4.1 / 4.5 metrics, cost-performance | A+D (typed A+E) | A+D |

**Q1 — 120 MCP tools, 45k tokens per request, selection accuracy falling, all tools legitimately needed.**
- Picked A: split into 15 agents behind an LLM router. **Correct D: keep a few frequent tools loaded, plus tool search that loads other definitions on demand.**
- Why A is wrong: the router still has to choose among 15 domains, so the selection problem moves instead of going away. Tasks that span servers now need several agents and coordination. Each request gets an extra hop. B (prompt caching) cuts cost and latency of the prefix, but 120 tools stay in context, so selection accuracy does not improve. C (one-line descriptions) makes selection *worse*.
- **Misconception:** reaching for multi-agent decomposition to fix a context-size problem. Objective 3.8 names the answer directly: progressive discovery instead of monolithic context. Multi-agent is for work that decomposes, not for a tool list that is too long.

**Q5 — quality drop after a release that changed prompt, model version, and top-k 5→15. Offline eval with fixed retrieved contexts shows no prompt+model difference.**
- Picked D: eval set not representative. **Correct C: the 10 extra chunks dilute the context.**
- Why D is wrong: the offline eval was a controlled experiment. It held retrieval constant and changed only prompt + model, and it found no difference. That rules out A and B. The only variable it did not test is top-k. D is a generic doubt that the evidence does not support. It also does not explain why quality dropped *at this release*.
- **Misconception:** treating a diagnostic item as "which explanation is possible" instead of "which explanation the evidence leaves". Same rule as the official sample Q3: pick the cause that the triggering change can explain, and use what the stem already ruled out.

**Q6 — X: 94%, p95 9 s, $0.04. Y: 91%, p95 2.5 s, $0.01. Requirements: p95 < 4 s, success ≥ 90%, 1M tasks/month.**
- Answered A+D (typo E in the first submission). **Correct A+D.**
- Why E is wrong: at 1M tasks/month, $0.04 vs $0.01 is $40k vs $10k per month, $360k per year. A small unit cost does not make cost negligible at volume.
- Why D is right: X fails the hard p95 requirement (9 s > 4 s), so it is out before any trade-off. Y is the only model that meets every requirement.
- **Rule (not a miss):** (1) Hard requirements are filters. Apply them first, and only then compare what is left. (2) Multiply unit cost by volume before calling it small.

### Pattern after round 2

- **Model selection / cost-performance (2.1, 4.5)** — 2 misses so far (d2-01, Timo Q18). Q6 was right. Rule: filter by hard requirements, multiply cost by volume, then pick the smallest model that meets the target, per task.
- **Diagnosis by elimination (4.4)** — new. Use what the stem rules out. Pick the cause the evidence leaves.
- **Progressive discovery (3.8)** — new. A long tool list is a context problem. Fix it with on-demand loading, not with more agents.

---

## Round 1 — 2026-10-14 — 6/6

Too easy: each item had one obvious distractor. Useful only as a check that the soft-vs-hard-control rule held (Q1 tool scoping, Q3 code-controlled workflow): it did.

Items: D3 tool scoping + per-user authz; D3 hybrid lexical + metadata filter for exact codes; D1 workflow vs agent for a fixed audited sequence; D1 coordinator scope overlap; D4 stratified high-stakes eval slices + per-category floors; D4 A/B with broken randomization.
