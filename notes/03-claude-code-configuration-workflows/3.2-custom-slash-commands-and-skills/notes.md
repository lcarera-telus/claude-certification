# Task Statement 3.2 — Skills Architecture (Personal vs Project, Frontmatter, Scoping)

Domain: D3 (Claude Code Configuration & Workflows).

---

## 2026-07-31 — Drill

Two sessions (Socratic tutoring → practice exam): **5/5 on the exam, zero hesitation.** Exam simulator confirmed reasoning already built in the tutoring session.

**Solid cold:**
- Project-scoped vs. user-scoped skills — paths, sharing behaviour, when to use each; nailed the "committed but teammates still can't see it" trap.
- `context: fork` — correctly tied to output isolation specifically, not tool access or argument handling (the usual trap).
- Skills vs. CLAUDE.md — on-demand vs. automatic distinction, correct in both sessions.
- Personal skill customisation — different name in `~/.claude/skills/`, never overwrite the team version.

**Rough edges (from the Socratic session, not the exam itself):**
1. Introduced two out-of-scope concepts — `model-invocable: false` and directory-level CLAUDE.md loading timing. Neither is real material. **General rule going forward: an unfamiliar-sounding term in a distractor is itself a signal it's fabricated — don't assume unfamiliar = something you forgot.**
2. `argument-hint` — first phrasing was loose ("configures what hint the user sees"). Precise trigger: it prompts for required parameters **when the skill is invoked without arguments**, not a general-purpose hint display.
3. `allowed-tools` — jumped to the accurate real-world behaviour (pre-approval) without anchoring the exam's official register first (**restriction**). Lead with "restricts tool access" as the expected exam answer.

**Takeaway:** The two heaviest-weighted traps for this task statement — file-structure (directory+SKILL.md vs. flat .md) and scoping (project vs. user) — are solid. Only gap is precise frontmatter wording for `argument-hint` and `allowed-tools`; worth a 30-second review before the real exam, not a re-drill.
