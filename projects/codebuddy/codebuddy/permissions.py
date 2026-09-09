"""Per-command tool policies and the destructive-shell guard for codebuddy.

Each command gets the narrowest tool surface that still lets it finish its job. The
rule form matters more than the rule count here: the wrong form matches nothing and
fails silently, so every rule below carries the reason for its exact shape.
Reference: https://code.claude.com/docs/en/agent-sdk/permissions
"""

# All text in this file is ASCII only. The Windows console default code page cannot
# always encode a Unicode character, and that encoding error would end a run.

from __future__ import annotations

from dataclasses import dataclass

from claude_agent_sdk import HookMatcher

# Lowercase substrings that must never appear in a Bash command during a chores run.
# These are the last line of defence, behind the deny rules and the narrow allowlist.
DESTRUCTIVE_PATTERNS: tuple[str, ...] = ("rm ", "rmdir", "del ", "git push", "git reset",
                                         "git commit", "git checkout", "shutdown",
                                         "format ", "mkfs", ":(){", "curl ", "iwr ",
                                         "invoke-webrequest")


@dataclass(frozen=True)
class ToolPolicy:
    """One command's tool surface: the allow rules, the deny rules, and the mode."""

    allowed_tools: list[str]
    disallowed_tools: list[str]
    permission_mode: str


def for_explore() -> ToolPolicy:
    """Read-only codebase exploration. The report file is the one writable path."""
    return ToolPolicy(
        allowed_tools=["Read", "Glob", "Grep",
                       # WHY the Edit form and not the write-tool form: Edit(path) is the
                       # rule form that governs every built-in tool that writes a file,
                       # and that includes the write tool and the notebook editor. A rule
                       # named after the write tool with a path in it is never matched by
                       # the file permission checks. It would not deny anything and it
                       # would not allow anything; the call would fall through to the
                       # mode with no error, which is the worst kind of failure.
                       # https://code.claude.com/docs/en/agent-sdk/permissions
                       "Edit(EXPLORATION.md)",
                       # WHY this exact glob: an allow-rule glob is only legal after a
                       # literal mcp__<server>__ prefix, so the server segment must name a
                       # server we configured. A bare mcp__* or a bare * is ignored with a
                       # startup warning and auto-approves nothing. WHY it is required at
                       # all: the acceptEdits mode does not auto-approve MCP tools, only
                       # file edits and filesystem shell commands, so an MCP tool needs an
                       # explicit allow entry in every mode.
                       # https://code.claude.com/docs/en/agent-sdk/mcp
                       "mcp__fs__*"],
        # WHY bare tool names here: a deny rule that names the tool alone removes the tool
        # definition from the request. Claude never sees the tool and cannot attempt it,
        # so no turn is wasted on a call that would be refused. A scoped deny such as
        # Bash(rm *) is the opposite: the tool stays visible and usable, and only the
        # matching calls are blocked. Exploration needs no shell and no network at all.
        disallowed_tools=["Bash", "WebFetch", "WebSearch"],
        # WHY dontAsk and not default: codebuddy runs non-interactively. In default mode
        # an unmatched call goes to a permission prompt that nobody is there to answer.
        # dontAsk denies anything not pre-approved, so the run dies loudly and fast.
        permission_mode="dontAsk")


def for_boilerplate(output_dir: str, tests_dir: str) -> ToolPolicy:
    """Scaffold generation. Writes are confined to the two named directories."""
    return ToolPolicy(
        # Same rule form as for_explore: Edit(path) governs the file writes. The /**
        # suffix covers the whole subtree, and a single leading slash would anchor the
        # path at the session working directory instead of the filesystem root.
        allowed_tools=["Read", "Glob", "Grep",
                       f"Edit({output_dir}/**)", f"Edit({tests_dir}/**)"],
        disallowed_tools=["Bash", "WebFetch", "WebSearch"],
        # WHY dontAsk: non-interactive again. A generator that stalls on a prompt in CI
        # looks like a hang, not like a permission problem.
        permission_mode="dontAsk")


def for_chores(target_dir: str, python_exe: str) -> ToolPolicy:
    """Mechanical edits in one directory, plus a small read-only shell allowance."""
    return ToolPolicy(
        allowed_tools=["Read", "Glob", "Grep", f"Edit({target_dir}/**)",
                       "Bash(git status:*)", "Bash(git diff:*)", "Bash(git ls-files:*)",
                       # ACCEPTED RISK: sed is not path-scoped by this rule. With -i it can
                       # rewrite any existing file the process can reach, inside or outside
                       # target_dir. The command layer must still validate the target path
                       # before it builds the prompt; this allowlist entry does not do it.
                       "Bash(sed:*)",
                       # WHY the absolute interpreter comes first: the bare "python" in the
                       # agent's shell is not the interpreter that runs codebuddy. Starting
                       # codebuddy through a virtual environment interpreter does not put
                       # that environment on PATH, so a bare "python" resolves to the system
                       # interpreter, which has no black. WHY python_exe must use forward
                       # slashes: a permission rule path is matched as a glob, and a
                       # backslash is read there as an escape character.
                       f"Bash({python_exe} -m black:*)",
                       f"Bash({python_exe} -m py_compile:*)",
                       # WHY the bare entries stay: they cost nothing, and they still match
                       # if the agent falls back to the plain command name.
                       "Bash(python -m black:*)", "Bash(python -m py_compile:*)"],
        # WHY this list repeats what the allowlist already excludes: the redundancy is the
        # point. Deny rules are step 2 of the evaluation order, before the permission mode
        # at step 4 and the allow rules at step 5, and a deny holds even under
        # bypassPermissions. So these survive a later careless change of mode, which the
        # narrow allowlist alone would not.
        disallowed_tools=["Bash(rm *)", "Bash(rmdir *)", "Bash(del *)", "Bash(git push:*)",
                          "Bash(git commit:*)", "Bash(git reset:*)", "Bash(git checkout:*)",
                          "Bash(curl *)", "WebFetch", "WebSearch"],
        # WHY dontAsk: same reason as the other two policies. No human is at the terminal,
        # so a prompt is a hang and a denial is an honest, immediate failure.
        permission_mode="dontAsk")


async def _deny_destructive_bash(input_data, tool_use_id, context) -> dict:
    """Deny a Bash call whose command contains a destructive substring."""
    # WHY guard on the event name first: one callback list can receive other events as
    # the SDK grows. Read tool_name only after the event is the expected one.
    if input_data.get("hook_event_name") != "PreToolUse":
        return {}
    if input_data.get("tool_name") != "Bash":
        return {}
    command = str(input_data["tool_input"].get("command", "")).lower()
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern in command:
            # Name the matched pattern in both messages. The model needs it so it stops
            # retrying variants, and the user needs it to see which rule fired.
            return {"hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"Blocked: the command contains the destructive pattern "
                            f"'{pattern}'. Do not retry it. Use a read-only command, or "
                            f"report that the step needs a human."),
                    },
                    "systemMessage": f"codebuddy blocked a Bash command containing '{pattern}'."}
    # An empty dict means "no decision". The call carries on to the deny rules, the
    # mode, and the allow rules, so the guard never widens the tool surface.
    return {}


def bash_guard_hooks() -> dict:
    """Return the hooks mapping for ClaudeAgentOptions.hooks."""
    # WHY a hook and not only deny rules: hooks are step 1 of the six evaluation steps,
    # ahead of the deny rules, the mode, the allow rules, and can_use_tool. This guard
    # therefore still fires if somebody later sets bypassPermissions.
    # https://code.claude.com/docs/en/agent-sdk/permissions
    #
    # WHY matcher="Bash" here, the opposite of the transparency logger's bare matcher:
    # this guard only concerns shell commands. A narrow matcher keeps it cheap and stops
    # it from inspecting the input of unrelated tools, which is input it has no rule for.
    return {"PreToolUse": [HookMatcher(matcher="Bash", hooks=[_deny_destructive_bash])]}
