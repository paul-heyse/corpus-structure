"""Shared native intent creation/resume and execution, independent of its transport."""

from __future__ import annotations

from pathlib import Path

from corpus_structure.semantic.data_operation_service import create_native_demand, read_data_demand
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.storage_target import acquired_target


def execute_native_intent(
    engine,
    admission_engine,
    *,
    source_root: Path | None,
    methods,
    demand=None,
    request=None,
    source_request=None,
    visual_actor=None,
    project=None,
    limit=100,
    max_rounds=100,
    required_targets=None,
    registered=None,
    completion_draft_root: Path | None = None,
):
    """Execute only one explicit intent; optional target restriction also checks resume."""
    from corpus_structure.semantic.data_operation_service import execute_data_demand

    if sum(value is not None for value in (demand, request, source_request)) != 1:
        raise SemanticRefusal("select one source request, native request or retained demand")
    if request is not None and required_targets is not None and request.targets != required_targets:
        raise SemanticRefusal("native request differs from the required explicit targets")
    with engine.begin() as connection:
        target = acquired_target(connection, purpose="write")
        if source_request is not None:
            from corpus_structure.orchestrate.source_operation import prepare_source_demand
            from corpus_structure.semantic.releases import load_release

            prepared = load_release(connection, source_request.release_id)
            request = prepare_source_demand(connection, source_request, prepared=prepared)
        else:
            prepared = None
        if request is not None:
            if project is not None and request.project_id != project:
                raise SemanticRefusal("request belongs to another project")
            receipt = create_native_demand(connection, request, prepared=prepared)
            demand = receipt["demand_id"]
    if demand is None:
        raise SemanticRefusal("native execution lacks its explicit demand")
    # Native read acquisition cannot share the registration write transaction.
    with engine.begin() as connection:
        snapshot = read_data_demand(connection, demand, limit=1)
        if project is not None and snapshot["project_id"] != project:
            raise SemanticRefusal("retained demand belongs to another project")
        if (
            required_targets is not None
            and tuple(snapshot["selection"]["targets"]) != required_targets
        ):
            raise SemanticRefusal("retained demand differs from the required explicit targets")
    if registered is not None:
        registered(snapshot, target, request)
    execute = execute_data_demand
    if visual_actor is not None:
        from functools import partial

        from corpus_structure.semantic.visual_requests import execute_visual_demand

        execute = partial(execute_visual_demand, visual_actor=visual_actor)
    return execute(
        engine,
        demand,
        source_root=source_root,
        limit=limit,
        max_rounds=max_rounds,
        policy=methods.execution_policy,
        project_id=project,
        nemotron_endpoint=methods.nemotron_endpoint,
        admission_engine=admission_engine,
        completion_draft_root=completion_draft_root,
    )
