"""Agent loader: Markdown design files in, `AgentDefinition` objects out.

WHY THE AGENTS LIVE IN MARKDOWN AND NOT IN PYTHON
=================================================
A subagent is two things: a configuration (which tools, which model) and a
prompt. The prompt is prose, and prose belongs in a prose file. Keeping it in
`agents/*.md` means it can be read, reviewed, and diffed on its own, without
Python quoting getting in the way, and it keeps the configuration next to the
prompt it constrains rather than three files away.

Each file is:

    ---
    name: searcher                  <- the dictionary key this loader returns
    description: ...                <- when to use this agent
    tools: ["WebSearch"]            <- see THE TOOLS TRAP below
    model: sonnet                   <- opus | sonnet | haiku | inherit | full id
    ---

    <!-- design notes, stripped before the prompt is built -->

    You are the searcher ...        <- everything else becomes the prompt

WHY THE HTML COMMENTS ARE STRIPPED
==================================
Each agent file carries a long design-rationale block in an HTML comment. That
rationale is the point of this artifact: it explains why the searcher has one
tool and why the synthesizer alone runs Opus. It has to ship next to the prompt
it justifies, because rationale kept in a separate document rots.

It must never reach the model, for two reasons.

  * Cost. The prompt is resent on every single call to that agent. A block of
    rationale that helps a human once would be paid for on every request, for
    the whole life of the system.
  * Behaviour. The notes discuss what the agent must not do, alternatives that
    were rejected, and failure modes. That is exactly the kind of text a model
    reads as instruction. Telling an agent at length about the searches it is
    forbidden to run puts those searches in its head.

So: ship the rationale, strip it at load time. The comment is for the reader of
the repository. The prompt is for the model. This loader is the boundary between
those two audiences, and stripping is not cosmetic - it is what lets the two
audiences be served by one file.

THE TOOLS TRAP
==============
`AgentDefinition.tools` is `list[str] | None`, and the SDK reads the two values
completely differently:

    tools omitted (None)  ->  the agent INHERITS EVERY TOOL available to
                              subagents: Read, Write, Bash, Grep, WebSearch...
    tools = []            ->  the agent gets NO tools at all.

Both are falsy in Python. Writing `if tools:` or `tools or None` anywhere in
this file would collapse the restrictive case into the permissive one and hand
the analyst, the synthesizer, and the reporter full filesystem and shell access,
with no error and nothing in the output to show it happened. The code below
therefore branches on the *presence of the key*, never on the value's truthiness.

From the SDK documentation, which is why omission is the strong control and a
prompt rule is the weak one: "A tool you leave out isn't in the subagent's
session at all: Claude works without it, with no permission prompt or error."
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from claude_agent_sdk import AgentDefinition

# Frontmatter: a `---` fence at the very start of the file, up to the next `---`
# on its own line. Anchored with \A so a `---` horizontal rule later in the body
# cannot be mistaken for the opening fence.
_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?(.*)\Z", re.DOTALL)

# Non-greedy so that two comments in one file are stripped as two comments and
# not as one span swallowing the prompt text between them. DOTALL so that `.`
# crosses newlines, because these blocks are dozens of lines long.
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def strip_html_comments(text: str) -> str:
    """Remove every HTML comment, however long, however many.

    Separate from the parser so the behaviour can be tested on its own. See
    WHY THE HTML COMMENTS ARE STRIPPED in the module docstring for the reason
    this step exists at all.
    """
    return _HTML_COMMENT_RE.sub("", text)


def parse_agent_file(path: Path) -> tuple[str, AgentDefinition]:
    """Read one `*.md` design file and return `(name, AgentDefinition)`.

    Every failure raises `ValueError` naming the file. A crew that half-loads is
    worse than one that refuses to start: an agent silently missing its prompt
    would still run, and would answer as a generic assistant.
    """
    raw = path.read_text(encoding="utf-8")

    match = _FRONTMATTER_RE.match(raw)
    if match is None:
        raise ValueError(f"{path}: no YAML frontmatter delimited by '---' at the top of the file")

    try:
        front = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        # safe_load, never load: this parser must not be able to construct
        # arbitrary Python objects from a file that anyone can edit.
        raise ValueError(f"{path}: frontmatter is not valid YAML: {exc}") from exc

    if not isinstance(front, dict):
        raise ValueError(f"{path}: frontmatter must be a YAML mapping, got {type(front).__name__}")

    name = str(front.get("name") or "").strip()
    description = str(front.get("description") or "").strip()
    if not name:
        raise ValueError(f"{path}: frontmatter key 'name' is missing or empty")
    if not description:
        raise ValueError(f"{path}: frontmatter key 'description' is missing or empty")

    prompt = strip_html_comments(match.group(2)).strip()
    if not prompt:
        raise ValueError(f"{path}: agent body is empty after HTML comments are stripped")

    # Build the keyword arguments one at a time, so that an absent key stays
    # absent. This is the trap described in the module docstring, and it is the
    # only place in the codebase where the distinction is made.
    kwargs: dict[str, object] = {"description": description, "prompt": prompt}

    if "tools" in front:
        # The key is present, so the file is making a deliberate statement about
        # capability - including the statement `[]`, meaning "no tools". Pass it
        # through exactly as written. Do NOT normalise an empty list away.
        tools = front["tools"]
        if not isinstance(tools, list):
            raise ValueError(f"{path}: frontmatter key 'tools' must be a list, got {type(tools).__name__}")
        kwargs["tools"] = [str(t) for t in tools]
    # else: the key is absent, so we pass nothing and `tools` stays None, which
    # the SDK reads as "inherit every subagent tool". That is the permissive
    # default, and it is reached only by writing no `tools` key at all.

    if "model" in front and front["model"] is not None:
        # Per-agent model choice is one of the concrete savings that splitting a
        # system into subagents buys: only the synthesizer pays the Opus rate.
        kwargs["model"] = str(front["model"])

    return name, AgentDefinition(**kwargs)


def load_agents(agents_dir: Path) -> dict[str, AgentDefinition]:
    """Load every `*.md` file in `agents_dir`, keyed by its frontmatter `name`.

    Keyed by the frontmatter name rather than the filename because the name is
    what the coordinator passes to the Agent tool. Tying the key to the filename
    would let a rename break delegation with no error at load time.

    Sorted for determinism: two runs of the same directory produce the same
    insertion order, which keeps recorded runs comparable.
    """
    agents: dict[str, AgentDefinition] = {}
    for path in sorted(Path(agents_dir).glob("*.md")):
        name, definition = parse_agent_file(path)
        if name in agents:
            raise ValueError(f"{path}: duplicate agent name {name!r}")
        agents[name] = definition
    return agents
