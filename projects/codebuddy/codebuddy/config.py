"""Environment loading, model choice, and error translation for codebuddy.

The Agent SDK reads credentials from the environment of the process that runs the
agent. It does not read .env files by itself, so this module loads the file first.
Reference: https://code.claude.com/docs/en/agent-sdk/quickstart
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# The project root is the parent of the codebuddy package. .env sits beside
# requirements.txt, one directory above this file.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_MODEL = "claude-opus-5"

# Only these three variables reach the SDK subprocess. A gateway needs the base URL
# and the auth token together. A first-party key needs neither of those two.
_SDK_ENV_KEYS = ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN")

# The SDK refuses to launch a .bat or .cmd claude launcher on Windows. This hint is
# the exact remedy the SDK itself names in the refusal message.
_NATIVE_HINT = ("Install Claude Code natively with: irm https://claude.ai/install.ps1 | iex "
                "-- or set ClaudeAgentOptions(cli_path=...) to a claude.exe.")


class CodebuddyError(Exception):
    """An error the user can act on. The CLI prints its message and exits non-zero."""


def load_env() -> None:
    """Load <project root>/.env into os.environ. An absent file is not an error."""
    # WHY: the SDK never loads .env itself. Any credential must already sit in
    # os.environ before the SDK starts the claude subprocess, or the run fails with
    # an auth error that looks unrelated to the missing file.
    # https://code.claude.com/docs/en/agent-sdk/quickstart
    load_dotenv(ENV_PATH)


def resolve_model(cli_value: str | None) -> str:
    """Return the model id: the CLI flag, then CODEBUDDY_MODEL, then the default."""
    # WHY: an empty environment variable is the normal state of a copied .env.example.
    # Treat it as unset, so the default still applies instead of sending "" as a model.
    for candidate in (cli_value, os.environ.get("CODEBUDDY_MODEL")):
        if candidate and candidate.strip():
            return candidate
    return DEFAULT_MODEL


def sdk_env() -> dict[str, str]:
    """Return the environment overlay for ClaudeAgentOptions.env. This never raises."""
    # WHY: ClaudeAgentOptions.env is merged into the claude subprocess environment.
    # An empty string would override a good value that the subprocess already has,
    # so drop empty values instead of passing them through. Never log a value.
    present = {key: os.environ.get(key, "") for key in _SDK_ENV_KEYS}
    overlay = {key: value for key, value in present.items() if value}
    return overlay


def preflight() -> None:
    """Raise CodebuddyError when the SDK package is missing."""
    # WHY: fail here with one clear instruction. Without this check the user meets a
    # bare ImportError from deep inside a command module instead.
    try:
        import claude_agent_sdk  # noqa: F401
    except ImportError as exc:
        raise CodebuddyError(
            "claude-agent-sdk is not installed. Run: pip install -r requirements.txt"
        ) from exc
    # Do not check credentials here. The local claude CLI can hold its own login, so
    # an unset ANTHROPIC_API_KEY is not an error.


def explain(exc: BaseException) -> str:
    """Turn an SDK exception into one short, actionable sentence."""
    # WHY import inside the body: explain must still work when the SDK is absent.
    # That is exactly the case preflight() reports, and the caller wraps both.
    try:
        from claude_agent_sdk import (CLIConnectionError, CLINotFoundError,
                                      ProcessError, ResultError)
    except ImportError:
        return f"{type(exc).__name__}: {exc}"
    text = str(exc)
    # WHY this order: ResultError subclasses ProcessError, and CLINotFoundError
    # subclasses CLIConnectionError. Test each subclass first. The reverse order lets
    # the wider branch swallow the narrower one, and the user loses the real remedy.
    # https://code.claude.com/docs/en/agent-sdk/troubleshooting
    if isinstance(exc, ResultError):
        return f"The CLI reported an error result before it exited: {getattr(exc, 'data', text)}"
    if isinstance(exc, ProcessError):
        stderr = str(getattr(exc, "stderr", "") or "").strip()[:300]
        return f"The claude CLI exited with code {getattr(exc, 'exit_code', '?')}. stderr: {stderr}"
    if isinstance(exc, CLINotFoundError):
        return f"No claude executable was found. {_NATIVE_HINT} Detail: {text}"
    if isinstance(exc, CLIConnectionError):
        # The SDK names this refusal verbatim on Windows, where npm installs a
        # claude.cmd shim. Match the text, because the class alone does not say which
        # of the three CLIConnectionError causes happened.
        if "Refusing to execute batch script" in text:
            return f"The SDK will not run a .bat or .cmd claude launcher. {_NATIVE_HINT}"
        return f"Could not start or reach the claude CLI. {_NATIVE_HINT} Detail: {text}"
    return f"{type(exc).__name__}: {text}"
