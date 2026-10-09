# CCAR-P Official Exam Guide — distilled

Source: **Claude Certified Architect – Professional Exam Guide, Version 1.0, effective July 2026** (exam code CCAR-P). PDF at `notes/ccar-p/ccar-p-exam-guide-v1.0.pdf` (copied from `~/Downloads`), 11 pages, read 2026-10-09. This is the authoritative reference for CCAR-P; where any third-party source in `resources.md` disagrees, **this wins**.

## What this settles

Third-party sites disagreed on several facts. The official guide resolves them:

| Third-party claims | Official |
|---|---|
| 60 or 63 items | **63** |
| $125 or $175 | **$175** (checkout shows any partner-tier discount) |
| Scenario-based like CCAR-F | The guide **does not mention scenarios**. No "4 of 6" structure. Items are written against domain objectives directly |
| Foundations required | **No prerequisites.** Experience is recommended, not required |

## Format and scoring

63 items · 120 minutes (~1.9 min/item, slightly tighter than CCAR-F's 2.0) · multiple-choice **and multiple-response**, each item states how many to select · scaled 100–1,000, **cut score 720** · $175/attempt · valid 12 months.

Criterion-referenced, same as CCAR-F. Per-domain percentages on the score report are informational only; pass/fail uses the total scaled score.

## Blueprint

| # | Domain | Weight | Overlap with CCAR-F |
|---|---|---|---|
| 3 | Integration | **19%** | High: MCP vs API, tool scoping, auth. **New:** RAG chunking/indexing, retrieval strategies |
| 1 | Solution Design & Architecture | 17% | High: workflow vs agentic, multi-agent, decomposition. **New:** business value pillars |
| 4 | Evaluation, Testing & Optimization | 16% | Partial. **New:** eval datasets, A/B testing, metrics |
| 5 | Governance, Safety & Risk Management | 14% | Partial: HITL, guardrails. **New:** GDPR/HIPAA/FedRAMP, bias/fairness |
| 6 | Stakeholder Communication & Lifecycle | 14% | **None.** Fully new |
| 2 | Claude Models, Prompting & Context Engineering | 13% | High: few-shot, caching, context windows. **New:** model selection, Skills |
| 7 | Developer Productivity & Operational Enablement | 7% | High: Claude Code config for teams |

Roughly half the blueprint maps onto CCAR-F material. The new ground is D6 (all of it), compliance in D5, evaluation methodology in D4, and RAG in D3.

### Objectives by domain

**D1 Solution Design & Architecture (17%)**
- Translate business problems into Claude-based solutions
- Design end-to-end architectures (input → processing → output → feedback loops)
- Select architectural patterns (workflow, agentic, augmented LLM)
- Design multi-agent systems and orchestration strategies
- Apply decomposition techniques
- Align solutions to business value pillars (efficiency, transformation, productivity, cost, performance SLAs)

**D2 Claude Models, Prompting & Context Engineering (13%)**
- Select Claude models based on trade-offs
- Design system prompts, templates, guardrails
- Apply zero-shot, few-shot, chain-of-thought
- Optimize context windows and token usage
- Implement prompt reuse (caching, modular prompts, Skills)

**D3 Integration (19%)**
- Evaluate tool/agent configuration for **capability bloat**
- Analyze authn/authz requirements to find security gaps
- Evaluate accuracy-latency trade-offs
- Analyze observability challenges; select monitoring at scale
- Design a RAG pipeline with chunking and indexing strategies
- Match retrieval strategy to data shape and query pattern
- Select the integration mechanism: **MCP vs API/CLI vs agent-to-agent**
- Evaluate **progressive discovery vs monolithic context**

**D4 Evaluation, Testing & Optimization (16%)**
- Define metrics (accuracy, latency, cost, safety, security)
- Design eval datasets and test frameworks with mixed methodologies
- Conduct A/B testing and iterative improvement
- Diagnose prompt failure, hallucinations, model mismatch
- Optimize token usage, latency, cost-performance
- Monitor with logging and observability tools

**D5 Governance, Safety & Risk Management (14%)**
- Implement guardrails and safety controls
- Identify risks, limitations, failure modes
- Apply human-in-the-loop validation
- Ensure compliance (GDPR, HIPAA, FedRAMP)
- Address bias, fairness, transparency

**D6 Stakeholder Communication & Lifecycle Management (14%)**
- Conduct structured discovery and requirement gathering
- Communicate architectural decisions and trade-offs
- Manage stakeholder feedback loops and expectations (including SLAs)
- Document architectures and give implementation guidance
- Support lifecycle phases (discovery, design, handoff, monitoring, iteration)

**D7 Developer Productivity & Operational Enablement (7%)**
- Configure Claude tools and environments for teams (e.g. Claude Code)
- Improve developer workflows with AI-assisted tooling
- Support debugging and operational issue resolution

## Official sample questions — the pattern behind each answer

1. **D3, least privilege.** Support agent has refund/delete tools staff never use. Answer: **remove the tools**. Logging and confirmation prompts are detective/compensating controls, not privilege removal. A bigger model is irrelevant to authorization scope.
   *Same principle as CCAR-F D2 tool scoping: eliminate the attack surface instead of guarding it.*
2. **D2, prompt caching.** Same 8k-token system prompt on every request. Answer: **static content first, enable prompt caching**. Truncation loses required policy; a smaller model risks quality; moving it into few-shot does not create a cacheable prefix.
3. **D4, diagnosis.** RAG gives confident wrong answers after a document refresh; model and latency unchanged. Answer: **check retrieval/indexing first** (broken re-index, mismatched embeddings). Pick the cause that the triggering change can actually explain.

Distractor style matches CCAR-F: "add monitoring", "use a bigger model", and "add a confirmation step" are the recurring wrong answers.

## Official prep advice

- Self-assess against every blueprint objective
- Read official docs: Claude API, models, prompt engineering, MCP, Skills
- Build and operate one end-to-end solution **including RAG, evaluation, and observability**
- Practice decisions: model selection, integration protocols, security trade-offs

## Logistics (same as CCAR-F)

Registration through Anthropic Partner Academy, delivery by Pearson VUE (online or test center). Cancel/reschedule up to 24h before. Retakes: 14 / 30 / 90 days, max 4 attempts per rolling 12 months, **limits are per exam**. Closed book, NDA before start.

**Renewal:** on-time renewal is a **free, non-proctored assessment** on Partner Academy. A lapsed credential needs a full retake at full fee. This also applies to CCAR-F.
