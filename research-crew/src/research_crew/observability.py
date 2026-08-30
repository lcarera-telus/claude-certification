"""Observability: one directory per run, written as the run happens.

WHY A MULTI-AGENT SYSTEM NEEDS THIS MORE THAN A SINGLE PROMPT DOES
==================================================================
A single prompt has one input and one output. If the answer is wrong, there is
exactly one place to look. This pipeline has four model calls chained
end to end, and every call is fed a string that the coordinator assembled from
the *previous* call's output. An error introduced at phase one is invisible at
phase one and arrives, laundered and fluent, in the final report.

So the run directory exists to answer one question after the fact: **which phase
first got it wrong?** A finished run looks like this:

    runs/20260830-113500/
        01-searcher.input.json         what the searcher was told
        01-searcher.output.md          what it said
        state-after-01-search.json     the run state once that was folded in
        02-analyst.input.json
        02-analyst.output.md
        state-after-02-analyze.json
        ...
        cost.json
        report.md

Read it top to bottom and the run replays as a document.

WHY THE INPUT IS RECORDED SEPARATELY FROM THE OUTPUT
====================================================
This is the part that earns the module.

The subagents share no memory. Each one receives exactly one string and sees
nothing else: no parent conversation, no sibling output, no earlier round. So
the input file is not a partial log or a summary of the context - it *is* the
complete context that agent had. Nothing else reached it.

That makes debugging a bisection instead of a search. Take a wrong claim in the
final report, find the phase that first states it, and open that phase's input
file:

  * the wrong claim is already in the input  -> this agent faithfully passed on
    someone else's error. Move one phase earlier and repeat.
  * the wrong claim is not in the input      -> this agent invented it. You have
    found the fault, and you have found it in one step.

One file, one question, one answer. Log only the outputs and that question
becomes guesswork, because you can no longer tell what the agent was working
from. This bisection point is a concrete thing the multi-agent split buys you
that a single mega-prompt cannot offer at any price: inside one long prompt
there is no boundary to cut at.

WHY A RUN DIRECTORY IS NEVER REUSED
===================================
The constructor raises if the directory exists. An audit trail that a later run
can quietly overwrite is not an audit trail. Losing the record of the failed run
is a much worse outcome than an error message on the successful one.
"""

from __future__ import annotations

import json
from pathlib import Path


class RunRecorder:
    """Writes the artifacts of one run into `runs_root/<run_id>/`.

    The coordinator owns every disk write in this system, and it does them
    through this object. The subagents have no Write tool, so nothing else can
    put a file on disk - which is why reading this directory tells you the whole
    truth about a run.
    """

    def __init__(self, runs_root: Path, run_id: str) -> None:
        """Create the run directory. Raise if it already exists.

        `exist_ok=False` is the point of this line, not an oversight. See WHY A
        RUN DIRECTORY IS NEVER REUSED above.
        """
        self.run_dir: Path = Path(runs_root) / run_id
        if self.run_dir.exists():
            raise FileExistsError(f"run directory already exists, refusing to overwrite: {self.run_dir}")
        self.run_dir.mkdir(parents=True, exist_ok=False)

    def _write(self, filename: str, text: str) -> Path:
        """Write one UTF-8 file into the run directory and return its path.

        UTF-8 is set explicitly because this code runs on Windows, where the
        default text encoding is still the ANSI codepage. A snippet quoted from
        a source page is arbitrary Unicode, and an encoding guess would either
        raise at write time or corrupt the evidence.
        """
        path = self.run_dir / filename
        path.write_text(text, encoding="utf-8")
        return path

    def record_input(self, seq: int, agent: str, payload: dict) -> Path:
        """Write `NN-<agent>.input.json`: the entire context this agent received.

        JSON rather than the raw prompt string, so the coordinator can record
        the assembled prompt alongside the settings that produced it - model,
        round, allowed tools - in one file. Indented, because a human reads it.
        """
        return self._write(f"{seq:02d}-{agent}.input.json", json.dumps(payload, indent=2, ensure_ascii=False))

    def record_output(self, seq: int, agent: str, text: str) -> Path:
        """Write `NN-<agent>.output.md`: the agent's reply, exactly as returned.

        Unparsed and unedited. The coordinator's JSON extraction is itself a
        step that can fail, and when it does, this file is the only evidence of
        what the model actually said.
        """
        return self._write(f"{seq:02d}-{agent}.output.md", text)

    def record_state(self, seq: int, phase: str, state_json: str) -> Path:
        """Write `state-after-NN-<phase>.json`: the run state once folded in.

        The input and output files show one agent in isolation. These snapshots
        show the accumulator between them, so diffing two consecutive files
        shows exactly what one phase contributed to the run.
        """
        return self._write(f"state-after-{seq:02d}-{phase}.json", state_json)

    def record_cost(self, summary: dict) -> Path:
        """Write `cost.json`: per-phase and total cost for the run.

        Kept as a separate artifact because it answers a different question from
        the rest of the directory - not "is this report right" but "what did
        this architecture cost", which is the number that justifies running only
        one phase of four on Opus.
        """
        return self._write("cost.json", json.dumps(summary, indent=2, ensure_ascii=False))

    def record_report(self, markdown: str) -> Path:
        """Write `report.md`: the deliverable, stored beside the trail that made it.

        The report lives in the same directory as its evidence on purpose. A
        reader who doubts a citation has the searcher's collected sources one
        file away.
        """
        return self._write("report.md", markdown)
