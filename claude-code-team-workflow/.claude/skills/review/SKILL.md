---
name: review
description: Review the staged changes before a commit or a pull request, and end with an explicit APPROVE or REQUEST CHANGES verdict.
allowed-tools: Bash(git diff *)
disable-model-invocation: true
---

<!--
DESIGN NOTES
Purpose:      Review what is staged, before it becomes a commit or a pull request.
Invocation:   Stage your work, then run `/review`. It takes no arguments.
Why a skill:  A review checklist in CLAUDE.md is loaded into every session and costs
              tokens on every turn, and a developer must still ask for the review by
              hand. A skill loads only when it is run, and it carries its own diff.
Key syntax:   Dynamic context injection, written as an exclamation mark followed by a
              command in backticks. The command runs before the content reaches Claude,
              so Claude receives the diff itself, not an instruction to go and fetch it.
              `allowed-tools` pre-approves those git commands for this turn, and
              `disable-model-invocation` keeps the skill manual.
-->

## Staged changes

Files staged: !`git diff --staged --name-only`

Diff:

!`git diff --staged`

## Your task

Review the staged diff above. If it is empty, say plainly that nothing is staged and stop.
Do not invent a review of changes that are not there.

Otherwise write exactly these four sections.

**Correctness** — Does the change do what it says? Look for wrong conditions, unhandled
error paths, and behaviour that the tests do not cover.

**Tests** — Does every changed endpoint still have a success-path test and an error-path
test? Flag any new behaviour that arrived without a test.

**Style** — Check the change against the conventions in `CLAUDE.md`: ESM only, two-space
indentation, single quotes, semicolons, `node:test` with `node:assert/strict`, port `0` in
tests, and comments that explain the *why*.

**Verdict** — End with one line, exactly `APPROVE` or `REQUEST CHANGES`, and one sentence
of justification. Do not hedge between the two.
