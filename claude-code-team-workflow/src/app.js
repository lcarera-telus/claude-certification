/**
 * src/app.js — the Express application for this teaching repository.
 *
 * This file builds the app and exports it. It deliberately does NOT call `listen()`.
 * Binding a port is I/O, and it belongs in `src/server.js`, which is the only file in
 * this repository that opens a socket.
 *
 * The reason for the split is the test suite. `test/app.test.js` imports this module
 * directly, so importing it must not bind a port. If `listen()` ran here, every import
 * of the app would take a fixed port. Two test runs at the same time, or a development
 * server that is already running, would then collide on that busy port and fail. The
 * tests keep control of the socket instead: they start the app on port 0, let the
 * operating system assign a free port, and close the server when they finish.
 *
 * The service is intentionally trivial. The real subject of this repository is the
 * Claude Code configuration layer that operates on this code.
 */
import express from 'express';

const app = express();

/**
 * The data store is a plain module-scope array. There is no database, because a database
 * would add setup that teaches nothing about Claude Code. The array is seeded with five
 * items, which is more than DEFAULT_LIMIT. That difference is what makes the limit
 * behaviour observable in the tests.
 */
const items = [
  { id: 1, name: 'item-1' },
  { id: 2, name: 'item-2' },
  { id: 3, name: 'item-3' },
  { id: 4, name: 'item-4' },
  { id: 5, name: 'item-5' },
];

// Number of items returned by GET /items when the caller sends no limit.
const DEFAULT_LIMIT = 3;

/**
 * GET /health
 *
 * Parameters: none.
 * Response 200: { "status": "ok" }
 *
 * A liveness probe. It reports only that the process answers requests. It does not check
 * the data store, so it must never return a non-200 status while the process is up.
 */
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

/**
 * GET /items
 *
 * Parameters: `limit` (optional query parameter). A non-negative integer.
 * Response 200: { "items": [ { "id": <number>, "name": <string> }, ... ],
 *                 "limit": <the limit actually applied> }
 * Response 400: { "error": "limit must be a non-negative integer" }
 *
 * Status codes: 200 for any accepted limit, including one larger than the store;
 * 400 when `limit` is present but is not a non-negative integer.
 */
app.get('/items', (req, res) => {
  // Parse the raw query value into a number, or undefined when absent.
  const raw = req.query.limit;
  const parsed = raw === undefined ? undefined : Number(raw);

  // Reject values that are not usable as a count.
  // Number('abc') is NaN, and Number.isInteger(NaN) is false, so a non-numeric limit
  // lands here and produces the 400 response.
  if (parsed !== undefined && (!Number.isInteger(parsed) || parsed < 0)) {
    return res.status(400).json({ error: 'limit must be a non-negative integer' });
  }

  // Apply the caller's limit, falling back to the default when none was given.
  const limit = parsed ?? DEFAULT_LIMIT;

  // slice() stops at the end of the array, so a limit larger than the store simply
  // returns every item instead of padding the response or raising an error.
  res.status(200).json({ items: items.slice(0, limit), limit });
});

export default app;
