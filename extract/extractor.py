"""Forced-tool-call extraction with one schema-driven correction retry."""

# =============================================================================
# WHY THIS FORCES A TOOL CALL INSTEAD OF ASKING FOR "JSON ONLY"
# =============================================================================
#
# This is the most important explanation in the codebase. Everything else here
# is plumbing; this is the design decision.
#
# 1. A PROMPT IS A REQUEST. A TOOL_CHOICE IS A CONSTRAINT.
#    "Respond with only JSON" is an instruction the model may follow. It usually
#    does. "Usually" is the problem. Passing
#    tool_choice={"type": "tool", "name": "record_invoice"} is not a request at
#    all: the API prefills the assistant turn so that the very next thing the
#    model can emit is a tool call. There is no position in the output where a
#    preamble, an apology, a clarifying question or a ```json fence could go,
#    because the turn has already been started for it. The difference is between
#    asking for a shape and making the other shapes unreachable.
#
# 2. "RETURN ONLY JSON" FAILS IN WAYS THAT LOOK LIKE SUCCESS.
#    The response arrives, has status 200, and contains the right data. It just
#    also contains "Here is the extracted JSON:" in front, or a markdown fence
#    around it, or "Let me know if you'd like any changes!" trailing after the
#    closing brace. Every one of those makes json.loads raise, and every fix is
#    a hack: slice from the first "{", regex out a fence, strip after the last
#    "}". Each hack works on the document that motivated it and fails on the
#    next one -- the brace-slice breaks the first time a vendor address contains
#    a "{", the fence regex breaks on a nested fence. You end up maintaining a
#    parser for a format that was never specified, and its failures are silent
#    corruptions rather than errors.
#
# 3. strict: True MOVES VALIDATION UPSTREAM OF OUR PROCESS.
#    With strict enabled on the tool definition, the API validates the tool
#    input against input_schema before the response is returned. A whole class
#    of malformed output -- wrong types, missing required keys, invented extra
#    properties -- never crosses the network to us. Code that cannot receive a
#    bad shape does not need a branch for one.
#
# 4. ONE SCHEMA, SO THE CONTRACT CANNOT DRIFT.
#    The tool's input_schema is the SAME object loaded by validate.load_schema()
#    and used for local validation. Not a copy, not a hand-written summary in
#    the prompt: the same dict. If those were two artefacts, the day someone
#    tightened one and forgot the other, the tool would start asking for one
#    thing and checking for another, and the mismatch would surface as confusing
#    validation failures on correct model output.
#
# 5. THE HONEST LIMIT: SHAPE IS GUARANTEED, CORRECTNESS IS NOT.
#    Forcing the call guarantees we receive a well-formed object with the right
#    fields and types. It guarantees nothing whatsoever about whether the values
#    are true. The model can return a flawlessly valid invoice with the wrong
#    vendor name, a total copied from the wrong column, or a confidently
#    hallucinated purchase-order number. strict: True will pass it. So will our
#    schema. That is precisely why arithmetic_errors() exists in validate.py to
#    check the relationships the schema cannot see, and why the evaluation
#    harness measures real output against hand-written expected files. Never
#    read "schema-valid" as "correct".
# =============================================================================

from dataclasses import dataclass, field

from .validate import arithmetic_errors, validation_errors

# One retry. Not two, not "until it works". See _retry rationale in
# extract_invoice() for why the budget is fixed at exactly one.
MAX_ATTEMPTS = 2

TOOL_NAME = "record_invoice"


class ExtractionError(RuntimeError):
    """A response came back that we cannot extract anything from at all.

    Distinct from a validation failure. A validation failure is expected traffic
    -- we got an object, it was wrong, we feed the errors back. These are cases
    where there is no object to inspect, so there is nothing to correct and the
    caller must be told plainly rather than handed a None to trip over later.
    """


class TruncatedResponseError(ExtractionError):
    """The model ran out of output tokens mid-object."""


class MissingToolUseError(ExtractionError):
    """The response contained no tool_use block despite the call being forced."""


@dataclass
class ExtractionResult:
    """What one extraction run produced. A plain data carrier, no behaviour."""

    data: dict | None
    errors: list = field(default_factory=list)
    attempts: int = 0

    @property
    def ok(self):
        """True when the extracted object passed both validators."""
        return not self.errors


# The system prompt sets the standing rules for the extraction. The per-document
# instruction goes in the user turn; this is the part that does not change.
#
# Every clause below exists to counter a specific, observed failure. A model
# asked to fill a required field will fill it -- inventing a plausible invoice
# number is a much more available behaviour than reporting absence, because the
# schema made the key mandatory and nothing told it that null was allowed. The
# prompt has to grant permission to say "not present", or the schema's carefully
# nullable fields will simply never be used.
SYSTEM_PROMPT = """\
You extract structured data from invoice documents. You are a careful reader, \
not a helpful assistant filling in blanks.

Rules, in order of importance:

1. NEVER INVENT A VALUE. Every value you record must be readable in the \
document in front of you. If you find yourself reasoning about what a field \
"probably" says, stop: that field is absent or unclear, and there are honest \
ways to record both below.

2. USE null FOR A FIELD THAT IS GENUINELY ABSENT. The nullable fields are \
invoice_date, due_date, purchase_order and tax. Many real invoices carry no \
purchase-order reference and no tax line. null is the correct, expected answer \
in that case, and it is always better than a plausible guess. Note that null \
means "I read the document and this was not in it" -- it does not mean "I am \
unsure", which is what confidence and ambiguity_notes are for.

3. RECORD EVERY JUDGEMENT CALL IN ambiguity_notes. Any time the document \
admits more than one reading and you choose one, write down what you saw, what \
the alternatives were, and why you chose as you did. Two unlabelled dates. An \
amount that could be a subtotal or a total. A number that might be a purchase \
order or a customer reference. Amounts in a format whose decimal separator is \
unclear. Without a note, your choice is indistinguishable from a certainty, \
and a human reviewer has no way to know a decision was ever made. Leave the \
array empty only when the document truly was unambiguous.

4. SET confidence TO REFLECT REAL UNCERTAINTY. It is a number from 0 to 1 and \
it is used to route documents: anything below a threshold is held for human \
review. A default high number defeats that mechanism entirely and lets a poor \
extraction auto-approve. A clean, fully legible invoice deserves something \
above 0.9. A document where you had to make several judgement calls deserves \
something well below that. Score the extraction you actually performed.

5. DATES ARE ALWAYS YYYY-MM-DD. Convert whatever the document prints. If a \
date is ambiguous between day-first and month-first order, pick the reading you \
judge correct and record the ambiguity in ambiguity_notes.\
"""


def build_tool_definition(schema):
    """Build the record_invoice tool definition from the loaded schema."""
    return {
        "name": TOOL_NAME,
        # The description is not documentation for a human reader -- it is
        # prompt text that the model reads on every call, and it is the primary
        # place the model learns what these fields MEAN. A thorough description
        # measurably improves extraction quality, because field names alone are
        # ambiguous: "subtotal" and "total" are near-synonyms in English, and a
        # model with only the names to go on will sometimes fill both with the
        # same figure. Spelling out the relationship between them costs nothing
        # at runtime and removes a whole category of error.
        "description": (
            "Record the structured contents of exactly one invoice document. "
            "Call this tool once, after you have read the entire document, with "
            "the values you can actually support from its text. "
            "invoice_number is the vendor's own identifier for this invoice, not "
            "the customer's reference and not the purchase-order number. "
            "vendor_name is the party being paid, which is the party that issued "
            "the document -- not the recipient, whose name usually appears in a "
            "'Bill To' block. "
            "invoice_date is the date the invoice was issued and due_date is the "
            "date payment is required; when a document states only terms such as "
            "'Net 30' and prints no explicit due date, record null rather than "
            "computing one. "
            "purchase_order is the buyer's own order reference and is absent from "
            "many invoices; record null when it is. "
            "line_items must contain one entry per charge line, with amount equal "
            "to quantity times unit_price, and the amounts must sum to subtotal. "
            "subtotal is the figure before tax, total is the figure after it, and "
            "they are equal when no tax is charged; derive subtotal from the line "
            "items when the document does not print it. "
            "tax is null when the document shows no tax line at all, which is "
            "different from a tax of zero. "
            "currency must be one of USD, EUR, GBP or CAD, chosen from symbols, "
            "codes or context in the document. "
            "ambiguity_notes records every judgement call you made, and confidence "
            "reports how much you trust this extraction on a scale from 0 to 1."
        ),
        # The SAME schema object used for local validation. See point 4 of the
        # comment block above: one artefact, so the contract cannot drift.
        "input_schema": schema,
        # strict belongs HERE, as a top-level sibling of name/description/
        # input_schema -- not on tool_choice, which only selects which tool to
        # force. It makes the API validate the tool input against input_schema
        # before responding, and it requires the schema to carry
        # additionalProperties: false and a required array, which ours does.
        "strict": True,
    }


def _build_request(model, schema, messages):
    """Assemble the keyword arguments for one messages.create call.

    Both attempts go through here so the two calls cannot drift apart. If the
    retry forgot tool_choice, it would be free to answer in prose and the
    correction round would fail for a reason that has nothing to do with the
    document.
    """
    return {
        "model": model,
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        # strict: True travels inside the tool definition, not out here.
        "tools": [build_tool_definition(schema)],
        # This is the constraint that makes the whole approach work: the model
        # must call this specific tool, so the response cannot be prose.
        "tool_choice": {"type": "tool", "name": TOOL_NAME},
        "messages": messages,
        #
        # NOTE ON THE `thinking` PARAMETER -- IT IS DELIBERATELY ABSENT.
        # Do not add thinking={"type": "enabled"} here. Manual extended thinking
        # is REJECTED WITH AN ERROR when combined with forced tool use, so the
        # request would fail outright rather than degrade. Adaptive thinking is
        # the default on Opus 5 and does support forced tool use, and leaving
        # the parameter unset is what selects it. In other words the working
        # configuration is the one where you write nothing at all, which is easy
        # to "fix" by adding a line and thereby break.
    }


def _first_tool_use(response):
    """Return the first tool_use block, or raise a named error explaining why not.

    The extracted object is block.input, which the SDK has already parsed into a
    Python dict. It is never re-serialised and string-matched: doing that would
    reintroduce exactly the fragile text handling that forcing the tool call was
    meant to eliminate.
    """
    # Check truncation FIRST. A max_tokens stop is the nastiest failure in this
    # pipeline because it can still produce a tool_use block -- one holding a
    # partial object that was cut off mid-write. Reported as an ordinary
    # validation error it would read as "the model omitted six fields", sending
    # us into a correction round for a problem that is really about output
    # length. Naming it as its own failure points at the real fix.
    if response.stop_reason == "max_tokens":
        raise TruncatedResponseError(
            "the model hit max_tokens before finishing the tool call, so the "
            "invoice object is truncated; raise max_tokens or split the document"
        )

    for block in response.content:
        if block.type == "tool_use":
            return block

    # Forcing the tool call makes this close to impossible, which is exactly why
    # it must be loud when it happens: it means an assumption this module is
    # built on no longer holds. Returning None here instead would push the
    # failure into the caller, where it would surface as an AttributeError on a
    # NoneType several frames away with nothing to explain it. The stop_reason
    # is named in the message because it is the one field that says why.
    raise MissingToolUseError(
        f"response contained no tool_use block despite tool_choice forcing "
        f"{TOOL_NAME!r} (stop_reason={response.stop_reason!r})"
    )


def _format_correction(errors):
    """Turn a list of {path, message} dicts into a correction instruction.

    This function is the reason the retry works at all.

    A generic "that was invalid, please try again" gives the model nothing to
    act on. It knows only that something was wrong somewhere, so the most likely
    second attempt is a near-copy of the first -- one wasted call for an
    identical answer. Naming the exact failing paths converts a guess into a
    targeted repair: "line_items.2.amount: quantity 500 * unit_price 0.12 is
    60.0, but amount is 6.0" tells the model which row, which field, and what
    the arithmetic actually says, and it can go back to that line of the
    document and re-read it. Specific feedback is the entire mechanism.
    """
    lines = [f"- {error['path']}: {error['message']}" for error in errors]
    return (
        "The invoice you recorded did not pass validation. These specific "
        "problems were found:\n\n"
        + "\n".join(lines)
        + "\n\nRe-read the document and call record_invoice again with these "
        "problems corrected. Change only what is wrong; keep every value that "
        "was not listed above. If a value cannot be supported by the document, "
        "use null rather than adjusting a number to make the arithmetic work."
    )


def extract_invoice(text, client, schema, model):
    """Extract one invoice, validating and retrying at most once.

    Returns an ExtractionResult. A result whose .errors is non-empty is a
    reported failure, not an exception: the caller gets the best object we
    managed along with a precise account of what is wrong with it.
    """
    messages = [{
        "role": "user",
        "content": (
            "Extract the structured data from the invoice document below.\n\n"
            "<document>\n" + text + "\n</document>"
        ),
    }]

    attempts = 0
    data = None
    errors = []

    # Bounded loop rather than a while-True with a break, so the retry budget is
    # visible in the control flow itself and cannot be accidentally extended by
    # a later edit that adds one more `continue`.
    while attempts < MAX_ATTEMPTS:
        response = client.messages.create(**_build_request(model, schema, messages))
        attempts += 1

        # Raises TruncatedResponseError or MissingToolUseError if there is
        # nothing usable. Both are unrecoverable in a way a correction prompt
        # cannot address, so neither is retried.
        tool_use = _first_tool_use(response)
        data = tool_use.input

        # BOTH validators, always. The schema check catches shape; the
        # arithmetic check catches the cross-field relationships the schema
        # cannot express. Running only the first would let a schema-perfect
        # object with a wrong total through unchallenged.
        errors = validation_errors(data, schema) + arithmetic_errors(data)
        if not errors:
            return ExtractionResult(data=data, errors=[], attempts=attempts)

        # Errors on the final permitted attempt: stop here and report. The
        # budget is exactly one retry, and that number is a judgement about what
        # the failure means. A transient fault -- a dropped field, a slip in one
        # multiplication -- is very likely fixed by one round of specific
        # feedback. A model that fails the SAME schema twice, having been shown
        # precisely what was wrong, is not suffering a transient fault: it is
        # misreading the document, or the document does not contain what we are
        # asking for. A third call re-reads the same text with the same
        # instructions and returns the same wrong answer, having spent more
        # money and more of the user's time to do it. Worse, an unbounded retry
        # turns one bad document into an unbounded bill. Fail, report the exact
        # errors, and let a human look at it.
        if attempts >= MAX_ATTEMPTS:
            break

        # Build the correction turn. The assistant's own turn must be replayed
        # first: the conversation has to contain the tool_use block before a
        # tool_result can refer to it, and the model needs to see what it
        # previously answered in order to revise rather than start over.
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                # Must be the id of the originating tool_use block. This is what
                # pairs the result with the call it answers; a wrong or absent
                # id leaves a tool_use with no matching result, which is an
                # invalid conversation the API will reject.
                "tool_use_id": tool_use.id,
                "content": _format_correction(errors),
            }],
        })

    # Fell out of the loop with errors still present. Return them as data, in
    # the same shape as a success, so the caller has one code path and can
    # decide what a failed extraction is worth: log it, queue it for a human, or
    # write it out flagged. That decision does not belong here.
    return ExtractionResult(data=data, errors=errors, attempts=attempts)
