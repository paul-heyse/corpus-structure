"""Versioned, source-qualified native reads without converter/model initialization."""

from __future__ import annotations

import base64
import json
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from pydantic_core import to_jsonable_python
from sqlalchemy import Connection, select, text

from corpus_structure.semantic.pdf_record_reader import published_native_table, published_record_reader
from corpus_structure.semantic.product_reference import ProductReference


class NativeSourceRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[3] = 3
    run_id: int = Field(gt=0)
    task_id: int = Field(gt=0)
    product_key: str = Field(min_length=1)
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    view: Literal[
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
    ] = "items"
    section_pointer: str | None = None
    membership: Literal["direct", "descendants"] | None = None
    pointer: str | None = None
    cell_index: int | None = Field(default=None, ge=0)
    occurrence_id: str | None = None
    artifact_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    collection: Literal["inputs", "coverage", "relations", "mapping_reports"] | None = None
    cursor: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)

    @model_validator(mode="after")
    def qualified_selection(self):
        if self.view == "artifact":
            if self.artifact_digest is None or any(
                value is not None
                for value in (
                    self.pointer,
                    self.section_pointer,
                    self.cell_index,
                    self.occurrence_id,
                    self.collection,
                )
            ):
                raise ValueError("artifact reads require one digest and an exact product pin")
        elif self.artifact_digest is not None:
            raise ValueError("artifact digest is only available for artifact reads")
        if self.membership is not None and self.section_pointer is None:
            raise ValueError("membership requires a selected section")
        if self.collection is not None and self.view != "manifest":
            raise ValueError("collection is only available for manifest reads")
        if self.view == "manifest" and (
            self.collection is None
            or any(
                value is not None
                for value in (
                    self.pointer,
                    self.section_pointer,
                    self.cell_index,
                    self.occurrence_id,
                )
            )
        ):
            raise ValueError("manifest reads require one collection and a whole product pin")
        if self.occurrence_id is not None and (
            self.view not in {"trace", "companion"}
            or any(
                value is not None for value in (self.pointer, self.section_pointer, self.cell_index)
            )
        ):
            raise ValueError(
                "occurrence identity requires a companion/trace selection without native selectors"
            )
        if self.view == "companion" and self.cell_index is not None:
            raise ValueError("companion cell reads require their exact occurrence identity")
        return self

    def selection_digest(self) -> str:
        values = self.model_dump(exclude={"cursor", "limit"})
        return sha256(
            json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


class NativeSourceResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[3] = 3
    selection: NativeSourceRequest
    release_id: str
    outcome: Literal["source_ready", "missing", "invalid", "unsupported"] = "source_ready"
    health: dict[str, JsonValue]
    rows: list[dict[str, JsonValue]]
    next_cursor: str | None = None
    companion: dict[str, JsonValue] | None = None


def _inline_alignment_reports(conn: Connection, *, task_id: int, product_key: str, pointer: str):
    """Read one item's own/ancestor prose diagnostics through fixed bounded projections."""
    rows = conn.execute(
        text("""
        WITH RECURSIVE ancestors(pointer) AS (
          SELECT pointer FROM kb.native_document_item
          WHERE task_id=:task AND product_key=:key AND pointer=:pointer
          UNION
          SELECT item.parent_pointer FROM kb.native_document_item item
          JOIN ancestors parent ON parent.pointer=item.pointer
          WHERE item.task_id=:task AND item.product_key=:key
            AND item.parent_pointer IS NOT NULL
        )
        SELECT report.page_no,report.candidate_index,report.outcome,report.basis,
          report.detail,report.candidate_basis,
          (SELECT jsonb_agg(endpoint.item_pointer ORDER BY endpoint.item_pointer)
           FROM kb.native_document_inline_alignment_item endpoint
           WHERE endpoint.task_id=report.task_id AND endpoint.product_key=report.product_key
             AND endpoint.page_no=report.page_no
             AND endpoint.candidate_index=report.candidate_index) AS item_pointers
        FROM kb.native_document_inline_alignment_report report
        WHERE report.task_id=:task AND report.product_key=:key AND EXISTS(
          SELECT FROM kb.native_document_inline_alignment_item linked
          WHERE linked.task_id=report.task_id AND linked.product_key=report.product_key
            AND linked.page_no=report.page_no AND linked.candidate_index=report.candidate_index
            AND linked.item_pointer IN (SELECT pointer FROM ancestors))
        ORDER BY report.page_no,report.candidate_index
    """),
        dict(task=task_id, key=product_key, pointer=pointer),
    ).mappings()
    return [dict(row) for row in rows]


def inspect_native_source(conn: Connection, request: NativeSourceRequest) -> NativeSourceResponse:
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_storage import read_native_items, read_native_regions

    runs, tasks, products, builds, runtime = map(
        table,
        (
            "ops.run",
            "ops.task",
            "ops.pdf_selected_product",
            "ops.source_build",
            "kb.native_document_runtime",
        ),
    )
    run = conn.execute(
        select(runs.c.project_id, runs.c.release_id).where(runs.c.id == request.run_id)
    ).one_or_none()
    if run is None:
        raise ValueError("unknown native source run")
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_run

    context = pdf_context_for_run(conn, request.run_id)
    context.execution.require_operation("read_native_source")
    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context

    trusted_pdf_context().boundary.validate_json(
        "PdfNativeReadRequest", request.model_dump_json(exclude_none=True)
    )
    if request.view in {"companion", "manifest", "artifact"} or (
        request.view == "trace" and request.occurrence_id is not None
    ):
        return _inspect_companion(conn, request, run.project_id)
    origin = runs.alias("native_origin_run")
    header = conn.execute(
        select(
            products.c.release_id,
            products.c.health.op("-")("formula_outcomes").label("health"),
            products.c.content_digest,
            products.c.parent_task_id,
            products.c.parent_product_key,
            products.c.parent_digest,
            runtime.c.report.label("runtime_report"),
            builds.c.artifact_digest,
            tasks.c.run_id.label("origin_run"),
        )
        .select_from(
            products.join(tasks, tasks.c.id == products.c.task_id)
            .join(origin, origin.c.id == tasks.c.run_id)
            .join(builds, builds.c.task_id == products.c.task_id)
            .outerjoin(
                runtime,
                (runtime.c.task_id == products.c.task_id)
                & (runtime.c.product_key == products.c.product_key),
            )
        )
        .where(
            products.c.task_id == request.task_id,
            products.c.product_key == request.product_key,
            origin.c.project_id == run.project_id,
        )
    ).one_or_none()
    if header is None:
        raise ValueError("native source is unavailable in the requested project")
    if header.content_digest != request.content_digest:
        raise ValueError("native source product differs from requested pin")
    if header.origin_run != request.run_id:
        # A retained input pin is reachable through the selected immutable product graph.
        from corpus_structure.semantic.pdf_storage import selected_native_ancestry

        selected = selected_native_ancestry(request.run_id)
        chosen = conn.execute(
            select(selected.c.task_id)
            .where(
                selected.c.task_id == request.task_id,
                selected.c.product_key == request.product_key,
                selected.c.content_digest == request.content_digest,
            )
            .limit(1)
        ).first()
        if chosen is None:
            raise ValueError("native source is not selected by the requested run")
    after = -1
    if request.cursor is not None:
        try:
            cursor = json.loads(base64.urlsafe_b64decode(request.cursor))
            if (
                cursor["selection"] != request.selection_digest()
                or type(cursor["after"]) is not int
            ):
                raise ValueError("cursor selection differs")
            after = cursor["after"]
        except (KeyError, ValueError, TypeError) as error:
            raise ValueError("invalid native continuation") from error
    pin = dict(
        task_id=request.task_id,
        product_key=request.product_key,
        content_digest=request.content_digest,
    )
    # The storage reader checks the admitted archive even for metadata-only selections.
    rows = read_native_items(
        conn,
        **pin,
        section_pointer=request.section_pointer,
        membership=request.membership or "direct",
        pointer=request.pointer,
        after=after,
        limit=request.limit,
    )
    next_cursor = None
    if request.view == "products":
        rows = [
            dict(
                task_id=request.task_id,
                product_key=request.product_key,
                content_digest=request.content_digest,
                artifact_digest=header.artifact_digest,
                runtime_report=header.runtime_report,
            )
        ]
    elif request.view == "sections":
        item = published_native_table(conn)
        if request.section_pointer is None:
            scope = []
        elif request.membership == "descendants":
            from corpus_structure.semantic.pdf_storage import native_descendant_pointers

            scope = [
                item.c.pointer.in_(
                    native_descendant_pointers(
                        task_id=request.task_id,
                        product_key=request.product_key,
                        section_pointer=request.section_pointer, conn=conn,
                    )
                ),
                item.c.pointer != request.section_pointer,
            ]
        else:
            scope = [item.c.parent_pointer == request.section_pointer]
        rows = [
            dict(r)
            for r in conn.execute(
                select(
                    *[c for c in item.columns if c.name != "native_json"],
                    item.c.native_json["name"].as_string().label("name"),
                )
                .where(
                    item.c.task_id == request.task_id,
                    item.c.product_key == request.product_key,
                    item.c.label.in_(["section", "chapter"]),
                    item.c.ordinal > after,
                    *scope,
                )
                .order_by(item.c.ordinal)
                .limit(request.limit)
            ).mappings()
        ]
    elif request.view in {"item", "formula", "cell", "regions", "trace"}:
        if request.pointer is None or len(rows) != 1:
            raise ValueError("native occurrence inspection requires one existing pointer")
        alignment = (
            _inline_alignment_reports(
                conn,
                task_id=request.task_id,
                product_key=request.product_key,
                pointer=request.pointer,
            )
            if request.view in {"item", "formula", "trace"}
            else []
        )
        for report in alignment:
            report["source_product"] = dict(
                task_id=header.parent_task_id,
                product_key=header.parent_product_key,
                content_digest=header.parent_digest,
            )
        if request.view in {"regions", "trace"}:
            rows = read_native_regions(conn, **pin, pointer=request.pointer)
            if request.view == "trace":
                derivation = table("kb.native_document_derivation")
                mappings = [
                    dict(row)
                    for row in conn.execute(
                        select(derivation)
                        .where(
                            derivation.c.task_id == request.task_id,
                            derivation.c.product_key == request.product_key,
                            derivation.c.pointer == request.pointer,
                        )
                        .order_by(derivation.c.mapping_index)
                    ).mappings()
                ]
                parent = (
                    None
                    if header.parent_task_id is None
                    else dict(
                        task_id=header.parent_task_id,
                        product_key=header.parent_product_key,
                        content_digest=header.parent_digest,
                    )
                )
                rows = [
                    dict(
                        pointer=request.pointer,
                        artifact_digest=header.artifact_digest,
                        space="pdf_points",
                        regions=rows,
                        parent_product=parent,
                        derivation_mappings=mappings,
                        inline_alignment_reports=alignment,
                    )
                ]
        else:
            # Transfer only the selected native object, not its containing document.
            item = published_native_table(conn)
            native = conn.execute(
                select(item.c.native_json).where(
                    item.c.task_id == request.task_id,
                    item.c.product_key == request.product_key,
                    item.c.pointer == request.pointer,
                )
            ).scalar_one()
            if not isinstance(native, dict):
                raise ValueError("native item object unavailable")
            if request.view == "cell":
                chart = native.get("meta", {}).get("tabular_chart")
                is_chart = isinstance(chart, dict)
                cells = (
                    chart.get("chart_data", {}).get("table_cells", [])
                    if is_chart
                    else native.get("data", {}).get("table_cells", [])
                )
                if request.cell_index is None or request.cell_index >= len(cells):
                    raise ValueError("table cell index unavailable")
                reports = table("kb.native_document_cell_report")
                report = (
                    conn.execute(
                        select(reports).where(
                            reports.c.task_id == request.task_id,
                            reports.c.product_key == request.product_key,
                            reports.c.table_pointer == request.pointer,
                            reports.c.cell_index == request.cell_index,
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                rows = [
                    dict(
                        pointer=request.pointer,
                        cell_index=request.cell_index,
                        cell=cells[request.cell_index],
                        recognition=None if report is None else dict(report),
                        source_field="chart_cell_text" if is_chart else "cell_text",
                    )
                ]
            elif request.view == "formula":
                if native.get("label") != "formula":
                    raise ValueError("native pointer is not a formula")
                record_reader = published_record_reader(conn,ProductReference(request.task_id,
                                                        request.product_key,request.content_digest))
                if record_reader is not None:
                    outcomes = list(record_reader.native_metadata("formula_outcomes",pointer=request.pointer))
                    if len(outcomes)>1:
                        raise ValueError("formula outcome metadata is ambiguous")
                    health = outcomes[0] if outcomes else {"outcome":"unknown"}
                else:
                    health = conn.execute(
                        text(
                            "SELECT outcome.value FROM ops.pdf_selected_product p\n"
                            "                    CROSS JOIN LATERAL "
                            "jsonb_array_elements(COALESCE(p.health->'formula_outcomes"
                            "','[]'::jsonb)) outcome(value)\n"
                            "                    WHERE p.task_id=:task AND "
                            "p.product_key=:key AND p.content_digest=:digest AND "
                            "outcome.value->>'pointer'=:pointer LIMIT 1"
                        ),
                        dict(
                            task=request.task_id,
                            key=request.product_key,
                            digest=request.content_digest,
                            pointer=request.pointer,
                        ),
                    ).scalar_one_or_none() or {"outcome": "unknown"}
                rows = [
                    dict(
                        pointer=request.pointer,
                        original_text=native.get("orig"),
                        recognized_latex=native.get("text"),
                        recognition=health,
                        inline_alignment_reports=alignment,
                        interpretation=_recorded_interpretations(conn, request),
                        regions=read_native_regions(conn, **pin, pointer=request.pointer),
                    )
                ]
            else:
                rows = [dict(rows[0], native=native, inline_alignment_reports=alignment)]
    if request.view in {"items", "sections"} and len(rows) == request.limit:
        next_cursor = base64.urlsafe_b64encode(
            json.dumps(
                dict(selection=request.selection_digest(), after=rows[-1]["ordinal"]),
                sort_keys=True,
            ).encode()
        ).decode()
    from corpus_structure.semantic.pdf_storage import integrated_source_context

    companion = integrated_source_context(
        conn,
        **pin,
        pointers=[request.pointer]
        if request.pointer is not None
        else [pointer for row in rows if isinstance(pointer := row.get("pointer"), str)],
        section_pointer=request.section_pointer or "#/body",
        membership=request.membership or "direct",
    )
    return NativeSourceResponse(
        selection=request,
        release_id=header.release_id,
        health=to_jsonable_python(header.health),
        rows=to_jsonable_python(rows),
        next_cursor=next_cursor,
        companion=to_jsonable_python(companion),
    )


def _inspect_companion(
    conn: Connection, request: NativeSourceRequest, project_id: int
) -> NativeSourceResponse:
    """Authorize the exact selected graph before reading retained companion/observation data."""
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_storage import (
        read_pdf_manifest,
        read_pdf_product,
        selected_native_ancestry,
        trace_pdf_occurrence,
    )

    products, tasks, runs = map(table, ("ops.pdf_product", "ops.task", "ops.run"))
    selected = selected_native_ancestry(request.run_id)
    reachable = (
        select(selected.c.task_id)
        .where(
            selected.c.task_id == products.c.task_id,
            selected.c.product_key == products.c.product_key,
            selected.c.content_digest == products.c.content_digest,
        )
        .exists()
    )
    row = conn.execute(
        select(products.c.release_id)
        .join(tasks, tasks.c.id == products.c.task_id)
        .join(runs, runs.c.id == tasks.c.run_id)
        .where(
            products.c.task_id == request.task_id,
            products.c.product_key == request.product_key,
            products.c.content_digest == request.content_digest,
            runs.c.project_id == project_id,
            (tasks.c.run_id == request.run_id) | reachable,
        )
    ).one_or_none()
    if row is None:
        raise ValueError("PDF companion is not selected by the requested project/run")
    after = ""
    if request.cursor is not None:
        try:
            cursor = json.loads(base64.urlsafe_b64decode(request.cursor))
            if cursor["selection"] != request.selection_digest() or not isinstance(
                cursor["after"], str
            ):
                raise ValueError("cursor selection differs")
            after = cursor["after"]
        except (KeyError, ValueError, TypeError) as error:
            raise ValueError("invalid PDF companion continuation") from error
    pin = dict(
        task_id=request.task_id,
        product_key=request.product_key,
        content_digest=request.content_digest,
    )
    if request.view == "artifact":
        from corpus_structure.semantic.pdf_storage import read_pdf_artifact

        if request.artifact_digest is None:
            raise ValueError("artifact digest is missing")
        try:
            offset = int(after) if after else 0
        except ValueError as error:
            raise ValueError("invalid artifact continuation offset") from error
        result = read_pdf_artifact(
            conn, **pin, artifact_digest=request.artifact_digest, offset=offset
        )
        following = result.pop("next_offset")
        content = result.pop("content")
        result.update(
            encoding="base64",
            data=base64.b64encode(content).decode(),
            length=len(content),
            next_offset=following,
        )
        continuation = (
            None
            if following is None
            else base64.urlsafe_b64encode(
                json.dumps(
                    dict(selection=request.selection_digest(), after=str(following))
                ).encode()
            ).decode()
        )
        return NativeSourceResponse(
            selection=request,
            release_id=row.release_id,
            health={},
            rows=[to_jsonable_python(result)],
            next_cursor=continuation,
        )
    if request.view == "trace":
        if request.occurrence_id is None or request.cursor is not None:
            raise ValueError("companion trace requires one occurrence and no continuation")
        result = trace_pdf_occurrence(
            conn, **pin, occurrence_id=request.occurrence_id, limit=request.limit
        )
    elif request.view == "manifest":
        if request.collection is None:
            raise ValueError("manifest inspection requires a named collection")
        result = read_pdf_manifest(
            conn, **pin, collection=request.collection, after=after, limit=request.limit
        )
    else:
        pointers = None
        if request.pointer is not None:
            pointers = [request.pointer]
        elif request.section_pointer is not None:
            from corpus_structure.semantic.pdf_storage import native_descendant_pointers

            item = published_native_table(conn)
            query = select(item.c.pointer).where(
                item.c.task_id == request.task_id, item.c.product_key == request.product_key
            )
            query = (
                query.where(
                    item.c.pointer.in_(
                        native_descendant_pointers(
                            task_id=request.task_id,
                            product_key=request.product_key,
                            section_pointer=request.section_pointer, conn=conn,
                        )
                    )
                )
                if request.membership == "descendants"
                else query.where(item.c.section_pointer == request.section_pointer)
            )
            pointers = list(conn.execute(query).scalars())
        result = read_pdf_product(
            conn,
            **pin,
            occurrence_id=request.occurrence_id,
            pointers=pointers,
            section_pointer=request.section_pointer,
            after=after,
            limit=request.limit,
        )
    continuation = result.get("cursor")
    next_cursor = (
        None
        if continuation is None
        else base64.urlsafe_b64encode(
            json.dumps(dict(selection=request.selection_digest(), after=continuation)).encode()
        ).decode()
    )
    return NativeSourceResponse(
        selection=request,
        release_id=row.release_id,
        health={},
        rows=[to_jsonable_python(result)],
        next_cursor=next_cursor,
    )


def _recorded_interpretations(conn: Connection, request: NativeSourceRequest) -> dict:
    """Read selected-run analysis only; inspection never requests stronger computation."""
    if request.pointer is None:
        raise ValueError("recorded analysis requires one native formula occurrence")
    from corpus_structure.core.vocab import ObservationKind
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import BoundReader
    from corpus_structure.semantic.releases import open_release

    runs = table("ops.run")
    release = conn.execute(
        select(runs.c.release_id).where(runs.c.id == request.run_id)
    ).scalar_one()
    reader = BoundReader(conn, request.run_id, open_release(conn, release), analysis=False)
    results = []
    views, selection = table("kb.source_view"), table("ops.run_source_view")
    newer = selection.alias("newer_analysis_selection")
    view_ids = conn.execute(
        select(views.c.id)
        .join(selection, selection.c.source_view_id == views.c.id)
        .where(
            selection.c.run_id == request.run_id,
            views.c.native_task_id == request.task_id,
            views.c.native_product_key == request.product_key,
            views.c.native_content_digest == request.content_digest,
            views.c.projection["items"].contains([request.pointer]),
            ~select(newer.c.source_view_id)
            .where(
                newer.c.run_id == request.run_id, newer.c.supersedes_source_view_id == views.c.id
            )
            .exists(),
        )
        .order_by(views.c.id)
    ).scalars()
    from corpus_structure.semantic.native_analysis import stored_native_analysis

    for view_id in view_ids:
        analysis = stored_native_analysis(reader, view_id, request.pointer)[request.pointer]
        requests = []
        for observation in reader.source_observations(
            view_id, "native.source_request", ObservationKind.RECORD
        ):
            payload = observation.payload
            if not isinstance(payload, dict):
                continue
            if payload.get("source_view_id") != view_id or payload.get("native_product") != dict(
                task_id=request.task_id,
                product_key=request.product_key,
                content_digest=request.content_digest,
            ):
                raise ValueError("recorded native request differs from the selected source pin")
            items = payload.get("items", [])
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and item.get("pointer") == request.pointer:
                    requests.append(
                        dict(
                            task_id=observation.task_id, demand=payload.get("demand"), analysis=item
                        )
                    )
        results.append(dict(analysis, requests=requests))
    recorded = any(result["observations"] or result["requests"] for result in results)
    return dict(
        status="recorded" if recorded else "not_selected", run_id=request.run_id, results=results
    )


NativeExportFormat = Literal["jsonl", "parquet", "docling-json", "integrated-json"]


def export_native_source(
    conn: Connection,
    request: NativeSourceRequest,
    destination,
    *,
    format: NativeExportFormat = "parquet",
) -> None:
    """Export a pinned projection or explicitly requested complete native document."""
    import os
    from collections import defaultdict
    from pathlib import Path

    from sqlalchemy import Text

    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    binding = dict(
        contract="integrated-pdf-source-3",
        selection=request.model_dump(mode="json", exclude_none=True),
        companion_request=request.model_copy(
            update={"view": "companion", "cursor": None}
        ).model_dump(mode="json", exclude_none=True),
        manifest_collections=["inputs", "coverage", "relations", "mapping_reports"],
    )
    if format in {"docling-json", "integrated-json"}:
        if (
            request.view not in {"items", "products"}
            or request.section_pointer is not None
            or request.membership is not None
            or request.pointer is not None
            or request.cell_index is not None
            or request.cursor is not None
        ):
            raise ValueError("complete Docling JSON export cannot carry a partial source selector")
        # Resolve authorization and the archived contract through the same pinned reader.
        # Casting the whole JSONB column transfers native JSON without a Python float roundtrip.
        inspect_native_source(conn, request.model_copy(update={"view": "products", "limit": 1}))
        from corpus_structure.semantic.metadata import table

        record_reader = published_record_reader(conn, ProductReference(
            request.task_id, request.product_key, request.content_digest))
        if record_reader is not None:
            temporary = destination.with_name(destination.name + ".partial")
            try:
                with temporary.open("xb") as sink:
                    receipt = (record_reader.write_integrated_json(sink, binding=binding)
                               if format == "integrated-json" else record_reader.write_native_json(sink))
                manifest = destination.with_name(destination.name + ".manifest.json")
                with manifest.open("x", encoding="utf-8") as stream:
                    json.dump(dict(binding, byte_length=receipt.byte_length,
                                   serialization_sha256=receipt.serialization_sha256,
                                   logical_digest=request.content_digest,
                                   projection="integrated-document" if format == "integrated-json" else "docling-content-only",
                                   omissions=[] if format == "integrated-json" else ["mandatory evidence companions"]), stream)
                    stream.write("\n")
                os.link(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
            return
        products = table("ops.pdf_selected_product")
        native = conn.execute(
            select(products.c.native_json.cast(Text)).where(
                products.c.task_id == request.task_id,
                products.c.product_key == request.product_key,
                products.c.content_digest == request.content_digest,
            )
        ).scalar_one()
        if format == "integrated-json":
            from corpus_structure.semantic.pdf_storage import read_pdf_product

            bundle = read_pdf_product(
                conn,
                task_id=request.task_id,
                product_key=request.product_key,
                content_digest=request.content_digest,
                limit=1,
                include_body=True,
            )
            if bundle["identity"]["kind"] != "integrated":
                raise ValueError("integrated JSON export requires an integrated product")
            native = json.dumps(
                to_jsonable_python(dict(binding=binding, product=bundle["body"])),
                ensure_ascii=False,
            )
        else:
            manifest = destination.with_name(destination.name + ".manifest.json")
            with manifest.open("x", encoding="utf-8") as stream:
                json.dump(
                    dict(
                        binding,
                        projection="docling-content-only",
                        omissions=[
                            "integration decisions",
                            "alternative observations",
                            "coverage",
                            "input provenance",
                        ],
                    ),
                    stream,
                    ensure_ascii=False,
                )
                stream.write("\n")
        temporary = destination.with_name(destination.name + ".partial")
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(native)
            stream.write("\n")
        os.link(temporary, destination)
        temporary.unlink()
        return
    if format not in {"jsonl", "parquet"}:
        raise ValueError("unsupported native export format")
    import pyarrow as pa
    import pyarrow.parquet as pq

    if request.view not in {"items", "sections"}:
        raise ValueError("streaming native export requires items or sections")
    response = inspect_native_source(conn, request)
    # Existing typed SQL projection determines Arrow types, retaining the original text.
    from corpus_structure.schema.interchange import _sql_arrow
    from corpus_structure.semantic.metadata import table

    relation = published_native_table(conn)
    derivation = table("kb.native_document_derivation")
    products, builds = table("ops.pdf_selected_product"), table("ops.source_build")
    source = conn.execute(
        select(
            builds.c.artifact_digest,
            products.c.parent_task_id,
            products.c.parent_product_key,
            products.c.parent_digest,
        )
        .join(products, products.c.task_id == builds.c.task_id)
        .where(
            products.c.task_id == request.task_id,
            products.c.product_key == request.product_key,
            products.c.content_digest == request.content_digest,
        )
    ).one()
    parent = (
        None
        if source.parent_task_id is None
        else dict(
            task_id=source.parent_task_id,
            product_key=source.parent_product_key,
            content_digest=source.parent_digest,
        )
    )
    schema = pa.schema(
        [
            pa.field(c.name, _sql_arrow(c.type), nullable=bool(c.nullable))
            for c in relation.columns
            if c.name != "native_json"
        ]
        + [
            pa.field("content_digest", pa.string(), nullable=False),
            pa.field("companion_binding", pa.string(), nullable=False),
            pa.field("name", pa.string()),
            pa.field("artifact_digest", pa.string(), nullable=False),
            pa.field(
                "parent_product",
                pa.struct(
                    [
                        pa.field("task_id", pa.int64()),
                        pa.field("product_key", pa.string()),
                        pa.field("content_digest", pa.string()),
                    ]
                ),
            ),
            pa.field("native_json", pa.json_(pa.string())),
            pa.field(
                "derivation_mappings",
                pa.list_(
                    pa.struct(
                        [
                            pa.field(c.name, _sql_arrow(c.type), nullable=bool(c.nullable))
                            for c in derivation.columns
                        ]
                    )
                ),
            ),
            pa.field(
                "regions",
                pa.list_(
                    pa.struct(
                        [
                            pa.field("region_index", pa.int64()),
                            pa.field("page_no", pa.int64()),
                            *[
                                pa.field(n, pa.float64())
                                for n in (
                                    "page_width",
                                    "page_height",
                                    "left",
                                    "top",
                                    "right",
                                    "bottom",
                                )
                            ],
                            pa.field("origin", pa.string()),
                        ]
                    )
                ),
            ),
        ]
    )
    schema = schema.with_metadata(
        {
            b"source_selection": request.model_dump_json().encode(),
            b"source_contract": json.dumps(binding).encode(),
        }
    )
    temporary = destination.with_name(destination.name + ".partial")
    with temporary.open("xb") as stream:
        writer = (
            pq.ParquetWriter(stream, schema, store_schema=True) if format == "parquet" else None
        )
        try:
            selected = request
            while True:
                pointers = [row["pointer"] for row in response.rows]
                region = published_native_table(conn, "region")
                by_pointer = defaultdict(list)
                for r in conn.execute(
                    select(region).where(
                        region.c.task_id == request.task_id,
                        region.c.product_key == request.product_key,
                        region.c.pointer.in_(pointers),
                    )
                ).mappings():
                    by_pointer[r["pointer"]].append(
                        {
                            n: (
                                float(r[n])
                                if n
                                in {"page_width", "page_height", "left", "top", "right", "bottom"}
                                else r[n]
                            )
                            for n in (
                                "region_index",
                                "page_no",
                                "page_width",
                                "page_height",
                                "left",
                                "top",
                                "right",
                                "bottom",
                                "origin",
                            )
                        }
                    )
                native = {
                    r.pointer: r.native_json
                    for r in conn.execute(
                        select(relation.c.pointer, relation.c.native_json).where(
                            relation.c.task_id == request.task_id,
                            relation.c.product_key == request.product_key,
                            relation.c.pointer.in_(pointers),
                        )
                    )
                }
                mappings = defaultdict(list)
                for row in conn.execute(
                    select(derivation)
                    .where(
                        derivation.c.task_id == request.task_id,
                        derivation.c.product_key == request.product_key,
                        derivation.c.pointer.in_(pointers),
                    )
                    .order_by(derivation.c.pointer, derivation.c.mapping_index)
                ).mappings():
                    mappings[row["pointer"]].append(dict(row))
                rows = [
                    dict(
                        row,
                        content_digest=request.content_digest,
                        companion_binding=json.dumps(binding),
                        name=native[row["pointer"]].get("name"),
                        artifact_digest=source.artifact_digest,
                        parent_product=parent,
                        derivation_mappings=mappings[row["pointer"]],
                        native_json=json.dumps(
                            native[row["pointer"]], ensure_ascii=False, allow_nan=False
                        ),
                        regions=sorted(by_pointer[row["pointer"]], key=lambda r: r["region_index"]),
                    )
                    for row in response.rows
                ]
                if writer is not None:
                    writer.write_batch(pa.RecordBatch.from_pylist(rows, schema=schema))
                else:
                    for row in rows:
                        stream.write(
                            (json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n").encode()
                        )
                if response.next_cursor is None:
                    break
                selected = selected.model_copy(update={"cursor": response.next_cursor})
                response = inspect_native_source(conn, selected)
        finally:
            if writer is not None:
                writer.close()
    os.link(temporary, destination)
    temporary.unlink()
