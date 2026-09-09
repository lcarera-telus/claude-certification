# Output sinks: the two places a result goes after it has been validated.
#
# Note the absence of an `anthropic` import. Same reasoning as validate.py --
# writing output has nothing to do with calling an API, so keeping the
# dependency out means the sinks can be exercised with no key and no network.
# Verification check 4 does exactly that.
#
# Both functions take out_dir as a parameter with a default rather than
# hardcoding "out", so the evaluation harness in task 04 can point them at a
# scratch directory without disturbing a real run's output.

import json
from pathlib import Path


def write_json(data, name, out_dir="out"):
    # The per-document file is pretty-printed, and that is a deliberate choice
    # about who reads it. This is the artifact a human opens when they want to
    # check an extraction by eye -- against the invoice on the other monitor,
    # field by field. indent=2 makes line_items scannable and puts each field
    # on its own line, so a diff against a previous run points at the one value
    # that changed instead of at a single reformatted mega-line. The extra bytes
    # are irrelevant at one file per document; legibility is not.
    path = Path(out_dir) / f"{name}.json"
    # parents=True and exist_ok=True so a first run works on a clean checkout
    # and a later run does not fail because the directory is already there.
    path.parent.mkdir(parents=True, exist_ok=True)
    # The trailing newline makes it a well-formed POSIX text file, so `cat`,
    # `tail` and git all behave rather than reporting "no newline at end".
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


# =============================================================================
# WHY NDJSON FOR THE EVENT LOG
# =============================================================================
# The obvious alternative is one big JSON array. NDJSON -- one complete JSON
# object per line, newline-delimited -- wins on four counts that all matter to
# whatever ingests this downstream.
#
# 1. STREAMING READS. Each line is a self-delimiting record, so a consumer
#    reads the file with `for line in file:` and processes one record at a time,
#    in constant memory, starting immediately. A single top-level array cannot
#    be read that way: a conforming parser needs the closing bracket before it
#    can hand back anything at all, so a 2 GB run means 2 GB resident and no
#    output until the last byte arrives.
#
# 2. APPENDS ARE O(1). Adding a record is open(..., "a") and one write. The OS
#    does the rest, and concurrent appends of short lines do not interleave.
#    Appending to a JSON array means read the whole file, parse it, push onto
#    the list, re-serialise, and rewrite -- O(file) per record, so a run gets
#    quadratically slower as it goes. Worse, the rewrite has a window where the
#    old file is gone and the new one is incomplete; a crash there loses every
#    record, not just the new one.
#
# 3. PARTIAL FILES STAY USEFUL. Kill the process mid-write and NDJSON loses the
#    last, partial line. Every line before it is still a complete, parseable
#    record, so a consumer skips the ragged tail and keeps the rest. A truncated
#    JSON array is unparseable in its entirety -- one missing bracket and every
#    record in the file is unreadable, including the thousands written hours
#    before the crash.
#
# 4. THE ECOSYSTEM ALREADY SPEAKS IT. `jq` consumes it by default. Log shippers
#    tail it. BigQuery and similar bulk loaders take it as a native input
#    format. Kafka-style pipelines are one-message-per-line by construction. So
#    the integration is usually zero code, whereas a JSON array needs an
#    unwrapping step in front of each of those.
#
# The tradeoff, stated honestly: the file as a whole is not valid JSON, so a
# tool that blindly calls json.loads on the entire thing will fail. That is the
# price, and it is why the extension says ndjson rather than json.
# =============================================================================


def append_event(record, out_dir="out", filename="events.ndjson"):
    path = Path(out_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    # separators=(",", ":") strips the whitespace json.dumps otherwise inserts,
    # and there is deliberately no indent= here. indent would embed newlines in
    # the record, which breaks the one-record-per-line invariant the entire
    # format rests on: a reader splitting on newlines would get fragments that
    # parse as nothing. Compactness is a side benefit; the real requirement is
    # that a serialised record contains no newline of its own.
    line = json.dumps(record, separators=(",", ":"))
    # Append mode, never "w". The event log is the running history of the whole
    # pipeline, so opening it for write would silently erase every prior run.
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return path
