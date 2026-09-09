"""Citation integrity: the one check that does not ask a model to cooperate.

WHAT THIS MODULE IS
===================
The reporter must not introduce new facts. Three things try to make that true,
and they are not of equal strength:

  1. THE PROMPT. `agents/reporter.md` says "add no new facts". Advisory. A model
     usually obeys it, and helpfully fills a thin section from memory when the
     claim set is weak. Every hallucinated citation ever shipped got past a
     prompt that told the model not to do that.
  2. TOOL SCOPING. The reporter is defined with `tools: []`, so WebSearch is not
     in its session at all. Structural: it closes the channel by which a fresh,
     real, uncited URL could enter at the last step. It does not stop the model
     recalling something from pre-training.
  3. THIS MODULE. The finished Markdown is parsed in Python, and every `[n]` is
     walked back to a `Source` the searcher actually collected. No model is
     involved anywhere in this file, so no amount of fluent prose talks its way
     past it.

That ordering is the lesson. When you want an agent to stop doing something,
prompt wording is the weakest instrument available; removing the capability
beats it; checking the output in code beats both.

WHAT THIS MODULE CANNOT DO - READ THIS BEFORE YOU TRUST IT
==========================================================
The check is **referential, not semantic.**

It proves that citation `[4]` resolves to a References entry, and that that
entry's URL is one the searcher really retrieved. It proves *nothing* about
whether the sentence carrying `[4]` is supported by what is at that URL.

A report that attaches a genuinely collected source to a completely fabricated
claim **passes this check**. That is not a bug to be fixed later; it is the
boundary of what string comparison can decide. `tests/test_verify.py` contains
`test_referential_check_cannot_detect_a_false_claim`, which exists to keep that
limitation visible rather than to protect against it.

Closing the gap needs something that can read the page and judge entailment: an
NLI model, a second agent handed the source text and asked whether it supports
the sentence, or a human reviewer. All three cost money or time per claim, and
all three can be wrong. This check is cheap, deterministic, and honest about its
own scope. Do not describe it in a design review as "hallucination detection".

WHY IT ALSO CHECKS THE OTHER DIRECTION
======================================
Three of the four checks look for a citation the reader cannot follow, or can
follow to the wrong place. `orphan_references` looks the opposite way, at a
References entry that no sentence cites. That is not a correctness failure, but
it is a reliable smell. It usually means the reporter dropped or reworded a
sentence and left its source behind, so the report the reader sees is not the
report the pipeline thought it wrote.

WHY THERE IS NO CONTIGUITY CHECK
================================
There used to be one - `numbering_gaps`, which flagged `[1] [2] [4]` as the
fingerprint of a reporter that renumbered. It was wrong, and it fired on every
correct run of this system. The coordinator hands the reporter the *whole*
citation map, and `agents/reporter.md` tells it to list only the numbers it
actually cited. A subset of an integer range is never contiguous, so the check
could not do anything except fail.

`misnumbered_references` is the check that was meant. The risk was never a gap;
it was a number pointing at the wrong URL, and comparing each References entry
against the coordinator's map catches that directly and without false alarms.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from .state import Conflict, Source

# `## References`, at any heading level and in any case. Matching loosely here
# is deliberate: if a reporter writes `### References`, the right outcome is to
# check its contents, not to declare every citation in the document unmapped.
_REFS_HEADING_RE = re.compile(r"^[ \t]*#{1,6}[ \t]*references[ \t]*$", re.IGNORECASE | re.MULTILINE)

# A citation marker: square brackets around digits only, NOT followed by "(".
#
# The negative lookahead is what separates a citation from a Markdown link.
# `[see here](https://x.com)` never matches, because "see here" is not digits.
# `[1](https://x.com)` never matches either, because the "(" says it is a link
# whose display text happens to be a number. Both are legitimate Markdown that a
# reporter may emit, and counting either as a citation would produce a false
# alarm - the failure mode that trains a reader to ignore the check.
#
# A run of markers such as `[1][3]` is two separate matches, because each pair
# of brackets matches independently. That matters: `MergedClaim.source_ids` is a
# list, so a multi-source sentence is the normal case, not an edge case.
_CITATION_RE = re.compile(r"\[(\d+)\](?!\()")

# One References line: `[1] Title - https://example.com/page`.
# The title is optional, and greedy (`.*\S`) so that a title containing " - "
# keeps its dashes and only the last separator before the URL is the separator.
# The URL must carry a scheme; a bare word in the URL slot is a malformed line,
# not a source, and saying so is more useful than silently treating it as one.
_REF_LINE_RE = re.compile(r"^\[(\d+)\][ \t]+(?:(.*\S)[ \t]+-[ \t]+)?([a-zA-Z][a-zA-Z0-9+.\-]*://\S+)[ \t]*$")


@dataclass(frozen=True)
class CitationReport:
    """The verdict on one report's citations. A record, never an exception.

    `checked_citations` counts marker *occurrences* in the body, not distinct
    numbers, because occurrences are what was actually scanned: a report citing
    `[1]` in nine sentences had nine markers checked. The problem lists are
    keyed on the distinct number, because "reference 5 is an orphan" is a fact
    about the number, and repeating it once per occurrence would be noise.

    Frozen, because this object is written to disk as `citation-report.json` and
    is the evidence for a pass or a fail. Evidence a later step can edit is not
    evidence.
    """

    ok: bool
    checked_citations: int
    unmapped_citations: list[int]
    uncollected_urls: list[tuple[int, str]]
    orphan_references: list[int]
    # `(number, url_in_report, url_in_citation_map)`. Three values and not two,
    # because the reader needs to see both sides to tell a renumbering from a
    # typo, and the number to find the line.
    misnumbered_references: list[tuple[int, str, str]]
    malformed_references: list[str]


def normalise_url(url: str) -> str:
    """Reduce a URL to the form used for comparison.

    Lowercase the scheme and the host, drop a default port, drop one trailing
    slash from the path, drop any `#fragment`. **Keep the query string.**

    WHY NORMALISE AT ALL
    --------------------
    The URL in the References section was copied by hand through two model
    calls: the searcher wrote it into JSON, the coordinator pasted it into the
    reporter's prompt, and the reporter typed it into a Markdown line. A
    trailing slash or an uppercase `HTTPS://` that survives that trip is not a
    citation error, and reporting it as one is worse than useless. A check that
    cries wolf over cosmetic differences teaches the reader to skim past its
    output, and then the one real dangling citation goes unread too.

    WHY THE QUERY STRING IS SIGNIFICANT
    -----------------------------------
    Because it routinely *is* the identity of the page. `?v=abc` names one video
    and `?id=17` names one record. Discarding it would make two unrelated pages
    compare equal, and would let a fabricated source pass by resembling a real
    one. A fragment is dropped instead, because `#section-3` addresses a place
    within one page rather than a different page.
    """
    try:
        parts = urlsplit(url.strip())
        scheme = parts.scheme.lower()
        host = (parts.hostname or "").lower()
        # `parts.port` raises ValueError on a non-numeric port, hence the guard.
        port = parts.port
    except ValueError:
        # An unparsable URL still has to compare *somehow*, and it must compare
        # equal to an identical unparsable URL. Falling back to the lowercased
        # literal keeps this function total: nothing in this module raises.
        return url.strip().lower()
    netloc = host if port in (None, {"http": 80, "https": 443}.get(scheme)) else f"{host}:{port}"
    path = parts.path[:-1] if parts.path.endswith("/") else parts.path
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def split_references(report_md: str) -> tuple[str, str]:
    """Return `(body, references_block)`, split at the `## References` heading.

    WHY THIS SPLIT HAS TO HAPPEN FIRST
    ----------------------------------
    `[1]` appears on both sides of that heading, and it means a different thing
    on each side. In the body it is a *use* of source 1. In the references block
    it is the *definition* of source 1.

    Count them together and the orphan check dies quietly: every References
    entry would be found "cited", because its own definition line looks exactly
    like a citation of itself. The check would then pass on every report ever
    written, which is indistinguishable from not running it at all.

    When there is no References heading, the whole document is body and the
    references block is empty. Every citation then lands in
    `unmapped_citations`, which is the correct verdict for a report that cites
    sources it never lists.
    """
    match = _REFS_HEADING_RE.search(report_md)
    if match is None:
        return report_md, ""
    return report_md[: match.start()], report_md[match.end() :]


def parse_references(block: str) -> tuple[dict[int, str], list[str]]:
    """Parse a references block into `({number: url}, malformed_lines)`.

    A line that does not parse is *recorded*, not raised on. A verifier that
    crashes on bad input tells you less than one that finishes and names
    precisely what was bad: the crash reports one line and hides the other
    nineteen problems behind it, and the reader has to re-run to find each one.
    This function's job is the fullest possible description of what is wrong,
    in a single pass.

    A duplicate number keeps the last URL seen. The numbering, mapping and
    orphan checks all operate on the *set* of numbers, so a duplicate can never
    hide a missing entry.
    """
    urls: dict[int, str] = {}
    malformed: list[str] = []
    for line in block.splitlines():
        if not line.strip():
            continue
        match = _REF_LINE_RE.match(line.strip())
        if match is None:
            malformed.append(line.strip())
            continue
        urls[int(match.group(1))] = match.group(3)
    return urls, malformed


def verify_report(
    report_md: str,
    sources: Sequence[Source],
    citation_map: Mapping[int, Source] | None = None,
) -> CitationReport:
    """Check every citation in a finished report against the collected sources.

    Uses no model, calls nothing over the network, and never raises. The point
    of this function is to be the one component in the pipeline whose verdict
    cannot be argued with. See the module docstring for what it does *not*
    establish.

    The four checks, and the failure each one catches:

      unmapped_citations   `[7]` in a sentence, no `[7]` in References. The
                           reader cannot follow the citation at all.
      uncollected_urls     A References URL matching no `Source` the searcher
                           retrieved. **This is the central check.** It is the
                           case where the reporter invented a source, and it is
                           the reason this module exists.
      orphan_references    A listed source that nothing cites. Usually a dropped
                           sentence rather than a lie, but it means the report
                           is not the one the pipeline thinks it produced.
      misnumbered_references
                           `[4]` in References carries a URL that is not the one
                           the coordinator assigned to 4. This is the renumbering
                           the reporter was forbidden to do - the failure that
                           yields a fluent, well-formed report in which every
                           citation points one row off, and which reads as
                           correct to everyone except the reader who follows a
                           link. It needs `citation_map`; without it the check is
                           skipped, exactly as in `validate_conflicts`.

    `sources` and `citation_map` are two views of the same set and both are
    needed. `uncollected_urls` asks "was this URL retrieved *at all*", which is a
    membership test over the collected set. `misnumbered_references` asks "was
    this URL retrieved *under this number*", which needs the number-to-source
    mapping. A report can pass the first and fail the second: shuffling the
    numbers of two genuinely collected sources leaves every URL in the collected
    set and every citation pointing at the wrong page.
    """
    body, refs_block = split_references(report_md)
    # Occurrences for the count, a set for the checks. See `CitationReport`.
    cited = [int(n) for n in _CITATION_RE.findall(body)]
    cited_numbers = set(cited)
    ref_urls, malformed = parse_references(refs_block)

    collected = {normalise_url(s.url) for s in sources}
    uncollected = [(n, u) for n, u in sorted(ref_urls.items()) if normalise_url(u) not in collected]

    # RENUMBERING, CHECKED AGAINST THE MAP RATHER THAN AGAINST CONTIGUITY.
    #
    # A number the map does not contain is skipped here on purpose: it is not a
    # renumbering, it is a citation of something never collected, and
    # `uncollected_urls` already names it. Reporting one failure twice trains a
    # reader to skim the verdict.
    #
    # WHAT THE OLD CONTIGUITY CHECK ACTUALLY MEASURED, AND WHY IT IS WORTH KNOWING
    # In run 20260830-152235 it flagged 23 missing numbers on a report with no
    # citation defect at all. The 23 turned out to be exactly the sources the
    # searcher had returned with no snippet text: the analyst could raise no
    # claim from an empty snippet, so those numbers reached no sentence and the
    # reporter correctly omitted them. The check was accidentally informative -
    # it surfaced a real phase-1 data-quality problem while claiming to detect a
    # phase-4 renumbering problem. That is worth recording once, because a check
    # firing for a reason unrelated to what it tests is a thing to notice rather
    # than a thing to trust. The data-quality signal it stumbled on belongs in
    # the searcher's own output, not here.
    misnumbered = [
        (number, url, citation_map[number].url)
        for number, url in sorted(ref_urls.items())
        if citation_map is not None
        and number in citation_map
        and normalise_url(url) != normalise_url(citation_map[number].url)
    ]

    unmapped = sorted(cited_numbers - set(ref_urls))
    orphans = sorted(set(ref_urls) - cited_numbers)
    return CitationReport(
        # `ok` is the conjunction of "every list is empty", written out rather
        # than derived by looping over the fields, so that adding a fifth check
        # forces a visible edit here instead of silently joining the verdict.
        ok=not (unmapped or uncollected or orphans or misnumbered or malformed),
        checked_citations=len(cited),
        unmapped_citations=unmapped,
        uncollected_urls=uncollected,
        orphan_references=orphans,
        misnumbered_references=misnumbered,
        malformed_references=malformed,
    )


def validate_conflicts(
    conflicts: Sequence[Conflict],
    citation_map: Mapping[int, Source] | None = None,
) -> list[str]:
    """Check the shape of every `Conflict` position. Returns problems, never raises.

    WHY THIS LIVES HERE
    -------------------
    `Conflict.position_a` and `position_b` are typed as a bare `dict`, so the
    type system permits any shape at all, and the synthesizer fills them from
    model output. A position missing its `text`, or carrying a `source_ids`
    entry naming a source the searcher never collected, serialises happily into
    the state snapshot and surfaces four files later as a Disagreements section
    citing a number the References block does not contain. Checking it at the
    boundary names the phase that produced it, which is the whole reason the
    pipeline has boundaries.

    The `citation_map` argument is optional because the spec gives a one-
    argument signature and then requires the ids to be checked "against the
    citation map passed alongside". Passing the map enables that check; omitting
    it checks shape only. The coordinator always passes it.

    Nothing here raises, for the reason `parse_references` does not: the caller
    wants every problem in one pass, and a malformed conflict is an expected
    model output rather than a programming error.
    """
    problems: list[str] = []
    for index, conflict in enumerate(conflicts):
        label = getattr(conflict, "id", "") or f"#{index}"
        for field_name in ("position_a", "position_b"):
            position = getattr(conflict, field_name, None)
            if not isinstance(position, dict):
                problems.append(f"conflict {label}: {field_name} is not a dict")
                continue
            text = position.get("text")
            if not isinstance(text, str) or not text.strip():
                problems.append(f"conflict {label}: {field_name} has no non-empty 'text' string")
            source_ids = position.get("source_ids")
            if not isinstance(source_ids, list):
                problems.append(f"conflict {label}: {field_name} has no 'source_ids' list")
                continue
            # `bool` is a subclass of `int`, so it is excluded explicitly: True
            # would otherwise pass as source id 1 and appear to cite a real
            # source.
            for value in source_ids:
                if isinstance(value, bool) or not isinstance(value, int):
                    problems.append(f"conflict {label}: {field_name} source_ids entry {value!r} is not an int")
                elif citation_map is not None and value not in citation_map:
                    problems.append(f"conflict {label}: {field_name} cites source {value}, never collected")
    return problems


def describe(report: CitationReport, conflict_problems: Sequence[str] = ()) -> list[str]:
    """Render a verdict as one human-readable line per problem.

    Formatting lives here and not in `cli.py`, so that the terminal output and
    the JSON artifact are two renderings of one object, and so that a test can
    assert on the wording without capturing stdout.
    """
    lines = [f"unmapped citation [{n}]: cited in the body, absent from References"
             for n in report.unmapped_citations]
    lines += [f"uncollected URL [{n}] {u}: no source the searcher collected matches it"
              for n, u in report.uncollected_urls]
    lines += [f"orphan reference [{n}]: listed in References, never cited in the body"
              for n in report.orphan_references]
    lines += [f"misnumbered reference [{n}] {u}: the citation map assigns {n} to {expected}"
              for n, u, expected in report.misnumbered_references]
    lines += [f"malformed References line: {line}" for line in report.malformed_references]
    return lines + list(conflict_problems)
