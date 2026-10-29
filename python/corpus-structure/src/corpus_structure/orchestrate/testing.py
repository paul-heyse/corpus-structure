"""In-process production driver shared by acceptance and evaluation (O2 §3.12)."""

from __future__ import annotations

from typing import Any

from corpus_structure.core.vocab import AgentMode
from corpus_structure.orchestrate import commands, phase0


def run_to_completion(
    engine: Any,
    *,
    url: str,
    project_name: str | None = None,
    slice: str | None = None,
    scope: str | None = None,
    corpus: str | None = None,
    agent_mode: AgentMode = AgentMode.COMPLETE,
    **kwargs: Any,
) -> commands.RunReport:
    from corpus_structure.consolidate import run_pass

    return commands.start_run(
        engine,
        url=url,
        project_name=project_name,
        slice=slice,
        scope=scope,
        corpus=corpus,
        explicit={"agent_mode": agent_mode, **kwargs.pop("explicit", {})},
        registry_for=kwargs.pop("registry_for", phase0.registry),
        graph=kwargs.pop("graph", phase0.PHASE0),
        run_pass=kwargs.pop("run_pass", run_pass),
        evaluate=kwargs.pop("evaluate", phase0.stub_evaluate),
        **kwargs,
    )
