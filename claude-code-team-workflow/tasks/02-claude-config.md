# Task 02 — Claude Code configuration layer

You are implementing one work package. This spec is self-contained. Do not assume any shared
conversation history.

**Read the reference section at the bottom of this file before you write anything.** It
contains excerpts from the current official Claude Code documentation, fetched on
2026-08-30. Your training data may describe an older syntax. Where your memory and the
excerpts disagree, the excerpts win.

## Context

`claude-code-team-workflow/` is an educational reference repo teaching engineers how a team
configures Claude Code. Task 01 built the substrate: a small Express service with tests.
Your job is the configuration layer that wraps it.

The configuration is the product here. Each file must teach as well as work.

## Working directory

Paths are relative to `claude-code-team-workflow/`. Do not touch files outside it. Do not
modify anything under `src/`, `test/`, `tasks/`, or `docs/`, and do not create or edit
`README.md`, `CLAUDE.md`, `DECISIONS.md`, or `COORDINATION.md`. Those are owned elsewhere.

## Files to create

1. `.claude/settings.json`
2. `.claude/settings.local.example.json`
3. `.claude/skills/review/SKILL.md`
4. `.claude/skills/test-gen/SKILL.md`
5. `.claude/skills/adr/SKILL.md`
6. `.claude/skills/standup/SKILL.md`
7. `.claude/commands/adr-legacy.md`

## Requirements

### 1. `.claude/settings.json` — shared, committed

This file is checked into version control and applies to everyone who clones the repo.

Include:

- `"defaultMode": "plan"` under a `permissions` object, so sessions start in plan mode.
- A `permissions.allow` list pre-approving the safe, common commands for this repo:
  `Bash(npm test)`, `Bash(npm install)`, `Bash(node --test *)`, `Bash(git diff *)`,
  `Bash(git log *)`, `Bash(git status *)`.
- A `permissions.ask` entry for `Bash(git push *)`, so pushing always prompts.
- A `permissions.deny` list blocking `Bash(rm -rf *)` and `Read(./.env)`.

JSON does not support comments. Because this file must still teach, add a top-level
`"$schema"` key pointing at
`https://json.schemastore.org/claude-code-settings.json`, and a top-level `"_comment"` key
whose value is a short string explaining that this file is committed, that Claude Code
ignores unknown keys beginning with an underscore, and that per-person overrides belong in
`settings.local.json`. Keep the string under 200 characters.

### 2. `.claude/settings.local.example.json` — personal, template

A committed *example* of the personal overrides file. The real `settings.local.json` is
gitignored (task 01 added that entry).

Show two realistic personal overrides that a developer might want without imposing them on
teammates:
- a `"model"` key,
- a `permissions.allow` entry for something individual, such as `Bash(gh pr view *)`.

Add a `"_comment"` key explaining: copy this file to `settings.local.json`, that the local
file takes precedence over the shared one, and that it must never be committed.

### 3. Four skills

Each is a directory under `.claude/skills/<name>/` containing `SKILL.md`. The directory name
becomes the command name. See the reference section for exact frontmatter and substitution
syntax.

Every `SKILL.md` must begin with a comment header, placed **after** the closing `---` of the
frontmatter and before the instructions, in this shape:

```markdown
<!--
DESIGN NOTES
Purpose:      what this command is for
Invocation:   how a developer triggers it, with an example
Why a skill:  why this belongs in a skill rather than in CLAUDE.md
Key syntax:   which documented feature this command demonstrates
-->
```

Keep each `SKILL.md` body focused — under 60 lines including the header.

#### `/review` — structured review of staged changes

- `description`: makes clear it reviews staged changes before a commit or PR.
- Must use **dynamic context injection** to pull in the staged diff, so Claude receives the
  actual diff rather than an instruction to fetch it. Use `` !`git diff --staged` `` and
  `` !`git diff --staged --name-only` ``.
- Set `allowed-tools` to permit the git commands it injects.
- Set `disable-model-invocation: true` — this is a command a developer triggers on purpose,
  not something Claude should start on its own.
- The body instructs a structured review with fixed sections: Correctness, Tests, Style
  (referencing the repo conventions), and a final explicit verdict of `APPROVE` or
  `REQUEST CHANGES`.
- Instruct it to say so plainly when the staged diff is empty, rather than inventing a
  review.

#### `/test-gen` — generate tests for a file (demonstrates argument passing)

- Takes a file path as its argument. **Use `$0` for the first argument.** Read the reference
  section carefully: indices are zero-based, so the first argument is `$0`, not `$1`.
- Set `argument-hint` to `[file-path]`.
- Set `disable-model-invocation: true`.
- The body tells Claude to read the file at `$0` and add tests to the matching file under
  `test/`, following the repo's existing conventions: the built-in `node:test` runner,
  `node:assert/strict`, port `0` binding, no external test framework.
- Include an instruction that the new tests must actually pass, and that Claude should run
  `npm test` to confirm.
- In the DESIGN NOTES, state explicitly that `$0` is the first argument and that writing
  `$1` here would be an off-by-one that silently expands to the *second* argument.

#### `/adr` — scaffold an ADR (demonstrates named arguments)

- Use the `arguments:` frontmatter field to declare **named** arguments, and reference them
  by name in the body. Declare two: `title` and `status`.
- Set `argument-hint` to `[title] [status]`.
- Set `disable-model-invocation: true`.
- The body instructs Claude to append a new ADR entry to `DECISIONS.md` using `$title` and
  `$status`, in the standard ADR shape: Context, Decision, Consequences.
- In the DESIGN NOTES, note that named arguments map to positions in order, so `$title` is
  the first argument and `$status` the second, and that a named placeholder with no matching
  argument expands to an empty string.

#### `/standup` — summarize recent commits

- Must use dynamic context injection for git history. Use a **multi-line fenced injection
  block** (see reference) running `git log --oneline -15` and `git status --short`.
- Set `allowed-tools` to permit those git commands.
- Set `disable-model-invocation: true`.
- The body asks for a three-part standup: what landed recently, what is in progress based on
  working-tree state, and anything that looks blocked. Instruct it to write plain prose a
  teammate could paste into a chat channel, not a commit list.

### 4. `.claude/commands/adr-legacy.md`

A single markdown file, not a directory — the older custom-command format, which still works.

This file exists to demonstrate that both formats produce a command. Name it `adr-legacy` so
it does **not** collide with the `adr` skill; the file name becomes the command name.

Give it frontmatter with a `description` and `argument-hint`, and a body that scaffolds an
ADR from `$ARGUMENTS`. Keep it deliberately simpler than the skill version.

Add a comment header explaining: this is the legacy `.claude/commands/` format; command files
support the same frontmatter **except** `name` and `paths`, which are ignored there; if a
skill and a command shared a name, the skill would win; and skills are now recommended
because they support supporting files and a directory of their own.

## Acceptance criteria

1. All seven files exist at the exact paths listed.
2. Both JSON files parse as valid JSON. Verify with
   `node -e "JSON.parse(require('fs').readFileSync('<path>','utf8'))"`.
3. Every `SKILL.md` opens with `---` on **line 1** — no blank line, no comment above it.
   Claude Code only reads frontmatter when the opening `---` is the file's first line.
4. Every `SKILL.md` frontmatter contains at least `name` and `description`.
5. `/test-gen` uses `$0`, not `$1`, for its file-path argument.
6. `/adr` declares `arguments:` in frontmatter and references those names in the body.
7. `/review` and `/standup` each contain at least one `` !`...` `` or ` ```! ` injection, and
   each injection's command is covered by that skill's `allowed-tools`.
8. Every injected command appears at the start of a line or immediately after whitespace.
9. All four skills carry the DESIGN NOTES header with all four fields filled in.
10. No file created or modified outside the seven listed.

## When you are done

Print the list of files created and the output of the two `JSON.parse` checks. Do not commit
anything to git.

---

# Reference — current Claude Code documentation

Excerpts fetched 2026-08-30 from `https://code.claude.com/docs/en/skills.md`. Treat these as
authoritative over your training data.

## Custom commands have been merged into skills

> **Custom commands have been merged into skills.** A file at `.claude/commands/deploy.md`
> and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and work the same
> way. Your existing `.claude/commands/` files keep working. Skills add optional features: a
> directory for supporting files, frontmatter to control whether you or Claude invokes them,
> and the ability for Claude to load them automatically when relevant.

> If you have files in `.claude/commands/`, those work the same way, but if a skill and a
> command share the same name, the skill takes precedence.

> Files in `.claude/commands/` support the same frontmatter, except `name` and `paths`, which
> Claude Code ignores in a command file. You invoke a command file by its file name. Skills
> are recommended since they support additional features like supporting files.

## Where skills live

> | Personal   | `~/.claude/skills/<skill-name>/SKILL.md`     | All your projects              |
> | Project    | `.claude/skills/<skill-name>/SKILL.md`       | This project only              |

## Frontmatter

> Claude Code reads the frontmatter only when the opening `---` is the file's first line.
> Otherwise it treats the whole file, `---` markers included, as skill content.

Relevant fields:

> | `argument-hint` | No | Hint shown during autocomplete to indicate expected arguments.
> Example: `[issue-number]` or `[filename] [format]`. |

> | `arguments` | No | Named positional arguments for `$name` substitution in the skill
> content. Accepts a space-separated string or a YAML list. Names map to argument positions
> in order. |

> | `disable-model-invocation` | No | Set to `true` to prevent Claude from automatically
> loading this skill. Use for workflows you want to trigger manually with `/name`. Default:
> `false`. |

> | `allowed-tools` | No | Tools Claude can use without asking permission during the turn
> that invokes this skill. The grant clears when you send your next message. Accepts a space-
> or comma-separated string, or a YAML list. |

Example of a task-content skill:

```yaml
---
name: deploy
description: Deploy the application
disable-model-invocation: true
allowed-tools: Read Grep
---
```

## Available string substitutions

> | `$ARGUMENTS` | All arguments passed when invoking the skill. |
> | `$ARGUMENTS[N]` | Access a specific argument by 0-based index, such as `$ARGUMENTS[0]`
> for the first argument. |
> | `$N` | Shorthand for `$ARGUMENTS[N]`, such as `$0` for the first argument or `$1` for
> the second. |
> | `$name` | Named argument declared in the `arguments` frontmatter list. Names map to
> positions in order, so with `arguments: [issue, branch]` the placeholder `$issue` expands
> to the first argument and `$branch` to the second. |

> Indexed arguments use shell-style quoting, so wrap multi-word values in quotes to pass them
> as a single argument. For example, `/my-skill "hello world" second` makes `$0` expand to
> `hello world` and `$1` to `second`.

> An indexed placeholder with no corresponding argument, such as `$2` when only one argument
> was passed, stays in the content unchanged. A named placeholder from the `arguments`
> frontmatter with no matching argument expands to an empty string.

## Inject dynamic context

> The `` !`<command>` `` syntax runs shell commands before the skill content is sent to
> Claude. The command output replaces the placeholder, so Claude receives actual data, not
> the command itself.

Worked example from the docs:

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`

## Your task
Summarize this pull request...
```

> The inline form is only recognized when `!` appears at the start of a line or immediately
> after whitespace. If `!` follows another character, as in `` KEY=!`cmd` ``, the placeholder
> is left as literal text and the command does not run.

> For multi-line commands, use a fenced code block opened with ` ```! ` instead of the inline
> form:

````markdown
## Environment
```!
node --version
git status --short
```
````

> Substitution runs once over the original file. Command output is inserted as plain text and
> is not re-scanned for further `` !`<command>` `` placeholders.

## Settings precedence

Excerpt from `https://code.claude.com/docs/en/settings.md`:

> Commit `.claude/settings.json` so everyone who clones the repository gets the same
> permissions, hooks, telemetry, and plugins. Each teammate can still override it for
> themselves in their own `.claude/settings.local.json`, so personal exceptions don't need a
> commit.

Precedence, highest first: managed settings → `claude --settings` → `.claude/settings.local.json`
→ `.claude/settings.json` → `~/.claude/settings.json`.

> | Project local | `.claude/settings.local.json` | You, in this one project only. Claude Code
> keeps it out of git when it creates the file; if you create it by hand, add it to
> `.gitignore` yourself |
