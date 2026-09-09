---
name: standup
description: Summarize recent commits and working-tree state as a short standup update a teammate can paste into chat.
allowed-tools: Bash(git log *), Bash(git status *)
disable-model-invocation: true
---

<!--
DESIGN NOTES
Purpose:      Turn git history and working-tree state into a standup update written for a
              human, not a machine.
Invocation:   `/standup`, usually before the daily call. It takes no arguments.
Why a skill:  This is a workflow a developer runs at a moment of their choosing. It has
              no bearing on how Claude edits code, so it does not belong in CLAUDE.md,
              which is loaded on every turn.
Key syntax:   A multi-line fenced injection block. The fence below opens with three
              backticks and an exclamation mark, which runs every line inside it, rather
              than the inline one-command form used by `/review`. Both commands run
              before the content is sent, and both are covered by `allowed-tools`.
-->

## Repository state

```!
git log --oneline -15
git status --short
```

## Your task

Write a standup update in three parts.

**What landed** — What was finished recently, read from the commit history above. Group
related commits into one statement of the work they add up to.

**In progress** — What is being worked on right now, inferred from the modified, staged,
and untracked files in the working tree.

**Blocked or at risk** — Anything that looks stuck: a branch with no recent commits, work
left half-staged, or a change that touches something the repository warns about.

Write plain prose that a teammate could paste straight into a chat channel. Do not list
commit hashes or file names one by one. Say what the work means. If a section has nothing
in it, say so in one short sentence and move on.
