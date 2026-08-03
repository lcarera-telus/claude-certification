"""Exercise 1.2 — Multi-agent Orchestration (Hub-and-Spoke Research Coordinator).

A coordinator decomposes a broad research topic into subtopics, delegates each
to two isolated subagents (web-search, then document-analysis), aggregates
the sections, and runs an iterative refinement loop that re-delegates any
subtopic a coverage check flags as thin -- before declaring the report done.

Every subagent call builds a brand-new `messages` list from scratch: nothing
from the coordinator's own reasoning or from sibling subagents is inherited.
Whatever a subagent needs (topic, subtopic, prior findings) is passed as an
explicit argument -- that's subagent isolation in code, not just in a diagram.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from client import DEFAULT_MODEL, get_client  # noqa: E402

MAX_REFINEMENT_ITERATIONS = 2

COORDINATOR_DECOMPOSE_SYSTEM = """You are the coordinator in a hub-and-spoke research system. \
You own the only view of the whole task; subagents never see each other's work or your reasoning. \
Break the given research topic into at least 5 distinct, non-overlapping subtopics that together \
give full breadth coverage, one subtopic per primary technology or solution category the topic \
spans (for "renewable energy technologies" that means categories like solar, wind, hydropower, \
geothermal, bioenergy, and emerging technologies such as fusion -- not cross-cutting themes like \
economics or grid integration unless the topic is specifically about those). Avoid narrow \
decomposition -- do not settle for the 2-3 most obvious categories if the topic spans more ground. \
Keep each subtopic name short, a few words."""

COORDINATOR_EVALUATE_SYSTEM = """You are the coordinator in a hub-and-spoke research system, \
reviewing draft report sections written by isolated subagents. For each subtopic, judge whether \
its section is substantive (specific facts, figures, named projects/technologies) or thin \
(vague, generic, or missing concrete detail). Mark thin sections as a "gap" and write a targeted \
follow-up query that would fill the specific missing detail -- not a repeat of the original topic."""

WEB_SEARCH_SUBAGENT_SYSTEM = """You are an isolated web-search subagent. You have no knowledge of \
any other subtopic, any other subagent's output, or the coordinator's reasoning -- only what is in \
this prompt. Call the web_search tool exactly once with the exact query given, then report the \
returned findings plainly in text. Do not call web_search more than once, and do not editorialize \
or organize into a polished report -- that is a different subagent's job."""

DOCUMENT_ANALYSIS_SUBAGENT_SYSTEM = """You are an isolated document-analysis subagent. You have no \
knowledge of any other subtopic or the coordinator's reasoning -- only the raw findings passed to \
you in this prompt. Synthesize them into a clear, substantive report section (3-5 sentences) for \
the given subtopic. If the raw findings are too thin to support that, say so plainly rather than \
padding with generic filler -- and do not supplement thin findings with unstated claims from your \
own general knowledge. Output only the section body text: no heading or title line, the coordinator \
adds that."""

WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web for a query and return raw findings.",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "The search query"}},
        "required": ["query"],
    },
}

DECOMPOSITION_TOOL = {
    "name": "record_decomposition",
    "description": "Record the broad decomposition of the research topic into subtopics.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subtopics": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 5,
                "description": "Distinct, non-overlapping subtopics giving full breadth coverage.",
            }
        },
        "required": ["subtopics"],
    },
}

COVERAGE_EVALUATION_TOOL = {
    "name": "record_coverage_evaluation",
    "description": "Record a completeness evaluation of the current draft report, subtopic by subtopic.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subtopics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "status": {"type": "string", "enum": ["covered", "gap"]},
                        "reason": {"type": "string"},
                        "follow_up_query": {
                            "type": "string",
                            "description": "Only set when status is 'gap': a targeted query to fill it.",
                        },
                    },
                    "required": ["name", "status", "reason"],
                },
            },
            "overall_complete": {"type": "boolean"},
        },
        "required": ["subtopics", "overall_complete"],
    },
}

# Mock knowledge base standing in for a real search index. Every entry is
# reasonably substantive except "fusion", which is deliberately thin on the
# first pass so the coverage-evaluation/refinement loop has a real gap to
# find and fix -- and richer on the follow-up so the re-delegation visibly
# resolves it. This mirrors 1.1's use of seeded mock data to make a mechanism
# reliably observable, rather than leaving it to API-response luck.
_MOCK_KB = {
    "solar": "Global installed solar PV capacity passed 1.6 TW in 2024, led by China, the US, and India. Levelized cost of solar has fallen below $30/MWh at optimal sites.",
    "wind": "Onshore and offshore wind together exceed 1 TW of installed capacity worldwide. Offshore wind is scaling fastest in the North Sea and East Asia, with turbines now exceeding 15 MW per unit.",
    "geothermal": "Geothermal supplies baseload power in volcanically active regions such as Iceland, Kenya, and Indonesia. Enhanced geothermal systems (EGS) are extending viability to non-volcanic regions via engineered fracturing.",
    "tidal": "Tidal stream and barrage projects remain pre-commercial at scale; the MeyGen array in Scotland is the largest operating tidal stream farm at roughly 6 MW.",
    "biomass": "Biomass and biogas provide dispatchable renewable power from agricultural and municipal waste, with combined heat and power (CHP) plants reaching 80%+ overall efficiency in some deployments.",
    "fusion": "Fusion energy is an active area of research; no commercial power plants exist yet.",
}
_MOCK_KB_FOLLOWUP = {
    "fusion": "NIF achieved fusion ignition (net energy gain from the fuel) in December 2022. Private developers Commonwealth Fusion, Helion, and TAE are targeting pilot plants in the early-to-mid 2030s. ITER is aiming for first full-power plasma to inform commercial reactor designs after 2035.",
}


def mock_web_search(query: str, is_follow_up: bool = False) -> str:
    query_lower = query.lower()
    kb = _MOCK_KB_FOLLOWUP if is_follow_up else _MOCK_KB
    for keyword, findings in kb.items():
        if keyword in query_lower:
            return f"Mock search results for '{query}':\n{findings}"
    for keyword, findings in _MOCK_KB.items():
        if keyword in query_lower:
            return f"Mock search results for '{query}':\n{findings}"
    return f"Mock search results for '{query}': no strong matches found; only general background available."


def decompose_topic(client, topic: str) -> list[str]:
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=512,
        system=COORDINATOR_DECOMPOSE_SYSTEM,
        tools=[DECOMPOSITION_TOOL],
        tool_choice={"type": "tool", "name": "record_decomposition"},
        messages=[{"role": "user", "content": f"Research topic: {topic}"}],
    )
    tool_use = next(b for b in response.content if b.type == "tool_use")
    return tool_use.input["subtopics"]


def run_web_search_subagent(client, topic: str, subtopic: str, follow_up_query: str | None = None) -> str:
    query = follow_up_query or subtopic
    user_message = (
        f"Parent research topic: {topic}\n"
        f"Your assigned subtopic: {subtopic}\n"
        f"Search query: {query}"
    )
    messages = [{"role": "user", "content": user_message}]
    for _ in range(3):
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1024,
            system=WEB_SEARCH_SUBAGENT_SYSTEM,
            tools=[WEB_SEARCH_TOOL],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason == "end_turn":
            return next((b.text for b in response.content if b.type == "text"), "")
        if response.stop_reason != "tool_use":
            return f"error: web-search subagent stopped early (stop_reason={response.stop_reason!r})"
        tool_results = [
            {"type": "tool_result", "tool_use_id": block.id, "content": mock_web_search(block.input["query"], is_follow_up=follow_up_query is not None)}
            for block in response.content
            if block.type == "tool_use"
        ]
        messages.append({"role": "user", "content": tool_results})
    return "error: web-search subagent did not reach a final answer"


def run_document_analysis_subagent(client, topic: str, subtopic: str, raw_findings: str) -> str:
    user_message = (
        f"Parent research topic: {topic}\n"
        f"Your assigned subtopic: {subtopic}\n"
        f"Raw findings from the web-search subagent:\n{raw_findings}"
    )
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=512,
        system=DOCUMENT_ANALYSIS_SUBAGENT_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )
    return next((b.text for b in response.content if b.type == "text"), "")


def evaluate_coverage(client, topic: str, sections: dict) -> dict:
    draft = "\n\n".join(f"## {name}\n{text}" for name, text in sections.items())
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=2048,
        system=COORDINATOR_EVALUATE_SYSTEM,
        tools=[COVERAGE_EVALUATION_TOOL],
        tool_choice={"type": "tool", "name": "record_coverage_evaluation"},
        messages=[{"role": "user", "content": f"Research topic: {topic}\n\nDraft report:\n{draft}"}],
    )
    tool_use = next(b for b in response.content if b.type == "tool_use")
    return tool_use.input


def _resolve_section_key(name: str, sections: dict) -> str:
    """Map a coverage-evaluation subtopic name back to its original `sections` key.

    The evaluator sees the draft as plain text and echoes subtopic names back
    from memory -- it can rephrase slightly, so exact-key lookups silently
    create a duplicate entry instead of updating the original one.
    """
    if name in sections:
        return name
    name_base = name.split("(")[0].strip().lower()
    for key in sections:
        if key.split("(")[0].strip().lower() == name_base:
            return key
    name_lower = name.lower()
    for key in sections:
        if key.lower() in name_lower or name_lower in key.lower():
            return key
    return name


def run_research_coordinator(client, topic: str) -> str:
    subtopics = decompose_topic(client, topic)
    print(f"Coordinator decomposed '{topic}' into {len(subtopics)} subtopics: {subtopics}\n")

    sections = {}
    for subtopic in subtopics:
        raw = run_web_search_subagent(client, topic, subtopic)
        sections[subtopic] = run_document_analysis_subagent(client, topic, subtopic, raw)

    persistent_gaps = []
    for iteration in range(1, MAX_REFINEMENT_ITERATIONS + 1):
        evaluation = evaluate_coverage(client, topic, sections)
        gaps = [s for s in evaluation["subtopics"] if s["status"] == "gap"]
        if not gaps:
            print(f"Coverage check (pass {iteration}): all subtopics covered.\n")
            persistent_gaps = []
            break
        print(f"Coverage check (pass {iteration}): gap(s) found -> {[g['name'] for g in gaps]}")
        for gap in gaps:
            key = _resolve_section_key(gap["name"], sections)
            print(f"  - {key}: {gap['reason']} (follow-up: {gap.get('follow_up_query', key)})")
            raw = run_web_search_subagent(
                client, topic, key, follow_up_query=gap.get("follow_up_query")
            )
            sections[key] = run_document_analysis_subagent(client, topic, key, raw)
        persistent_gaps = gaps
        print()

    if persistent_gaps:
        names = [g["name"] for g in persistent_gaps]
        print(
            f"Diagnostic: {names} still thin after {MAX_REFINEMENT_ITERATIONS} refinement pass(es). "
            "Before re-querying again, check whether this traces back to the coordinator's initial "
            "decomposition (subtopic scoped too broadly/vaguely to search well) rather than treating "
            "it as a subagent execution failure.\n"
        )

    report = f"# Research Report: {topic}\n\n" + "\n\n".join(
        f"## {name}\n{text}" for name, text in sections.items()
    )
    return report


if __name__ == "__main__":
    client = get_client()
    report = run_research_coordinator(client, "renewable energy technologies")
    print("=" * 60)
    print(report)
