# Task 01 — Sample Express application and tests

You are implementing one work package. This spec is self-contained. Do not assume any
shared conversation history. Everything you need is in this file.

## Context

The repository `claude-code-team-workflow/` is an educational reference repo. It teaches
engineers how a team configures Claude Code. A tiny Express service is the substrate that
the configuration layer operates on. The application is deliberately trivial. The
configuration and documentation are the real product.

Your job is the substrate only. Do not create any `.claude/` files. Do not create any
markdown documentation. Another work package covers those.

## Working directory

All paths below are relative to `claude-code-team-workflow/` inside the current repository.
Create the directory if it does not exist. Do not touch any file outside it.

## Files to create

1. `claude-code-team-workflow/package.json`
2. `claude-code-team-workflow/src/app.js`
3. `claude-code-team-workflow/src/server.js`
4. `claude-code-team-workflow/test/app.test.js`
5. `claude-code-team-workflow/.gitignore`

## Requirements

### `package.json`

- Name `claude-code-team-workflow`, version `1.0.0`, `"private": true`.
- Set `"type": "module"` so the files use ESM `import` syntax.
- One runtime dependency: `express` (version `^5.2.1`).
- No other dependencies. No dev dependencies. Use the built-in Node test runner.
- Scripts:
  - `"test": "node --test test/"`
  - `"start": "node src/server.js"`
- Requires Node 18 or later. Add an `"engines"` field saying `">=18"`.

### `src/app.js`

Export an Express app. Do not call `listen()` in this file — that belongs in `server.js`,
so tests can import the app without opening a port.

Hold an in-memory array of item objects at module scope. Each item is
`{ id: <number>, name: <string> }`. Seed it with exactly 5 items, ids 1 through 5, names
`"item-1"` through `"item-5"`.

Define a module-scope constant `DEFAULT_LIMIT` set to `3`.

**Endpoint 1 — `GET /health`**

Responds `200` with JSON `{ "status": "ok" }`.

**Endpoint 2 — `GET /items`**

Accepts an optional `limit` query parameter. Returns JSON
`{ "items": [...], "limit": <the limit actually applied> }` with status `200`.

Parse the parameter as follows, and follow this exactly:

```js
// Parse the raw query value into a number, or undefined when absent.
const raw = req.query.limit;
const parsed = raw === undefined ? undefined : Number(raw);

// Reject values that are not usable as a count.
if (parsed !== undefined && (!Number.isInteger(parsed) || parsed < 0)) {
  return res.status(400).json({ error: 'limit must be a non-negative integer' });
}

// Apply the caller's limit, falling back to the default when none was given.
const limit = parsed || DEFAULT_LIMIT;
```

Then slice the items array to `limit` and return it with the applied `limit` value.

**Important:** write the fallback line exactly as `const limit = parsed || DEFAULT_LIMIT;`.
Do not "improve" it to `??`. Do not add a comment calling it a bug. A later work package
deals with that line. Write it as specified and move on.

A request with a non-numeric limit such as `?limit=abc` must produce the `400` response,
because `Number('abc')` is `NaN` and `Number.isInteger(NaN)` is `false`.

### `src/server.js`

Import the app from `./app.js` and start it listening. Read the port from
`process.env.PORT`, defaulting to `3000`. Log a single line saying which port it listens on.
Keep this file under 15 lines.

### `test/app.test.js`

Use the built-in Node test runner and assertion library only:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
```

Do not add supertest, jest, mocha, or any other test dependency.

To test the app without binding a fixed port, start it on port `0` (the OS assigns a free
port), read the assigned port from the server address, use `fetch` against it, and close the
server afterwards. Write a small helper that starts the server, runs a callback, and always
closes the server, including when the callback throws.

Write these tests. All of them must pass against the code as specified above:

1. `GET /health` returns status `200` and body `{ status: 'ok' }`.
2. `GET /items` with no query returns `200`, exactly 3 items, and `limit` equal to `3`.
3. `GET /items?limit=2` returns `200`, exactly 2 items, and `limit` equal to `2`.
4. `GET /items?limit=abc` returns status `400`.
5. `GET /items?limit=99` returns `200` and all 5 items, because the array is shorter than
   the requested limit.

Do not write a test asserting the behaviour of `?limit=0`. That case is covered later.

### `.gitignore`

Include at minimum:

```
node_modules/
.claude/settings.local.json
```

Add a short comment above the second line explaining that personal Claude Code settings stay
out of version control while the shared `.claude/settings.json` is committed.

## Commenting requirements

This repository is read top to bottom by engineers learning the tooling. The comment density
must be high enough that a newcomer understands not just what the code does but why.

- Start `src/app.js` with a block comment explaining the file's role and, specifically, why
  the app is exported without calling `listen()` — that tests import the app directly, so no
  port is bound and tests cannot collide on a busy port.
- Comment each endpoint with its contract: method, path, parameters, response shape, status
  codes.
- In `test/app.test.js`, add a block comment explaining why the tests bind port `0` rather
  than a fixed port, and why the built-in runner is used instead of a test framework.
- Explain any non-obvious line. Do not comment self-evident lines such as variable
  assignment with an obvious name.

## Constraints

- `src/app.js` and `src/server.js` together must be **under 150 lines**, excluding comments
  and blank lines. Comments do not count against this budget — write them generously.
- ESM syntax throughout (`import` / `export`), no `require`.
- No frameworks beyond Express. No linter configs, no build step, no TypeScript.
- Do not create `README.md`, `CLAUDE.md`, or anything under `docs/` or `.claude/`.

## Acceptance criteria

The reviewer checks each of these. Your work is accepted only if all pass.

1. `npm install` completes in `claude-code-team-workflow/`.
2. `npm test` passes with all 5 tests green, no failures and no unhandled rejections.
3. `src/app.js` contains the line `const limit = parsed || DEFAULT_LIMIT;` verbatim.
4. `GET /items?limit=0` returns 3 items — the specified parsing makes `0` fall through to
   the default. This is expected right now. Do not fix it.
5. Combined non-comment, non-blank line count of `src/` is under 150.
6. No files created outside the five listed above.
7. Every endpoint carries a contract comment; `app.js` and the test file each carry the
   block comment described above.

## When you are done

Print a short summary listing the files you created and the result of running `npm test`.
Do not commit anything to git. The coordinator reviews and commits.
