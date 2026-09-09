---
name: test-gen
description: Generate tests for one source file, following this repository's node:test conventions, and run the suite to prove they pass.
argument-hint: [file-path]
disable-model-invocation: true
---

<!--
DESIGN NOTES
Purpose:      Add tests for a single source file, in the style this repository already
              uses, and confirm that they pass.
Invocation:   `/test-gen src/app.js`. Wrap a path that contains spaces in quotes,
              because indexed arguments use shell-style quoting.
Why a skill:  The instruction is long, and it is needed only when someone writes tests.
              Putting it in CLAUDE.md would spend those tokens on every session,
              including the ones that never touch the test directory.
Key syntax:   Argument passing by index. `$0` is the FIRST argument, because indices are
              zero-based. Writing `$1` here is an off-by-one: it expands to the SECOND
              argument, which is normally absent, so the command reads an empty path and
              appears to do nothing.
-->

## Your task

Read the file at `$0`.

Add tests for it to the matching file under `test/`. A source file `src/app.js` gets its
tests in `test/app.test.js`. Add to that file if it exists; create it if it does not.

Follow the conventions already in `test/`:

- Use the built-in `node:test` runner and `node:assert/strict`. Do not add jest, mocha, or
  supertest. The single dependency of this repository is express, and it stays that way.
- Start any server on port `0` so the operating system assigns a free port. Read the port
  back from `server.address()`. Never hardcode a port.
- Close the server in a `finally` block, so an assertion that throws still releases the
  handle.
- ESM only. Two-space indentation, single quotes, semicolons.
- Cover the success path and the error path of every behaviour you test.

The tests must actually pass. Run `npm test` and report the real output. If a test fails,
fix it and run the suite again. Do not report a result you have not run.
