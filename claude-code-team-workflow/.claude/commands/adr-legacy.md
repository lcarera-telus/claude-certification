---
description: Scaffold an ADR from a one-line title. The older .claude/commands/ format, kept as a working example.
argument-hint: [title]
---

<!--
DESIGN NOTES
Purpose:      Scaffold an ADR the short way, and show that a single markdown file under
              `.claude/commands/` still produces a working command.
Invocation:   `/adr-legacy Use the built-in node:test runner`. The file name becomes the
              command name, so this file is `/adr-legacy`.
Why a file:   This is the legacy `.claude/commands/` format. Custom commands have been
              merged into skills, but command files are not deprecated and keep working.
              The name is `adr-legacy`, not `adr`, so it does not collide with the
              `/adr` skill. If a skill and a command shared a name, the skill would win.
Key syntax:   `$ARGUMENTS` expands to everything typed after the command name, as one
              string. Command files support the same frontmatter as a skill, except
              `name` and `paths`, which Claude Code ignores here. Skills are recommended
              for new work, because a skill owns a directory and can carry supporting
              files next to its `SKILL.md`. This one deliberately stays smaller than the
              `/adr` skill: one argument, no named substitution, no injected context.
-->

## Your task

Append a new ADR to `DECISIONS.md`, titled `$ARGUMENTS`, numbered one higher than the last
entry in the file. Leave the status as `Proposed`.

Write three sections under the title: **Context**, **Decision**, and **Consequences**. Fill
each one from the conversation so far. Do not leave an empty heading.
