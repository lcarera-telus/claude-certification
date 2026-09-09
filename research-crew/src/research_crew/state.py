"""Run state: the only thing that crosses a phase boundary.

WHY THIS MODULE EXISTS
======================
Four subagents run in this pipeline. They share nothing. Each one is handed a
single string, answers it, and is gone. A subagent cannot see the coordinator's
conversation, cannot see a sibling's output, and cannot remember a previous
round. That isolation is the property that makes the crew debuggable, and it is
also the property that creates the problem this module solves.

Because nothing is shared, every fact the next phase needs must be:

    1. read out of this object by the coordinator, and
    2. written into a prompt string by hand.

There is no implicit channel. If the analyst's claims are not spelled into the
synthesizer's prompt, the synthesizer never learns that they exist. `RunState`
is where those facts live between phases, so it is the one seam at which the
whole pipeline can be inspected.

READ THIS AS THE PIPELINE'S MEMORY
----------------------------------
    searcher     writes  sources
    analyst      writes  claims, coverage_sufficient, coverage_gaps
    synthesizer  writes  merged_claims, conflicts
    reporter     writes  report_md
    every phase  appends one PhaseRecord

Each field names the phase that fills it. A learner can follow a fact from a URL
to a citation number by reading successive snapshots of this one object, which
is why `to_json()` prefers a verbose, readable dump over a compact one.

WHY THE PAYLOAD DATACLASSES ARE FROZEN AND `RunState` IS NOT
------------------------------------------------------------
A `Source` is evidence. Once the searcher retrieved it, no later phase may edit
it: a mutated snippet breaks the provenance chain that the verifier walks back
from a citation. `frozen=True` makes that a runtime error instead of a rule in a
comment. `RunState` itself is mutable because it is the accumulator, and the
coordinator appends to it as the run proceeds.

WHY SERIALISATION IS AN EXACT ROUND TRIP
----------------------------------------
`from_dict(to_dict(x)) == x` is not a tidiness concern. The recorder writes a
state snapshot after every phase. If loading a snapshot gave back something
subtly different from the live object, a replay of a failed run would not be a
replay of that run, and the audit trail would be decorative.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Source:
    """One retrieved web result. The origin of every fact in the final report.

    `id` is the citation number. The coordinator assigns it, not a model: a
    number is bookkeeping, and bookkeeping done in Python cannot drift.
    """

    id: int
    url: str
    title: str
    snippet: str
    query: str


@dataclass(frozen=True)
class Claim:
    """One atomic statement the analyst extracted from exactly one source.

    `source_id` is the load-bearing link in the provenance chain. Without it a
    claim cannot be cited, so the analyst's prompt tells it to drop such a claim
    rather than emit it. `evidence` holds a verbatim quote, so a reviewer can
    check the extraction without re-fetching the page.
    """

    id: str
    text: str
    source_id: int
    evidence: str
    confidence: str


@dataclass(frozen=True)
class MergedClaim:
    """Several agreeing claims collapsed into one, keeping every source.

    `source_ids` is a list, not a single id, because merging is the step at
    which one sentence starts to rest on several sources. The reporter renders
    that as `[1][3]`.
    """

    id: str
    text: str
    source_ids: list[int]
    support: str


@dataclass(frozen=True)
class Conflict:
    """A disagreement between sources, recorded rather than resolved.

    A conflict is a result, not an error. `kind` separates the two cases that
    matter. A *real* conflict means two sources contradict each other under the
    same conditions. An *apparent* conflict means they measured different
    things, and then `explanation` carries the condition that separates them.
    Averaging the two positions would destroy the most useful finding in the
    report.
    """

    id: str
    topic: str
    position_a: dict
    position_b: dict
    kind: str
    explanation: str


@dataclass(frozen=True)
class PhaseRecord:
    """What one agent call cost, in money, time, and outcome.

    Per-phase accounting is the evidence for the central architectural claim of
    this system: only the synthesizer needs Opus, so only one phase of four pays
    that rate. A single mega-prompt has no such dial. `subtype` carries the
    SDK's terminal result subtype, which is how a run that stopped early is told
    apart from one that finished.
    """

    phase: str
    agent: str
    round: int
    cost_usd: float | None
    duration_s: float
    subtype: str


@dataclass
class RunState:
    """Everything one research run knows, at one moment in time."""

    question: str
    run_id: str
    search_round: int = 1
    sources: list[Source] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    merged_claims: list[MergedClaim] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    # Three states, not two. None means "the analyst has not reported yet".
    # False means "it reported, and the sources are thin". The coordinator reads
    # this field, and only this field, when it decides whether to spend the one
    # retry the budget allows, so "not yet known" has to be representable.
    coverage_sufficient: bool | None = None
    coverage_gaps: list[str] = field(default_factory=list)
    report_md: str | None = None
    phases: list[PhaseRecord] = field(default_factory=list)

    @classmethod
    def new(cls, question: str) -> "RunState":
        """Start a run. The `run_id` is a UTC timestamp, `YYYYMMDD-HHMMSS`.

        UTC rather than local time, because run directories sort
        chronologically on disk and a local clock crossing a DST boundary would
        break that order. The format is also filesystem-safe on Windows, which
        rules out the obvious ISO-8601 spelling with its colons.
        """
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return cls(question=question, run_id=run_id)

    def to_dict(self) -> dict:
        """Serialise the whole run, nested dataclasses included.

        Written out field by field rather than with a blanket `asdict(self)`, so
        that the on-disk shape is visible in one place and any change to it is a
        deliberate edit rather than a side effect of adding an attribute.
        """
        return {
            "question": self.question,
            "run_id": self.run_id,
            "search_round": self.search_round,
            "sources": [asdict(s) for s in self.sources],
            "claims": [asdict(c) for c in self.claims],
            "merged_claims": [asdict(m) for m in self.merged_claims],
            "conflicts": [asdict(x) for x in self.conflicts],
            "coverage_sufficient": self.coverage_sufficient,
            "coverage_gaps": list(self.coverage_gaps),
            "report_md": self.report_md,
            "phases": [asdict(p) for p in self.phases],
        }

    def to_json(self) -> str:
        """Indented JSON with non-ASCII left intact. Meant to be read by a human.

        This is the text the recorder drops after every phase, so it is tuned
        for a person diffing two snapshots, not for wire size.
        """
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> "RunState":
        """The exact inverse of `to_dict()`.

        Every nested list is rebuilt into its dataclass. Skipping that step
        would give back a `RunState` whose `sources` were plain dicts. It would
        look right, compare unequal to the original, and fail much later.
        """
        return cls(
            question=d["question"],
            run_id=d["run_id"],
            search_round=d["search_round"],
            sources=[Source(**s) for s in d["sources"]],
            claims=[Claim(**c) for c in d["claims"]],
            merged_claims=[MergedClaim(**m) for m in d["merged_claims"]],
            conflicts=[Conflict(**x) for x in d["conflicts"]],
            coverage_sufficient=d["coverage_sufficient"],
            coverage_gaps=list(d["coverage_gaps"]),
            report_md=d["report_md"],
            phases=[PhaseRecord(**p) for p in d["phases"]],
        )

    def citation_map(self) -> dict[int, Source]:
        """Citation number -> `Source`.

        The coordinator writes this map into the reporter's prompt and forbids
        renumbering. Fixing the numbers in Python removes one decision from the
        model. A drifted number would still produce a well-formed report in
        which every citation pointed one row off, and that failure reads as
        correct to everyone except the person who checks a link.
        """
        return {s.id: s for s in self.sources}

    def total_cost_usd(self) -> float:
        """Sum the known per-phase costs and ignore the unknown ones.

        The SDK does not always report a cost, so `None` means "not reported"
        and never zero. Skipping those entries keeps the total honest, and keeps
        this method from raising on a partial run, which is exactly the run you
        most want a cost figure for.
        """
        # float(...) because `sum()` over an empty sequence returns the int 0,
        # and this function promises a float. A run in which nothing reported a
        # cost is the common case early in a run, not an edge case.
        return float(sum(p.cost_usd for p in self.phases if p.cost_usd is not None))
