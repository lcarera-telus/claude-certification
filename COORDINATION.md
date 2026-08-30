# Coordination log

This file tracks every work package dispatched to a delegated implementation agent.
One row per task. The coordinator writes this file; the implementer never touches it.

## Delegation protocol

1. The coordinator writes a self-contained spec to `tasks/NN-<name>.md`. The implementer
   sees only that file, so each spec restates the project context in full.
2. The coordinator dispatches the spec through the `orca` CLI to an agent running in its
   own terminal.
3. The coordinator reads every produced file directly and scores it against the spec's
   acceptance criteria.
4. A failing package gets **one** revision task listing the concrete defects.
5. A package that fails twice is escalated to the human with an analysis. It is not
   attempted a third time.

## Implementer: Claude, not Codex

The original brief specified Codex as the implementer. Codex is not installed on this
machine. Verified absent by four independent checks:

- No `codex` binary on `PATH` (checked from both Bash and PowerShell).
- No `~/.codex` configuration directory.
- Not present in the global npm package list, nor in Orca's bundled `resources/bin`.
- `orca account list --json` reports `codex.accounts: []` and `hasAuth: false`.

The human approved substituting a delegated `claude` agent, launched with
`orca terminal create --command "claude --permission-mode acceptEdits"`. The protocol
above is otherwise unchanged: the coordinator still writes no source code, and every
output is still reviewed against written criteria before the next package is dispatched.

## Task ledger

| # | Spec | Scope | Iterations | Verdict | Revision fixed |
|---|------|-------|-----------:|---------|----------------|
| 01 | [tasks/01-scaffold-schema-fixtures.md](tasks/01-scaffold-schema-fixtures.md) | requirements, `.env.example`, `.gitignore`, invoice JSON Schema, 4 samples, 3 expected outputs | 1 | **accepted** — 15/15 criteria | none needed |
| 02 | [tasks/02-extraction-core.md](tasks/02-extraction-core.md) | Claude client, forced-tool-call extractor, validator, one-retry correction loop | 1 | **accepted** — 18/18 criteria | none needed |
| 03 | [tasks/03-cli-and-sinks.md](tasks/03-cli-and-sinks.md) | CLI entrypoint with fail-fast input guard, JSON + NDJSON sinks | 1 | **accepted** — 15/15 criteria | none needed |
| 04 | [tasks/04-eval-harness.md](tasks/04-eval-harness.md) | field-level accuracy harness over `samples/` vs `expected/` | 1 | **accepted** — 15/15 criteria | none needed |

## Review notes

Filled in as each package returns.

### Task 01 — accepted on the first iteration

The coordinator re-ran all three verification commands independently rather than relying
on the implementer's report. All reproduced: three expected files validate, the deliberately
corrupted record produces exactly the three expected errors, `samples/empty.txt` is 0 bytes.

Checks the coordinator ran beyond the spec's three commands:

- **Arithmetic, all three expected files.** Line items sum to `subtotal`; `subtotal + tax`
  equals `total`; every row's `quantity * unit_price` equals its `amount`. This matters
  because `expected/*.json` is the measuring stick for the accuracy harness in task 04 — a
  wrong number here would not fail loudly, it would silently bias every future score.
- **Fixture content, not just fixture presence.** `samples/ambiguous.txt` really does carry
  two unlabelled dates (`2026-05-02` in the letterhead, `2026-06-01` on the remittance
  stub). `grep -inE "p\.?o\.?|purchase order|tax|vat"` over `samples/sparse.txt` returns
  nothing, so the sparse case is genuinely sparse rather than merely declared so.
- **Nullable semantics.** `expected/sparse.json` has `purchase_order` and `tax` *present*
  with a `null` value, not omitted — the distinction the schema is built around.
- **No scope creep.** `git status` shows only the files the spec listed.

Two judgements in the output were better than the spec asked for. The `ambiguous` fixture
uses European decimal formatting (`1.900,00`), and the implementer recorded that in
`ambiguity_notes` along with the consequence of misreading it — a US-convention parse
understates the invoice by three orders of magnitude. It also justified its date assignment
from the stated Net 30 terms rather than asserting it.

Two limitations were reported honestly and are accepted as correct:

1. `$comment` attaches per subschema, not per keyword — JSON Schema offers no way to
   annotate an individual keyword. So `invoice_date` carries one `$comment` covering its
   `type`, `format`, and `pattern` together. This is a constraint of the format, not a gap
   in the work.
2. `format: "date"` is annotation-only unless a format checker is passed, so the `pattern`
   is what actually rejects `March 14, 2026`. Neither can reject `2026-13-45`, which is
   well-formed but not a real date. The implementer wrote this limit into the `$comment`
   rather than leaving a reader to assume `format` was load-bearing. A calendar check
   belongs in application code; task 02 picks it up.

### Task 02 — accepted on the first iteration

All five spec verification commands re-run independently by the coordinator and reproduced.
Structural criteria checked by direct inspection: `validate.py` does not import `anthropic`
(the only occurrence is a docstring explaining the deliberate absence); `strict: True` is a
top-level sibling of `name`/`description`/`input_schema` on the tool definition, not on
`tool_choice`; the `thinking` parameter appears nowhere except in a comment warning against
adding it; no hardcoded credential.

**The retry loop was tested behaviourally, not just read.** The spec's own commands exercise
the validators offline but never touch `extract_invoice`, so the most important criteria —
"exactly one retry", "feeds back concrete error paths", "second failure returns rather than
raises" — would otherwise have been accepted on inspection alone. The coordinator wrote a
throwaway harness (in the session scratchpad, not the repo) that drives `extract_invoice`
with a fake client returning scripted responses:

| Case | Result |
|---|---|
| Valid on first try | 1 API call, no retry, `ok=True` |
| Invalid then valid | exactly 2 calls, succeeds; retry messages are `[user, assistant, user]`; the `tool_result` carries the originating `tool_use_id`; the correction text names the failing path `total` |
| Invalid twice | stops at 2 calls — **no third attempt** — and returns the errors as data rather than raising |
| `stop_reason == "max_tokens"` | raises `TruncatedResponseError` with a message that names the fix |
| No `tool_use` block | raises `MissingToolUseError` naming the `stop_reason` |
| Both calls | `tool_choice` forced and `strict: True` present on the retry as well as the first call |

That last row is worth noting: a retry that quietly dropped `tool_choice` would let the
correction round answer in prose, and the failure would look like a document problem rather
than a request-construction bug. The implementer routed both calls through a single
`_build_request` helper specifically so they cannot drift apart.

Three judgements above the spec:

- `_number()` excludes `bool` explicitly, because `bool` subclasses `int` in Python — a
  stray `True` would otherwise be read as the number 1 and produce a baffling arithmetic
  message instead of an honest type error.
- Check 2 (line items sum to subtotal) stands down when any line amount is unreadable,
  rather than reporting a sum that is missing a term.
- Truncation is checked *before* the `tool_use` scan, because a `max_tokens` stop can still
  emit a tool_use block holding a half-written object. Reported as ordinary validation
  errors that would read as "the model omitted six fields" and trigger a pointless
  correction round.

**Size:** 385 code lines against 199 comment lines across the package so far. The <400-line
source ceiling covers the whole project and tasks 03 and 04 still have to fit. Flagged to
the implementer in the task 03 spec as a hard budget rather than left to chance.

### Task 03 — accepted on the first iteration

All six spec verification commands re-run independently and reproduced. The three
fail-fast cases each exit `2` with a specific message, produce no traceback, and — the
point of the exercise — never mention a missing credential, because no credential is
needed to reach them.

**Criterion 8 needed a careful check.** A naive grep for `get_client()` in
`__main__.py` returns two hits, the first of which sits *above* the guard and would
suggest the ordering was wrong. That first hit is inside the explanatory comment block,
which discusses the ordering. The real call is at line 77, below the guard at line 66.
Ordering is correct; the first reading of the evidence was not. Worth recording because
the same false positive would catch a future reviewer.

The `--out` flag is threaded through to `append_event` as well as `write_json`, so a run
directed at a scratch directory does not append to the real event log. That was implied
by the spec rather than stated, and getting it wrong would have contaminated the
production log during the task 04 eval runs.

Honest tradeoff recorded in the code: the NDJSON comment block states that the file as a
whole is *not* valid JSON, so a tool that calls `json.loads` on the entire thing will
fail — and that this is why the extension is `.ndjson`. A comment listing only the
advantages would have been the easier thing to write and the less useful thing to read.

**Size.** 58 code lines across the two files against the 60-line budget.

### Project-wide size check after task 03

A line count that treats every non-comment line as code reports 447 against the 400
ceiling, which looks like a breach. It is not: that count charges the multi-line
`SYSTEM_PROMPT` and the tool `description` — which are prompt *text*, not logic — plus
every module docstring, as source code.

Tokenising each file and counting only lines carrying executable tokens gives the real
figure:

| File | Source | Comments | Prose / docstrings |
|---|---:|---:|---:|
| `__init__.py` | 1 | 0 | 13 |
| `client.py` | 9 | 10 | 21 |
| `validate.py` | 109 | 50 | 70 |
| `extractor.py` | 124 | 139 | 72 |
| `sinks.py` | 14 | 68 | 0 |
| `__main__.py` | 44 | 65 | 0 |
| **Total** | **301** | **332** | **176** |

301 source lines against the 400 ceiling, leaving room for task 04. The comment-to-code
ratio is above 1:1, which was the stated goal — a newcomer can read any file top to
bottom.

### Task 04 — accepted on the first iteration

All four spec verification commands re-run independently and reproduced.

The comparison logic behaves correctly on every scoring rule:

| Case | Score | Reading |
|---|---|---|
| Identical objects | 12.0 / 12 | perfect match |
| One wrong `vendor_name` | 11.0 / 12 | costs exactly one field, no collateral |
| `confidence` off by −0.10 | 12.0 / 12 | inside the ±0.15 tolerance, correct |
| `confidence` off by −0.50 | 11.0 / 12 | outside tolerance, correctly wrong |
| `ambiguity_notes` different prose, both empty | 12.0 / 12 | scored on emptiness, not text |
| One line item dropped | 11.75 / 12 | **partial credit** — `line_items` scores 0.75 |
| `null` vs invented `PO-INVENTED` | 11.0 / 12 | a fabricated value is not a match for `null` |

The dropped-line-item row is the one that matters most. Under exact-match scoring that
document would have scored zero and been indistinguishable from a total failure. It scores
11.75/12 and names `line_items` as the degraded field — which is the actionable output.

**Graceful degradation verified.** With no `ANTHROPIC_API_KEY` set, `python -m extract.eval`
skips each document with a clear per-document message, prints "no document could be
evaluated, so no score is reported", and exits `2`. It does not crash, and — the important
part — it does not print `0%`, which would be indistinguishable from a real total failure.

**Size.** 59 code lines against the 60 budget.

## Final project size

| File | Source | Comments | Prose / docstrings |
|---|---:|---:|---:|
| `__init__.py` | 1 | 0 | 13 |
| `client.py` | 9 | 10 | 21 |
| `validate.py` | 109 | 50 | 70 |
| `extractor.py` | 124 | 139 | 72 |
| `sinks.py` | 14 | 68 | 0 |
| `__main__.py` | 44 | 65 | 0 |
| `eval.py` | 59 | ~90 | — |
| **Total** | **360** | — | — |

360 source lines against the 400 ceiling, with a comment-to-code ratio above 1:1.

## Outcome

Four work packages, four dispatches, **zero revision rounds**. No package required a second
iteration and none was escalated.

What made that work, recorded for reuse:

1. **Every spec restated the full context.** The implementer never saw an earlier spec, so
   each one repeated the project description, the schema shape, and the exact function
   signatures already on disk. Nothing was left to shared memory.
2. **The verified API shapes were written into the specs.** `tool_choice`, the placement of
   `strict: True`, and the incompatibility between manual extended thinking and forced tool
   use were fetched from the official documentation *before* the first dispatch and quoted
   into each spec, with an explicit instruction not to substitute remembered shapes. Two of
   those three are recent changes a remembered prior would get wrong.
3. **Acceptance criteria were falsifiable.** "Comment the schema well" cannot be reviewed.
   "Every constraint carries a `$comment` naming the concrete failure it prevents; a
   `$comment` that only restates the constraint fails this criterion" can — and the spec
   included a weak/strong example pair so the bar was unambiguous.
4. **Every spec carried its own verification commands** that run without a credential, so
   the implementer could check its own work before reporting, and the coordinator could
   re-run the identical commands rather than taking the report on trust.
5. **The coordinator tested behaviour, not just structure, where it mattered.** The retry
   budget in task 02 and the partial-credit scoring in task 04 were both verified by driving
   the real functions with scripted inputs. Reading the code would have suggested they were
   right; running them proved it.
