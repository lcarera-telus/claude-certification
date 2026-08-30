"""Tool-use transparency for codebuddy.

Two independent channels report every tool interaction: SDK hooks and the query()
message stream. The block comment above ToolCallLogger.hooks() says why both exist.
Reference: https://code.claude.com/docs/en/agent-sdk/hooks
"""

# All console output here is ASCII only. The Windows console default code page cannot
# always encode a Unicode ellipsis, box drawing, or emoji, and that encoding error
# would crash the run in the middle of a tool call.

from __future__ import annotations

import sys
import time

# WHY import these at module level: render() dispatches with isinstance, so it needs
# the real classes, not duck typing. Duck typing on a .content attribute would confuse
# AssistantMessage with UserMessage, and both carry content blocks.
from claude_agent_sdk import (AssistantMessage, HookMatcher, ResultMessage, SystemMessage,
                              TextBlock, ThinkingBlock, ToolResultBlock, ToolUseBlock, UserMessage)

# A tool name that starts with this prefix came from an MCP server, not from the
# built-in tool set. https://code.claude.com/docs/en/agent-sdk/mcp
MCP_PREFIX = "mcp__"

# WHY getattr with a default at the call site: these attribute names vary by SDK
# version, and a missing one must not end the run at the last message.
_RESULT_FIELDS = ("subtype", "num_turns", "total_cost_usd")


class ToolCallLogger:
    """Prints every tool call to the console and counts the calls per tool."""

    def __init__(self, quiet: bool = False, max_value_chars: int = 120,
                 max_line_chars: int = 220) -> None:
        self.quiet = quiet
        self.max_value_chars = max_value_chars
        self.max_line_chars = max_line_chars
        self.counts: dict[str, int] = {}
        self.mcp_calls = 0
        self.builtin_calls = 0
        self._started: dict[str, float] = {}

    # ---------------------------------------------------------------- channel 1
    # Tool-call events surface in the SDK in two places, and they are not the same
    # event. A hook callback runs inside this process, synchronously, before the tool
    # executes; it holds the call open, so it can block the call, rewrite its input,
    # or start a timer. A stream message is the after-the-fact transcript that query()
    # yields, and it can change nothing that already happened. This logger needs both:
    # the hook supplies the "before" edge and therefore the duration, and the stream
    # supplies the session init line and the final cost, which no hook reports.
    # https://code.claude.com/docs/en/agent-sdk/hooks
    def hooks(self) -> dict:
        # WHY no matcher: an omitted matcher fires for every tool call, so nothing
        # escapes the log. A matcher such as "Bash" would silently skip every other
        # tool, including every MCP tool, and the transparency claim would be false.
        return {
            "PreToolUse": [HookMatcher(hooks=[self._on_pre_tool_use])],
            "PostToolUse": [HookMatcher(hooks=[self._on_post_tool_use])],
        }

    async def _on_pre_tool_use(self, input_data, tool_use_id, context) -> dict:
        # WHY guard on the event name: one callback list can receive other events as
        # the SDK grows. Read tool_name only after the event is the expected one.
        if input_data.get("hook_event_name") != "PreToolUse":
            return {}  # {} means "allow, no change". See the note on the return below.
        name = input_data.get("tool_name", "unknown")
        is_mcp = name.startswith(MCP_PREFIX)
        self.counts[name] = self.counts.get(name, 0) + 1
        self.mcp_calls += int(is_mcp)
        self.builtin_calls += int(not is_mcp)
        # WHY key on tool_use_id: it correlates PreToolUse with the PostToolUse of the
        # same call, so parallel tool calls do not mix up their start times.
        self._started[tool_use_id or name] = time.monotonic()
        kind = "mcp" if is_mcp else "builtin"
        self._say(f"-> [{kind}] {name} {self._brief(input_data.get('tool_input'))}")
        # An empty dict means "allow, no change": the SDK carries on to the deny rules,
        # the permission mode, and the allow rules. Returning permissionDecision "allow"
        # instead would widen the tool surface and skip every later deny rule, because an
        # auto-approved call also never reaches can_use_tool. Never return
        # permissionDecision from these hooks. A logger observes; it must not decide.
        # https://code.claude.com/docs/en/agent-sdk/permissions
        return {}

    async def _on_post_tool_use(self, input_data, tool_use_id, context) -> dict:
        name = input_data.get("tool_name", "unknown")
        started = self._started.pop(tool_use_id or name, None)
        elapsed_ms = 0.0 if started is None else (time.monotonic() - started) * 1000.0
        # WHY tool_response: PostToolUse input adds the result that PreToolUse cannot
        # have. https://code.claude.com/docs/en/agent-sdk/hooks
        result = input_data.get("tool_response")
        failed = isinstance(result, dict) and result.get("is_error")
        status = "error" if failed else "ok"
        self._say(f"<- {name} {elapsed_ms:.0f}ms {status} {len(str(result))} chars")
        # Same rule as the pre hook: {} means "allow, no change". Never return
        # permissionDecision here either. It would widen the tool surface and skip the
        # later deny rules, and this hook sees a finished call, so it would also be late.
        return {}

    # ---------------------------------------------------------------- channel 2
    def render(self, message: object) -> None:
        if isinstance(message, SystemMessage) and getattr(message, "subtype", "") == "init":
            # WHY message.data: the init payload is an untyped dict, so read it with
            # .get and never index it. https://code.claude.com/docs/en/agent-sdk/mcp
            data = getattr(message, "data", {}) or {}
            servers = ", ".join(f"{s.get('name')}={s.get('status')}" for s in data.get("mcp_servers", []))
            tools = [t for t in data.get("tools", []) if t.startswith(MCP_PREFIX)]
            # This is the live proof that the MCP schemas reached the model. A status of
            # "pending" is not a failure on its own; only "failed" and "needs-auth" are.
            self._say(f"[mcp-discovery] servers: {servers or 'none'}", always=True)
            self._say(f"[mcp-discovery] tool schemas: {tools or 'none'}", always=True)
        elif isinstance(message, AssistantMessage):
            for block in getattr(message, "content", []) or []:
                if isinstance(block, ThinkingBlock):
                    continue  # Reasoning is not a tool event, and it is noise here.
                if isinstance(block, TextBlock):
                    self._say(f"[claude] {getattr(block, 'text', '').strip()}")
                elif isinstance(block, ToolUseBlock):
                    self._say(f"[stream] tool_use {getattr(block, 'name', '?')}")
        elif isinstance(message, UserMessage):
            # Tool results come back to the model as a user message, not as a result
            # message. https://code.claude.com/docs/en/agent-sdk/python
            for block in getattr(message, "content", []) or []:
                if isinstance(block, ToolResultBlock):
                    state = "error" if getattr(block, "is_error", False) else "ok"
                    self._say(f"[stream] tool_result {state}")
        elif isinstance(message, ResultMessage):
            fields = " ".join(f"{k}={getattr(message, k, 'n/a')}" for k in _RESULT_FIELDS)
            self._say(f"[result] {fields}", always=True)

    def summary(self) -> str:
        total = sum(self.counts.values())
        ranked = sorted(self.counts.items(), key=lambda pair: (-pair[1], pair[0]))
        detail = ", ".join(f"{name} x{count}" for name, count in ranked) or "none"
        return f"tool calls: {total} (builtin {self.builtin_calls}, mcp {self.mcp_calls}) [{detail}]"

    # The one truncation helper. It renders tool_input as compact key=value pairs,
    # clips each value, clips the assembled line, and never raises.
    def _brief(self, tool_input: object) -> str:
        def clip(value: object, limit: int) -> str:
            # Flatten first, then cut. A newline inside a value would otherwise break
            # the one-line-per-call rule and hide the next call in the scrollback.
            text = str(value).replace("\r", " ").replace("\n", " ")
            return text if len(text) <= limit else text[:limit] + "..."

        try:
            body = " ".join(f"{key}={clip(value, self.max_value_chars)}"
                            for key, value in tool_input.items())  # type: ignore[union-attr]
        except Exception:
            # A tool input is whatever the server declared, so it may not be a mapping.
            # Logging must never be the thing that ends a run.
            body = clip(repr(tool_input), self.max_value_chars)
        return clip(body, self.max_line_chars)

    def _say(self, line: str, always: bool = False) -> None:
        # quiet mode keeps only the init line and the result line. Those two carry the
        # MCP proof and the cost, which are the facts a run report needs.
        if always or not self.quiet:
            # WHY re-encode before printing: the ASCII-only rule above governs the text
            # this package writes, but _say also relays model text, which is arbitrary
            # Unicode nobody here controls. The Windows console default code page cannot
            # encode a star or a box-drawing character, and print() would then raise
            # UnicodeEncodeError in the middle of a tool call and end the whole run.
            # Substitute the unencodable characters instead, so logging never kills a run.
            encoding = getattr(sys.stdout, "encoding", None) or "ascii"
            print(line.encode(encoding, "replace").decode(encoding, "replace"), flush=True)
