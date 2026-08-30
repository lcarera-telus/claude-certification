/**
 * test/app.test.js — HTTP tests for the Express app.
 *
 * Why the built-in runner:
 * These tests use `node:test` and `node:assert/strict`, which ship with Node 18 and later.
 * A framework such as jest, mocha, or supertest would add dependencies, a configuration
 * file, and a transform step to a repository whose whole point is that its configuration
 * is Claude Code configuration and nothing else. The built-in runner needs none of that,
 * so `npm install` pulls exactly one package: express.
 *
 * Why port 0:
 * The tests exercise the app over real HTTP, so something must listen. Binding a fixed
 * port, 3000 for example, makes the suite fail whenever that port is already taken, by a
 * development server or by a second test run in CI. Port 0 asks the operating system for
 * any free ephemeral port. The assigned port is then read back from `server.address()`
 * and used to build the request URL, so no two runs can collide.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';

import app from '../src/app.js';

/**
 * Starts the app on an OS-assigned port, passes the resulting base URL to `run`, and
 * always closes the server afterwards.
 *
 * The `finally` block is the important part: if an assertion inside `run` throws, the
 * server must still be closed, otherwise the open handle keeps the Node process alive
 * and the test run hangs instead of reporting the failure.
 */
async function withServer(run) {
  // listen() is asynchronous, so wait for its callback before reading the address.
  const server = await new Promise((resolve) => {
    const listener = app.listen(0, () => resolve(listener));
  });

  try {
    const { port } = server.address();
    await run(`http://127.0.0.1:${port}`);
  } finally {
    // fetch() keeps its socket alive by default, which would leave close() waiting for a
    // connection that never ends. Drop those sockets first, then close.
    server.closeAllConnections?.();
    await new Promise((resolve) => server.close(resolve));
  }
}

test('GET /health returns 200 and a status of ok', async () => {
  await withServer(async (baseUrl) => {
    const response = await fetch(`${baseUrl}/health`);

    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { status: 'ok' });
  });
});

test('GET /items with no query applies the default limit of 3', async () => {
  await withServer(async (baseUrl) => {
    const response = await fetch(`${baseUrl}/items`);
    const body = await response.json();

    assert.equal(response.status, 200);
    assert.equal(body.items.length, 3);
    assert.equal(body.limit, 3);
  });
});

test('GET /items?limit=2 applies the caller supplied limit', async () => {
  await withServer(async (baseUrl) => {
    const response = await fetch(`${baseUrl}/items?limit=2`);
    const body = await response.json();

    assert.equal(response.status, 200);
    assert.equal(body.items.length, 2);
    assert.equal(body.limit, 2);
  });
});

test('GET /items?limit=0 returns zero items', async () => {
  await withServer(async (baseUrl) => {
    // 0 is a valid limit, but it is also falsy. A `||` fallback would discard it and
    // apply DEFAULT_LIMIT instead. `??` falls back only on null and undefined, so an
    // explicit 0 survives. This test is what holds that distinction in place.
    const response = await fetch(`${baseUrl}/items?limit=0`);
    const body = await response.json();

    assert.equal(response.status, 200);
    assert.equal(body.items.length, 0);
    assert.equal(body.limit, 0);
  });
});

test('GET /items?limit=abc is rejected with 400', async () => {
  await withServer(async (baseUrl) => {
    // Number('abc') is NaN, which fails the Number.isInteger check in the route.
    const response = await fetch(`${baseUrl}/items?limit=abc`);

    assert.equal(response.status, 400);
  });
});

test('GET /items?limit=99 returns every item the store holds', async () => {
  await withServer(async (baseUrl) => {
    // The store holds 5 items, so slice() stops there rather than failing.
    const response = await fetch(`${baseUrl}/items?limit=99`);
    const body = await response.json();

    assert.equal(response.status, 200);
    assert.equal(body.items.length, 5);
  });
});
