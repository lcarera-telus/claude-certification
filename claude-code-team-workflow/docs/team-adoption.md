# Team adoption

How a team shares Claude Code configuration without stepping on each other, and how to make
the tooling stick.

## Shared vs. personal: the file split

Settings resolve across five layers. Highest precedence first:

| Layer | File | Applies to |
|---|---|---|
| Managed | `managed-settings.json`, MDM, or the console | Everyone in the org; cannot be overridden |
| Command line | `claude --settings` | You, this session |
| **Project local** | **`.claude/settings.local.json`** | **You, this project** |
| **Shared project** | **`.claude/settings.json`** | **Everyone in the project** |
| User | `~/.claude/settings.json` | You, every project |

The two middle rows are the ones a team touches daily, and the ordering is the point:
**project local beats shared project**. A teammate can always override the team file for
themselves without a commit and without a discussion.

> Commit `.claude/settings.json` so everyone who clones the repository gets the same
> permissions, hooks, telemetry, and plugins. Each teammate can still override it for
> themselves in their own `.claude/settings.local.json`, so personal exceptions don't need a
> commit.

### What goes in which

| Content | File | Reason |
|---|---|---|
| Permission rules for repo commands | `.claude/settings.json` | Everyone benefits; everyone should agree |
| `defaultMode` | `.claude/settings.json` | A team norm about caution |
| Hooks that enforce standards | `.claude/settings.json` | Enforcement is worthless if optional |
| Your model preference | `.claude/settings.local.json` | Nobody else's concern |
| Approvals for your personal tools (`gh`, your editor) | `.claude/settings.local.json` | Your machine, your tools |
| Anything with a credential or a private URL | `.claude/settings.local.json` | Must never be committed |

This repo ships both: a committed `.claude/settings.json`, and
`.claude/settings.local.example.json` as a template to copy.

### Keeping the local file out of git

> Claude Code keeps it out of git when it creates the file; if you create it by hand, add it
> to `.gitignore` yourself.

Specifically, the first time Claude Code writes `.claude/settings.local.json` in a repository
that does not already ignore it, it adds `**/.claude/settings.local.json` to your **global**
git excludes. That protects you and nobody else — a teammate who creates the file by hand
before Claude Code ever writes it has no such protection.

So do not rely on it. This repo's `.gitignore` lists the path explicitly. Verify:

```bash
git check-ignore -v .claude/settings.local.json
```

A path echoed back means it is ignored. Silence means it is not, and you are one `git add .`
from committing your personal overrides.

## Review CLAUDE.md like source code

`CLAUDE.md` and `.claude/settings.json` change how the tool behaves for **every engineer on
the team**. A careless line in CLAUDE.md is a bug that manifests as bad output in other
people's sessions, days later, with no stack trace pointing back at it.

Treat both as reviewable code.

### What to look for in a CLAUDE.md diff

- **Is it specific enough to verify?** "Use 2-space indentation" is reviewable. "Write clean
  code" is not — it consumes tokens and changes nothing.
- **Does it contradict an existing rule?** If two rules conflict, Claude may pick either one
  arbitrarily, and the resulting behaviour looks random. This is the single highest-value
  thing a reviewer catches, because the author was only looking at their own addition.
- **Does it belong in CLAUDE.md at all?** A multi-step procedure belongs in a skill, where it
  loads on demand. A rule for one directory belongs in `.claude/rules/` with `paths:`
  frontmatter. See `docs/claude-md-annotated.md`.
- **Is the file still under 200 lines?** Past that, the docs warn that adherence *drops*. An
  addition can make the whole file less effective, so growth is a review concern even when
  each line is individually fine.
- **Is it a hard requirement pretending to be a note?** CLAUDE.md is context, not enforcement.
  "Never push to main" in CLAUDE.md is a suggestion; in `permissions.deny` or a `PreToolUse`
  hook it is a rule. If a reviewer would be alarmed by the instruction being ignored, it is in
  the wrong file.

### A worked entry

From this repo's CLAUDE.md:

```markdown
- **Adding a test framework.** The built-in `node:test` runner is a deliberate choice, not
  an oversight. Reaching for jest or supertest adds dependencies this repo does not want.
```

This earns its place on three counts: it overrides a strong and otherwise-sensible prior, it
is verifiable, and it states the *reason*, so a future maintainer can tell whether it still
applies. Compare with "keep dependencies minimal", which is agreeable, unfalsifiable, and
changes no behaviour.

## Wiring a command into an existing habit

New tooling fails when it needs a new habit. It sticks when it attaches to one that already
exists.

**The existing habit:** staging changes, then opening a pull request.

**The wiring:** run `/review` between those two steps.

```bash
git add -p              # habit you already have
/review                 # the new step, ~15 seconds
git push && gh pr create
```

`/review` works here because it fits the shape of the moment:

- **It needs no arguments.** The command injects the staged diff itself, with
  `` !`git diff --staged` ``. Anything requiring you to remember a file path would not survive
  contact with a Friday afternoon.
- **It runs on exactly what you are about to push.** Staged changes, not the working tree, not
  the branch. The scope matches the decision you are making.
- **It ends in a verdict.** `APPROVE` or `REQUEST CHANGES`, no hedging. A review that trails
  off into "consider possibly looking at" gets ignored.
- **`disable-model-invocation: true`.** It fires when you ask, never on its own. A command
  that surprises people gets disabled.

The gain is not that Claude reviews better than your teammate. It is that it reviews
*earlier* — the typo, the missing test, the debug log you left in are caught before a human
spends attention on them. Your reviewer's attention then goes to the design.

### Rolling it out

1. **One command, one team, two weeks.** Four commands introduced at once means none of them
   get learned.
2. **Put the invocation in the PR template.** A checkbox reading "ran `/review`" does more for
   adoption than any announcement.
3. **Let the CLAUDE.md entries accumulate from real corrections.** The trigger is: someone
   typed the same correction twice. That keeps the file honest and short, and it means every
   line has a story behind it.
4. **Review the config in the same PR as the code that motivated it.** A settings change with
   no accompanying context is hard to evaluate six weeks later.

## Onboarding a new teammate

Everything they need is in the repo:

```bash
git clone <repo> && cd claude-code-team-workflow
npm install && npm test          # confirm the substrate works
cp .claude/settings.local.example.json .claude/settings.local.json
claude
```

At that point they have the team's permissions, the team's default mode, all four commands,
and the project's CLAUDE.md — because those are committed files, not machine setup. The only
thing they configure is the personal overrides file.

In a session, `/context` shows what actually loaded, under **Memory files**. If a file is not
listed there, Claude cannot see it, and no amount of rewording the instruction will help.
