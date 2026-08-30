"""research-crew: a coordinator-and-subagents research pipeline.

This package holds the foundation layer of the crew. Three modules, three jobs:

  state.py            the single object that carries data across phase boundaries
  agents_loader.py    turns agents/*.md design files into SDK AgentDefinition objects
  observability.py    writes one auditable directory per run

The coordinator, the CLI, and the citation verifier are built in a later task and
are deliberately absent here.

Nothing in this package calls the model. Everything here is a pure data or
filesystem concern, which is what makes the whole layer testable offline.
"""
