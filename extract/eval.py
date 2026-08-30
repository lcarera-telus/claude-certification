# Field-level accuracy harness. Run it with: python -m extract.eval
#
# It extracts each sample for real, compares the result against the hand-written
# expected file field by field, and reports where the extractor is losing
# accuracy. It reuses load_schema, extract_invoice, validation_errors and
# arithmetic_errors rather than reimplementing any of them -- a harness that
# reimplements the thing it measures ends up measuring its own copy.

# =============================================================================
# WHY SCORING IS FIELD-LEVEL AND NOT EXACT-MATCH ON THE WHOLE DOCUMENT
# =============================================================================
# The tempting metric is "did the extracted object equal the expected object?"
# -- one boolean per document, easy to compute, easy to put in a dashboard. It
# is also nearly useless, for three reasons.
#
# 1. IT DESTROYS THE INFORMATION YOU NEED. An extraction that gets eleven of
#    twelve fields right and an extraction that gets every field wrong both
#    score 0. Those are wildly different systems -- one is nearly working, one
#    is broken -- and the metric cannot tell them apart.
#
# 2. IT CANNOT SEE PROGRESS. Change the tool description, tighten the system
#    prompt, swap the model: under exact-match the score stays 0 until the very
#    last field falls into place, then jumps to 1. Every intermediate
#    improvement is invisible, so you cannot tell a change that helped from a
#    change that did nothing, and you end up tuning by superstition.
#
# 3. IT DOES NOT LOCALISE THE FAULT. "Document failed" is not actionable.
#    "due_date was wrong in 3 of 3 documents" is -- it points straight at the
#    date instruction in the prompt. That per-field breakdown at the end of this
#    report is the most useful thing the harness produces, because it names the
#    field to go and fix.
#
# THE HONEST CAVEAT, WHICH MATTERS MORE THAN THE METRIC ITSELF:
# a 92% field score does NOT mean "92% of documents are usable". Those are
# different quantities and confusing them is how a team ships a broken
# extractor with a green dashboard. One wrong `total` invalidates an otherwise
# perfect record -- nobody pays an invoice that is right about the vendor and
# wrong about the amount. Field accuracy is a DIAGNOSTIC SIGNAL for finding
# what to improve. It is not a business metric, and it must never be quoted as
# a document-level success rate.
# =============================================================================

import json
import pathlib

from .client import DEFAULT_MODEL, get_client
from .extractor import extract_invoice
from .validate import arithmetic_errors, load_schema, validation_errors

# empty.txt is deliberately absent: it has no expected file, because there is no
# correct extraction of an empty document. The CLI's fail-fast guard is what
# covers that case, and it is tested there rather than scored here.
DOCUMENTS = ("clean", "ambiguous", "sparse")
FIELDS = ("invoice_number", "vendor_name", "invoice_date", "due_date", "purchase_order",
          "currency", "line_items", "subtotal", "tax", "total", "confidence", "ambiguity_notes")
ITEM_FIELDS = ("description", "quantity", "unit_price", "amount")


def _text(value):
    # Strip and lower-case before comparing, so "Northwind Paper & Print Co." and
    # " northwind paper & print co. " count as the same answer. Trailing spaces
    # and capitalisation are artefacts of how the text sat on the page; scoring
    # them as errors would report noise as regression. Non-strings pass through
    # untouched, which is what makes None == None work as "both said absent".
    return value.strip().lower() if isinstance(value, str) else value


def _row(rows, index):
    # An out-of-range index yields {} rather than raising, so a length mismatch
    # between expected and actual line_items scores its missing rows as wrong
    # instead of crashing the whole run.
    return rows[index] if index < len(rows) and isinstance(rows[index], dict) else {}


def _score_field(name, want, got):
    if name == "line_items":
        return _score_items(want, got)
    # ambiguity_notes is free prose and will never match verbatim -- two correct
    # notes about the same ambiguity can share no words at all. Comparing the
    # strings would score writing style, so instead this scores the signal we
    # actually depend on downstream: did the model agree with us about WHETHER
    # this document required a judgement call? A model that silently picked one
    # of two unlabelled dates and left the array empty has destroyed the only
    # trace a human reviewer had, and that failure is what this catches.
    if name == "ambiguity_notes":
        return float(bool(want) == bool(got))
    # String fields, including a line item's description. null matches null (both
    # said "absent"); null against a value is wrong in either direction, which is
    # what catches an invented purchase-order number.
    if name in ("invoice_number", "vendor_name", "invoice_date", "due_date", "purchase_order", "currency", "description"):
        return float(_text(want) == _text(got))
    # confidence is scored with a WIDE tolerance and everything else with a tight
    # one, and the difference is the point. Every other field has a fact of the
    # matter printed on the document. confidence does not: it is the model's own
    # judgement about its own work, and our expected value is a hand-written
    # guess at what a reasonable judgement looks like. Demanding it match 0.91
    # exactly would measure agreement with our guess rather than extraction
    # quality, and would mark a perfectly calibrated 0.88 as a failure. What we
    # actually care about is that the model is in the right region -- confident
    # on the clean invoice, visibly less so on the ambiguous one -- because that
    # is what a review-routing threshold reads. +/-0.15 tests that and nothing
    # more. The money fields use 0.01 for the usual float reason: these are
    # binary floats, 0.1 + 0.2 != 0.3, and exact equality would reject correct
    # numbers.
    tolerance = 0.15 if name == "confidence" else 0.01
    return float(want is None and got is None or isinstance(want, (int, float)) and isinstance(got, (int, float)) and abs(want - got) <= tolerance)


def _score_items(want, got):
    want = want if isinstance(want, list) else []
    got = got if isinstance(got, list) else []
    # Iterate to the LONGER list, never zip(). zip stops at the shorter one, so a
    # dropped row would silently score 100% on the rows that survived -- the
    # harness would report perfection on an extraction that lost a charge line.
    # Taking the max makes every missing or extra row cost its four sub-fields.
    rows = max(len(want), len(got))
    if not rows:
        return 1.0
    # Partial credit, expressed as the fraction of sub-fields that matched. This
    # is the same argument as the block at the top of the file, one level down:
    # dropping one row out of four (0.75) must not score the same as getting
    # every row wrong (0.0). Each sub-field is scored by _score_field, so a
    # description obeys the string rule and the three numbers obey the 0.01
    # tolerance -- one rule set, applied at both levels.
    matched = sum(_score_field(k, _row(want, i).get(k), _row(got, i).get(k)) for i in range(rows) for k in ITEM_FIELDS)
    return matched / (rows * len(ITEM_FIELDS))


def compare(expected, actual):
    # Returns the per-field detail alongside the total, not just a number. The
    # caller needs to know WHICH fields failed, and a bare score cannot say.
    detail = {n: _score_field(n, expected.get(n), (actual or {}).get(n)) for n in FIELDS}
    return {"score": round(sum(detail.values()), 2), "of": len(FIELDS), "fields": detail}


def run():
    schema = load_schema()
    results = []
    for name in DOCUMENTS:
        expected = json.loads(pathlib.Path("expected", f"{name}.json").read_text(encoding="utf-8"))
        try:
            # get_client() is inside the try on purpose. With no credentials it
            # raises during construction, and that must skip a document rather
            # than kill the run -- otherwise the harness cannot be exercised at
            # all without a key. The catch is deliberately broad, which would be
            # wrong in library code but is right here: auth failures, rate
            # limits, timeouts and network errors are all "this document did not
            # get evaluated", and a harness that dies on document one tells you
            # nothing about documents two and three.
            outcome = extract_invoice(pathlib.Path("samples", f"{name}.txt").read_text(encoding="utf-8"), get_client(), schema, DEFAULT_MODEL)
        except Exception as exc:
            print(f"{name}: SKIPPED, extraction failed - {type(exc).__name__}: {exc}")
            continue
        report = compare(expected, outcome.data)
        results.append((name, report))
        # Both validators are reported separately rather than as one ok/not-ok,
        # because they fail for different reasons: schema errors mean the shape
        # is wrong, arithmetic errors mean the shape is fine and the numbers do
        # not add up. The fix differs, so the report should too.
        print(f"\n{name}: schema_errors={len(validation_errors(outcome.data, schema))} arithmetic_errors={len(arithmetic_errors(outcome.data))} attempts={outcome.attempts} score={report['score']}/{report['of']} fields")
        for field, mark in report["fields"].items():
            # A wrong field prints expected AND actual side by side. "vendor_name
            # WRONG" sends the reader back to the document; showing both values
            # usually makes the cause obvious on sight.
            print(f"  {field:16} {mark:>5.2f}  " + ("correct" if mark == 1.0 else f"WRONG  expected={expected.get(field)!r}  actual={(outcome.data or {}).get(field)!r}"))
    if not results:
        # Exit 2, and print no score at all. An empty run must never render as
        # 0%, because those two states demand opposite responses: 0% means the
        # extractor is broken and you should go read the prompt, while an empty
        # run means the harness never got to try and you should go check your
        # credentials. Printing "0.0% accuracy" for a missing API key would send
        # someone off to debug an extractor that was never invoked.
        print("\nno document could be evaluated, so no score is reported")
        return 2
    earned = sum(r["score"] for _, r in results)
    print(f"\naggregate: {earned:.2f}/{len(results) * len(FIELDS)} fields ({earned / (len(results) * len(FIELDS)):.1%}) across {len(results)} documents\nper-field across documents:")
    # The most useful output in the file. A per-document score says how bad
    # things are; this says WHAT to fix. A field wrong in all three documents is
    # a systematic prompt or schema problem worth an afternoon. The same field
    # wrong in one document is probably that document being hard.
    for field in FIELDS:
        misses = [n for n, r in results if r["fields"][field] < 1.0]
        print(f"  {field:16} {sum(r['fields'][field] for _, r in results):.2f}/{len(results)}  " + (f"failed in: {', '.join(misses)}" if misses else "correct in all"))
    # Exit 0 on any score. The harness REPORTS accuracy, it does not enforce a
    # threshold, and that is a deliberate separation. A pass mark is a policy
    # decision -- 95% might be right for invoices feeding a payment run and 80%
    # fine for a search index -- and policy belongs to the caller, not to the
    # measuring instrument. Hardcoding a bar here would force every consumer to
    # accept our opinion or parse stdout to override it. A CI job that wants a
    # gate compares the printed aggregate against its own number.
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
