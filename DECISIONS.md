# Architecture decisions

Short ADR-style notes. Each records the context that forced a choice, the choice, and what
it costs — including the parts that are genuinely worse as a result.

---

## ADR-001 — Force a tool call rather than prompt for JSON

**Context.** The tool has to turn an invoice into a JSON object the rest of the pipeline can
rely on. Three routes were available: ask the model to "reply with JSON only" and parse the
text; use `output_config.format` with a JSON schema; or define a tool and force the model to
call it with `tool_choice`.

Prompting for JSON is a *request*. The model usually complies. "Usually" is the whole
problem, and the failure mode is the bad kind: the response arrives with HTTP 200 and the
right data, wrapped in "Here is the extracted JSON:" or a markdown fence or a trailing
"Let me know if you need changes!". Each of those makes `json.loads` raise, and each repair
is a hack — slice from the first `{`, regex out the fence, strip after the last `}` — that
works on the document which motivated it and breaks on the next one. The brace-slice fails
the first time a vendor address contains a `{`.

**Decision.** Force the call: `tool_choice={"type": "tool", "name": "record_invoice"}`, with
`strict: True` on the tool definition.

Forcing the call makes the API prefill the assistant turn, so there is no position in the
output where a preamble could go. The other shapes become unreachable rather than merely
discouraged. `strict: True` makes the API validate the tool input against `input_schema`
before responding, so a class of malformed output never crosses the network. And the tool's
`input_schema` is *the same dict* `load_schema()` returns, so the thing we ask for and the
thing we check cannot drift apart.

**Consequences.** The response cannot be prose, so the parsing layer disappears entirely.

The cost is that `strict: True` constrains the schema — it requires `additionalProperties:
false` and a `required` array, which is why `schemas/invoice.schema.json` carries both. It
also rules out manual extended thinking: `thinking: {"type": "enabled"}` is rejected
outright when combined with forced tool use. Adaptive thinking (the default on Opus 5) works
and is what we get by leaving the parameter unset, so the working configuration is the one
where you write nothing — easy to "fix" by adding a line and thereby break. There is a
comment in `extractor.py` saying so.

`output_config.format` was the close alternative and would have been a defensible choice.
Forced tool use was picked because the tool's `description` field is prompt text the model
reads on every call, which gives a natural home for the per-field guidance that measurably
improves extraction quality.

**The honest limit.** Forcing the call guarantees *shape*, never *correctness*. The model
can return a flawlessly valid invoice with the wrong vendor name. `strict: True` passes it,
our schema passes it. That is why ADR-003 and ADR-005 exist.

---

## ADR-002 — Nullable fields are required, not optional

**Context.** Real invoices are missing things. Many carry no purchase-order reference and no
tax line. The schema has to represent absence. The reflexive move is to leave those keys out
of `required` and let them be omitted.

**Decision.** `invoice_date`, `due_date`, `purchase_order`, and `tax` are typed
`["string", "null"]` (or `["number", "null"]`) **and** listed in `required`. The key must
always be present; its value may be `null`.

**Consequences.** This buys a distinction that omission cannot express:

- **present and `null`** — the extractor read the document and the field was genuinely
  absent from it. A fact about the document.
- **key missing** — the extractor forgot, or the response was truncated mid-object. A bug in
  the pipeline.

If nullable fields were merely optional, both situations would produce the same JSON and
nothing downstream could tell them apart. Making them required forces the model to state,
key by key, that it looked.

There is a second-order effect on the prompt. A model asked to fill a mandatory field will
fill it — inventing a plausible invoice number is a far more available behaviour than
reporting absence. So the system prompt has to grant explicit permission to answer `null`,
or the carefully nullable fields never get used. Schema and prompt are one design here, not
two.

The same reasoning drives `tax: null` versus `tax: 0`. `null` means the document printed no
tax line at all — zero-rated freight, a vendor not registered for VAT. `0` claims the
document *stated* a tax of zero. A VAT reconciliation needs those apart, and forcing a
number would produce a fabricated `0` that is unrecoverable afterwards.

**Cost.** Every consumer must handle `null` for four fields. That is real work pushed
downstream, and it is the right trade: the alternative pushes *ambiguity* downstream, which
is worse and is not visible in the type.

---

## ADR-003 — Validate locally as well, and retry exactly once

**Context.** `strict: True` already validates the tool input server-side. A local validation
pass is, on the face of it, redundant.

It is not, for two reasons. JSON Schema constrains each value independently — a type, a
range, a pattern — and has no way to say "this number must equal the sum of those numbers",
because a subschema cannot see its siblings. Every relationship *between* fields is
invisible to it. A model can return an object that is perfectly schema-valid and
arithmetically nonsense: correct line items under a total matching none of them. Second, the
schema's date `pattern` checks shape only, so `2026-13-45` satisfies it while naming a
thirteenth month.

**Decision.** Run two validators on every response — `validation_errors` (schema) and
`arithmetic_errors` (cross-field). On failure, make **exactly one** more API call, feeding
back the concrete failing paths as a `tool_result`. Validate again. A second failure is
returned as a reported failure, not retried.

The feedback has to be specific. "That was invalid, try again" gives the model nothing to
act on, so the likely second attempt is a near-copy of the first — one wasted call for an
identical answer. `line_items.2.amount: quantity 500 * unit_price 0.12 is 60.0, but amount
is 6.0` names the row, the field, and the arithmetic, so the model can go back to that line
of the document. Specific feedback is the entire mechanism.

**Consequences.** A worst-case document costs two API calls instead of one.

The budget is fixed at one retry because of what a second failure *means*. A transient
fault — a dropped field, a slip in one multiplication — is very likely fixed by one round of
specific feedback. A model that fails the same schema twice, having been shown exactly what
was wrong, is not suffering a transient fault: it is misreading the document, or the
document does not contain what we are asking for. A third call re-reads the same text with
the same instructions and returns the same wrong answer, having spent more money to do it.
An unbounded retry turns one bad document into an unbounded bill.

Validation is also kept free of the `anthropic` import. That is what lets the entire
validation layer be exercised with no API key, no network, and no cost — and it is why the
retry loop itself could be tested with a scripted fake client rather than a live call.

---

## ADR-004 — NDJSON for the event log, pretty JSON for the document

**Context.** Output goes to two consumers with opposite needs: a human checking one
extraction by eye, and a downstream ingestion queue reading a running history.

**Decision.** Two sinks. `out/<name>.json` is pretty-printed with `indent=2`. `out/events.
ndjson` is one compact, newline-delimited JSON object per run, opened in append mode.

**Consequences.** NDJSON beats a single top-level JSON array on four counts that matter
downstream:

1. **Streaming reads.** Each line is self-delimiting, so a consumer uses `for line in file`
   in constant memory and starts immediately. A conforming array parser needs the closing
   bracket before it can yield anything at all.
2. **O(1) appends.** Adding a record is `open(..., "a")` and one write. Appending to an
   array means read, parse, mutate, re-serialise, rewrite — O(file) per record, with a
   window where the old file is gone and the new one is incomplete.
3. **Partial files stay useful.** A crash mid-write loses the last partial line; every
   earlier record is still parseable. A truncated array is unreadable in its entirety,
   including the thousands of records written hours before.
4. **The ecosystem already speaks it.** `jq`, log shippers, and bulk loaders take it
   natively.

The tradeoff, stated plainly: the file as a whole is **not valid JSON**, so anything that
blindly calls `json.loads` on the entire thing will fail. That is the price, and it is why
the extension is `.ndjson`.

Failed extractions are logged too. A queue that only hears about successes cannot
distinguish "nothing was submitted today" from "everything submitted today failed" — both
look like silence.

---

## ADR-005 — Score field-level accuracy, not exact match

**Context.** Extraction quality has to be measurable, or a prompt change is a guess. The
cheapest metric is exact match: does the extracted object equal the expected one?

**Decision.** Score the twelve top-level fields individually, with `line_items` scored
sub-field by sub-field for partial credit. Three sample/expected pairs live in `samples/`
and `expected/`; `python -m extract.eval` reports per-document and aggregate accuracy plus a
per-field breakdown.

Two fields are scored differently on purpose. `confidence` is compared within ±0.15, because
demanding a model match a hand-written 0.91 exactly measures agreement with our guess rather
than extraction quality. `ambiguity_notes` is scored on empty versus non-empty, because the
strings are free prose that will never match verbatim — what we depend on is whether the
model agreed that a judgement call was needed.

**Consequences.** Exact match collapses "one wrong field out of twelve" and "every field
wrong" into the same `0`. It cannot distinguish a nearly-working extractor from a broken
one, so it cannot tell you whether a change helped. Field-level scoring also *localises* the
regression — the per-field breakdown names which field degraded, which is the thing you act
on.

**The honest caveat.** A 92% field score is **not** "92% of documents are usable". One wrong
`total` invalidates an otherwise perfect record. Field accuracy is a diagnostic signal for
improving the extractor, not a business metric for trusting its output. The two get confused
constantly and the distinction is worth stating out loud.

**Cost.** The expected files are hand-written, so they are a maintenance burden and a source
of error — a wrong number in `expected/*.json` does not fail loudly, it silently biases every
score the harness ever reports. That is why their arithmetic was verified independently
before task 04 was dispatched.

---

## ADR-006 — Python, and `python -m extract.eval` as the eval entrypoint

**Context.** The brief allowed Node.js or Python, and named `npm run eval` or `make eval` as
the eval command.

**Decision.** Python, with `python -m extract.eval`.

**Consequences.** Python matches the surrounding repository — the existing CCA-F exercises
under `projects/claudecertificationguide/` are Python, sharing an `anthropic` +
`python-dotenv` stack — so a reader moves between them without a context switch.
`jsonschema.Draft202012Validator` is a genuine draft 2020-12 implementation, which the schema
requires.

The cost is the entrypoint. `npm run eval` was unavailable by choosing Python, and `make
eval` was unavailable in fact: `make` is not installed on the target machine, so a `Makefile`
would have documented a command that does not run. `python -m extract.eval` needs no build
tool at all. It is the least memorable of the three, which is a real if minor loss, and the
README states it prominently to compensate.
