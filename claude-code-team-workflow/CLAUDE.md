# CLAUDE.md

Project instructions for `claude-code-team-workflow`, a small Express service used as a
teaching substrate for Claude Code configuration.

<!--
MAINTAINER NOTE — not sent to Claude.
Block-level HTML comments are stripped before this file is injected into context, so notes
like this cost zero tokens. See docs/claude-md-annotated.md for why each section below
exists. Keep this file under 200 lines; the docs recommend that ceiling for adherence.
-->

## Commands

```bash
npm install     # install dependencies (express only)
npm test        # run the full suite: node --test test/
npm start       # run the service on PORT, default 3000
```

Run a single test file with `node --test test/app.test.js`.

There is no build step, no linter, and no TypeScript. If you find yourself adding one, stop
and raise it first.

## Repo layout

- `src/app.js` — the Express app, exported without `listen()` so tests can import it
- `src/server.js` — the only file that binds a port
- `test/app.test.js` — tests, using the built-in `node:test` runner
- `.claude/` — the configuration layer this repo exists to demonstrate
- `docs/` — teaching documents about Claude Code itself
- `tasks/` — work-package specs used to build this repo

## Code style

- ESM only. Use `import` / `export`. This project sets `"type": "module"`; `require` fails.
- Two-space indentation. Single quotes. Semicolons.
- Tests use `node:test` and `node:assert/strict`. Do not add jest, mocha, or supertest.
- Tests bind port `0` so the OS assigns a free port. Never hardcode a port in a test.
- Keep `src/` under 150 non-comment lines. This repo teaches configuration, not application
  code. If the app grows, the repo has drifted from its purpose.
- Comment the *why*, not the *what*. A newcomer should be able to read `src/` top to bottom.

## Testing rules

- Every endpoint needs a test for its success path and its error path.
- Run `npm test` before you say work is finished. Do not report a result you have not run.
- A test that needs the server running must start it on port `0` and close it afterwards,
  including when the assertion throws.

## Things Claude gets wrong in this repo

These are real, repeated mistakes. They are listed because each one has happened.

- **Changing the `??` in the limit fallback back to `||`.** `src/app.js:76` reads
  `parsed ?? DEFAULT_LIMIT`, and that is correct: `??` falls back only on `null` and
  `undefined`, so an explicit `?limit=0` survives it and returns zero items. The line was
  deliberately seeded as `||` and fixed as a worked example; see `DECISIONS.md` (ADR-003)
  and `docs/plan-mode-guide.md`. Do not "simplify" it back.
- **Adding a test framework.** The built-in `node:test` runner is a deliberate choice, not
  an oversight. Reaching for jest or supertest adds dependencies this repo does not want.
- **Calling `listen()` in `src/app.js`.** The app is exported unbound on purpose. Moving the
  `listen()` call into `app.js` makes the test suite bind a real port and fail under
  parallel runs.
- **Writing `$1` for the first skill argument.** In `.claude/skills/`, argument indices are
  zero-based: `$0` is the first argument. `$1` silently expands to the *second* one, which
  is usually empty, so the command appears to do nothing.
- **Editing `.claude/settings.local.json`.** That file is personal and gitignored. Team-wide
  changes belong in `.claude/settings.json`, which is committed and code-reviewed.
- **Assuming `.claude/commands/` is deprecated.** It is not. Command files still work. Skills
  are recommended for new work, and win on a name collision.

## Conventions for changes

- Changes to `.claude/settings.json` or `CLAUDE.md` are reviewed like source code. They
  change how the tool behaves for every teammate. See `docs/team-adoption.md`.
- Run `/review` on staged changes before opening a pull request.
- Record a decision with `/adr` when you choose between real alternatives.

<!--
On-demand vs. always-loaded: the four commands in .claude/skills/ are deliberately NOT
described in detail here. Their bodies load only when invoked, so documenting them at length
in CLAUDE.md would pay their token cost in every single session for no benefit.
-->
