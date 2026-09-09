# `extract` — structured data extraction with JSON Schema validation

A small, production-shaped CLI that turns an unstructured invoice into validated,
schema-conformant JSON. Built as a teaching artifact for the **Claude Certified Architect –
Foundations (CCA-F)** exam, so every design decision is explained in the code rather than
assumed. The comment-to-code ratio is above 1:1 on purpose: a newcomer should be able to
read any file top to bottom.

360 lines of source, 400-line ceiling. No framework — the standard library, one API client,
one validator.

---

## Why Python

The brief allowed Node.js or Python. Python was chosen because it matches the surrounding
repository: the existing CCA-F exercises under `projects/claudecertificationguide/` are
Python on an `anthropic` + `python-dotenv` stack, so a reader moves between them without a
context switch. `jsonschema.Draft202012Validator` is a genuine draft 2020-12 implementation,
which the schema requires.

The cost is the eval entrypoint. `npm run eval` went away with the language choice, and
`make eval` was unavailable in fact — `make` is not installed on the target machine, so a
`Makefile` would have documented a command that does not run. The eval is
`python -m extract.eval`, which needs no build tool. Full reasoning in
[DECISIONS.md](DECISIONS.md) → ADR-006.

---

## Architecture

```
  samples/clean.txt                          schemas/invoice.schema.json
  (unstructured text)                        (draft 2020-12, $comment on every constraint)
         │                                              │
         ▼                                              │
  ┌──────────────────┐                                  │
  │  __main__.py     │  FAIL-FAST GUARD                 │
  │                  │  empty / whitespace / < 20 chars │
  │                  │  ──> exit 2, NO API CALL         │
  └────────┬─────────┘                                  │
           │ text is worth processing                   │
           ▼                                            │
  ┌──────────────────┐                                  │
  │  client.py       │  Anthropic()  ← env only,        │
  │                  │  no credential in source         │
  └────────┬─────────┘                                  │
           ▼                                            │
  ┌───────────────────────────────────────────┐         │
  │  extractor.py                             │         │
  │                                           │         │
  │   tool_choice={"type":"tool",             │◄────────┤ same schema object,
  │                "name":"record_invoice"}   │         │ so the contract
  │   strict: True  ← on the TOOL definition  │         │ cannot drift
  │   thinking      ← deliberately unset      │         │
  │                                           │         │
  │   response.content → tool_use → .input    │         │
  └────────┬──────────────────────────────────┘         │
           ▼                                            │
  ┌───────────────────────────────────────────┐         │
  │  validate.py         (no anthropic import)│◄────────┘
  │                                           │
  │   validation_errors()   schema conformance│
  │   arithmetic_errors()   cross-field checks│
  │                         JSON Schema cannot│
  │                         express           │
  └────────┬──────────────────────────────────┘
           │
      errors? ──── yes ──►  ONE retry, feeding back the concrete
           │                failing paths as a tool_result
           │                       │
           │                  still failing? ──► report errors, exit 1
           │                                     (no third attempt)
           ▼ no
  ┌──────────────────┐
  │  sinks.py        │
  │                  ├──► out/<name>.json      pretty, indent=2   (a human reads this)
  │                  └──► out/events.ndjson    one compact line   (a queue reads this)
  └──────────────────┘

  ── measured separately ────────────────────────────────────────────────
  eval.py :  samples/*.txt ──► extract ──► compare field-by-field
                                              against expected/*.json
```

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env          # then add your credential
```

`.env` accepts either the first-party API key or a gateway:

```bash
ANTHROPIC_API_KEY=sk-ant-...
# or, for a bearer-token gateway:
# ANTHROPIC_BASE_URL=https://api.example-gateway.com
# ANTHROPIC_AUTH_TOKEN=...
# ANTHROPIC_MODEL=claude-opus-5     # optional override
```

The client is constructed as `anthropic.Anthropic()` with no arguments — the SDK reads the
environment itself, so pointing at a gateway is a config change rather than a code change
and no credential ever passes through the source.

## Running

```bash
python -m extract samples/clean.txt
python -m extract samples/ambiguous.txt --out /tmp/scratch
python -m extract.eval
```

**Exit codes**, which are deliberately distinct:

| Code | Meaning |
|---|---|
| `0` | extracted and validated |
| `1` | extraction ran, result failed validation after the retry |
| `2` | bad input or usage error — **no API call was made** |

`1` and `2` differ because a caller acts on them differently. A shell loop over a directory
should treat `2` as "not a document, skip it" and `1` as "the model could not extract this
one, set it aside for a human". Collapsing both into a bare `1` forces every caller to parse
stderr.

### Works with no API key

The whole validation layer is free of the `anthropic` import, so these run offline:

```bash
# fail-fast guard — exits 2, never mentions a missing credential
python -m extract samples/empty.txt

# validators, against the hand-written fixtures
python -c "
import json, pathlib
from extract.validate import load_schema, validation_errors, arithmetic_errors
s = load_schema()
for p in sorted(pathlib.Path('expected').glob('*.json')):
    d = json.loads(p.read_text())
    print(p.name, validation_errors(d, s), arithmetic_errors(d))
"
```

---

## The edge cases, and how each is handled

| Case | Handling |
|---|---|
| **Missing fields** | `invoice_date`, `due_date`, `purchase_order`, `tax` are `["string","null"]` **and** in `required`. Present-and-`null` = "I read the document, it wasn't there". A missing *key* = truncation or a pipeline bug. Different failures, and the schema can tell them apart. |
| **Validation failure** | Exactly **one** retry, feeding back the concrete failing paths (`line_items.2.amount: quantity 500 * unit_price 0.12 is 60.0, but amount is 6.0`) as a `tool_result`. A second failure is reported, not retried. |
| **Ambiguous values** | `ambiguity_notes[]` plus a `confidence` score. Two unlabelled dates get *recorded* — what was seen, what the alternatives were, why one was chosen — instead of one being silently discarded. `samples/ambiguous.txt` exercises this. |
| **Empty / garbage input** | Rejected before `get_client()` is called. No API call, no credential needed, exit `2`. |

The ordering of the last one is the part that is easy to get wrong. Constructing the client
first would fail on a missing API key — a true statement about the wrong problem, sending
someone off to fix their `.env` when the real fault is an empty file.

---

## Why force a tool call instead of asking for "JSON only"

The long version is the comment block at the top of `extract/extractor.py`. In short:

A prompt is a **request**; `tool_choice` is a **constraint**. "Return only JSON" usually
works, and "usually" is the problem — the response arrives with HTTP 200 and the right data,
wrapped in `Here is the extracted JSON:` or a markdown fence. Every repair is a hack that
works on the document which motivated it and breaks on the next one.

Forcing the call makes the API prefill the assistant turn, so there is no position in the
output where a preamble could go. `strict: True` on the tool definition makes the API
validate the input against the schema *before responding*. And the tool's `input_schema` is
the same dict `load_schema()` returns, so what we ask for and what we check cannot drift.

**The honest limit:** this guarantees *shape*, never *correctness*. The model can return a
flawlessly valid invoice with the wrong vendor name. That is why local validation and the
eval both exist.

Two API details worth knowing, both verified against the current docs:

- `strict: True` is a top-level field on the **tool definition**, not on `tool_choice`.
- `thinking` is **deliberately unset**. Manual extended thinking (`{"type": "enabled"}`) is
  *rejected with an error* when combined with forced tool use. Adaptive thinking, the
  default on Opus 5, supports it. The working configuration is the one where you write
  nothing — easy to "fix" by adding a line and thereby break.

---

## Why evals matter for extraction systems

An extraction system fails **silently**. A web server that breaks returns a 500; an
extractor that breaks returns a beautifully formatted, schema-valid JSON object with the
wrong total in it. Nothing raises. `strict: True` passes it, the schema passes it, and it
lands in `out/` looking exactly like a correct extraction. Without a measurement you have no
signal at all — only the absence of complaints, which is not the same thing.

That is also why every prompt change is otherwise a guess. Tighten the tool description and
you cannot say whether it helped, hurt, or shifted the errors somewhere else.

**Scoring is field-level, not exact-match.** Exact match collapses "one wrong field out of
twelve" and "every field wrong" into the same `0`, so it cannot distinguish a nearly-working
extractor from a broken one. Field-level scoring also *localises* the regression — the
per-field breakdown names which field degraded, which is what you act on.

Two fields are scored differently on purpose:

- **`confidence`** — within **±0.15**, not exact. Every other field has a fact of the matter
  printed on the document; `confidence` is the model's judgement about its own work, and our
  expected value is a hand-written guess at what a reasonable judgement looks like. Exact
  comparison would measure agreement with our guess and would mark a well-calibrated 0.88 as
  a failure.
- **`ambiguity_notes`** — scored on **empty vs non-empty**. Two correct notes about the same
  ambiguity can share no words at all, so comparing strings would score writing style. What
  matters downstream is whether the model agreed a judgement call was needed.

`line_items` gets **partial credit**, scored sub-field by sub-field. Dropping one row out of
four scores `0.75`, not `0` — a real distinction that exact match destroys.

**The caveat that matters:** a 92% field score is **not** "92% of documents are usable". One
wrong `total` invalidates an otherwise perfect record. Field accuracy is a diagnostic signal
for improving the extractor, not a business metric for trusting its output.

---

## What this teaches you for the CCA-F

The exam scores judgement about **tradeoffs**, not API trivia. Each file maps to a concept
and, more usefully, to the tradeoff it resolves.

| File | Exam concept | The tradeoff it settles |
|---|---|---|
| `extract/extractor.py` | **D4 — structured output with tool use** | Forced tool call vs. prompting for JSON vs. `output_config.format`. Why a constraint beats a request, and why `strict: True` sits on the tool, not `tool_choice`. |
| `extract/extractor.py` (retry loop) | **D4 — validation, retry and feedback loops** | Why the retry budget is *one*, and why specific failing paths beat "that was invalid, try again". A model failing the same schema twice is misreading the document, not glitching. |
| `schemas/invoice.schema.json` | **D4 — structured output; D5 — reliability** | Nullable-and-required vs. optional. Present-and-`null` (a fact about the document) vs. a missing key (a pipeline bug). Also `tax: null` vs. `tax: 0`. |
| `extract/validate.py` | **D5 — context management & reliability** | What JSON Schema structurally *cannot* do: no cross-field arithmetic, and `2026-13-45` passes a date `pattern`. Where the validation boundary sits. |
| `extract/__main__.py` | **D5 — reliability; D2 — tool design** | Fail fast before spending an API call. Why the guard must precede client construction, and why bad input and validation failure get different exit codes. |
| `extract/sinks.py` | **D2 — tool & integration design** | NDJSON vs. a JSON array: streaming reads, O(1) appends, partial-file survival — and the honest cost that the file is not valid JSON. |
| `extract/eval.py` | **D4 — prompt engineering; D5 — confidence calibration** | Field-level vs. exact-match scoring. Why `confidence` and free-prose fields need different comparison rules than facts. |
| `extract/client.py` | **D3 — configuration & workflows** | Zero-argument client construction: gateway vs. first-party becomes config, not code, and no credential touches the source. |
| `tasks/`, `COORDINATION.md` | **D1 — agent architecture & orchestration** | Coordinator/implementer split: self-contained specs, falsifiable acceptance criteria, a bounded revision budget, and verification the coordinator re-runs rather than trusts. |

The two ideas most likely to be worth exam marks:

1. **A constraint is not a request.** Forcing a tool call removes failure modes; prompting
   for JSON only discourages them. The same distinction shows up across the exam whenever a
   question offers "instruct the model to..." against "configure the API so it cannot...".
2. **Schema-valid is not correct.** Every layer here exists because the one above it
   guarantees less than it appears to: `strict: True` guarantees shape, the schema cannot
   see across fields, the arithmetic check cannot tell you the vendor name is wrong, and
   only the eval can — against hand-written ground truth.

---

## Project layout

```
schemas/invoice.schema.json   draft 2020-12; every constraint carries a $comment
                              naming the concrete failure it prevents
samples/                      clean, ambiguous (two unlabelled dates),
                              sparse (no PO, no tax), empty (0 bytes)
expected/                     hand-written ground truth for the eval
extract/
  __main__.py                 CLI + fail-fast guard
  client.py                   zero-arg Anthropic client
  extractor.py                forced tool call + one-retry correction loop
  validate.py                 schema + cross-field arithmetic (no anthropic import)
  sinks.py                    out/<name>.json and out/events.ndjson
  eval.py                     field-level accuracy harness
out/                          generated, gitignored

DECISIONS.md                  6 ADRs: context / decision / consequences
COORDINATION.md               the delegation ledger — spec, verdict, iterations
tasks/                        the four work-package specs
```

## How this was built

Coordinator/implementer split. A coordinator wrote the plan, the four task specs, and the
reviews; a separate delegated agent wrote every line of source, schema, and fixture. Each
package was dispatched with a self-contained spec, its own offline verification commands,
and 15–18 falsifiable acceptance criteria, then reviewed against those criteria before the
next package went out.

Four packages, four dispatches, **zero revision rounds**. The ledger is in
[COORDINATION.md](COORDINATION.md), including what made the specs work and the one case
where a naive `grep` produced a false failure the coordinator had to look past.
