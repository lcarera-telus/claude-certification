# The one agent driver. Every command builds a prompt and a policy, then calls
# run_agent. Nothing else in this package talks to the SDK query() function.
# Reference: https://code.claude.com/docs/en/agent-sdk/python
#
# All text in this file is ASCII only. The Windows console default code page cannot
# always encode a Unicode character, and that encoding error would end a run.

from __future__ import annotations

import os

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from .. import config


def merge_hooks(*hook_dicts: dict | None) -> dict:
    """Return one hooks mapping. Lists under a repeated event key are concatenated."""
    # WHY concatenate and not dict.update: two independent sources register PreToolUse
    # in this project. The transparency logger registers a matcher-less matcher, and the
    # chores safety guard registers a matcher="Bash" one. A plain dict.update would keep
    # only the last dict's list and silently drop the other matcher, so either the audit
    # trail or the destructive-command guard would disappear with no error. Both must
    # fire: when an event fires, all matching hooks run, and the most restrictive result
    # wins, so a single deny still blocks the call.
    # https://code.claude.com/docs/en/agent-sdk/hooks
    merged: dict = {}
    for event, matchers in [kv for d in hook_dicts if d for kv in d.items()]:
        merged.setdefault(event, []).extend(matchers)
    return merged


async def run_agent(*, prompt: str, policy, logger, model: str, cwd: str, mcp_servers: dict | None = None,
                    extra_allowed: list | None = None, extra_hooks: dict | None = None,
                    system_prompt_append: str | None = None, max_turns: int | None = None) -> int:
    """Run one agentic loop to the end. Return 0 on a success result, 1 on anything else."""
    # WHY collect stderr through a callback: the troubleshooting page states that
    # ProcessError.stderr carries fixed placeholder text, so the exception never shows
    # what the CLI actually wrote. This callback is the only channel that does. Print the
    # tail only on failure, because a healthy run writes noise here that helps nobody.
    # https://code.claude.com/docs/en/agent-sdk/troubleshooting
    # code starts at 1, so a run that never yields a ResultMessage is reported as a
    # failure. Only an explicit "success" subtype below lowers it to 0.
    tail, code = [], 1
    # WHY system_prompt as a preset instead of a plain string: the preset keeps Claude
    # Code's own tool-use guidance, which already teaches Read, Glob, Grep, and Write. The
    # append adds only this command's rules on top. A bare string would replace that
    # guidance and the agent would lose its tool judgement.
    # https://code.claude.com/docs/en/agent-sdk/python
    extra: dict = {"system_prompt": {"type": "preset", "preset": "claude_code",
                                     "append": system_prompt_append}} if system_prompt_append else {}
    options = ClaudeAgentOptions(
        # allowed_tools: the policy surface plus anything this call adds. disallowed_tools:
        # WHY both, and WHY deny is not redundant: a deny rule is evaluated before the
        # permission mode, and it holds even under a wider mode set later by mistake.
        allowed_tools=list(policy.allowed_tools) + list(extra_allowed or []),
        # permission_mode: WHY the policy decides it: codebuddy runs non-interactively, so
        # each policy picks dontAsk. An unmatched call then fails loudly instead of waiting
        # on a permission prompt that nobody is present to answer.
        # model: WHY passed explicitly: config.resolve_model already applied the CLI flag,
        # then the environment, then the default, so the choice is settled before this line.
        disallowed_tools=list(policy.disallowed_tools), permission_mode=policy.permission_mode, model=model,
        # cwd: WHY the caller decides it: a relative permission rule such as
        # Edit(EXPLORATION.md) anchors at the session working directory, not at the
        # filesystem root, so cwd is what decides where that rule points. Each command sets
        # it deliberately. https://code.claude.com/docs/en/agent-sdk/permissions
        # env: WHY only the credential subset: config.sdk_env drops empty values so an
        # empty string cannot override a good value the subprocess already holds.
        # hooks: WHY merge_hooks and not a literal dict: see the comment on merge_hooks.
        cwd=cwd, env=config.sdk_env(), hooks=merge_hooks(logger.hooks(), extra_hooks),
        # mcp_servers: WHY "or {}": an empty mapping is the field default, so passing it
        # when the caller has no server is the same as not setting the field at all.
        # https://code.claude.com/docs/en/agent-sdk/mcp
        # max_turns: WHY a ceiling: the agentic loop ends when Claude finishes or errors,
        # and a confused agent can otherwise loop until the budget runs out. This bounds it.
        # max_budget_usd: WHY here: this is a hard cost ceiling and a reliability control,
        # not a performance tuning knob. It stops a runaway loop from spending real money.
        mcp_servers=mcp_servers or {}, max_turns=max_turns,
        # strict_mcp_config: WHY True: only the servers passed in mcp_servers are used, and
        # every other MCP configuration on the machine is ignored. Without it the reader's
        # own connectors load, their tool schemas fill the context window, and the
        # transcript stops being reproducible. This is a CONTEXT control, and it is separate
        # from allowed_tools, which is a PERMISSION control. allowed_tools decides what may
        # run; strict_mcp_config decides what is even described to the model.
        # https://code.claude.com/docs/en/agent-sdk/mcp
        strict_mcp_config=True,
        # setting_sources: WHY an empty list: it loads no settings file at all, so no user,
        # project, or local settings reach the run. That is what keeps the machine's global
        # MCP configuration, its memory files, and its shell hooks out of a teaching run.
        # https://code.claude.com/docs/en/agent-sdk/python
        setting_sources=[],
        max_budget_usd=float(os.environ.get("CODEBUDDY_MAX_USD") or 2.0), stderr=tail.append, **extra)
    # The agentic loop. It streams while Claude thinks, calls tools, reads results, and
    # decides the next step. Render every message, so the transcript shows the whole run.
    async for message in query(prompt=prompt, options=options):
        logger.render(message)
        # WHY isinstance and not a subtype check alone: SystemMessage also carries a
        # subtype ("init"), so duck typing on that attribute would misread the init line
        # as a result. Default to 1, so a run with no ResultMessage at all also fails.
        if isinstance(message, ResultMessage):
            code = 0 if getattr(message, "subtype", "") == "success" else 1
    if code and tail:
        print("codebuddy: last claude CLI stderr:\n" + "".join(tail[-20:]).rstrip(), flush=True)
    return code
