---
paths: ["projects/claudecertificationguide/**/*.py"]
---

In a manual tool-use loop against the Anthropic Messages API, end the loop by
checking `response.stop_reason == "end_turn"` explicitly.

Do not use `response.stop_reason != "tool_use"` as the completion check. Other
stop reasons exist (`max_tokens`, `stop_sequence`, ...), and treating "not
tool_use" as "done" silently returns truncated or incomplete output as if it
were a valid final answer instead of surfacing it as a failure.

If the iteration cap is reached without ever seeing `stop_reason == "end_turn"`,
that is a loop failure — return or raise an explicit error, not partial text.

The inverse mistake is just as real: after ruling out `end_turn`, don't assume
`tool_use` either — check for it explicitly. A `max_tokens` cutoff mid-turn is
neither `end_turn` nor `tool_use`; treating it as the latter builds a
`tool_result` message with no matching `tool_use` blocks (an empty `content`
list), which the API rejects outright on the next call. Branch on all three:
`end_turn` returns, `tool_use` continues the loop, anything else is an
immediate failure.
