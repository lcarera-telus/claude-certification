# Task 02 — Extraction core: client, forced tool call, validation, one retry

You are implementing one work package of a larger project. You see only this
specification. Do not assume knowledge from any other conversation. Everything you need is
written below, including the exact Claude API shapes to use.

## Project context (restated — do not skip)

We are building `extract`, a command-line tool. It reads an unstructured invoice written as
plain text, sends it to the Claude API, gets structured JSON back, validates that JSON
against a JSON Schema, and writes the validated result to disk.

The audience is an engineer studying for the Claude Certified Architect – Foundations exam.
**This code is a teaching artifact.** A newcomer must read it top to bottom and understand
*why* each decision was made. Comment density must be high — comments explaining reasoning,
not comments restating syntax. Clarity beats cleverness.

Python 3.13. The project root is the current working directory.

## What already exists (task 01 — do not modify any of it)

```
requirements.txt              anthropic, jsonschema, python-dotenv
.env.example                  documents ANTHROPIC_API_KEY, or ANTHROPIC_BASE_URL +
                              ANTHROPIC_AUTH_TOKEN for a gateway, and optional
                              ANTHROPIC_MODEL
schemas/invoice.schema.json   draft 2020-12 invoice schema (details below)
samples/*.txt                 clean, ambiguous, sparse, empty
expected/*.json               hand-written correct extractions
```

The schema's root object has `"additionalProperties": false` and a `"required"` array
naming **all twelve** fields: `invoice_number`, `vendor_name`, `invoice_date`, `due_date`,
`purchase_order`, `currency`, `line_items`, `subtotal`, `tax`, `total`, `confidence`,
`ambiguity_notes`.

Four of those are nullable *and* required: `invoice_date`, `due_date`, `purchase_order`
(all `["string", "null"]`) and `tax` (`["number", "null"]`). This is deliberate — the key
must always be present, its value may be `null`. Present-and-null means "the extractor
looked and the field was genuinely absent from the document". An omitted key means "the
extractor forgot, or the response was truncated". Different failures, different fixes.

`currency` is an enum of `["USD", "EUR", "GBP", "CAD"]`. `confidence` is a number from 0 to
1. `ambiguity_notes` is an array of strings, possibly empty. `line_items` is an array with
`minItems: 1`, each item an object with `description`, `quantity`, `unit_price`, `amount`.

## Claude API facts — verified against the official documentation

**Use these shapes exactly. Do not substitute anything you remember; several of these
changed recently and a remembered shape will be wrong.**

- Default model: `claude-opus-5`. Read `ANTHROPIC_MODEL` from the environment first and
  fall back to that literal.
- **Force the tool call** with `tool_choice={"type": "tool", "name": "record_invoice"}`.
- **Enable strict schema validation** with `strict: True` as a **top-level field on the
  tool definition** — a sibling of `name`, `description`, and `input_schema`. It does
  **not** go on `tool_choice`. It requires the schema to have `additionalProperties: false`
  and a `required` array, which ours does.
- **Do not set the `thinking` parameter at all.** Manual extended thinking
  (`{"type": "enabled"}`) is *rejected with an error* when combined with forced tool use.
  Adaptive thinking, which is the default on Opus 5, supports forced tool use. Leaving the
  parameter unset gets the working combination. Write this reason in a comment — it is a
  real constraint a reader would otherwise trip over.
- **Do not use assistant-message prefill.** It returns a 400 error on Opus 5.
- Read the result by iterating `response.content` and selecting blocks where
  `block.type == "tool_use"`. The extracted object is `block.input`, already a Python dict.
  Never string-match against a serialized version of it.
- Set `max_tokens` to `4096`.

The request looks like this:

```python
response = client.messages.create(
    model=model,
    max_tokens=4096,
    system=SYSTEM_PROMPT,
    tools=[tool_definition],                                    # strict: True lives inside
    tool_choice={"type": "tool", "name": "record_invoice"},
    messages=messages,
)
```

## Files to create

Create exactly these four files. Do not create or modify anything else.

```
extract/__init__.py
extract/client.py
extract/extractor.py
extract/validate.py
```

Do not create `extract/__main__.py`, `extract/sinks.py`, or `extract/eval.py` — later work
packages own those. Do not write a CLI here.

### 1. `extract/__init__.py`

A short module docstring naming the package and listing what each module does. Keep it
under 15 lines. No logic.

### 2. `extract/client.py` (~25 lines of code)

One function, `get_client()`, returning an `anthropic.Anthropic()` instance, plus a
module-level `DEFAULT_MODEL`.

Load `.env` from the project root with `python-dotenv` before reading anything.

Construct the client with **no arguments**: `anthropic.Anthropic()`. The SDK reads
`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, and `ANTHROPIC_BASE_URL` from the environment
itself. Comment on why the zero-argument constructor is the right call: pointing the tool
at a gateway instead of the first-party API becomes a config change, not a code change, and
no credential is ever passed through the source.

Expose `DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")`.

### 3. `extract/validate.py` (~50 lines of code)

Loads the schema and validates candidate objects. It must **not** import the `anthropic`
package — keeping validation independent of the API is what lets the whole layer be tested
offline, and a reader should be able to see that at a glance.

Provide:

- `load_schema(path="schemas/invoice.schema.json")` — reads the schema, calls
  `Draft202012Validator.check_schema(schema)`, returns it. Comment on why validating the
  schema itself is worth a line of code: a typo in a schema keyword otherwise fails open,
  silently accepting everything.
- `validation_errors(instance, schema)` — returns a **list of dicts**, one per error, each
  with a `path` key (the dotted field path, e.g. `line_items.0.amount`, or `<root>` when
  the error is at the top level) and a `message` key. Returns an empty list when the
  instance is valid. Use `Draft202012Validator(schema).iter_errors(instance)` and sort the
  errors for stable output.
  **Return errors, do not raise.** The caller feeds these back to the model as a correction
  prompt, so they are data, not control flow. Comment on that.
- `arithmetic_errors(instance)` — the cross-field checks JSON Schema structurally cannot
  express. Returns a list in the same `{path, message}` shape. Check:
  - each line item's `quantity * unit_price` equals its `amount`
  - the line-item amounts sum to `subtotal`
  - `subtotal + tax` equals `total`, treating a `null` tax as 0 for this check only
  - `invoice_date` and `due_date` are real calendar dates (use
    `datetime.date.fromisoformat`), because the schema's `pattern` accepts the well-formed
    but impossible `2026-13-45`
  - when both dates are present, `due_date` is not earlier than `invoice_date`

  Compare money with a small tolerance (`abs(a - b) < 0.01`), and comment on why: these are
  binary floats, and `0.1 + 0.2 != 0.3`. An exact equality test here would reject correct
  extractions.

  Guard every one of these against missing or wrong-typed keys, because
  `arithmetic_errors` may run on an object that has not yet passed schema validation.

### 4. `extract/extractor.py` (~90 lines of code)

The heart of the project.

**Required comment block.** At the top, a comment block of at least 12 lines explaining
**why forcing a tool call is more reliable than asking for "JSON only" in the prompt**.
This is the single most important explanation in the codebase. It must make these points
concretely:

- A prompt is a *request*. `tool_choice={"type": "tool", ...}` is a *constraint applied by
  the API*, which prefills the assistant turn so the model structurally cannot emit prose,
  a preamble, an apology, or a ` ```json ` fence before the object.
- "Return only JSON" fails in ways that look like success: a leading "Here is the JSON:", a
  markdown fence, a trailing "Let me know if you need anything else." Each forces the
  caller into fragile substring-slicing and regex recovery, and each of those recovery
  hacks fails differently on the next document.
- With `strict: True`, the tool input is schema-validated by the API, so an entire class of
  malformed response never reaches our code at all.
- The tool's `input_schema` is *the same schema* the response is validated against, so the
  contract cannot drift between what we asked for and what we check.
- Be honest about the boundary: forcing the call guarantees *shape*, never *correctness*.
  The model can still return a well-formed object with the wrong vendor name. That is why
  local validation and the eval harness in task 04 both exist.

Provide:

- `build_tool_definition(schema)` — returns the tool dict. `name` is `record_invoice`,
  `input_schema` is the loaded schema, `strict` is `True`, and the `description` is a
  genuinely detailed several-sentence description of when and how to use the tool. Comment
  that a thorough tool description measurably improves extraction quality — it is the
  primary place the model learns what the fields mean.
- `SYSTEM_PROMPT` — a module constant instructing the model to extract faithfully. It must
  tell the model explicitly: never invent a value; use `null` for a field genuinely absent
  from the document; record every judgement call in `ambiguity_notes`; and set `confidence`
  to reflect real uncertainty rather than defaulting to a high number.
- `extract_invoice(text, client, schema, model)` — runs the extraction and returns a
  result object or dict carrying at least: the extracted `data`, the list of `errors`
  (empty on success), and an `attempts` count.

**The retry rule — implement exactly this, no more.**

1. Call the API with the forced tool call.
2. Pull `block.input` from the `tool_use` block.
3. Validate: `validation_errors` **plus** `arithmetic_errors`.
4. If there are no errors, return successfully.
5. If there are errors, make **exactly one** more API call. Append the assistant's own
   turn, then a `tool_result` block whose content is the concrete list of errors, phrased
   as a correction instruction. Feeding back the specific failing paths — not a generic
   "that was invalid, try again" — is what makes the retry work; comment on that.
6. Validate the second response. If it still fails, **return the errors as a failure**. Do
   not retry a third time. Comment on why the retry budget is fixed at one: a model that
   fails the same schema twice is misreading the document, not suffering a transient fault,
   and further attempts spend money to produce the same wrong answer.

A `tool_result` block must reference the originating `tool_use` block's `id` via
`tool_use_id`, and its shape is
`{"type": "tool_result", "tool_use_id": <id>, "content": <string>}`.

**Also handle these, each with a comment:**
- No `tool_use` block in the response at all — raise a clear error naming
  `response.stop_reason`. Do not return `None` and let it fail later somewhere confusing.
- `response.stop_reason == "max_tokens"` — the object is truncated. Treat this as a
  distinct, clearly-named failure rather than letting a half-parsed object through.

## Constraints

- Standard library, plus `anthropic`, `jsonschema`, and `python-dotenv`. Nothing else.
- No framework, no class hierarchy, no abstract base classes. Plain functions.
- Do not hardcode a key anywhere. Do not print a key or token, even partially.
- Total source across all four files should stay near 165 lines excluding comments and
  blank lines. Comments are not counted and should be plentiful.

## How to verify before you report finished

These run **without an API key**, which is the point — the validation layer must be
testable offline.

```bash
# 1. Imports are clean and the schema loads and self-checks.
python -c "
from extract.validate import load_schema, validation_errors, arithmetic_errors
s = load_schema()
print('schema loaded and self-checked, keys:', len(s['properties']))
"

# 2. Valid fixtures produce zero errors from BOTH validators.
python -c "
import json, pathlib
from extract.validate import load_schema, validation_errors, arithmetic_errors
s = load_schema()
for p in sorted(pathlib.Path('expected').glob('*.json')):
    d = json.loads(p.read_text())
    print(p.name, 'schema:', validation_errors(d, s), 'arithmetic:', arithmetic_errors(d))
"

# 3. Both validators actually catch what they are meant to catch.
python -c "
import json, pathlib
from extract.validate import load_schema, validation_errors, arithmetic_errors
s = load_schema()
d = json.loads(pathlib.Path('expected/clean.json').read_text())

bad = json.loads(json.dumps(d)); bad['currency'] = 'dollars'; del bad['tax']
print('schema errors:', validation_errors(bad, s))

bad2 = json.loads(json.dumps(d)); bad2['total'] = 999999.0
print('arithmetic errors:', arithmetic_errors(bad2))

bad3 = json.loads(json.dumps(d)); bad3['invoice_date'] = '2026-13-45'
print('impossible date:', arithmetic_errors(bad3))
"

# 4. The tool definition is well formed and carries strict.
python -c "
from extract.validate import load_schema
from extract.extractor import build_tool_definition
t = build_tool_definition(load_schema())
print('name:', t['name'])
print('strict:', t.get('strict'))
print('description length:', len(t['description']))
print('schema wired in:', t['input_schema']['additionalProperties'] is False)
"

# 5. No credential is ever printed.
grep -rniE "sk-ant|api[_-]?key\s*=\s*[\"'][^\"']" extract/ || echo "no hardcoded credential"
```

Check 2 must print two empty lists for all three fixtures. Check 3 must report a missing
`tax` key, a bad `currency`, a `total` mismatch, and an impossible date. Check 4 must print
`strict: True`.

## Acceptance criteria

1. Exactly the four listed files exist. `__main__.py`, `sinks.py`, and `eval.py` were
   **not** created.
2. `client.py` constructs `anthropic.Anthropic()` with no arguments and comments on why.
3. `DEFAULT_MODEL` reads `ANTHROPIC_MODEL`, falling back to `claude-opus-5`.
4. `validate.py` does not import `anthropic`.
5. `load_schema` calls `Draft202012Validator.check_schema`.
6. `validation_errors` returns a list of `{path, message}` dicts and never raises on an
   invalid instance.
7. `arithmetic_errors` implements all five listed checks, uses a `< 0.01` money tolerance
   with a comment explaining float behaviour, and does not crash on a malformed instance.
8. `extractor.py` opens with a comment block of **at least 12 lines** on forced tool use
   versus prompting for JSON, covering all five required points including the honest
   limitation that shape is guaranteed but correctness is not.
9. The request uses `tool_choice={"type": "tool", "name": "record_invoice"}`.
10. `strict: True` is a top-level key of the **tool definition**, not of `tool_choice`.
11. The `thinking` parameter is **not set anywhere**, and a comment explains that manual
    extended thinking is rejected with forced tool use.
12. The tool's `input_schema` is the same loaded schema used for validation.
13. Exactly **one** retry. Not zero, not two. The retry feeds back the concrete error paths
    via a `tool_result` block carrying the correct `tool_use_id`.
14. A second failure returns errors as a failure result — it does not retry again and does
    not raise an unhandled exception.
15. A missing `tool_use` block and a `max_tokens` stop reason are each handled explicitly
    with a clear, distinct error.
16. No hardcoded credential anywhere; no key or token is printed.
17. All five verification commands were run and produced the stated results.
18. Comment density is high enough that a newcomer can read each file top to bottom.
    Comments explain *why*, not *what the syntax does*.

## Report back

State the files you created, the exact output of all five verification commands, and
anything you could not satisfy and why. An unmet criterion reported plainly is far more
useful than a false claim of success.
