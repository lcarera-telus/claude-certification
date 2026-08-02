"""Shared Claude API client setup, reused across exercises.

Reads ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN, ANTHROPIC_BASE_URL, and
ANTHROPIC_MODEL from the environment (loaded from .env at the project root),
so pointing at a gateway (e.g. a Bearer-token proxy instead of the
first-party API) is a config change only.
"""

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")


def get_client() -> anthropic.Anthropic:
    """Return an Anthropic client. Reads credentials and base URL from the environment."""
    return anthropic.Anthropic()
