---
name: adr
description: Scaffold a new Architecture Decision Record and append it to DECISIONS.md.
argument-hint: [title] [status]
arguments: [title, status]
disable-model-invocation: true
---

<!--
DESIGN NOTES
Purpose:      Record a decision between real alternatives, in one fixed ADR shape, so
              the reasoning survives after the people who had it move on.
Invocation:   `/adr "Use the built-in node:test runner" Accepted`. Quote a multi-word
              title, or its second word becomes the status.
Why a skill:  The ADR template is a form to fill in on demand, not standing guidance.
              CLAUDE.md holds rules that apply to every turn; this applies to one.
Key syntax:   Named arguments. The `arguments:` frontmatter list declares the names, and
              the body uses `$title` and `$status`. Names map to argument positions in
              order, so `$title` is the first argument and `$status` the second. A named
              placeholder with no matching argument expands to an empty string, unlike an
              indexed one, which is left in the content unchanged.
-->

## Your task

Append a new ADR entry to `DECISIONS.md`. Do not rewrite the entries already there.

Number it one higher than the last entry in the file. Title it `$title`. Record its status
as `$status`. If either value came through empty, ask for it before you write.

Use this shape:

```markdown
## ADR-NNN — $title

**Status:** $status

**Context**
What forced a decision. The constraint, the trigger, and the alternatives that were real.

**Decision**
What was chosen, in the active voice. One decision per ADR.

**Consequences**
What this makes easy, what it makes hard, and what has to be revisited if it is reversed.
```

Fill each section from the conversation so far. Write what was actually decided and why.
Do not leave a placeholder heading with no content under it.
