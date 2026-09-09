# Task 04 — Field-level accuracy evaluation harness

You are implementing the final work package of a larger project. You see only this
specification. Do not assume knowledge from any other conversation.

## Project context (restated — do not skip)

We are building `extract`, a command-line tool. It reads an unstructured invoice written as
plain text, sends it to the Claude API via a **forced tool call**, validates the returned
JSON against a JSON Schema, and writes the result to `out/`.

The audience is an engineer studying for the Claude Certified Architect – Foundations exam.
**This code is a teaching artifact.** Comments explain *why*, not syntax. Clarity over
cleverness. Python 3.13. Project root is the current working directory.

## What already exists — do not modify any of it

Tasks 01–03 are complete and accepted.

```
schemas/invoice.schema.json   draft 2020-12 invoice schema
samples/*.txt                 clean.txt, ambiguous.txt, sparse.txt, empty.txt
expected/*.json               clean.json, ambiguous.json, sparse.json
                              hand-written correct extractions, all schema-valid

extract/client.py     get_client() -> anthropic.Anthropic();  DEFAULT_MODEL
extract/validate.py   load_schema(path="schemas/invoice.schema.json") -> dict
                      validation_errors(instance, schema) -> [{path, message}]
                      arithmetic_errors(instance) -> [{path, message}]
extract/extractor.py  extract_invoice(text, client, schema, model) -> ExtractionResult
                      ExtractionError, TruncatedResponseError, MissingToolUseError
extract/sinks.py      write_json(data, name, out_dir="out") -> Path
                      append_event(record, out_dir="out", filename="events.ndjson") -> Path
extract/__main__.py   the CLI: python -m extract <path> [--out DIR]
```

`ExtractionResult` is a dataclass with `data` (dict or None), `errors` (list of
`{path, message}`), `attempts` (int), and an `ok` property that is `True` when `errors` is
empty.

The twelve schema fields: `invoice_number`, `vendor_name`, `invoice_date`, `due_date`,
`purchase_order`, `currency`, `line_items`, `subtotal`, `tax`, `total`, `confidence`,
`ambiguity_notes`.

Four are nullable **and** required — `invoice_date`, `due_date`, `purchase_order`, `tax`.
`null` means "the document genuinely did not contain this", which is a *correct* answer
when the expected file also says `null`.

## Files to create

Exactly one file. Do not create or modify anything else.

```
extract/eval.py
```

It runs as `python -m extract.eval`.

## Size budget

The project ceiling is **under 400 lines of source excluding comments**, and tasks 01–03
used 301. Your budget is **60 lines of code**. Comments do not count and should stay
plentiful; keep the *code* tight. No class hierarchy, no test framework, no `argparse`
subcommands — plain functions and `print`.

## What the harness does

For each of the three sample/expected pairs (`clean`, `ambiguous`, `sparse` — **not**
`empty`, which has no expected file):

1. Read `samples/<name>.txt`.
2. Run the real extraction through `extract_invoice`.
3. Compare the extracted object against `expected/<name>.json` **field by field**.
4. Report per-field results, a per-document score, and an aggregate across all documents.

### Comparison rules — implement exactly these

Compare the **twelve top-level fields**. For each, decide correct or incorrect:

- **`confidence`** — do **not** compare for equality. It is a self-reported judgement, and
  demanding the model match a hand-written 0.91 exactly would measure agreement with our
  guess rather than extraction quality. Score it correct when it lands within **±0.15** of
  the expected value. Comment on why this field is scored differently from the rest.

- **`ambiguity_notes`** — do **not** compare the strings. They are free prose and will never
  match verbatim. Score it correct when **both are empty or both are non-empty** — that is,
  when the model agreed with the expected file about *whether* the document was ambiguous.
  Comment that this measures the signal we actually depend on (was a judgement call made?)
  rather than prose similarity.

- **`line_items`** — compare **element by element**, and each element **field by field**
  (`description`, `quantity`, `unit_price`, `amount`). Report the line-item score as a
  fraction of matched sub-fields, so dropping one row out of four is not scored the same as
  getting every row wrong. A length mismatch counts the missing or extra rows as incorrect.
  Compare `description` case-insensitively after stripping whitespace.

- **Money and number fields** (`subtotal`, `tax`, `total`) — compare with a tolerance of
  `0.01`, because these are binary floats. `null` matches `null`.

- **String fields** (`invoice_number`, `vendor_name`, `invoice_date`, `due_date`,
  `purchase_order`, `currency`) — compare after stripping whitespace, case-insensitively.
  `null` matches `null`, and `null` against a value is incorrect.

**Scoring must be field-level, not exact-match on the whole document.** Include a comment
block of at least 6 lines explaining why. Make these points concretely: an exact-match score
collapses "one wrong field out of twelve" and "every field wrong" into the same 0, so it
cannot tell a nearly-working extractor from a broken one and cannot show whether a prompt
change helped. Field-level scoring also localises the problem — it names *which* field
regressed, which is what you act on. Say plainly that a 92% field score is not "92% of
documents are usable": one wrong `total` can invalidate an otherwise perfect record, so
field accuracy is a diagnostic signal, not a business metric.

### Output

Print a readable report to stdout:

- Per document: the name, whether it passed schema and arithmetic validation, the attempt
  count, and a per-field `correct` / `WRONG` list. For a wrong field, show the expected and
  the actual value so the reader can see what happened.
- Per document: a field score, e.g. `10/12 fields`.
- At the end: an aggregate line across all documents, and a **per-field breakdown across
  documents** — which fields were correct in all 3, which failed and where. That breakdown
  is the most useful output of the whole harness, because it points at the field to fix.

### Behaviour when there is no API key

`get_client()` will construct, but the API call will fail. Catch the failure per document,
print a clear message, and continue to the next one rather than crashing the whole run.
Exit `2` if **no** document could be evaluated, so the harness cannot silently report a
meaningless 0%. Comment on why an empty run must not look like a failing run.

Exit `0` when every document was evaluated, whatever the score. The harness *reports*
accuracy; it does not enforce a threshold. Comment on that choice: a hard-coded pass mark
in the harness is a policy decision that belongs to the caller, and a CI job can compare the
printed aggregate against its own bar.

## Constraints

- Standard library plus `anthropic`, `jsonschema`, `python-dotenv`. Nothing else.
- Reuse the existing functions. Do not reimplement schema loading, validation, or
  extraction.
- Never print a key or token.
- Do not modify any file from tasks 01–03.

## How to verify before you report finished

The first two run **without an API key**.

```bash
# 1. The comparison logic is correct, tested directly against the fixtures with no API.
#    Substitute the real name of your comparison function if it differs.
python -c "
import json, pathlib
from extract.eval import compare
exp = json.loads(pathlib.Path('expected/clean.json').read_text())

# Identical objects must score a perfect 12/12.
r = compare(exp, exp)
print('identical:', r)

# One wrong field must cost exactly one field.
bad = json.loads(json.dumps(exp)); bad['vendor_name'] = 'Wrong Vendor Ltd'
print('one wrong field:', compare(exp, bad))

# confidence within tolerance is correct; outside it is not.
c1 = json.loads(json.dumps(exp)); c1['confidence'] = exp['confidence'] - 0.10
c2 = json.loads(json.dumps(exp)); c2['confidence'] = exp['confidence'] - 0.50
print('confidence -0.10 (want correct):', compare(exp, c1))
print('confidence -0.50 (want WRONG):  ', compare(exp, c2))

# ambiguity_notes: different prose, same emptiness -> correct.
n = json.loads(json.dumps(exp)); n['ambiguity_notes'] = []
print('notes both empty:', compare(exp, n))

# a dropped line item must be partial credit, not total loss
d = json.loads(json.dumps(exp)); d['line_items'] = d['line_items'][:-1]
print('dropped one line item:', compare(exp, d))
"

# 2. null handling: sparse.json has purchase_order and tax as null.
python -c "
import json, pathlib
from extract.eval import compare
exp = json.loads(pathlib.Path('expected/sparse.json').read_text())
print('null vs null:', compare(exp, exp))
g = json.loads(json.dumps(exp)); g['purchase_order'] = 'PO-INVENTED'
print('null vs invented value (want WRONG):', compare(exp, g))
"

# 3. The harness runs end to end without crashing when there is no key.
python -m extract.eval; echo "exit code: $?"

# 4. Code budget.
python -c "
import pathlib
ls = pathlib.Path('extract/eval.py').read_text(encoding='utf-8').splitlines()
print('code-ish lines:', len([l for l in ls if l.strip() and not l.strip().startswith('#')]))
"
```

Check 1 must show a perfect score for identical objects, exactly one field lost for one
wrong field, `confidence` correct at −0.10 and wrong at −0.50, and **partial** credit for a
dropped line item. Check 3 must not produce a traceback.

## Acceptance criteria

1. Only `extract/eval.py` was created. No task 01–03 file was modified.
2. It reuses `load_schema`, `extract_invoice`, `validation_errors` / `arithmetic_errors`.
   It does not reimplement them.
3. All twelve top-level fields are compared.
4. `confidence` uses a ±0.15 tolerance, with a comment on why it is scored differently.
5. `ambiguity_notes` is scored on empty-vs-non-empty, with a comment on why.
6. `line_items` is compared element-wise and sub-field-wise, and gives **partial credit**.
   A length mismatch counts the missing or extra rows as incorrect.
7. Money fields use a `0.01` tolerance. String fields strip and compare case-insensitively.
   `null` matches `null`; `null` against a value is incorrect.
8. A comment block of **at least 6 lines** explains why scoring is field-level rather than
   exact-match, including the honest point that field accuracy is a diagnostic signal and
   not a business metric.
9. Output shows per-document results, per-field correct/wrong with expected vs actual, a
   per-document score, an aggregate, and a **per-field breakdown across documents**.
10. A per-document API failure is caught and reported; the run continues to the next
    document.
11. Exit `2` when no document could be evaluated, with a comment on why an empty run must
    not read as a 0% run. Exit `0` otherwise, with a comment on why the harness reports
    rather than enforces a threshold.
12. `empty.txt` is not evaluated — it has no expected file.
13. Code is **at or under 60 lines** excluding comments and blank lines. Report the number.
14. No credential printed or hardcoded.
15. All four verification commands were run, with real output pasted.

## Report back

State the file created, the exact output of all four verification commands, your actual
code-line count, and anything you could not satisfy and why. An unmet criterion reported
plainly is more useful than a false claim of success.
