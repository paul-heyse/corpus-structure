"""Explicit current demand execution with the pinned local Chandra actor."""

from pathlib import Path
from typing import Annotated

import typer

from corpus_structure.cli.output import JsonOpt


def visual_request(
    ctx: typer.Context,
    artifacts: Annotated[Path, typer.Option(file_okay=False)],
    request: Annotated[Path | None, typer.Option(help="NativeDemandRequest JSON for source.visual/map; '-' reads stdin.")] = None,
    demand: Annotated[str | None, typer.Option(help="Resume this exact retained visual demand.")] = None,
    source_root: Path | None = None,
    project: str | None = None,
    execution_policy: Path | None = None,
    limit: int = 100,
    max_rounds: int = 100,
    json: JsonOpt = False,
):
    """Render genuine source input, retain actual Chandra output, then derive its mapping."""
    from corpus_structure.cli.demands import execute_request
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.output import read_request_bytes, state
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_service import NativeDemandRequest
    from corpus_structure.semantic.visual_requests import ChandraActorInputs, VISUAL_MAP

    if (request is None) == (demand is None):
        raise typer.BadParameter("select exactly one --request or --demand")
    with failure_boundary(json, expected=(ValueError, OSError)):
        parsed = None if request is None else NativeDemandRequest.model_validate(json_loads(read_request_bytes(request)))
        if parsed is not None and parsed.targets != (VISUAL_MAP,):
            raise ValueError("visual-request requires the explicit source.visual/map target")
        settings = state(ctx).settings()
        actor = ChandraActorInputs(artifacts, settings.nemotron.receipts, settings.nemotron.endpoint)
        execute_request(ctx, request=parsed, demand=demand, source_root=source_root, project=project,
                        execution_policy=execution_policy, limit=limit, max_rounds=max_rounds,
                        action="source.visual-request", visual_actor=actor, json=json)


def visual_group(
    ctx: typer.Context,
    artifacts: Annotated[Path, typer.Option(file_okay=False)],
    requests: Annotated[Path | None, typer.Option(help="JSON list of up to four explicit visual NativeDemandRequests.")] = None,
    demands: Annotated[Path | None, typer.Option(help="JSON list of up to four exact retained demand IDs.")] = None,
    source_root: Path | None = None,
    project: str | None = None,
    execution_policy: Path | None = None,
    json: JsonOpt = False,
):
    """Execute a bounded collection of explicit visual demands, retaining each native result."""
    from pydantic import RootModel, TypeAdapter

    from corpus_structure.cli.demands import DemandActionReport, execute_request
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.output import emit, state
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_service import NativeDemandRequest
    from corpus_structure.semantic.visual_requests import ChandraActorInputs, VISUAL_MAP

    if (requests is None) == (demands is None):
        raise typer.BadParameter("select exactly one --requests or --demands")
    with failure_boundary(json, expected=(ValueError, OSError)):
        path = requests if requests is not None else demands
        assert path is not None
        rows = json_loads(path.read_bytes())
        if not isinstance(rows, list) or not 1 <= len(rows) <= 4:
            raise ValueError("visual-group requires one to four explicit requests or demand IDs")
        parsed = [NativeDemandRequest.model_validate(value) for value in rows] if requests is not None else None
        if parsed is not None and any(value.targets != (VISUAL_MAP,) for value in parsed):
            raise ValueError("every visual request requires its explicit source.visual/map target")
        retained = TypeAdapter(tuple[str, ...]).validate_python(tuple(rows), strict=True) if parsed is None else None
        if retained is not None and any(not value for value in retained):
            raise ValueError("retained visual demands require actual nonempty demand IDs")
        settings = state(ctx).settings()
        actor = ChandraActorInputs(artifacts, settings.nemotron.receipts, settings.nemotron.endpoint)
        completed = []
        try:
            for index, value in enumerate(rows):
                completed.append(execute_request(ctx, request=None if parsed is None else parsed[index],
                    demand=retained[index] if retained is not None else None, source_root=source_root, project=project,
                    execution_policy=execution_policy, action="source.visual-request", visual_actor=actor,
                    json=json, deliver=False))
        except BaseException as error:
            if completed:
                error.add_note("completed visual demand actions: " + ", ".join(result.id for result in completed))
            raise
        emit(RootModel[list[DemandActionReport]](completed), json=json)
