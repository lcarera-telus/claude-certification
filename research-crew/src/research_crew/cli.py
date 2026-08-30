"""Command-line entry point: `python -m research_crew.cli "<question>"`.

WHY THE CLI IS A SEPARATE MODULE FROM THE COORDINATOR
=====================================================
`coordinator.run_research` is a coroutine that takes a question and returns a
`RunState`. It knows nothing about argv, exit codes, terminals, or which stream
a message belongs on. Everything in this file is exactly that knowledge, and
keeping it here is what lets the pipeline be driven from a test, a notebook, or
another program without any of it coming along.

That split is also what makes `tests/test_coordinator.py` possible at all. The
tests call `run_research` directly with a monkeypatched `query`; if argument
parsing and `asyncio.run` were tangled into the pipeline, testing the re-search
gate would mean shelling out to a subprocess.

THE TWO OUTPUT STREAMS, AND WHY THE SPLIT MATTERS
=================================================
    stderr  progress, the error message when a run fails, and each citation
            problem when the mechanical check rejects the report
    stdout  the report path, the total cost, the one-line citation verdict on
            success, and nothing else

A research run takes minutes, so it must say what it is doing while it does it.
It is also a step in somebody's shell pipeline, so its result must be readable
by the next command. Those two requirements conflict on one stream and coexist
on two. The per-phase progress lines are emitted by `coordinator._progress` as
each phase starts, because only the coordinator knows when a phase begins; this
module owns the final two lines.

WHY FAILURE EXITS NON-ZERO
==========================
Every `CoordinatorError` in this system means the report is missing or would be
untrustworthy: the budget ran out, a phase stopped on an unhandled subtype, no
subagent was ever invoked, or an agent returned something unparsable. A shell
that got exit code 0 would treat any of those as a finished research run and
carry on to the next step. The exit code is the only part of this program that
an automated caller is guaranteed to read.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .coordinator import DEFAULT_MAX_BUDGET_USD, CoordinatorError, run_research
from .verify import describe

# Defaults resolved from this file's location, not from the process working
# directory. `.../research-crew/src/research_crew/cli.py` -> parents[2] is the
# project root, so `agents/` and `runs/` are found whether the command is run
# from the repository root, from `research-crew/`, or from anywhere else. A
# relative default like `Path("research-crew/agents")` would work in exactly one
# directory and fail with a confusing "no agents found" everywhere else.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AGENTS_DIR = _PROJECT_ROOT / "agents"
DEFAULT_RUNS_ROOT = _PROJECT_ROOT / "runs"


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Split out from `main` so the flags can be inspected and tested without
    running a research run.
    """
    parser = argparse.ArgumentParser(
        prog="python -m research_crew.cli",
        description="Run the multi-agent research crew over one question.",
    )
    parser.add_argument("question", help="The research question to investigate.")
    parser.add_argument(
        "--max-budget-usd",
        type=float,
        default=DEFAULT_MAX_BUDGET_USD,
        help="Ceiling for the whole run, in US dollars (default: %(default)s).",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=DEFAULT_RUNS_ROOT,
        help="Directory that holds one sub-directory per run (default: %(default)s).",
    )
    parser.add_argument(
        "--agents-dir",
        type=Path,
        default=DEFAULT_AGENTS_DIR,
        help="Directory of agent Markdown definitions (default: %(default)s).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the pipeline, and return a process exit code.

    Returns rather than calls `sys.exit`, so a test can assert on the code
    without catching `SystemExit`. The `__main__` block below does the exiting.
    """
    args = build_parser().parse_args(argv)

    try:
        # One `asyncio.run` for the whole pipeline. The phases are sequential
        # and each waits on the one before it, so there is no concurrency to
        # manage here; async is the SDK's streaming interface, not a
        # parallelism strategy in this program.
        state = asyncio.run(
            run_research(
                args.question,
                agents_dir=args.agents_dir,
                runs_root=args.runs_root,
                max_budget_usd=args.max_budget_usd,
            )
        )
    except CoordinatorError as exc:
        # Catching the base class covers `BudgetExceeded`, `TurnLimitExceeded`
        # and `PhaseFailed` along with `NoDelegation` and `MalformedAgentReply`.
        # Every one of them means there is no trustworthy report, so every one
        # of them exits non-zero. The class name is printed alongside the
        # message because it, not the prose, is what tells the reader whether to
        # raise the budget or to fix a prompt.
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    # stdout, and only these two lines. The run directory holds the report next
    # to the input, output and state files that produced it, so the path is the
    # useful thing to hand on - not the report text, which would bury the cost
    # line under a page of Markdown.
    print(f"report: {Path(args.runs_root) / state.run_id / 'report.md'}")
    print(f"total cost: ${state.total_cost_usd():.4f}")

    # ---- The citation verdict ---------------------------------------------
    #
    # Printed *after* the report path, and the path is printed either way. A
    # failed citation check does not mean there is no report; it means the
    # report needs a reader. Suppressing the path on failure would hide the one
    # document that explains the verdict.
    #
    # The verdict still sets the exit code, because an automated caller reads
    # nothing else. A run whose citations do not resolve is not a finished
    # research run, and a shell that got 0 would carry on to the next step with
    # it. The problems go to stderr with the rest of the diagnostics; stdout
    # stays the two-line machine-readable result it was.
    #
    # `getattr` with a default rather than a plain attribute read: the verdict
    # is attached to the state by `run_research`, and a caller that built a
    # `RunState` some other way still has to be printable here.
    citation_report = getattr(state, "citation_report", None)
    if citation_report is None:
        return 0
    problems = describe(citation_report, getattr(state, "conflict_problems", ()))
    if not problems:
        print(f"citations: {citation_report.checked_citations} checked, all resolved")
        return 0
    print("citation check FAILED - the report is on disk and should be read:", file=sys.stderr)
    for problem in problems:
        print(f"  {problem}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
