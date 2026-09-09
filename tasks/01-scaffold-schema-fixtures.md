# Task 01 — Scaffold, JSON Schema, and evaluation fixtures

You are implementing one work package of a larger project. You see only this
specification. Do not assume knowledge from any other conversation. Everything you need
is written below.

## Project context (restated — do not skip)

We are building `extract`, a small command-line tool. It reads an unstructured invoice
written as plain text. It sends the text to the Claude API. It gets structured JSON back.
It validates that JSON against a JSON Schema. It writes the validated result to disk.

The audience is an engineer who studies for the Claude Certified Architect – Foundations
exam. The code is a teaching artifact. A newcomer must be able to read it from top to
bottom and understand **why** each decision was made. Clarity beats cleverness every time.

The project uses **Python 3.13**. The project root is the current working directory.

This work package builds the foundation only. It contains **no Claude API code**. Later
work packages add the API client, the CLI, and the evaluation harness.

## Goal

Create the project scaffold, the invoice JSON Schema, and the sample and expected-output
fixture pairs that a later evaluation harness will measure accuracy against.

## Files to create

Create exactly these files. Do not create any other files.

```
requirements.txt
.env.example
.gitignore
schemas/invoice.schema.json
samples/clean.txt
samples/ambiguous.txt
samples/sparse.txt
samples/empty.txt
expected/clean.json
expected/ambiguous.json
expected/sparse.json
```

### 1. `requirements.txt`

Exactly three dependencies, one per line, unpinned:

```
anthropic
jsonschema
python-dotenv
```

Do not add any other dependency. The project constraint is: standard library, plus one
API client, plus one validator. `python-dotenv` loads the local `.env` file.

### 2. `.env.example`

A template that documents the environment variables. It must never contain a real key.
Use these contents:

```
# Copy this file to .env and fill in your credentials.
# .env is gitignored. Never commit a real key.

# Option A — first-party Anthropic API:
ANTHROPIC_API_KEY=your-key-here

# Option B — a gateway that authenticates with a bearer token.
# If you use a gateway, set these two instead of ANTHROPIC_API_KEY.
# ANTHROPIC_BASE_URL=https://api.example-gateway.com
# ANTHROPIC_AUTH_TOKEN=your-token-here

# Optional. Overrides the default model.
# ANTHROPIC_MODEL=claude-opus-5
```

### 3. `.gitignore`

Must ignore at least `.env`, `out/`, and `__pycache__/`. Add a short comment above each
entry that says why it is ignored.

### 4. `schemas/invoice.schema.json` — the central deliverable

A JSON Schema that uses **draft 2020-12**. Set
`"$schema": "https://json-schema.org/draft/2020-12/schema"`.

**Commenting requirement.** JSON has no comment syntax. Draft 2020-12 defines the
`$comment` keyword for exactly this purpose. Put a `$comment` on **every** constraint you
write. Each `$comment` must state *what that constraint protects against* — the concrete
bad output it stops. Write what breaks without it, not what it does.

Weak `$comment`, do not write this: `"$comment": "The invoice number is a string."`
Strong `$comment`, write this instead: `"$comment": "minLength 1 rejects an empty string.
A model that cannot find the invoice number must return null, which is an explicit 'I
looked and it was absent'. An empty string is indistinguishable from a formatting bug
downstream."`

The root object must set `"additionalProperties": false` and list a `"required"` array.
Both are needed later: a companion tool definition sets `strict: true`, which the Claude
API only accepts on a schema that has `additionalProperties: false` and `required`.

Model these fields:

| Field | Type | Notes |
|---|---|---|
| `invoice_number` | string, `minLength` 1 | required, not nullable |
| `vendor_name` | string, `minLength` 1 | required, not nullable |
| `invoice_date` | `["string", "null"]`, `format: "date"`, `pattern` for `YYYY-MM-DD` | required, nullable |
| `due_date` | `["string", "null"]`, same date constraints | required, nullable |
| `purchase_order` | `["string", "null"]` | required, nullable — the sparse sample has none |
| `currency` | string, `enum` of `["USD", "EUR", "GBP", "CAD"]` | required |
| `line_items` | array, `minItems` 1 | required |
| `subtotal`, `tax`, `total` | number, `minimum` 0 | `tax` nullable, the other two not |
| `confidence` | number, `minimum` 0, `maximum` 1 | required |
| `ambiguity_notes` | array of strings | required, may be empty |

Each `line_items` entry is an object with `description` (string, `minLength` 1),
`quantity` (number, `exclusiveMinimum` 0), `unit_price` (number, `minimum` 0), and
`amount` (number, `minimum` 0). Set `additionalProperties: false` and a `required` array
on the line-item object too.

Four design points your `$comment` text must cover explicitly, because these are the
teaching content of this file:

1. **Nullable versus optional.** `invoice_date`, `due_date`, `purchase_order`, and `tax`
   are `["string", "null"]` (or `["number", "null"]`) **and** appear in `required`. This is
   deliberate. The key must always be present; its value may be `null`. Present-and-null
   means "the extractor looked and the field was genuinely absent from the document". An
   omitted key means "the extractor forgot, or the response was truncated". Those are
   different failures and the schema must be able to tell them apart. Explain this.
2. **`ambiguity_notes` captures what a single value would destroy.** An invoice often
   carries two unlabelled dates. Any schema that offers exactly one date field forces the
   model to silently pick one and throw the other away, leaving no trace for a human
   reviewer. This array is where the model records "two dates present, 2026-03-14 and
   2026-04-13; assigned the earlier as invoice_date". Explain this.
3. **`confidence` exists to route documents, not to decorate them.** A downstream queue
   can hold anything below a threshold for human review. Explain this.
4. **`enum` on `currency`.** A free-string currency lets `$`, `USD`, `usd`, and `dollars`
   all through, and the downstream consumer then needs its own normalising layer. The enum
   moves that failure to extraction time, where the error message is actionable. Explain
   this.

### 5. Sample documents — `samples/*.txt`

Plain-text invoices. Realistic and messy, like something pasted out of an email or a PDF
text layer. Not tidy key-value lists. Vary the layout between the three files so they do
not all share one template.

- **`samples/clean.txt`** — every field is present and unambiguous. One clearly labelled
  invoice date, one clearly labelled due date, a purchase-order number, a tax line, and
  three or four line items whose amounts sum to the stated subtotal.
- **`samples/ambiguous.txt`** — contains **two dates that are not clearly labelled**. For
  example a bare date in the header and another bare date near the payment terms, with
  neither marked "invoice date" or "due date". This file exists to exercise
  `ambiguity_notes`. It should also carry a slightly lower expected confidence.
- **`samples/sparse.txt`** — **no purchase-order number and no tax line**. Everything else
  is present. This file exercises the nullable-versus-required distinction.
- **`samples/empty.txt`** — a genuinely empty file, zero bytes. Later work packages use it
  to prove the CLI fails fast before it ever constructs an API client.

### 6. Expected outputs — `expected/*.json`

One file per non-empty sample: `expected/clean.json`, `expected/ambiguous.json`,
`expected/sparse.json`. Each is the correct extraction for its sample, hand-written by
you. A later evaluation harness compares real model output against these field by field.

Hard requirements:

- Every expected file **must validate against `schemas/invoice.schema.json`**. Check this
  before you finish. See "How to verify" below.
- `expected/sparse.json` must have `"purchase_order": null` and `"tax": null`. The keys are
  present with a null value; they are not omitted.
- `expected/ambiguous.json` must have a **non-empty** `ambiguity_notes` array that names
  both candidate dates and states which reading was chosen.
- Every number must be consistent with its own sample text. Line-item amounts must sum to
  the subtotal, and `subtotal + tax` must equal `total`. Do the arithmetic and check it.
  These files are the measuring stick, so an error here silently corrupts every future
  accuracy number.

## How to verify before you report finished

Run these and confirm they pass. Do not report success without running them.

```bash
pip install -r requirements.txt

# 1. Every expected file validates against the schema.
python -c "
import json, pathlib
from jsonschema import Draft202012Validator
schema = json.loads(pathlib.Path('schemas/invoice.schema.json').read_text())
Draft202012Validator.check_schema(schema)
v = Draft202012Validator(schema)
for p in sorted(pathlib.Path('expected').glob('*.json')):
    errs = sorted(v.iter_errors(json.loads(p.read_text())), key=lambda e: e.path)
    print(p.name, 'OK' if not errs else [f'{list(e.path)}: {e.message}' for e in errs])
"

# 2. The constraints actually bite. This must report errors, not OK.
python -c "
import json, pathlib
from jsonschema import Draft202012Validator
schema = json.loads(pathlib.Path('schemas/invoice.schema.json').read_text())
bad = json.loads(pathlib.Path('expected/clean.json').read_text())
bad['currency'] = 'dollars'      # not in the enum
bad['invoice_number'] = ''       # violates minLength
bad['confidence'] = 1.5          # above maximum
errs = list(Draft202012Validator(schema).iter_errors(bad))
print(f'{len(errs)} errors (expect at least 3)')
for e in errs: print(' -', list(e.path), e.message)
"

# 3. samples/empty.txt really is empty.
python -c "import pathlib; print('empty.txt bytes:', pathlib.Path('samples/empty.txt').stat().st_size)"
```

Check 1 must print `OK` for all three files. Check 2 must report at least 3 errors. Check
3 must print `0`.

## Acceptance criteria

A reviewer reads your output against this list. Every line must hold.

1. All eleven listed files exist. No extra files were created.
2. `requirements.txt` has exactly the three named dependencies.
3. `.env.example` contains no real credential.
4. `.gitignore` covers `.env`, `out/`, and `__pycache__/`, each with a reason comment.
5. The schema declares draft 2020-12 and passes `Draft202012Validator.check_schema`.
6. The root object sets `additionalProperties: false` and a `required` array.
7. **Every constraint carries a `$comment`** that names the concrete failure it prevents.
   A `$comment` that only restates the constraint in English fails this criterion.
8. The four design points above — nullable versus optional, `ambiguity_notes`,
   `confidence`, and the currency `enum` — are each explained in `$comment` text.
9. `invoice_date`, `due_date`, `purchase_order`, and `tax` are nullable **and** listed in
   `required`.
10. All four sample files exist. `empty.txt` is zero bytes. `ambiguous.txt` genuinely
    contains two unlabelled dates. `sparse.txt` genuinely lacks a PO number and a tax line.
11. All three expected files validate cleanly against the schema.
12. `expected/sparse.json` has `purchase_order` and `tax` present and set to `null`.
13. `expected/ambiguous.json` has a non-empty `ambiguity_notes` naming both dates.
14. Arithmetic is consistent in all three expected files: line items sum to `subtotal`, and
    `subtotal + tax` equals `total`.
15. All three verification commands were run and produced the stated results.

## Report back

When you finish, state:
- The files you created.
- The exact output of all three verification commands.
- Anything in this spec you could not satisfy, and why. Be honest — an unmet criterion
  reported plainly is far more useful than a false claim of success.
