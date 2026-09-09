# CLI entrypoint: python -m extract <path-to-document>
#
# This file is deliberately thin. It parses arguments, guards the input, calls
# the extractor, and routes the result to the sinks. No extraction logic lives
# here, so a reader looking for "how does the extraction work?" is never sent
# on a detour through argument handling.

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from .client import DEFAULT_MODEL, get_client
from .extractor import ExtractionError, extract_invoice
from .sinks import append_event, write_json
from .validate import load_schema

# Below this many non-whitespace characters, a document cannot be an invoice.
# Twenty is deliberately generous: the shortest plausible invoice still carries
# a vendor, a number and an amount. The point is not to be clever about the
# threshold, it is to reject the obviously-empty before spending money on it.
MIN_CHARS = 20


def main():
    parser = argparse.ArgumentParser(prog="python -m extract", description="Extract structured invoice JSON from a plain-text document.")
    parser.add_argument("path", help="path to the plain-text invoice document")
    # --out exists so a batch run can keep its artifacts apart from a manual one.
    parser.add_argument("--out", default="out", help="output directory (default: out)")
    args = parser.parse_args()

    source = Path(args.path)
    if not source.is_file():
        # Exit 2, not 1: this is a usage problem, not a bad document. See the
        # exit-code note at the bottom of main().
        print(f"error: no such document: {source}", file=sys.stderr)
        return 2

    # =========================================================================
    # THE FAIL-FAST GUARD -- WHY IT RUNS BEFORE ANYTHING ELSE
    # =========================================================================
    # An empty or near-empty document cannot produce a valid invoice, so the API
    # call is guaranteed waste. It costs tokens on a request that has no useful
    # answer, and it adds seconds of latency to a result we already know.
    #
    # The worse outcome is not the cost, it is the response. Asked to extract an
    # invoice from nothing, a model either refuses -- which we then have to
    # detect and handle -- or it obligingly invents one. A confidently
    # hallucinated invoice is schema-valid, arithmetically consistent, and
    # entirely fictional. It passes every check this project has and lands in
    # the output directory looking exactly like a real extraction. Refusing to
    # ask the question is the only reliable defence.
    #
    # Note the ORDERING, which is the part that is easy to get wrong. This check
    # sits above get_client(). Construct the client first and, on a machine with
    # no credentials, the run dies with "missing API key" -- a true statement
    # about the wrong problem, which sends someone off to fix their .env when
    # the actual fault is that they passed an empty file.
    #
    # Keeping the guard first also means this whole path needs no credential at
    # all, so the three input-rejection cases stay testable offline. That is
    # what verification checks 1 to 3 exercise: no key present, no key needed.
    # =========================================================================
    text = source.read_text(encoding="utf-8")
    stripped = text.strip()
    if len(stripped) < MIN_CHARS:
        # Name the specific reason. "Invalid input" would leave the user
        # guessing which of several rules they broke.
        reason = "is empty or contains only whitespace" if not stripped else f"holds only {len(stripped)} non-whitespace characters, below the {MIN_CHARS} minimum"
        print(f"error: {source} {reason}; refusing to spend an API call on it", file=sys.stderr)
        return 2

    # Only now, with the input known to be worth processing, do we build the
    # client and load the schema.
    schema = load_schema()
    try:
        result = extract_invoice(text, get_client(), schema, DEFAULT_MODEL)
    except ExtractionError as exc:
        # Truncated output or a missing tool_use block. Both are real failures
        # with nothing to write, but neither should reach the user as a
        # traceback: a stack trace tells them about our call frames when what
        # they need is the one sentence saying what went wrong.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    stem = source.stem
    json_path = write_json(result.data, stem, args.out)
    # An event is appended whether the extraction validated or not, and that is
    # the point of having an event log at all. A queue that only hears about
    # successes cannot distinguish "nothing was submitted today" from
    # "everything submitted today failed" -- both look like silence. Recording
    # failures makes the failure rate a measurable quantity instead of an
    # absence, so an alert can fire on it.
    event = {"document": stem, "ok": result.ok, "attempts": result.attempts,
             "error_count": len(result.errors),
             "confidence": (result.data or {}).get("confidence"),
             "extracted_at": datetime.now(timezone.utc).isoformat()}
    append_event(event, args.out)

    print(f"wrote {json_path}")
    print(f"validated: {'yes' if result.ok else 'NO'}  (attempts: {result.attempts})")
    for error in result.errors:
        print(f"  {error['path']}: {error['message']}")

    # EXIT CODES
    #   0 -- extraction succeeded and validated.
    #   1 -- the extraction ran but the result failed validation after the retry.
    #   2 -- bad input or a usage error; no API call was made (returned above).
    #
    # 1 and 2 are deliberately different, because a caller has to act on them
    # differently. A shell loop over a directory of documents should treat 2 as
    # "this file is not a document, skip it and carry on", and 1 as "the model
    # could not extract this one, set it aside for a human". Collapsing both
    # into a bare 1 forces every caller to parse stderr to tell a malformed
    # input from a broken pipeline -- and a CI job that should stop on a
    # systemic failure would instead keep grinding through a whole directory.
    return 0 if result.ok else 1


if __name__ == "__main__":
    # sys.exit so the return value above becomes the process exit status.
    sys.exit(main())
