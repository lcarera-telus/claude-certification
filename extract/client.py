"""Client construction and model selection.

Everything here is configuration, not logic. It is a separate module so that a
reader looking for "where do the credentials come from?" finds one short file
and does not have to read the extractor to answer the question.
"""

import os

import anthropic
from dotenv import load_dotenv

# Load .env from the project root before anything reads the environment.
# load_dotenv() searches upward from the working directory, so it finds the
# root .env whether the tool is invoked from the root or from a subdirectory.
# It never overwrites a variable that is already set, so a value exported in a
# real shell or injected by a CI runner still wins over the local file. That
# ordering is what makes the same code work on a laptop and in a pipeline.
load_dotenv()

# The model is configuration, not a constant of the program. Reading it from
# the environment means a reader can pin an older model to reproduce a result,
# or point at a cheaper one for a bulk run, without touching source. The
# fallback is the literal default this project was written against.
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")


def get_client():
    """Return an Anthropic client configured entirely from the environment.

    The zero-argument constructor is a deliberate choice, not laziness.

    The SDK itself reads ANTHROPIC_API_KEY, and also ANTHROPIC_AUTH_TOKEN and
    ANTHROPIC_BASE_URL. So pointing this tool at a gateway instead of the
    first-party API is a change to .env — a config change — and not a change to
    this file. If we passed api_key=... here we would have to grow a branch for
    the gateway case, and that branch would be a second code path to keep
    correct forever.

    The second reason matters more: no credential is ever named in the source,
    so none can be committed by accident, printed in a traceback that includes
    local variables, or captured in a log line that echoes the call arguments.
    The key travels from the environment straight into the SDK and is never
    held in a variable this project owns.
    """
    return anthropic.Anthropic()
