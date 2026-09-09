# The chores command: mechanical cleanup inside one bounded directory.
# Reference: https://code.claude.com/docs/en/agent-sdk/permissions
#
# All text in this file is ASCII only, for the same console encoding reason as the rest
# of the package.

from __future__ import annotations

import sys
from pathlib import Path

from .. import config, observability, permissions
from ._common import run_agent

# TOOL PLAN. Grep and Glob find the work, Edit or a scoped sed does it, Bash reports it.
#
# Grep and Glob, not a shell search: both are first-class tools, they need no shell, and
# they behave the same on Windows. The chores policy does allow a shell, but only for a
# short allowlist, and a search binary is not on it.
#
# Edit, for a file rewrite: Edit is path-scoped by the Edit(<target>/**) allow rule, so
# the permission layer confines it to the target directory.
#
# Bash, for git status, git diff, and black only: these are read-only or formatter-only
# commands that no built-in tool replaces. Everything else is denied.
# https://code.claude.com/docs/en/tools-reference

PROMPT = """Do three mechanical chores in {relative}, in this order. Do not do anything else.

1. Find every file under {relative} that uses CRLF line endings, then rewrite those files
   to LF. Use Grep or Glob to find the files. Use Edit, or a sed command scoped to one
   file at a time, to rewrite them. Change line endings only. Change no other character.

2. Run {python_exe} -m black on {relative}.

3. Summarise what changed. Run git diff --stat, then list each changed file with the one
   reason it changed. A file that black reformatted and a file whose line endings changed
   are two different reasons; say which applies to each file.

Your shell surface is a short allowlist: git status, git diff, git ls-files, sed,
{python_exe} -m black, and {python_exe} -m py_compile. Use that exact command text for the
formatter. Do not quote it, and do not shorten it, because the allowlist matches the command
by prefix. Anything outside that list is denied, and a
safety hook also blocks any command that looks destructive. If a command is denied, stop
and report the denial in your final answer. Do not work around it, do not retry a variant
of it, and do not try a different tool to achieve the same effect.

Stay inside {relative}. Do not touch a file outside it.
"""


async def run(*, target: str, model: str, quiet: bool, logger=None) -> int:
    """Run the mechanical chores inside target. Return an exit code."""
    # WHY this bound exists in code and not only in the policy: for_chores allows
    # Bash(sed:*), and that rule is not path-scoped. With -i, sed can rewrite any existing
    # file the process can reach, inside or outside the target. permissions.py names this
    # as an accepted risk and states that the command layer must validate the target. This
    # is that validation, and it is the only thing standing between a bad --path and a
    # rewrite of an unrelated file. https://code.claude.com/docs/en/agent-sdk/permissions
    root = config.PROJECT_ROOT
    path = Path(target).expanduser().resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise config.CodebuddyError(
            f"The chores target {path} is outside the project root {root}. Choose a directory inside it.") from exc
    logger = logger or observability.ToolCallLogger(quiet=quiet)
    # Name the interpreter absolutely, so neither the prompt nor the allow rule depends on
    # PATH. Forward slashes again, for the glob reason stated below.
    python_exe = Path(sys.executable).as_posix()
    if " " in python_exe:
        # WHY fall back: the agent would have to quote a path that holds a space, and a
        # quoted command does not prefix-match the allow rule, so the call would be denied.
        print("codebuddy: the interpreter path contains a space, so this run falls back to "
              "the bare 'python' command and the formatter step may fail.", flush=True)
        python_exe = "python"
    # Forward slashes, because a permission rule path is matched as a glob and a backslash
    # is an escape character there. A Windows-style path would match nothing and the
    # Edit rule would silently allow no file at all.
    policy = permissions.for_chores(relative.as_posix(), python_exe)
    # WHY cwd is the project root and not the target: git status and git diff must run
    # inside the repository to see anything, and the Edit(<relative>/**) rule is relative,
    # so it anchors at this same directory. Both facts point at the project root.
    # WHY extra_hooks: run_agent merges this guard with the logger hooks instead of
    # replacing them, so a Bash call fires both. The logger records the call and the guard
    # can deny it, and a single deny blocks the call whatever the other hook returned.
    # https://code.claude.com/docs/en/agent-sdk/hooks
    # WHY max_turns=20: three chores over many files, with a report at the end. Enough
    # room to finish, and a firm stop for a run that keeps retrying a denied command.
    code = await run_agent(prompt=PROMPT.format(relative=relative.as_posix(), python_exe=python_exe), policy=policy,
                           logger=logger, model=model, cwd=str(root), max_turns=20,
                           extra_hooks=permissions.bash_guard_hooks())
    print(logger.summary(), flush=True)
    return code
