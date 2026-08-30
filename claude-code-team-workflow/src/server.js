/**
 * src/server.js — the only file in this repository that binds a port.
 *
 * It exists so that `src/app.js` stays free of I/O and remains importable by the tests.
 */
import app from './app.js';

// PORT lets a container or a process manager choose the port; 3000 is the local default.
const port = process.env.PORT || 3000;

app.listen(port, () => {
  console.log(`claude-code-team-workflow listening on port ${port}`);
});
