"""Validation: schema conformance, plus the arithmetic the schema cannot express.

Note what this module does NOT import: the `anthropic` package. That absence is
a design decision, not an oversight. Validation is pure — an object goes in, a
list of problems comes out — so the entire layer runs with no API key, no
network, and no cost. Every verification command for this work package exercises
this file offline. If validation imported the API client, checking a fixture
would require a credential, and the fastest feedback loop in the project would
become the slowest one.

The other decision worth naming up front: these functions RETURN errors, they do
not RAISE them. See validation_errors below for why.
"""

import json
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator

# Money is compared with a tolerance rather than with ==. See _close().
MONEY_TOLERANCE = 0.01


def load_schema(path="schemas/invoice.schema.json"):
    """Read the invoice schema from disk and check that the schema is itself valid."""
    schema = json.loads(Path(path).read_text(encoding="utf-8"))

    # check_schema validates the schema AGAINST the draft 2020-12 metaschema.
    # It is one line and it is worth it, because the failure it prevents is
    # silent. Misspell a keyword -- "minimun" for "minimum", "require" for
    # "required" -- and JSON Schema does not complain. Unknown keywords are
    # legal and simply ignored, so the constraint disappears and the validator
    # cheerfully accepts everything it was supposed to reject. The schema fails
    # OPEN. Every downstream check still runs, still reports success, and the
    # bad data flows through. check_schema turns that silent hole into a loud
    # error at startup, before a single document is processed.
    Draft202012Validator.check_schema(schema)
    return schema


def _dotted(path_parts):
    """Render a jsonschema error path as `line_items.0.amount`, or `<root>` if empty.

    An empty path means the error is about the object as a whole -- a missing
    required key, or an unexpected additional property. "" would render as
    nothing at all in a message, so it gets an explicit name a human can read.
    """
    parts = [str(part) for part in path_parts]
    return ".".join(parts) if parts else "<root>"


def validation_errors(instance, schema):
    """Return a list of {path, message} dicts. Empty list means the instance is valid.

    Errors are returned as DATA, never raised. That is the whole point of this
    signature. The caller's next move on failure is to send these exact paths
    and messages back to the model as a correction instruction, so an error here
    is an ordinary value that gets formatted into a prompt -- not an exceptional
    condition that unwinds the stack. Raising would force the caller to wrap
    every call in try/except purely to recover a value it always expects to
    handle, which is control flow disguised as error handling.

    It also means this function never itself fails on bad input. Any instance,
    however malformed, produces a list. A None, a string, a list where an object
    belongs: all of them come back as reportable errors rather than as a crash.
    """
    validator = Draft202012Validator(schema)
    errors = [
        {"path": _dotted(error.path), "message": error.message}
        for error in validator.iter_errors(instance)
    ]

    # iter_errors yields in an order that depends on dict iteration, so two runs
    # over the same bad object can list the same errors in different orders.
    # Sorting makes the output stable, which matters twice over: a reader
    # diffing two runs sees only real changes, and the correction prompt built
    # from these errors stays byte-identical for identical input, so it can be
    # cached and compared.
    return sorted(errors, key=lambda error: (error["path"], error["message"]))


def _number(container, key):
    """Return container[key] as a float, or None if it is absent or not a number.

    Every arithmetic check below runs through this. The reason is that
    arithmetic_errors may be handed an object that has NOT yet passed schema
    validation -- that is exactly the case in the retry loop, where both
    validators run on the same raw model output. So no key can be assumed
    present and no value can be assumed numeric. Returning None for anything
    unusable lets each check skip cleanly instead of raising TypeError and
    losing the other errors that were about to be reported.

    bool is excluded explicitly because bool subclasses int in Python, so a
    stray True would otherwise sail through as the number 1 and produce a
    baffling arithmetic message instead of an honest type complaint. The schema
    is the right place to report a wrong type; this function just declines to
    guess.
    """
    if not isinstance(container, dict):
        return None
    value = container.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _close(left, right):
    """Compare two money amounts with a tolerance rather than for exact equality.

    These are IEEE 754 binary floats, and money in decimal is not exactly
    representable in binary. The canonical demonstration is 0.1 + 0.2, which
    evaluates to 0.30000000000000004 and is therefore != 0.3. The same thing
    happens here: 222.0 + 430.0 + 60.0 + 45.0 can land a fraction of a cent away
    from 757.0 depending on the order of the additions.

    An exact == test would report those as extraction failures, so the tool
    would reject a perfectly correct extraction, send it back to the model for
    correction, and the model would return the same correct numbers again. A
    tolerance below one cent is far tighter than any real transcription error
    while being far wider than any float artefact.
    """
    return abs(left - right) < MONEY_TOLERANCE


def _parse_date(instance, field, errors):
    """Parse one date field, appending an error if it is present but impossible."""
    raw = instance.get(field)

    # null is a legitimate value here -- it means the document printed no such
    # date -- so absence is not an error and there is nothing to parse.
    if raw is None:
        return None
    if not isinstance(raw, str):
        # The schema reports the type problem with a better message than we
        # could. Stay quiet rather than emit a duplicate.
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        # This is the gap the schema structurally cannot close. Its regex
        # pattern checks SHAPE -- four digits, dash, two digits, dash, two
        # digits -- and 2026-13-45 satisfies that perfectly while naming a
        # thirteenth month and a forty-fifth day. A pattern cannot know how many
        # days are in February, still less which years are leap years. Only a
        # real calendar can, so the check belongs here.
        errors.append({
            "path": field,
            "message": f"{raw!r} matches the YYYY-MM-DD pattern but is not a real calendar date",
        })
        return None


def arithmetic_errors(instance):
    """Cross-field checks that JSON Schema structurally cannot express.

    JSON Schema constrains each value independently: a type, a range, a pattern.
    It has no way to say "this number must equal the sum of those numbers",
    because a subschema cannot see its siblings. So every relationship BETWEEN
    fields is invisible to it, and a model can return an object that is
    perfectly schema-valid and arithmetically nonsense -- correct line items
    under a total that matches none of them. That object would pass the API's
    strict validation, pass ours, and reach a payment queue unchallenged.

    Same {path, message} shape as validation_errors, and the same contract:
    return, never raise.
    """
    # The instance may be anything at all if the model returned something odd,
    # so establish it is a mapping before touching a single key.
    if not isinstance(instance, dict):
        return [{"path": "<root>", "message": "expected a JSON object to check arithmetic against"}]

    errors = []

    # --- Check 1: each line's quantity * unit_price equals its own amount ------
    # This catches a transcription slip on one row. Without it, a single wrong
    # unit price is invisible as long as the columns still add up.
    items = instance.get("line_items")
    amounts_are_complete = isinstance(items, list) and bool(items)
    running_total = 0.0

    if isinstance(items, list):
        for index, item in enumerate(items):
            amount = _number(item, "amount")
            if amount is None:
                # One unreadable amount makes the subtotal comparison below
                # meaningless, so record that fact and let check 2 stand down
                # rather than report a sum that is missing a term.
                amounts_are_complete = False
                continue
            running_total += amount

            quantity = _number(item, "quantity")
            unit_price = _number(item, "unit_price")
            if quantity is None or unit_price is None:
                continue
            if not _close(quantity * unit_price, amount):
                errors.append({
                    "path": f"line_items.{index}.amount",
                    "message": (
                        f"quantity {quantity} * unit_price {unit_price} is "
                        f"{round(quantity * unit_price, 2)}, but amount is {amount}"
                    ),
                })
    else:
        amounts_are_complete = False

    # --- Check 2: the line amounts sum to subtotal ----------------------------
    # This is what catches a row the model dropped entirely. A missing line is
    # otherwise undetectable: what remains is internally consistent and simply
    # understates the invoice.
    subtotal = _number(instance, "subtotal")
    if amounts_are_complete and subtotal is not None and not _close(running_total, subtotal):
        errors.append({
            "path": "subtotal",
            "message": (
                f"line item amounts sum to {round(running_total, 2)}, "
                f"but subtotal is {subtotal}"
            ),
        })

    # --- Check 3: subtotal + tax equals total ---------------------------------
    # The total is the number that gets paid, so this is the check with money at
    # the end of it. A null tax counts as 0 HERE AND ONLY HERE: for arithmetic,
    # "no tax line was printed" and "the tax was zero" add the same amount. They
    # remain different facts everywhere else, which is why the schema keeps them
    # distinct rather than normalising null to 0 at the source.
    total = _number(instance, "total")
    tax = 0.0 if instance.get("tax") is None else _number(instance, "tax")
    if subtotal is not None and total is not None and tax is not None:
        if not _close(subtotal + tax, total):
            errors.append({
                "path": "total",
                "message": (
                    f"subtotal {subtotal} + tax {tax} is {round(subtotal + tax, 2)}, "
                    f"but total is {total}"
                ),
            })

    # --- Check 4: the dates are real days on a real calendar ------------------
    invoice_date = _parse_date(instance, "invoice_date", errors)
    due_date = _parse_date(instance, "due_date", errors)

    # --- Check 5: payment is not due before the invoice was issued ------------
    # A due date earlier than the invoice date is the signature of the two dates
    # being swapped, which is the exact failure samples/ambiguous.txt is built
    # to provoke. Schema-valid, arithmetically silent, and it would drive a
    # late-payment alert on an invoice that is not yet due.
    if invoice_date is not None and due_date is not None and due_date < invoice_date:
        errors.append({
            "path": "due_date",
            "message": (
                f"due_date {due_date.isoformat()} is earlier than "
                f"invoice_date {invoice_date.isoformat()}; the two dates look swapped"
            ),
        })

    return errors
