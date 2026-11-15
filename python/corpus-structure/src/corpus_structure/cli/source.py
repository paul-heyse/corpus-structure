"""Pinned PDF source inspection shared with MCP; historical HTML requests are retired."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Annotated, Literal

import typer
from pydantic import BaseModel, RootModel

from corpus_structure.cli.output import JsonOpt, emit, report_fields, state
from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.serve.native_source import NativeExportFormat, NativeSourceRequest
from corpus_structure.semantic.visual_evidence import VisualEvidenceKind
from corpus_structure.semantic.visual_evidence import VisualEvidencePin

app = typer.Typer(help="Inspect pinned PDF sources and integration custody.", no_args_is_help=True)


class SourceCoverageReport(BaseModel):
    selection: NativeSourceRequest
    release_id: str
    outcome: str
    page_outcomes: dict[str, int]
    page_rows: int | None
    next_cursor: str | None


@app.command("find")
def find(
    ctx: typer.Context,
    request: Annotated[str, typer.Argument(help="SourceSearchRequest JSON path or '-' with explicit project/demand/read and source publication pins.")],
    json: JsonOpt = False,
):
    """Search the explicit selected native source population and retain retrievable handles."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.output import read_request_bytes, write_report_text
    from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
    from corpus_structure.semantic.demand_results import selected_read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.source_search import SourceSearchRequest, search_source

    with failure_boundary(json, expected=(ValueError, OSError)):
        selected = SourceSearchRequest.model_validate(json_loads(read_request_bytes(request)))
        with (
            open_runtime_engine(state(ctx).settings(), application_name="ci-source-find", purpose="read") as engine,
            selected_read_snapshot(engine) as connection,
        ):
            response = search_source(connection, selected)
    if json:
        write_report_text(json_bytes(response.model_dump(mode="python")).decode() + "\n")
    else:
        emit(response, json=False)


@app.command("inspect")
def inspect(
    ctx: typer.Context,
    demand: str,
    project: str = typer.Option(...),
    read: str = typer.Option(...),
    use: str = typer.Option(...),
    product: str = typer.Option(...),
    derivation: str = typer.Option(...),
    pointer: str | None = None,
    section: str | None = None,
    membership: Literal["direct", "descendants"] | None = None,
    cell: int | None = None,
    native_view: Literal[
        "products",
        "items",
        "sections",
        "item",
        "formula",
        "cell",
        "regions",
        "trace",
        "companion",
        "manifest",
        "artifact",
        "visual-evidence",
    ] = "items",
    occurrence: str | None = None,
    artifact_digest: str | None = None,
    collection: Literal["inputs", "coverage", "relations", "mapping_reports"] | None = None,
    evidence_use: str | None = None,
    evidence_derivation: str | None = None,
    evidence_product: str | None = None,
    page: int | None = None,
    region_index: int | None = None,
    visual_kind: VisualEvidenceKind | None = None,
    visual_query: str | None = None,
    cursor: str | None = None,
    limit: int = 100,
    max_rows: int = 10000,
    max_bytes: int = 1048576,
    view: Literal["summary", "full"] | None = None,
    json: JsonOpt = False,
):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.demand_results import selected_read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.native_source import inspect_native_source

    coverage = native_view == "manifest" and collection == "coverage"
    if view == "summary" and not coverage:
        raise typer.BadParameter("summary requires --native-view manifest --collection coverage")
    cancellation = BorrowerCancellation()
    with failure_boundary(json, expected=(ValueError,)):
        evidence = None
        if any(
            part is not None
            for part in (evidence_use, evidence_derivation, evidence_product)
        ):
            evidence = VisualEvidencePin.model_validate(
                dict(
                    use_id=evidence_use, derivation_id=evidence_derivation,
                    product_id=evidence_product,
                )
            )
        request = NativeSourceRequest(
            project_id=project, demand_id=demand, read_id=read,
            use_id=use, product_id=product, derivation_id=derivation,
            view="visual_evidence" if native_view == "visual-evidence" else native_view,
            pointer=pointer,
            section_pointer=section,
            membership=membership,
            cell_index=cell,
            occurrence_id=occurrence,
            artifact_digest=artifact_digest,
            collection=collection,
            evidence=evidence,
            page_no=page,
            region_index=region_index,
            visual_kind=visual_kind,
            visual_query=visual_query,
            cursor=cursor,
            limit=limit,
            max_rows=max_rows,
            max_bytes=max_bytes,
        )
    with (
        failure_boundary(json, expected=(ValueError,)),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-source", purpose="read"
        ) as engine,
        selected_read_snapshot(engine, cancellation=cancellation) as conn,
    ):
        response = inspect_native_source(conn, request, cancellation=cancellation)

    if not (coverage and (view == "summary" or (view is None and not json))):
        emit(response, json=json)
        return
    coverage_page = response.rows[0] if response.rows else {}
    rows = coverage_page.get("rows")
    page_outcomes = (
        Counter(
            str(row.get("outcome", "unavailable")) if isinstance(row, dict) else "unavailable"
            for row in rows
        )
        if isinstance(rows, list)
        else Counter()
    )
    emit(
        SourceCoverageReport(
            selection=response.selection,
            release_id=response.release_id,
            outcome=response.outcome,
            page_rows=len(rows) if isinstance(rows, list) else None,
            page_outcomes=dict(page_outcomes),
            next_cursor=response.next_cursor,
        ),
        json=json,
        render=lambda report: report_fields(
            ("Demand", report.selection.demand_id),
            ("Read", report.selection.read_id),
            ("Product", report.selection.product_id),
            ("Producer", report.selection.derivation_id),
            ("Release", report.release_id),
            ("Outcome", report.outcome),
            (
                "Coverage page rows",
                report.page_rows if report.page_rows is not None else "unavailable",
            ),
            (
                "Page outcomes",
                ", ".join(f"{key}: {count}" for key, count in sorted(report.page_outcomes.items()))
                or "none",
            ),
            ("Continuation", report.next_cursor or "none"),
        ),
    )


def register(root: typer.Typer):
    from corpus_structure.cli.visual_request import visual_group, visual_request
    from corpus_structure.cli.visual_route import visual_route

    app.command("visual-request")(visual_request)
    app.command("visual-group")(visual_group)
    app.command("visual-route")(visual_route)
    root.add_typer(app, name="source")


@app.command("visual-observations")
def visual_observations(
    ctx: typer.Context,
    demand: Annotated[str, typer.Option()],
    project: Annotated[str, typer.Option()],
    read: Annotated[str, typer.Option()],
    use: Annotated[str, typer.Option()],
    product: Annotated[str, typer.Option()],
    derivation: Annotated[str, typer.Option()],
    page: int | None = None,
    cursor: str | None = None,
    limit: int = 100,
    max_bytes: int = 1024*1024,
    json: JsonOpt = False,
):
    """Discover visual observations in one authenticated selected demand cut."""
    import json as json_module
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.demand_results import selected_read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.selected_pdf import SelectedPdfSourceReference
    from corpus_structure.serve.pdf_visual_evidence import visual_observation_manifest
    with (
        failure_boundary(json,expected=(ValueError,)),
        open_runtime_engine(state(ctx).settings(),application_name="ci-visual-observations",purpose="read") as engine,
        selected_read_snapshot(engine) as conn,
    ):
        source=SelectedPdfSourceReference(project_id=project,demand_id=demand,read_id=read,use_id=use,
            product_id=product,derivation_id=derivation)
        emit(visual_observation_manifest(conn,source,page_no=page,continuation=json_module.loads(cursor) if cursor else None,
            limit=limit,max_bytes=max_bytes),json=json)


@app.command("native-export")
def native_export(
    ctx: typer.Context,
    demand: Annotated[str, typer.Option()],
    project: Annotated[str, typer.Option()],
    read: Annotated[str, typer.Option()],
    use: Annotated[str, typer.Option()],
    product: Annotated[str, typer.Option()],
    derivation: Annotated[str, typer.Option()],
    output: Annotated[Path, typer.Option()],
    section: str | None = None,
    membership: Literal["direct", "descendants"] | None = None,
    format: NativeExportFormat = "parquet",
):
    """Export pinned projections or complete native Docling JSON without inference."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.demand_results import selected_read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.native_source import NativeSourceRequest, export_native_source

    cancellation = BorrowerCancellation()
    if format == "selected-source-v2":
        from corpus_structure.serve.selected_source import export_selected_native_source

        with failure_boundary(True, expected=(ValueError, FileExistsError)):
            receipt = export_selected_native_source(
                NativeSourceRequest(
                    project_id=project, demand_id=demand, read_id=read,
                    use_id=use, product_id=product, derivation_id=derivation,
                    section_pointer=section,
                    membership=membership,
                ),
                output,
                state(ctx).settings(),
                cancellation=cancellation,
            )
            emit(receipt, json=True)
        return
    from tempfile import TemporaryDirectory

    from corpus_structure.serve.native_source import _publish_native_export

    with failure_boundary(True, expected=(ValueError, FileExistsError)):
        if output.exists():
            raise FileExistsError(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".pdf-export-snapshot-", dir=output.parent) as directory:
            staged = Path(directory) / output.name
            with (
                open_runtime_engine(
                    state(ctx).settings(), application_name="ci-native-export", purpose="read"
                ) as engine,
                selected_read_snapshot(engine, cancellation=cancellation) as conn,
            ):
                export_native_source(
                    conn,
                    NativeSourceRequest(
                        project_id=project, demand_id=demand, read_id=read,
                        use_id=use, product_id=product, derivation_id=derivation,
                        section_pointer=section,
                        membership=membership,
                        limit=1000,
                    ),
                    staged,
                    format=format,
                    cancellation=cancellation,
                )
            _publish_native_export(staged, output, cancellation=cancellation)


def _source_catalog(ctx, demand, project, cursor, limit, max_bytes, view, *, json):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.output import write_report_text
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.demand_results import selected_read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.source_catalog import SourceCatalogRequest, read_source_catalog

    with (
        failure_boundary(json, expected=(ValueError,)),
        open_runtime_engine(state(ctx).settings(), application_name="ci-source-catalog", purpose="read") as engine,
        selected_read_snapshot(engine) as connection,
    ):
        report = read_source_catalog(connection, SourceCatalogRequest(
            project_id=project, demand_id=demand, view=view,
            cursor=cursor, limit=limit, max_bytes=max_bytes,
        ))
    if json:
        write_report_text(json_bytes(report.model_dump(mode="python")).decode() + "\n")
    else:
        emit(report, json=False)


@app.command("native-products")
def native_products(
    ctx: typer.Context,
    demand: str,
    project: Annotated[str, typer.Option()],
    cursor: str | None = None,
    limit: int = typer.Option(100, min=1, max=1000),
    max_bytes: int = typer.Option(1048576, min=1024, max=8388608),
    json: JsonOpt = False,
):
    """List selected PDF publications with authentic producer and publication pins."""
    _source_catalog(ctx, demand, project, cursor, limit, max_bytes, "publications", json=json)


@app.command("native-render")
def native_render(
    ctx: typer.Context,
    request: Annotated[
        Path | None,
        typer.Option(
            help="NativeDemandRequest JSON for source.pdf_region/render; '-' reads stdin."
        ),
    ] = None,
    demand: Annotated[
        str | None, typer.Option(help="Resume an exact retained rendering demand.")
    ] = None,
    source_root: Path | None = None,
    project: str | None = None,
    execution_policy: Path | None = None,
    json: JsonOpt = False,
):
    """Render frozen native geometry under an explicit demand and actual source custody."""
    from corpus_structure.cli.demands import execute_request
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.output import read_request_bytes
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_service import NativeDemandRequest
    from corpus_structure.semantic.native_requests import TARGET

    if (request is None) == (demand is None):
        raise typer.BadParameter("select exactly one --request or --demand")
    with failure_boundary(json, expected=(ValueError, OSError)):
        parsed = (
            None
            if request is None
            else NativeDemandRequest.model_validate(json_loads(read_request_bytes(request)))
        )
        if parsed is not None and parsed.targets != (TARGET,):
            raise ValueError("native-render requires the explicit source.pdf_region/render target")
        execute_request(
            ctx,
            request=parsed,
            demand=demand,
            source_root=source_root,
            project=project,
            execution_policy=execution_policy,
            limit=100,
            max_rounds=100,
            required_targets=(TARGET,),
            action="source.native-render",
            json=json,
        )


@app.command("views")
def native_views(
    ctx: typer.Context,
    demand: str,
    project: Annotated[str, typer.Option()],
    cursor: str | None = None,
    limit: int = typer.Option(100, min=1, max=1000),
    max_bytes: int = typer.Option(1048576, min=1024, max=8388608),
    json: JsonOpt = False,
):
    """List selected source-view members and their exact original projection coordinates."""
    _source_catalog(ctx, demand, project, cursor, limit, max_bytes, "views", json=json)


@app.command("companion-export")
def companion_export(
    ctx: typer.Context,
    demand: Annotated[str, typer.Option()],
    read: Annotated[str, typer.Option()],
    use: Annotated[str, typer.Option()],
    derivation: Annotated[str, typer.Option()],
    product: Annotated[str, typer.Option()],
    project: Annotated[str, typer.Option()],
    output: Annotated[Path, typer.Option()],
    family: Annotated[list[str] | None, typer.Option("--family")] = None,
    json: JsonOpt = False,
):
    """Export detached typed companion families from one exact published pin."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.companion_export import (
        CompanionExportRequest,
        export_companion_parquet,
    )

    from corpus_structure.serve.selected_pdf import SelectedPdfSourceReference

    with failure_boundary(json, expected=(ValueError, FileExistsError)):
        values: dict = dict(
            pin=SelectedPdfSourceReference(
                project_id=project, demand_id=demand, read_id=read,
                use_id=use, product_id=product, derivation_id=derivation,
            ),
            destination=output,
        )
        if family:
            values["families"] = tuple(family)
        request = CompanionExportRequest.model_validate(values)
        emit(export_companion_parquet(request, state(ctx).settings()), json=json)


@app.command("companion-inventory")
def companion_inventory(manifest: Path, json: JsonOpt = False):
    """Inventory only verified manifest-listed files, without a database session."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.companion_export import inventory_companion_export

    with failure_boundary(json, expected=(ValueError, OSError)):
        emit(RootModel(inventory_companion_export(manifest)), json=json)


@app.command("companion-compare")
def companion_compare(left: Path, right: Path, json: JsonOpt = False):
    """Compare compatible detached projections while preserving duplicates."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.companion_export import compare_companion_exports

    with failure_boundary(json, expected=(ValueError, OSError)):
        emit(RootModel(compare_companion_exports(left, right)), json=json)


@app.command("native-request")
def native_request(
    ctx: typer.Context,
    request: Annotated[
        Path | None,
        typer.Option(
            help="NativeDemandRequest JSON with actual source facts and acquired analysis targets; '-' reads stdin."
        ),
    ] = None,
    demand: Annotated[
        str | None, typer.Option(help="Resume this exact retained native demand ID.")
    ] = None,
    source_root: Path | None = None,
    project: str | None = None,
    execution_policy: Path | None = None,
    limit: int = 100,
    max_rounds: int = 100,
    json: JsonOpt = False,
):
    """Execute declared native analysis or resume its exact immutable demand.

    Analysis targets are analyze.math/lexical and analyze.math/contextual. The
    request freezes demand/question/predicate choices and genuine OriginalFactRef
    selections. Rendering is available through native-render.
    """
    from corpus_structure.cli.demands import execute_request
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.output import read_request_bytes
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_service import NativeDemandRequest

    if (request is None) == (demand is None):
        raise typer.BadParameter("select exactly one --request or --demand")
    with failure_boundary(json, expected=(ValueError, OSError)):
        parsed = (
            None
            if request is None
            else NativeDemandRequest.model_validate(json_loads(read_request_bytes(request)))
        )
        execute_request(
            ctx,
            request=parsed,
            demand=demand,
            source_root=source_root,
            project=project,
            execution_policy=execution_policy,
            limit=limit,
            max_rounds=max_rounds,
            action="source.native-request",
            json=json,
        )
