"""Current CLI adapters for explicit demand results and selected native members."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import typer

from corpus_structure.cli.output import JsonOpt, state, write_report_text
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.serve.demand_journey import DemandQueryRequest, serve_demand_query


def query(
    ctx: typer.Context,
    name: Annotated[Literal["members", "operations", "sources", "support", "coverage"], typer.Argument()],
    demand: Annotated[str, typer.Option(help="Exact target demand; no promoted/latest selection.")],
    project: Annotated[str, typer.Option(help="Required project of the selected demand.")],
    operation: str | None = None,
    subject: str | None = None,
    original_source: str | None = None,
    kind_contract: str | None = None,
    product: str | None = None,
    member: str | None = None,
    cursor: str | None = None,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
    max_bytes: Annotated[int, typer.Option(min=1024, max=67108864)] = 1048576,
    json: JsonOpt = False,
) -> None:
    """Read selected members or operation/source/support standing under native pins."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.runtime import open_runtime_engine

    with failure_boundary(json, expected=(ValueError, KeyError)):
        request = DemandQueryRequest(demand_id=demand, project_id=project, view=name,
            operation_id=operation, subject=subject, original_source=original_source,
            kind_contract=kind_contract, product_id=product, member_id=member,
            cursor=cursor, limit=limit, max_bytes=max_bytes)
        with open_runtime_engine(state(ctx).settings(), "ci-selected-result", purpose="read") as engine, engine.begin() as connection:
            result = serve_demand_query(connection, request)
    write_report_text(json_bytes(result).decode() + "\n")


contributions_app = typer.Typer(help="Read current selected contributions and operation standing.", no_args_is_help=True)

records_app = typer.Typer(help="Read exact current semantic product/member records.", no_args_is_help=True)
@records_app.command("list")
def records(
    ctx: typer.Context,
    demand: Annotated[str, typer.Option()],
    project: Annotated[str, typer.Option()],
    operation: str | None = None,
    subject: str | None = None,
    original_source: str | None = None,
    kind_contract: str | None = None,
    product: str | None = None,
    member: str | None = None,
    cursor: str | None = None,
    limit: int = 100,
    max_bytes: int = 1048576,
    json: JsonOpt = False,
):
    return query(ctx, "members", demand, project, operation=operation, subject=subject,
                 original_source=original_source, kind_contract=kind_contract,
                 product=product, member=member, cursor=cursor, limit=limit,
                 max_bytes=max_bytes, json=json)



@records_app.command("support")
def support(
    ctx: typer.Context,
    demand: Annotated[str, typer.Option()],
    project: Annotated[str, typer.Option()],
    operation: str | None = None,
    subject: str | None = None,
    cursor: str | None = None,
    limit: int = 100,
    max_bytes: int = 1048576,
    json: JsonOpt = False,
):
    return query(ctx, "support", demand, project, operation=operation, subject=subject,
                 cursor=cursor, limit=limit, max_bytes=max_bytes, json=json)


def export(
    ctx: typer.Context,
    out: Annotated[Path, typer.Option()],
    demand: Annotated[str, typer.Option()],
    project: Annotated[str, typer.Option()],
    format: Literal["jsonl", "parquet"] = "parquet",
    page_rows: Annotated[int, typer.Option(min=1, max=1000)] = 100,
    page_bytes: Annotated[int, typer.Option(min=1024, max=67108864)] = 8388608,
    json: JsonOpt = False,
):
    """Export exact selected source/support/contracts/runtime on the acquiring session."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.demand_export import export_demand_result

    with failure_boundary(json, expected=(ValueError, KeyError, OSError)):
        with open_runtime_engine(state(ctx).settings(), "ci-selected-export", purpose="read") as engine, engine.begin() as connection:
            manifest = export_demand_result(connection, demand, project_id=project,
                destination=out, format=format, page_rows=page_rows, page_bytes=page_bytes)
    write_report_text(json_bytes(dict(path=str(out), manifest=manifest)).decode() + "\n")


records_app.command("export")(export)


@records_app.command("verify")
def verify(
    artifact: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    manifest_digest: Annotated[str, typer.Option(help="Expected trusted manifest SHA-256.")],
    json: JsonOpt = False,
):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.demand_export import verify_demand_export
    with failure_boundary(json, expected=(ValueError, KeyError, OSError)):
        report = verify_demand_export(artifact, manifest_digest=manifest_digest)
    write_report_text(json_bytes(report).decode() + "\n")



def explain(ctx:typer.Context,demand:Annotated[str,typer.Option()],project:Annotated[str,typer.Option()],product:Annotated[str,typer.Option(help="Actual selected semantic product to explain.")],cursor:str|None=None,limit:int=100,max_bytes:int=1048576,json:JsonOpt=False):
    """Read the selected product's authentic producing/support closure under one cut."""
    return query(ctx,"support",demand,project,product=product,cursor=cursor,limit=limit,max_bytes=max_bytes,json=json)


def register(root: typer.Typer):
    root.command("query")(query)
    root.command("explain")(explain)
    review=typer.Typer(help="Export and verify selected semantic/source/support closure.")
    review.command("export")(export)
    review.command("verify")(verify)
    root.add_typer(review,name="review")
    root.command("export")(export)
    root.add_typer(records_app, name="records")
    contributions_app.command("list")(records)
    contributions_app.command("export")(export)
    root.add_typer(contributions_app, name="contributions")
    root.command("characterization")(characterization)
    root.command("query-context")(query_context)
    root.command("definition")(definition)


def _inspect(ctx, request, model, operation, *, json):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.output import read_request_bytes
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.runtime import open_runtime_engine
    with failure_boundary(json, expected=(ValueError, KeyError, OSError)):
        parsed = model.model_validate(json_loads(read_request_bytes(request)))
        with open_runtime_engine(state(ctx).settings(), "ci-selected-inspection", purpose="read") as engine, engine.begin() as connection:
            result = operation(connection, parsed)
    write_report_text(json_bytes(result).decode() + "\n")


def characterization(ctx: typer.Context, request: Annotated[Path, typer.Option()], json: JsonOpt = False):
    from corpus_structure.serve.characterization import DemandCharacterizationRequest, inspect_demand_characterization
    return _inspect(ctx, request, DemandCharacterizationRequest, inspect_demand_characterization, json=json)


def query_context(ctx: typer.Context, request: Annotated[Path, typer.Option()], json: JsonOpt = False):
    from corpus_structure.serve.demand_context import DemandContextRequest, inspect_demand_context
    return _inspect(ctx, request, DemandContextRequest, inspect_demand_context, json=json)


def definition(ctx: typer.Context, request: Annotated[Path, typer.Option()], json: JsonOpt = False):
    from corpus_structure.serve.characterization import DemandDefinitionRequest, inspect_demand_definition
    return _inspect(ctx, request, DemandDefinitionRequest, inspect_demand_definition, json=json)
