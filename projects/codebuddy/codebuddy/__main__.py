# codebuddy CLI entry point.
#
# Documentation used to build this project. Read on 2026-08-30.
# https://code.claude.com/docs/en/agent-sdk/overview
# https://code.claude.com/docs/en/agent-sdk/quickstart
# https://code.claude.com/docs/en/agent-sdk/python
# https://code.claude.com/docs/en/agent-sdk/hooks
# https://code.claude.com/docs/en/agent-sdk/mcp
# https://code.claude.com/docs/en/agent-sdk/permissions
# https://code.claude.com/docs/en/tools-reference
# https://code.claude.com/docs/en/agent-sdk/troubleshooting
#
# The SDK API changes often. These URLs are the source of truth for this code, not
# memory of an earlier version of the SDK.
#
# All text in this file is ASCII only. The Windows console default code page cannot
# always encode a Unicode character, and that encoding error would end a run.

from __future__ import annotations

import argparse
import asyncio
import sys

from . import config
from .commands import boilerplate, chores, explore
from .observability import ToolCallLogger

DEFAULT_PATH = "sample-legacy-app"


def _target(path: str) -> str:
    """Resolve a --path value against the project root, so the default works from anywhere."""
    # An absolute path passed by the user wins here, because joining an absolute path
    # onto a base returns the absolute path unchanged. That is what makes the
    # outside-the-root check in chores.run reachable and testable.
    return str((config.PROJECT_ROOT / path).resolve())


def build_parser() -> argparse.ArgumentParser:
    """Build the three-subcommand parser."""
    parser = argparse.ArgumentParser(prog="codebuddy", description="A developer productivity agent.")
    subparsers = parser.add_subparsers(dest="command", metavar="{explore,boilerplate,chores}")
    explore_parser = subparsers.add_parser("explore", help="Survey a codebase and write EXPLORATION.md.")
    explore_parser.add_argument("path", help="Directory to explore.")
    boilerplate_parser = subparsers.add_parser("boilerplate", help="Generate a component and its test.")
    boilerplate_parser.add_argument("component", help="Component name: lowercase, digits, underscores.")
    chores_parser = subparsers.add_parser("chores", help="Fix line endings, format, and report the diff.")
    for sub in (boilerplate_parser, chores_parser):
        sub.add_argument("--path", default=DEFAULT_PATH, help=f"Directory to work in. Default: {DEFAULT_PATH}")
    for sub in (explore_parser, boilerplate_parser, chores_parser):
        sub.add_argument("--model", default=None, help="Model id. Default: CODEBUDDY_MODEL, then the built-in default.")
        sub.add_argument("--quiet", action="store_true", help="Print only the MCP discovery and result lines.")
    return parser


def main() -> int:
    """Parse the arguments, run one command, and return the process exit code."""
    # WHY parsing comes first, outside the try: --help and an argument error must still
    # work when the SDK is not installed. A preflight() call placed before parse_args
    # would turn every --help into an install error. Parsing also stays outside the try
    # because argparse reports --help and a bad argument by raising SystemExit, and the
    # BaseException handler below would otherwise catch that and report it as a crash.
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 2
    try:
        model = config.resolve_model(args.model)
        config.load_env()
        config.preflight()
        # One logger for the run. It holds the per-tool counts that summary() reports, so
        # a second instance would split the count and undercount the run.
        logger = ToolCallLogger(quiet=args.quiet)
        common = {"model": model, "quiet": args.quiet, "logger": logger}
        if args.command == "explore":
            return asyncio.run(explore.run(args.path, **common))
        if args.command == "boilerplate":
            return asyncio.run(boilerplate.run(args.component, target=_target(args.path), **common))
        return asyncio.run(chores.run(target=_target(args.path), **common))
    except config.CodebuddyError as exc:
        print(f"codebuddy: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("codebuddy: interrupted.", file=sys.stderr)
        return 130
    except BaseException as exc:
        # WHY config.explain: it translates the SDK exception classes into one action the
        # user can take, such as installing the CLI natively, instead of a traceback that
        # names a class the user has never heard of.
        print(f"codebuddy: {config.explain(exc)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
