# CLAUDE.md, annotated

This document reproduces the project `CLAUDE.md` section by section, with commentary on why
each section exists, what happens without it, and what it costs in tokens.

Read this once. Then read `CLAUDE.md` on its own — it should feel obvious.

## The thing to understand first

CLAUDE.md is **context, not configuration**. The docs are explicit:

> Claude treats them as context, not enforced configuration. To block an action regardless of
> what Claude decides, use a PreToolUse hook instead.

and:

> CLAUDE.md content is delivered as a user message after the system prompt, not as part of the
> system prompt itself. Claude reads it and tries to follow it, but there's no guarantee of
> strict compliance, especially for vague or conflicting instructions.

Everything below follows from that. A CLAUDE.md entry raises the probability of a behaviour;
it does not guarantee it. When you need a guarantee, you need a hook or a permission rule —
not a more emphatic sentence.

---

## Section: the title and the maintainer note

```markdown
# CLAUDE.md

Project instructions for `claude-code-team-workflow` ...

<!--
MAINTAINER NOTE — not sent to Claude.
...
-->
```

**Why it exists.** One line of orientation, then a note aimed at humans.

**The trick.** Block-level HTML comments are stripped before the file is injected:

> Block-level HTML comments (`<!-- maintainer notes -->`) in CLAUDE.md files are stripped
> before the content is injected into Claude's context. Use them to leave notes for human
> maintainers without spending context tokens on them.

So maintainer notes are **free**. Reasoning about why a rule exists is often longer than the
rule, and putting it in a comment keeps the loaded file short without losing the reasoning.

**Without it.** The rationale either bloats every session or gets lost entirely, and the next
maintainer deletes a rule because nobody recorded why it was added.

---

## Section: Commands

```markdown
npm install / npm test / npm start
```

**Why it exists.** This is the highest-value content in any CLAUDE.md. Without it Claude
infers the test command by reading `package.json`, or guesses `npm run test:unit`, or invents
a script that does not exist. Every session pays that cost again.

**Why it names the negative case too.** "There is no build step, no linter, and no
TypeScript" prevents a plausible wrong action. Absence is not observable — Claude cannot see
that you decided against a linter, only that there isn't one, which reads as an omission to
fix.

**Token cost.** ~60 tokens, paid every session, and worth it. This is the canonical example of
content that belongs in CLAUDE.md rather than on demand: short, universally relevant, and
needed before any work starts.

---

## Section: Repo layout

**Why it exists.** Cheap orientation that saves exploratory tool calls.

**Where it earns its place, and where it doesn't.** Keep it to a handful of lines that carry a
*reason* — "exported without `listen()` so tests can import it" is the kind of thing no
directory listing reveals. A full file tree does not belong here; Claude can run `ls`.

The `/doctor` checkup makes exactly this cut:

> it cuts content Claude can derive from the codebase, such as directory layouts, dependency
> lists, and architecture overviews, and keeps pitfalls, rationale, and conventions that
> differ from tool defaults.

**Without it.** A few extra Glob and Read calls per session. Mild.

---

## Section: Code style

**Why it exists.** These are the conventions that differ from the defaults a model would
otherwise assume. "Do not add jest, mocha, or supertest" is worth more than "write clean
code", because it is verifiable and it contradicts a strong prior — reaching for a test
framework is the common reflex.

**Specificity is the whole game:**

> * "Use 2-space indentation" instead of "Format code properly"
> * "Run `npm test` before committing" instead of "Test your changes"

Vague instructions consume tokens and change nothing.

**Without it.** Correct code in a foreign style, and a review cycle spent on formatting
instead of behaviour.

---

## Section: Things Claude gets wrong in this repo

**Why it exists.** This is the section most projects lack and most need. Each entry is a
mistake that actually happened, and each names a specific wrong action rather than a virtue.

The docs give a clear trigger for adding one:

> * Claude makes the same mistake a second time
> * A code review catches something Claude should have known about this codebase
> * You type the same correction or clarification into chat that you typed last session

**Why these particular entries.** Look at what they have in common: every one is a case where
the *sensible general behaviour* is wrong *here*.

- Reverting `parsed ?? DEFAULT_LIMIT` to the shorter-looking `||` is normally an innocuous
  simplification. Here it reintroduces a documented bug (ADR-003) that a test now guards.
- Adding supertest is normally reasonable. Here it violates the zero-framework constraint.
- `$1` for a first argument is a near-universal habit from shell scripting. In skills the
  indices are zero-based, so `$0` is first — and `$1` fails *silently*, expanding to an empty
  second argument.

A rule that merely restates good general practice is wasted context. A rule that overrides a
strong, sensible prior is where the tokens go.

**Without it.** The same correction typed into chat every week, and a fixed teaching example
that has to be un-fixed.

---

## Section: Conventions for changes

**Why it exists.** Points at the workflow: `/review` before a PR, `/adr` for real decisions.
Short pointers, not procedures.

**Why the commands are not documented here in detail.** This is the token-budget decision that
matters most, and the file's closing comment says so explicitly. The four commands live in
`.claude/skills/`. A skill's body loads **only when invoked**:

> Unlike CLAUDE.md content, a skill's body loads only when it's used, so long reference
> material costs almost nothing until you need it.

Describing `/review`'s output format in CLAUDE.md would pay for it in every session, including
the ones that never review anything.

---

## What belongs where

The decision is not "important vs. unimportant". It is **how often it is needed** against
**how much it costs**.

| Content | Goes in | Because |
|---|---|---|
| Build and test commands | CLAUDE.md | Needed before any work; two lines |
| Conventions that differ from defaults | CLAUDE.md | Cheap, and they override strong priors |
| Repeated mistakes | CLAUDE.md | Nothing else prevents them |
| A multi-step procedure | A skill | Loads on invocation, costs nothing until then |
| Rules for one directory or file type | `.claude/rules/` with `paths:` | Loads only when a matching file is touched |
| Personal preference | `~/.claude/CLAUDE.md` or `CLAUDE.local.md` | Not your teammates' business |
| A hard prohibition | `settings.json` `permissions.deny`, or a hook | Enforced regardless of what Claude decides |

The docs state the ceiling plainly:

> **Size**: target under 200 lines per CLAUDE.md file. Longer files consume more context and
> reduce adherence.

Note "**and reduce adherence**" — an over-long CLAUDE.md is not merely expensive, it is *less
effective*. Every marginal line dilutes the ones that matter.

### The import trap

The intuitive fix for a large CLAUDE.md is to split it into `@path` imports. That does not
save any context:

> Splitting into `@path` imports helps organization but doesn't reduce context, since imported
> files load at launch.

Imports are an *organizational* tool. The mechanisms that actually reduce loaded context are
**path-scoped rules** (`.claude/rules/` with `paths:` frontmatter, loaded only when a matching
file is read) and **skills** (loaded on invocation). Reach for those.

Imports resolve relative to the file containing them, and nest to a maximum depth of four
hops. To mention a path without importing it, wrap it in backticks.

## Verifying any of this

Two commands, worth knowing:

- `/memory` — lists memory file locations across scopes and opens them for editing. It is
  diagnostic: it shows you where files live, it does not force a reload.
- `/context` — shows what **actually loaded** in this session, under **Memory files**. If your
  file is not listed there, Claude cannot see it, and no amount of rewording will help.

When an instruction is being ignored, check `/context` first. The usual cause is a file that
never loaded, or two rules that contradict each other — where Claude may pick either one.
