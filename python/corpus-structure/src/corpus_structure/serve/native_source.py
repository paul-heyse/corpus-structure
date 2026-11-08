"""Versioned, source-qualified native reads without converter/model initialization."""

from __future__ import annotations

import base64
import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from pydantic_core import to_jsonable_python
from sqlalchemy import Connection, select

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin, VisualEvidenceRead


class NativeSourceRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[4] = 4
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
        "visual_evidence",
    ] = "items"
    section_pointer: str | None = None
    membership: Literal["direct", "descendants"] | None = None
    pointer: str | None = None
    cell_index: int | None = Field(default=None, ge=0)
    occurrence_id: str | None = None
    artifact_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    collection: Literal["inputs", "coverage", "relations", "mapping_reports"] | None = None
    evidence: VisualEvidencePin | None = Field(default=None, exclude_if=lambda value: value is None)
    page_no: int | None = Field(default=None, gt=0, exclude_if=lambda value: value is None)
    region_index: int | None = Field(default=None, ge=0, exclude_if=lambda value: value is None)
    cursor: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    max_rows: int = Field(default=10000, strict=True, ge=1, le=10000)
    max_bytes: int = Field(default=1024 * 1024, strict=True, ge=1, le=8 * 1024 * 1024)

    @model_validator(mode="after")
    def qualified_selection(self):
        if self.view == "visual_evidence":
            if (
                self.evidence is None
                or (self.page_no is None and self.pointer is None)
                or (self.region_index is not None and self.pointer is None)
                or any(
                    value is not None
                    for value in (
                        self.section_pointer,
                        self.membership,
                        self.cell_index,
                        self.occurrence_id,
                        self.collection,
                    )
                )
            ):
                raise ValueError(
                    "visual evidence requires an exact observation pin and page/item scope"
                )
            if self.artifact_digest is not None and self.pointer is not None:
                raise ValueError("visual evidence artifacts require their submitted page scope")
            return self
        if any(value is not None for value in (self.evidence, self.page_no, self.region_index)):
            raise ValueError("evidence, page and region selectors require the visual evidence view")
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
    version: Literal[4] = 4
    selection: NativeSourceRequest
    release_id: str
    outcome: Literal["source_ready", "missing", "invalid", "unsupported"] = "source_ready"
    health: dict[str, JsonValue]
    rows: list[dict[str, JsonValue]]
    next_cursor: str | None = None
    population_complete: bool = True
    companion: dict[str, JsonValue] | None = None
    visual_evidence: VisualEvidenceRead | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


def _source_cursor(request, after):
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.query import ReadLimit

    token = base64.urlsafe_b64encode(
        canonical_bytes(dict(cursor_version=4, selection=request.selection_digest(), after=after))
    ).decode("ascii")
    if len(token.encode("ascii")) > 8192:
        raise ReadLimit("native source cursor exceeds 8192 bytes", reason="oversized_item")
    return token


def _source_position(request):
    from corpus_structure.semantic.refusals import InvalidContinuation

    try:
        if len(request.cursor.encode("utf-8")) > 8192:
            raise ValueError("oversized cursor")
        body = json.loads(base64.b64decode(request.cursor, altchars=b"-_", validate=True))
        if (
            set(body) != {"cursor_version", "selection", "after"}
            or type(body["cursor_version"]) is not int
            or body["cursor_version"] != 4
            or body["selection"] != request.selection_digest()
        ):
            raise ValueError("cursor version or selection differs")
        return body["after"]
    except (ValueError, TypeError, KeyError) as error:
        raise InvalidContinuation(
            "invalid native source continuation", reason="invalid_continuation"
        ) from error


def _published_derivations(reader, pointers):
    """Translate the declared retained mapping family into the existing export shape."""
    for row in reader.selected_item_reports(pointers, kinds=("derivation_mappings",)):
        body = row["body"]
        if body["kind"] != "derivation_mappings":
            continue
        mapping = body["value"]
        yield dict(
            task_id=reader.reference.task_id,
            product_key=reader.reference.product_key,
            pointer=mapping["pointer"],
            mapping_index=body["ordinal"],
            origin_pointer=mapping["origin_pointer"],
            source_field=mapping["source_field"],
            start_offset=mapping["start"],
            end_offset=mapping["end"],
            cell_index=mapping.get("cell_index"),
            kind=mapping["kind"],
        )


def _published_alignment_reports(reader, pointer):
    """Absent retained diagnostics are unavailable, distinct from a matching empty set."""
    if not reader.has_native_metadata("inline_alignment_reports"):
        return None
    reports = [
        row["body"]["value"]
        for row in reader.selected_item_reports((pointer,), kinds=("inline_alignment_reports",))
        if row["body"]["kind"] == "inline_alignment_reports"
    ]
    bases = reader.candidate_bases(
        [(report["page_no"], report["candidate_index"]) for report in reports]
    )
    return [
        dict(report, candidate_basis=bases[report["page_no"], report["candidate_index"]])
        for report in reports
    ]


def _published_parent_product(reader):
    """The structural input owns original prose custody for retained diagnostics."""
    parents = [row for row in reader.iter_companions("input") if row.get("role") == "structural"]
    if len(parents) > 1:
        raise ValueError("native product structural input is ambiguous")
    if not parents:
        return None
    return {key: parents[0][key] for key in ("task_id", "product_key", "content_digest")}


def _cell_companion(reader, request: NativeSourceRequest, *, row_budget: int):
    """Complete selected-cell and parent custody, excluding sibling cell occurrences."""
    if reader.product_kind() == "native":
        return None
    from corpus_structure.semantic.pdf_storage import NativeDocumentUnavailable

    pointer = request.pointer
    if pointer is None or request.cell_index is None:
        raise ValueError("cell custody requires one native cell selector")
    if pointer.startswith("#/tables/"):
        address = pointer + "/data/table_cells/" + str(request.cell_index)
        parent_kind = "item"
    elif pointer.startswith("#/pictures/"):
        address = pointer + "/meta/tabular_chart/chart_data/table_cells/" + str(request.cell_index)
        parent_kind = "chart"
    else:
        raise NativeDocumentUnavailable("cell pointer has no declared native table/chart address")
    selected = [
        reader._one("companion", {"family": "occurrence", "local_id": address}),
        reader._one("companion", {"family": "occurrence", "local_id": pointer}),
    ]
    cell, parent = (reader.decode_companion_row(row) for row in selected)
    if (
        cell.get("kind") != "cell"
        or cell.get("pointer") != pointer
        or cell.get("cell_index") != request.cell_index
        or cell.get("occurrence_id") != address
        or parent.get("kind") != parent_kind
        or parent.get("pointer") != pointer
        or parent.get("occurrence_id") != pointer
    ):
        raise NativeDocumentUnavailable(
            "selected cell/parent occurrence differs from native selector"
        )
    return reader.occurrence_context(
        selected, request.section_pointer or "#/body", row_budget=row_budget
    )


def inspect_native_source(
    conn: Connection,
    request: NativeSourceRequest,
    *,
    cancellation: BorrowerCancellation | None = None,
) -> NativeSourceResponse:
    """Finish a selected read before releasing its cancellation registration."""
    cancellation = cancellation or BorrowerCancellation()
    with cancellation.borrow(conn):
        from corpus_structure.semantic.identity import canonical_bytes
        from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
        from corpus_structure.semantic.query import ReadLimit

        budget = PublishedReadBudget(request.max_rows, request.max_bytes)
        response = _inspect_native_source(
            conn, request, cancellation=cancellation, read_budget=budget
        )
        response = response.model_copy(update={"population_complete": response.next_cursor is None})
        if len(canonical_bytes(response.model_dump(mode="json"))) > request.max_bytes:
            raise ReadLimit(
                "complete native source envelope exceeds max_bytes", reason="oversized_item"
            )
        cancellation.check_active()
        return response


def _published_native_header(reader, origin_run: int, *, runtime: bool):
    """Read only bounded native health and requested runtime bytes under the exact pin."""
    from contextlib import closing
    from itertools import islice

    with closing(reader.iter_rows("companion", {"family": "health"}, batch_size=3)) as rows:
        health_rows = [reader.decode_companion_row(row) for row in islice(rows, 3)]
    native_health = [row for row in health_rows if "source_scope" in row]
    if len(health_rows) > 2 or len(native_health) != 1:
        raise ValueError("published native health is unavailable or ambiguous")
    runtime_report = None
    if runtime:
        with closing(reader.native_metadata("runtime_report")) as rows:
            reports = list(islice(rows, 2))
        if len(reports) > 1:
            raise ValueError("published runtime metadata is ambiguous")
        if reports:
            runtime_report = reports[0]
    return SimpleNamespace(
        release_id=reader.revision["release_id"],
        content_digest=reader.revision["logical_digest"],
        artifact_digest=reader.revision["source_digest"],
        origin_run=origin_run,
        page_start=native_health[0].get("page_start"),
        page_end=native_health[0].get("page_end"),
        health={
            key: value
            for key, value in native_health[0].items()
            if key not in {"source_scope", "page_start", "page_end", "formula_outcomes"}
        },
        runtime_report=runtime_report,
    )


def _inspect_native_source(
    conn: Connection,
    request: NativeSourceRequest,
    *,
    cancellation: BorrowerCancellation,
    read_budget,
) -> NativeSourceResponse:
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_record_reader import (
        published_record_reader,
    )
    from corpus_structure.semantic.pdf_storage import read_native_items, read_native_regions

    runs, tasks = map(table, ("ops.run", "ops.task"))
    run = conn.execute(
        select(runs.c.project_id, runs.c.release_id).where(runs.c.id == request.run_id)
    ).one_or_none()
    if run is None:
        raise ValueError("unknown native source run")
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_release
    from corpus_structure.semantic.releases import open_release

    projection_context = open_release(conn, run.release_id)
    context = pdf_context_for_release(conn, projection_context)
    context.execution.require_operation("read_native_source")
    if request.view == "visual_evidence":
        from corpus_structure.serve.pdf_visual_evidence import inspect_pdf_visual_evidence

        return inspect_pdf_visual_evidence(
            conn,
            request,
            project_id=run.project_id,
            projection_context=projection_context,
            cancellation=cancellation,
            read_budget=read_budget,
        )
    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context

    trusted_pdf_context().boundary.validate_json(
        "PdfNativeReadRequest", request.model_dump_json(exclude_none=True)
    )
    if request.view in {"companion", "manifest", "artifact"} or (
        request.view == "trace" and request.occurrence_id is not None
    ):
        return _inspect_companion(
            conn,
            request,
            run.project_id,
            cancellation=cancellation,
            projection_context=projection_context,
            read_budget=read_budget,
        )
    pin = dict(
        task_id=request.task_id,
        product_key=request.product_key,
        content_digest=request.content_digest,
    )
    published = published_record_reader(
        conn,
        ProductReference(**pin),
        cancellation=cancellation,
        projection_context=projection_context,
        read_budget=read_budget,
    )
    if published is None:
        raise ValueError("native source requires a current published record")
    origin = runs.alias("native_origin_run")
    origin_run = conn.execute(
        select(tasks.c.run_id)
        .join(origin, origin.c.id == tasks.c.run_id)
        .where(tasks.c.id == request.task_id, origin.c.project_id == run.project_id)
    ).scalar_one_or_none()
    if origin_run is None:
        raise ValueError("native source is unavailable in the requested project")
    header = _published_native_header(published, origin_run, runtime=request.view == "products")
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
        after = _source_position(request)
        if type(after) is not int:
            from corpus_structure.semantic.refusals import InvalidContinuation

            raise InvalidContinuation(
                "invalid native ordinal continuation", reason="invalid_continuation"
            )
    parent_product = _published_parent_product(published)
    # The storage reader checks the admitted archive even for metadata-only selections.
    if request.view in {"products", "sections"}:
        published._native_schema_mapping()
        rows = []
    else:
        rows = read_native_items(
            conn,
            **pin,
            section_pointer=request.section_pointer,
            membership=request.membership or "direct",
            pointer=request.pointer,
            after=after,
            limit=request.limit,
            projection_context=projection_context,
            read_budget=read_budget,
            _reader=published,
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
        selected = published.sections(
            after=after,
            section_pointer=request.section_pointer,
            membership=request.membership or "direct",
            limit=request.limit + 1,
        )
        more = len(selected) > request.limit
        selected = selected[: request.limit]
        rows = [
            dict(
                task_id=request.task_id,
                product_key=request.product_key,
                **{key: value for key, value in row.items() if key != "ancestors"},
            )
            for row in selected
        ]
        if more:
            next_cursor = _source_cursor(request, rows[-1]["ordinal"])
    elif request.view in {"item", "formula", "cell", "regions", "trace"}:
        if request.pointer is None or len(rows) != 1:
            raise ValueError("native occurrence inspection requires one existing pointer")
        alignment = []
        if request.view in {"item", "formula", "trace"}:
            alignment = _published_alignment_reports(published, request.pointer)
        for report in alignment or ():
            report["source_product"] = parent_product
        if request.view in {"regions", "trace"}:
            rows = read_native_regions(
                conn,
                **pin,
                pointer=request.pointer,
                projection_context=projection_context,
                read_budget=read_budget,
            )
            if request.view == "trace":
                mappings = (
                    list(_published_derivations(published, (request.pointer,)))
                    if published.has_native_metadata("derivation_mappings")
                    else None
                )
                rows = [
                    dict(
                        pointer=request.pointer,
                        artifact_digest=header.artifact_digest,
                        space="pdf_points",
                        regions=rows,
                        parent_product=parent_product,
                        derivation_mappings=mappings,
                        inline_alignment_reports=alignment,
                    )
                ]
        else:
            # Transfer only the selected native object, not its containing document.
            native = published.selected_native_items((request.pointer,))[request.pointer]
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
                matches = [
                    row["body"]["value"]
                    for row in published.selected_item_reports(
                        (request.pointer,), kinds=("cell_reports",)
                    )
                    if row["body"]["kind"] == "cell_reports"
                    and row["body"]["value"]["cell_index"] == request.cell_index
                ]
                if len(matches) > 1:
                    raise ValueError("cell recognition report is ambiguous")
                report = matches[0] if matches else None
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
                outcomes = list(
                    published.native_metadata("formula_outcomes", pointer=request.pointer)
                )
                if len(outcomes) > 1:
                    raise ValueError("formula outcome metadata is ambiguous")
                health = outcomes[0] if outcomes else {"outcome": "unknown"}
                rows = [
                    dict(
                        pointer=request.pointer,
                        original_text=native.get("orig"),
                        recognized_latex=native.get("text"),
                        recognition=health,
                        inline_alignment_reports=alignment,
                        interpretation=_recorded_interpretations(
                            conn, request, read_budget=read_budget
                        ),
                        regions=read_native_regions(
                            conn,
                            **pin,
                            pointer=request.pointer,
                            projection_context=projection_context,
                            read_budget=read_budget,
                        ),
                    )
                ]
            else:
                rows = [dict(rows[0], native=native, inline_alignment_reports=alignment)]
    if request.view == "items" and len(rows) == request.limit:
        last_ordinal = rows[-1]["ordinal"]
        if type(last_ordinal) is not int:
            raise ValueError("native item cursor requires an integer ordinal")
        following = read_native_items(
            conn,
            **pin,
            section_pointer=request.section_pointer,
            membership=request.membership or "direct",
            pointer=request.pointer,
            after=last_ordinal,
            limit=1,
            projection_context=projection_context,
            read_budget=read_budget,
            _reader=published,
        )
        if following:
            next_cursor = _source_cursor(request, last_ordinal)
    from corpus_structure.semantic.pdf_storage import integrated_source_context

    if request.view == "cell":
        companion = _cell_companion(published, request, row_budget=request.max_rows)
    else:
        companion = integrated_source_context(
            conn,
            **pin,
            pointers=[request.pointer]
            if request.pointer is not None
            else [pointer for row in rows if isinstance(pointer := row.get("pointer"), str)],
            section_pointer=request.section_pointer or "#/body",
            membership=request.membership or "direct",
            cancellation=cancellation,
            read_budget=read_budget,
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
    conn: Connection,
    request: NativeSourceRequest,
    project_id: int,
    *,
    cancellation: BorrowerCancellation,
    projection_context,
    read_budget,
) -> NativeSourceResponse:
    """Authorize the exact selected graph before reading retained companion/observation data."""
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_record_reader import (
        published_record_reader,
    )
    from corpus_structure.semantic.pdf_storage import (
        read_pdf_manifest,
        read_pdf_product,
        selected_native_ancestry,
        trace_pdf_occurrence,
    )

    products, tasks, runs, bodies = map(
        table, ("ops.pdf_product", "ops.task", "ops.run", "ops.pdf_product_body")
    )
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
        select(
            products.c.release_id,
            bodies.c.descriptor["observation"]["pass_role"].astext.label("pass_role"),
        )
        .join(tasks, tasks.c.id == products.c.task_id)
        .join(runs, runs.c.id == tasks.c.run_id)
        .outerjoin(
            bodies,
            (bodies.c.task_id == products.c.task_id)
            & (bodies.c.product_key == products.c.product_key),
        )
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
    if row.pass_role in {"chandra_page", "chandra_crop"}:
        raise ValueError("Chandra observation inspection requires the visual evidence selection")
    after = ""
    if request.cursor is not None:
        after = _source_position(request)
        if not isinstance(after, str):
            from corpus_structure.semantic.refusals import InvalidContinuation

            raise InvalidContinuation(
                "invalid native companion continuation", reason="invalid_continuation"
            )
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
            conn,
            **pin,
            artifact_digest=request.artifact_digest,
            offset=offset,
            cancellation=cancellation,
            read_budget=read_budget,
        )
        following = result.pop("next_offset")
        content = result.pop("content")
        result.update(
            encoding="base64",
            data=base64.b64encode(content).decode(),
            length=len(content),
            next_offset=following,
        )
        continuation = None if following is None else _source_cursor(request, str(following))
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
            conn,
            **pin,
            occurrence_id=request.occurrence_id,
            limit=request.limit,
            cancellation=cancellation,
            read_budget=read_budget,
        )
    elif request.view == "manifest":
        if request.collection is None:
            raise ValueError("manifest inspection requires a named collection")
        result = read_pdf_manifest(
            conn,
            **pin,
            collection=request.collection,
            after=after,
            limit=request.limit,
            cancellation=cancellation,
            read_budget=read_budget,
        )
    else:
        pointers = None
        if request.pointer is not None:
            pointers = [request.pointer]
        elif request.section_pointer is not None:
            published = published_record_reader(
                conn,
                ProductReference(**pin),
                cancellation=cancellation,
                projection_context=projection_context,
                read_budget=read_budget,
            )
            if published is None:
                raise ValueError("native section requires a current published record")
            pointers = [
                node["pointer"]
                for node in published.section_nodes(
                    request.section_pointer, request.membership or "direct"
                )
                if node["role"] == "selected"
            ]
        result = read_pdf_product(
            conn,
            **pin,
            occurrence_id=request.occurrence_id,
            pointers=pointers,
            section_pointer=request.section_pointer,
            after=after,
            limit=request.limit,
            row_budget=request.max_rows,
            cancellation=cancellation,
            read_budget=read_budget,
        )
    continuation = result.get("cursor")
    next_cursor = None if continuation is None else _source_cursor(request, continuation)

    return NativeSourceResponse(
        selection=request,
        release_id=row.release_id,
        health={},
        rows=[to_jsonable_python(result)],
        next_cursor=next_cursor,
    )


def _recorded_interpretations(
    conn: Connection, request: NativeSourceRequest, *, read_budget=None
) -> dict:
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
    reader = BoundReader(
        conn, request.run_id, open_release(conn, release), analysis=False, read_budget=read_budget
    )
    results = []
    views, selection = table("kb.source_view"), table("ops.run_source_view")
    newer = selection.alias("newer_analysis_selection")
    view_query = (
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
    )
    if read_budget is not None:
        read_budget.preflight(conn, view_query)
    view_ids = tuple(conn.execute(view_query).scalars())
    if read_budget is not None:
        read_budget.value(view_ids)
    from corpus_structure.semantic.native_analysis import stored_native_analysis

    for view_id in view_ids:
        analysis = stored_native_analysis(reader, view_id, request.pointer)[request.pointer]
        reference = reader.source_view_ref(view_id)
        requests = []
        for observation in reader.source_observations_for_ref(
            reference, "native.source_request", ObservationKind.RECORD
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


NativeExportFormat = Literal[
    "jsonl", "parquet", "docling-json", "integrated-json", "selected-source-v1"
]


def _export_native_source(
    conn: Connection,
    request: NativeSourceRequest,
    destination,
    *,
    format: NativeExportFormat = "parquet",
    settings=None,
    cancellation: BorrowerCancellation,
) -> None:
    """Export a pinned projection or explicitly requested complete native document."""
    import os
    from collections import defaultdict
    from pathlib import Path

    from corpus_structure.semantic.pdf_record_reader import published_record_reader

    destination = Path(destination)
    if format == "selected-source-v1":
        from .selected_source import export_selected_native_source

        if settings is None:
            raise ValueError("selected-source-v1 requires the owned runtime settings")
        export_selected_native_source(request, destination, settings)
        return
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
        inspect_native_source(
            conn,
            request.model_copy(update={"view": "products", "limit": 1}),
            cancellation=cancellation,
        )
        from corpus_structure.semantic.metadata import table

        record_reader = published_record_reader(
            conn,
            ProductReference(request.task_id, request.product_key, request.content_digest),
            cancellation=cancellation,
        )
        if record_reader is None:
            raise ValueError("native export requires a current published record")
        temporary = destination.with_name(destination.name + ".partial")
        try:
            with temporary.open("xb") as sink:
                receipt = (
                    record_reader.write_integrated_json(sink, binding=binding)
                    if format == "integrated-json"
                    else record_reader.write_native_json(sink)
                )
            manifest = destination.with_name(destination.name + ".manifest.json")
            with manifest.open("x", encoding="utf-8") as stream:
                json.dump(
                    dict(
                        binding,
                        byte_length=receipt.byte_length,
                        serialization_sha256=receipt.serialization_sha256,
                        logical_digest=request.content_digest,
                        projection="integrated-document"
                        if format == "integrated-json"
                        else "docling-content-only",
                        omissions=[]
                        if format == "integrated-json"
                        else ["mandatory evidence companions"],
                    ),
                    stream,
                )
                stream.write("\n")
            cancellation.check_active()
            os.link(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return
    if format not in {"jsonl", "parquet"}:
        raise ValueError("unsupported native export format")
    import pyarrow as pa
    import pyarrow.parquet as pq

    if request.view not in {"items", "sections"}:
        raise ValueError("streaming native export requires items or sections")
    response = inspect_native_source(conn, request, cancellation=cancellation)
    # Existing typed SQL projection determines Arrow types, retaining the original text.
    from corpus_structure.schema.interchange import _sql_arrow
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.releases import open_release

    runs = table("ops.run")
    projection_context = open_release(
        conn,
        conn.execute(select(runs.c.release_id).where(runs.c.id == request.run_id)).scalar_one(),
    )
    published = published_record_reader(
        conn,
        ProductReference(request.task_id, request.product_key, request.content_digest),
        cancellation=cancellation,
        projection_context=projection_context,
    )
    if published is None:
        raise ValueError("native source requires a current published record")
    has_derivations = published.has_native_metadata("derivation_mappings")
    # This is the public export shape; placement coordinates remain private to its reader.
    relation = table("ops.pdf_published_item")
    derivation = table("ops.pdf_published_derivation")
    source = _published_native_header(published, request.run_id, runtime=False)
    parent = _published_parent_product(published)
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
                cancellation.check_active()
                pointers: list[str] = []
                for row in response.rows:
                    pointer = row["pointer"]
                    if not isinstance(pointer, str):
                        raise ValueError("native export row requires its string pointer")
                    pointers.append(pointer)
                by_pointer = defaultdict(list)
                region_rows = published.selected_regions(pointers)
                native = published.selected_native_items(pointers)
                for r in region_rows:
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
                mappings = defaultdict(list)
                mapping_rows = _published_derivations(published, pointers)
                for row in mapping_rows:
                    mappings[row["pointer"]].append(dict(row))
                rows = [
                    dict(
                        row,
                        content_digest=request.content_digest,
                        companion_binding=json.dumps(binding),
                        name=native[row["pointer"]].get("name"),
                        artifact_digest=source.artifact_digest,
                        parent_product=parent,
                        derivation_mappings=mappings[row["pointer"]] if has_derivations else None,
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
                        cancellation.check_active()
                        stream.write(
                            (json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n").encode()
                        )
                if response.next_cursor is None:
                    break
                selected = selected.model_copy(update={"cursor": response.next_cursor})
                response = inspect_native_source(conn, selected, cancellation=cancellation)
        finally:
            if writer is not None:
                writer.close()
    os.link(temporary, destination)
    temporary.unlink()


def export_native_source(
    conn: Connection,
    request: NativeSourceRequest,
    destination,
    *,
    format: NativeExportFormat = "parquet",
    settings=None,
    cancellation: BorrowerCancellation | None = None,
) -> None:
    """Publish a complete selected export after sink closure and cancellation checks.

    The caller owns snapshot settlement; pass this same token to read_snapshot to
    keep native cancellation registered through transaction exit.
    """
    from tempfile import TemporaryDirectory

    cancellation = cancellation or BorrowerCancellation()
    cancellation.check_active()
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if format == "selected-source-v1":
        from .selected_source import export_selected_native_source

        if settings is None:
            raise ValueError("selected-source-v1 requires the owned runtime settings")
        export_selected_native_source(request, destination, settings, cancellation=cancellation)
        return
    with (
        cancellation.borrow(conn),
        TemporaryDirectory(prefix=".pdf-export-", dir=destination.parent) as directory,
    ):
        staged = Path(directory) / destination.name
        _export_native_source(
            conn, request, staged, format=format, settings=settings, cancellation=cancellation
        )
        cancellation.check_active()
        _publish_native_export(staged, destination, cancellation=cancellation)


def _publish_native_export(
    staged: Path, destination: Path, *, cancellation: BorrowerCancellation
) -> None:
    """No-replace publication after the caller's required resource settlement."""
    import os

    cancellation.check_active()
    staged_manifest = staged.with_name(staged.name + ".manifest.json")
    manifest = destination.with_name(destination.name + ".manifest.json")
    linked_manifest = False
    try:
        if staged_manifest.exists():
            os.link(staged_manifest, manifest)
            linked_manifest = True
        cancellation.check_active()
        os.link(staged, destination)
    except BaseException:
        if linked_manifest:
            manifest.unlink()
        raise
