# Task 03 — CLI entrypoint and downstream sinks

You are implementing one work package of a larger project. You see only this
specification. Do not assume knowledge from any other conversation.

## Project context (restated — do not skip)

We are building `extract`, a command-line tool. It reads an unstructured invoice written as
plain text, sends it to the Claude API, gets structured JSON back via a forced tool call,
validates it against a JSON Schema, and writes the validated result to disk.

The audience is an engineer studying for the Claude Certified Architect – Foundations exam.
**This code is a teaching artifact.** A newcomer must read it top to bottom and understand
*why* each decision was made. Comments explain reasoning, not syntax. Clarity over
cleverness. Python 3.13. Project root is the current working directory.

## What already exists — do not modify any of it

Tasks 01 and 02 are complete and accepted.

```
requirements.txt              anthropic, jsonschema, python-dotenv
.env.example  .gitignore      (.gitignore already ignores out/)
schemas/invoice.schema.json   draft 2020-12 invoice schema
samples/*.txt                 clean, ambiguous, sparse, empty (empty.txt is 0 bytes)
expected/*.json               hand-written correct extractions
extract/__init__.py
extract/client.py             get_client() -> anthropic.Anthropic(); DEFAULT_MODEL
extract/validate.py           load_schema(path=...) -> dict
                              validation_errors(instance, schema) -> [{path, message}]
                              arithmetic_errors(instance) -> [{path, message}]
extract/extractor.py          extract_invoice(text, client, schema, model) -> ExtractionResult
                              ExtractionError, TruncatedResponseError, MissingToolUseError
```

`ExtractionResult` is a dataclass with fields `data` (dict or None), `errors` (list of
`{path, message}` dicts, empty on success), `attempts` (int), and a property `ok` that is
`True` when `errors` is empty.

`get_client()` takes no arguments and reads credentials from the environment.
`DEFAULT_MODEL` reads `ANTHROPIC_MODEL`, falling back to `claude-opus-5`.

The twelve schema fields are `invoice_number`, `vendor_name`, `invoice_date`, `due_date`,
`purchase_order`, `currency`, `line_items`, `subtotal`, `tax`, `total`, `confidence`,
`ambiguity_notes`.

## Files to create

Exactly these two. Do not create or modify anything else. In particular **do not create
`extract/eval.py`** — task 04 owns it.

```
extract/sinks.py
extract/__main__.py
```

## Size budget — read this before you write

The project has a hard constraint: **under 400 lines of source code excluding comments**,
across the whole project. Tasks 01 and 02 already used most of it. Your budget for these
two files is **60 lines of code total** — roughly 25 for `sinks.py` and 35 for
`__main__.py`.

Comments do not count toward the budget and should still be plentiful. Keep the *code*
tight: no helper class, no argument-parsing abstraction, no logging framework. Plain
functions and `argparse`.

### 1. `extract/sinks.py` (~25 lines of code)

Writes results to the two downstream destinations. Must not import `anthropic`.

Provide:

- `write_json(data, name, out_dir="out")` — writes `out/<name>.json`, pretty-printed with
  `indent=2` and a trailing newline. Creates the directory if absent. Returns the path.
  Comment on why the per-document file is pretty-printed: a human opens it to check an
  extraction by eye, and this is the artifact they read.

- `append_event(record, out_dir="out", filename="events.ndjson")` — appends **one line** of
  compact JSON to `out/events.ndjson`. Opens in append mode `"a"`. The JSON must be written
  with **no embedded newlines** — pass `separators=(",", ":")` and do not use `indent`.
  Returns the path.

  **Required comment block** — at least 8 lines, on **why NDJSON is a common integration
  format** for a downstream ingestion queue. It must make these points concretely:
  - One self-delimiting record per line, so a reader consumes it with a `for line in file`
    loop and never has to hold the whole file in memory. A single top-level JSON array
    cannot be read that way — the parser needs the closing bracket before it can yield
    anything.
  - Appending is an `open(..., "a")` and a `write`. Appending to a JSON array means reading
    the whole file, parsing it, mutating it, and rewriting it — which is O(file) per record
    and loses data if the process dies mid-rewrite.
  - A truncated NDJSON file loses only its last partial line; every earlier record is still
    valid and readable. A truncated JSON array is unparseable in its entirety.
  - It is the format the common ingestion paths already speak — `jq`, log shippers,
    BigQuery and similar bulk loaders, Kafka-style one-message-per-line pipelines.

  The event record is built by the caller (see below), not by this function.

Both functions take `out_dir` as a parameter with a default rather than hardcoding `out/`,
so the eval harness in task 04 can write elsewhere. One comment line saying so is enough.

### 2. `extract/__main__.py` (~35 lines of code)

The CLI entrypoint, run as `python -m extract <path-to-document>`.

Use `argparse`. One required positional argument: the path to the document. Add one
optional `--out` flag defaulting to `out`. Nothing else.

**The fail-fast guard is the point of this file.** In this exact order:

1. Read the input file. If the path does not exist, exit with a clear message.
2. **Validate the input BEFORE constructing the client and before any API call.** Reject
   the document when it is empty, whitespace-only, or shorter than 20 characters after
   stripping. Exit with a clear, specific message naming the reason.
3. Only after the input passes: `get_client()`, `load_schema()`, `extract_invoice(...)`.

**Required comment block** — at least 6 lines — explaining why the guard runs first. Make
these points: an empty or garbage document cannot produce a valid invoice, so the API call
is guaranteed waste — it costs money, adds seconds of latency, and returns either a refusal
or a confidently hallucinated invoice, which is the worse outcome. Placing the check before
`get_client()` also means this path needs **no credential at all**, so it stays testable
offline. Note the deliberate ordering: constructing the client first would fail on a missing
API key and mask the real problem, which is that the document is empty.

On a successful or failed extraction:

- Write `out/<name>.json` via `write_json`, where `<name>` is the input file's stem
  (`samples/clean.txt` -> `clean`). Use `pathlib.Path(args.path).stem`.
- Append one event to `out/events.ndjson` via `append_event`. Build the record with these
  keys: `document` (the stem), `ok` (bool), `attempts` (int), `error_count` (int),
  `confidence` (from the data, or `None`), and `extracted_at` (a UTC ISO-8601 timestamp —
  use `datetime.now(timezone.utc).isoformat()`).

  Comment on why the event log records a *failed* extraction too: a queue that only hears
  about successes cannot tell "nothing was submitted today" from "everything failed today".

- Print a short human summary to stdout: the output path, whether validation passed, the
  attempt count, and — when it failed — each error's path and message.

**Exit codes**, each with a comment:
- `0` — extraction succeeded and validated.
- `1` — the extraction ran but the result failed validation after the retry.
- `2` — bad input or a usage error; no API call was made.

Comment on why a validation failure and a bad-input error get *different* non-zero codes:
a shell script or CI job needs to distinguish "this document is malformed, skip it" from
"the pipeline is broken, stop".

Catch `ExtractionError` (which covers `TruncatedResponseError` and `MissingToolUseError`),
print the message clearly, and exit `1`. Do not let a traceback reach the user.

Guard the entrypoint with `if __name__ == "__main__":`.

## Constraints

- Standard library plus `anthropic`, `jsonschema`, `python-dotenv`. Nothing else.
- No class hierarchy, no framework, no logging library. Plain functions and `print`.
- Never print a key or token, even partially.
- Do not modify any file from tasks 01 or 02.

## How to verify before you report finished

The first three run **with no API key**, which is the point.

```bash
# 1. Fail fast on an empty document. Must exit 2 and must NOT mention a missing API key.
python -m extract samples/empty.txt; echo "exit code: $?"

# 2. Fail fast on garbage/too-short input.
printf 'xx' > /tmp/tiny.txt 2>/dev/null || printf 'xx' > tiny.txt
python -m extract tiny.txt; echo "exit code: $?"
rm -f tiny.txt

# 3. Missing file. Must exit 2 with a clear message.
python -m extract samples/does-not-exist.txt; echo "exit code: $?"

# 4. The sinks work, tested directly with no API involved.
python -c "
import json, pathlib, shutil
from extract.sinks import write_json, append_event
shutil.rmtree('out', ignore_errors=True)
d = json.loads(pathlib.Path('expected/clean.json').read_text())
print('json written to:', write_json(d, 'clean'))
append_event({'document':'clean','ok':True,'attempts':1,'error_count':0,'confidence':0.96,'extracted_at':'2026-01-01T00:00:00+00:00'})
append_event({'document':'sparse','ok':False,'attempts':2,'error_count':1,'confidence':None,'extracted_at':'2026-01-01T00:00:01+00:00'})
lines = pathlib.Path('out/events.ndjson').read_text().splitlines()
print('ndjson line count:', len(lines))
print('every line parses independently:', all(json.loads(l) for l in lines))
print('no line contains a newline:', all('\n' not in l for l in lines))
print('line 1 is compact:', lines[0])
"

# 5. No credential is printed or hardcoded.
grep -rniE \"sk-ant|api[_-]?key\s*=\s*[\\\"'][^\\\"']\" extract/ || echo "no hardcoded credential"

# 6. Report your code-line budget.
python -c "
import pathlib
for n in ['sinks.py','__main__.py']:
    ls=[l for l in pathlib.Path('extract',n).read_text(encoding='utf-8').splitlines()]
    code=[l for l in ls if l.strip() and not l.strip().startswith('#')]
    print(n, 'code-ish lines:', len(code))
"
```

Checks 1, 2 and 3 must exit `2` and must **not** produce a traceback or complain about
credentials. Check 4 must show two independently-parseable compact lines.

## Acceptance criteria

1. Exactly `extract/sinks.py` and `extract/__main__.py` were created. `extract/eval.py` was
   **not** created. No task 01 or 02 file was modified.
2. `sinks.py` does not import `anthropic`.
3. `write_json` writes `out/<name>.json` with `indent=2` and creates the directory if
   absent.
4. `append_event` opens in append mode and writes exactly one line per call, compact
   (`separators=(",", ":")`), with no embedded newline.
5. The NDJSON comment block is at least 8 lines and makes all four required points
   (streaming reads, cheap appends, partial-file survival, ecosystem support).
6. Both sink functions accept an `out_dir` parameter with a default.
7. `__main__.py` uses `argparse` with one positional path and an optional `--out`.
8. **The empty/garbage/short-input guard runs before `get_client()` is called.** Verify by
   reading the code, not by assuming.
9. The fail-fast comment block is at least 6 lines and covers wasted cost, the hallucination
   risk, offline testability, and why client construction must not come first.
10. Exit codes are 0 success, 1 validation failure, 2 bad input — each commented, including
    why 1 and 2 differ.
11. An event is appended for failed extractions as well as successful ones, with a comment
    explaining why.
12. The event record has all six required keys including a UTC ISO-8601 `extracted_at`.
13. `ExtractionError` is caught and reported cleanly. No traceback reaches the user.
14. Combined code across the two files is **at or under 60 lines** excluding comments and
    blank lines. Report the actual number.
15. All six verification commands were run and produced the stated results.

## Report back

State the files created, the exact output of all six verification commands, your actual
code-line count for criterion 14, and anything you could not satisfy and why. An unmet
criterion reported plainly is more useful than a false claim of success.
