# The boilerplate command: generate one module and its test, in the house style that
# EXPLORATION.md recorded. Reference: https://code.claude.com/docs/en/tools-reference
#
# All text in this file is ASCII only, for the same console encoding reason as the rest
# of the package.

from __future__ import annotations

import re
from pathlib import Path

from .. import config, observability, permissions
from ._common import run_agent

OUTPUT_DIR = "codebuddy_generated"
TESTS_DIR = "codebuddy_generated/tests"

# A component name becomes a Python module name and a path segment. Restricting it to
# lowercase letters, digits, and underscores keeps it a legal module name and keeps a
# path separator or a ".." out of the two paths the prompt builds from it.
_NAME_RULE = re.compile(r"^[a-z0-9_]+$")

# TOOL PLAN. Read first, then Write twice.
#
# Read, on EXPLORATION.md: the conventions were already discovered by the explore
# command. Re-deriving them here would cost turns and could reach a different answer.
#
# Write, not a Bash heredoc: Write is a first-class tool, so the permission layer can
# scope it by path. The allow rules Edit(codebuddy_generated/**) and
# Edit(codebuddy_generated/tests/**) confine every write to those two directories. A
# heredoc is opaque shell text; the permission layer cannot see the path inside it, so it
# could write anywhere. This command denies Bash outright for that reason.
# https://code.claude.com/docs/en/agent-sdk/permissions

PROMPT = """Generate a new component named {component}, with its test.

1. Use Read on {report} first. That file is the survey of this codebase. Take the house
   style from its "Conventions detected" section: the test file naming pattern, the
   import style, and the docstring style. Follow all three exactly. Do not invent a
   different style, and do not copy a style from your own habits.

2. Use Write to create {output_dir}/{component}.py. Give it a module docstring, the
   imports the house style calls for, and a small, honest implementation. Leave no
   placeholder that would fail to import.

3. Use Write to create {tests_dir}/test_{component}.py. Cover the normal case and at
   least one edge case. Follow the test naming pattern the report recorded.

Use the Write tool for both files. Do not use a shell heredoc and do not use a shell
redirect. Write is the correct tool here because it is a first-class tool that the
permission layer can scope by path, so these two files are the only places you can
write. A shell command is opaque to that layer and is denied in this run.

Report which two files you wrote and which conventions you followed.
"""


async def run(component: str, *, target: str, model: str, quiet: bool, logger=None) -> int:
    """Generate <component>.py and its test from the conventions in EXPLORATION.md."""
    if not _NAME_RULE.match(component):
        raise config.CodebuddyError(
            f"Invalid component name '{component}'. Use lowercase letters, digits, and underscores only.")
    # Fail before the agent starts. Without the report the agent has no conventions to
    # copy, so it would invent a style and the whole point of the command would be lost.
    # One sentence, one action, no traceback.
    root = Path(target).expanduser().resolve()
    report = root / "EXPLORATION.md"
    if not report.is_file():
        raise config.CodebuddyError(f"No EXPLORATION.md in {root}. Run: codebuddy explore {root}")
    logger = logger or observability.ToolCallLogger(quiet=quiet)
    policy = permissions.for_boilerplate(OUTPUT_DIR, TESTS_DIR)
    # WHY cwd is the project root: the Edit rules above are relative paths, and a relative
    # rule anchors at the session working directory. The project root is therefore what
    # scopes every write to codebuddy_generated/. Point cwd anywhere else and the same
    # rules would allow writes into a codebuddy_generated/ under that other directory.
    # https://code.claude.com/docs/en/agent-sdk/permissions
    # WHY max_turns=15: this is read one file, then write two. It needs far fewer turns
    # than a survey, and a low ceiling turns a confused run into a fast failure.
    code = await run_agent(
        prompt=PROMPT.format(component=component, report=report, output_dir=OUTPUT_DIR, tests_dir=TESTS_DIR),
        policy=policy, logger=logger, model=model, cwd=str(config.PROJECT_ROOT), max_turns=15)
    # Check the artefacts. A success result does not prove the files exist.
    for path in (config.PROJECT_ROOT / OUTPUT_DIR / f"{component}.py",
                 config.PROJECT_ROOT / TESTS_DIR / f"test_{component}.py"):
        print(f"{'wrote' if path.is_file() else 'MISSING'}: {path}", flush=True)
    print(logger.summary(), flush=True)
    return code
