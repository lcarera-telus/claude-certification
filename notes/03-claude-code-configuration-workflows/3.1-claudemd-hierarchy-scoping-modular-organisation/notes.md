# Task Statement 3.1 — CLAUDE.md Hierarchy, Scoping, and Modular Organisation

Domain: D3 (Claude Code Configuration & Workflows).

---

## 2026-07-31 — Re-drill

**5/5 — flawless.**

Confirms the previous re-drill recommendation worked: no "root CLAUDE.md as a level name" slips this time.

**Traps confirmed cold (flagged by the tool as worth re-confirming even at 5/5, since a perfect score can mask surface pattern-matching):**
- Dev A/Dev B trap → always a team-standards doc misplaced in user-level config instead of project-level. Never blame `/memory`, MCP servers, or `.claude/rules/` compatibility.
- `/memory` is diagnostic only — reveals what's loaded, never triggers/reloads/forces loading.
- Two valid project-level locations: root `CLAUDE.md` and `.claude/CLAUDE.md` — both correct, don't assume only one.
- `.claude/rules/` vs. skills: rules apply automatically as always-in-context guidance; skills require invocation for task-style workflows. Don't conflate.
- `@import` is the fix whenever a question describes conventions copy-pasted across multiple directories.

**Takeaway:** Task Statement 3.1 is now solid. The terminology fix from the previous session held under a fresh drill — good signal, not just luck. Ready to move on to 3.3 as previously planned.

---

## 2026-07-31 — Initial drill

Overall approval: **85%**.

**Strong:**
- Solid grasp of the three hierarchy levels (user / project / directory) from the first question.
- Nailed the classic "new team member" exam trap on the second attempt once redirected — root cause was misplaced user-level config.
- `@import` and `/memory` explained accurately, no correction needed — best answers of the session.
- 50+ directories bridging scenario — correctly rejected directory-level CLAUDE.md and identified the duplication anti-pattern; applied reasoning, not just recall.

**Weak:**
- **Terminology precision:** repeatedly said "root CLAUDE.md" / "root claude.md" instead of user-level / project-level / directory-level. Distractors on the real exam exploit exactly this confusion — drill exact terms.
- **Root cause diagnosis (Dev A vs Dev B trap):** first instinct was an *extra* personal instruction rather than a *misplaced* one. Flagged as one of the highest-yield traps on the exam — re-drill this scenario specifically.
- **Scope discipline:** introduced "lazy loading" for `.claude/rules/` — not part of the official material. Reasoning instinct was fine, but don't import outside concepts under exam conditions.

**Takeaway:** Reinforces the 2026-07-29 diagnostic finding that D3 is a weak domain. The terminology slip (root vs. user/project/directory) is a recurring, fixable pattern — worth a dedicated flashcard pass before the next drill.

**Next actions:**
- Re-drill the Dev A/Dev B diagnostic scenario until root-cause identification is automatic.
- Flashcard pass on user-level / project-level / directory-level naming — eliminate "root" as a level name.
- Proceed to Task 3.3 per recommendation.
