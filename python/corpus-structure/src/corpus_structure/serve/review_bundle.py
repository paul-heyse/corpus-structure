"""Declared-scope portable review over pinned retained products.

The bundle is a detached reading, not admission or original-document completeness.
Public capture never opens an evaluator connection. Authorized assessment owners may
supply separately captured relations; callers retain responsibility for exposure.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict
from hashlib import file_digest, sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select

from corpus_structure.core.db.cancellation import OperationCancellation
from corpus_structure.semantic.capture_storage import LogicalRows
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view, selected_source_views
from corpus_structure.serve.companion_export import _publish_directory
from corpus_structure.serve.contributions import ContributionRequest, _contributions
from corpus_structure.serve.structural_products import (
    StructuralExportRequest,
    read_structural_export_page,
)
from corpus_structure.settings import Settings

FORMAT = "progressive-review-bundle-1"
_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class ReviewComparison(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    baseline_evaluation_id: int = Field(strict=True, gt=0)
    revised_evaluation_id: int = Field(strict=True, gt=0)


class ReviewSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    selections: tuple[ContributionRequest, ...] = ()
    structural_selections: tuple[StructuralExportRequest, ...] = ()
    selected_evaluation_ids: tuple[int, ...] = ()
    comparisons: tuple[ReviewComparison, ...] = ()
    completeness: Literal["selected_source_closure", "inventory"] = "selected_source_closure"
    max_bytes: int = Field(default=134_217_728, strict=True, gt=0)
    max_source_rows: int = Field(default=100_000, strict=True, gt=0)

    @model_validator(mode="after")
    def full_selections(self):
        if not self.selections and not self.structural_selections:
            raise ValueError("review requires a contribution or structural selection")
        if any(item.after_task_id for item in self.structural_selections):
            raise ValueError("structural review cannot begin after a task")
        if len(set(self.selected_evaluation_ids)) != len(self.selected_evaluation_ids) or any(
            type(value) is not int or value < 1 for value in self.selected_evaluation_ids
        ):
            raise ValueError("selected evaluations must have distinct positive identifiers")
        if any(item.cursor is not None for item in self.selections):
            raise ValueError("review selection cannot begin at a continuation")
        identities = [canonical_bytes(item.selection()) for item in self.selections]
        if len(identities) != len(set(identities)):
            raise ValueError("review selections must be distinct")
        return self


def _json(value: Any) -> Any:
    from pydantic_core import to_jsonable_python

    return json.loads(canonical_bytes(to_jsonable_python(value)))


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def _contract_row(prepared):
    return {
        "release_id": prepared.release_id,
        "definitions": [asdict(value) for value in prepared.definitions],
        "registry_rows": [
            {
                "kind": value.kind,
                "name": value.name,
                "body_base64": base64.b64encode(value.body).decode(),
            }
            for value in prepared.registry_rows
        ],
    }


def capture_review_relations(conn, selection: ReviewSelection, cancellation: OperationCancellation):
    """One caller-owned snapshot; shared source and report objects captured once.

    Existing inventory admission is bounded before hydration. Source closure has a
    separate cumulative native-read budget and never initializes analytical layout.
    """
    seen_reports: set[int] = set()
    seen_sources: set[int] = set()
    coordinate_versions: dict[int, int] = {}
    seen_releases: set[str] = set()
    seen_documents: set[int] = set()
    seen_producers: set[int] = set()
    validated_external: set[str] = set()
    predecessor_readers = {}
    origin_metadata = {}
    budget = PublishedReadBudget(selection.max_source_rows, selection.max_bytes)
    for index, original in enumerate(selection.selections):
        cancellation.check_active()
        request = original.model_copy(update={"include_details": True})
        page = _contributions(conn, request, paginate=False)
        run = table("ops.run")
        project_id = conn.scalar(select(run.c.project_id).where(run.c.id == original.run_id))
        yield (
            "selections",
            {
                "selection_index": index,
                "project_id": project_id,
                **page.model_dump(exclude={"items"}),
            },
        )
        session = bind_completed_result(conn, original.run_id)
        if session.binding.release_id not in seen_releases:
            seen_releases.add(session.binding.release_id)
            yield "contracts", _contract_row(session.prepared)
        source_ids: set[int] = set()
        report_ids: set[int] = set()
        for item in page.items:
            row = item["row"]
            if not isinstance(row, dict):
                raise SemanticRefusal("review inventory row must be an object")
            origin_id = row.get("origin_task_id")
            if type(origin_id) is int and selection.completeness == "selected_source_closure":
                if origin_id not in origin_metadata:
                    tasks, producer = table("ops.task"), table("ops.run")
                    origin_metadata[origin_id] = dict(
                        conn.execute(
                            select(
                                tasks.c.run_id.label("origin_run_id"),
                                producer.c.project_id.label("origin_project_id"),
                                producer.c.runtime_id.label("runtime_fingerprint"),
                            )
                            .join(producer, producer.c.id == tasks.c.run_id)
                            .where(tasks.c.id == origin_id)
                        )
                        .mappings()
                        .one()
                    )
                row = {**row, **origin_metadata[origin_id]}
            yield "inventory", {"selection_index": index, **item, "row": row}
            if isinstance(row.get("source_view_id"), int):
                source_ids.add(row["source_view_id"])
            if item["population"] == "report" and isinstance(row.get("origin_task_id"), int):
                report_ids.add(row["origin_task_id"])
        if original.source_view_id is not None:
            source_ids.add(original.source_view_id)
        elif not any(
            (
                original.method,
                original.operation_key,
                original.operation_version,
                original.contribution_id,
                original.occurrence_id,
                original.kind,
            )
        ):
            # Empty source regions still belong to an unfiltered run inventory.
            source_ids.update(ref.id for ref in selected_source_views(conn, original.run_id))
        if selection.completeness == "inventory":
            continue
        permitted = {ref.id for ref in selected_source_views(conn, original.run_id)}
        if not source_ids <= permitted:
            raise SemanticRefusal("review source is outside selected run membership")
        reports = table("ops.task_result")
        task, cfg = table("ops.task"), table("ops.method_config")
        run, method = table("ops.run"), table("ops.method")
        pending_reports = set(report_ids)
        while pending_reports:
            report_id = min(pending_reports)
            pending_reports.remove(report_id)
            if report_id in seen_reports:
                continue
            seen_reports.add(report_id)
            cancellation.check_active()
            statement = (
                select(
                    reports.c.body,
                    task.c.input_hash,
                    task.c.method_config_id,
                    cfg.c.params.label("configuration"),
                    cfg.c.config_hash,
                    task.c.run_id.label("origin_run_id"),
                    task.c.unit_type,
                    task.c.unit_id.label("origin_unit_id"),
                    task.c.status.label("task_status"),
                    task.c.error.label("task_error"),
                    run.c.project_id,
                    run.c.runtime_id.label("runtime_fingerprint"),
                    method.c.name.label("method"),
                )
                .select_from(task)
                .outerjoin(reports, reports.c.task_id == task.c.id)
                .join(cfg, cfg.c.id == task.c.method_config_id)
                .join(run, run.c.id == task.c.run_id)
                .join(method, method.c.id == cfg.c.method_id)
                .where(task.c.id == report_id)
            )
            budget.preflight(conn, statement)
            report = conn.execute(statement).mappings().one_or_none()
            if report is None:
                yield (
                    "omissions",
                    {"origin_task_id": report_id, "reason": "no_retained_task_metadata"},
                )
                continue
            if report["body"] is None:
                yield (
                    "omissions",
                    {
                        "origin_task_id": report_id,
                        "reason": "no_retained_report_body; task diagnostics included separately",
                    },
                )
            budget.value(dict(report))
            if report["project_id"] != project_id and report["project_id"] != origin_metadata.get(
                report_id, {}
            ).get("origin_project_id"):
                raise SemanticRefusal("retained producer dependency belongs to another project")
            if report["unit_type"] == "source_view":
                source_ids.add(report["origin_unit_id"])
            source_ids.update(_report_source_ids(report["body"]))
            pending_reports.update(_retained_report_ids(report))
            permitted.update(ref.id for ref in selected_source_views(conn, report["origin_run_id"]))
            yield "reports", {"origin_task_id": report_id, **dict(report)}
        if not source_ids <= permitted:
            raise SemanticRefusal("raw report source is outside selected/original run membership")
        yield from _capture_sources(
            conn,
            source_ids,
            budget,
            seen_sources,
            seen_documents,
            seen_producers,
            cancellation,
            coordinate_versions=coordinate_versions,
        )
    for index, original in enumerate(selection.structural_selections):
        selected_session = bind_completed_result(conn, original.run_id)
        run = table("ops.run")
        project_id = conn.scalar(select(run.c.project_id).where(run.c.id == original.run_id))
        if selected_session.binding.release_id not in seen_releases:
            seen_releases.add(selected_session.binding.release_id)
            yield "contracts", _contract_row(selected_session.prepared)
        after = 0
        while True:
            cancellation.check_active()
            page = read_structural_export_page(
                conn,
                original.model_copy(
                    update={
                        "after_task_id": after,
                        "max_bytes": min(original.max_bytes, selection.max_bytes),
                    }
                ),
            )
            if after == 0:
                yield (
                    "structural_selections",
                    {
                        "selection_index": index,
                        "project_id": project_id,
                        "binding": {
                            "release_id": selected_session.binding.release_id,
                            "data_revision": selected_session.binding.data_revision,
                        },
                        **page.model_dump(
                            mode="json", exclude={"reports", "task_ids", "public_assertions"}
                        ),
                    },
                )
            enriched_assertions = {}
            for task_id, report in zip(page.task_ids, page.reports, strict=True):
                tasks = table("ops.task")
                origin = tasks.alias("structural_origin")
                producer = table("ops.run")
                custody = dict(
                    conn.execute(
                        select(
                            origin.c.id.label("origin_task_id"),
                            origin.c.run_id.label("origin_run_id"),
                            producer.c.project_id.label("origin_project_id"),
                            producer.c.runtime_id.label("runtime_fingerprint"),
                        )
                        .select_from(tasks)
                        .join(
                            origin, origin.c.id == func.coalesce(tasks.c.reused_task_id, tasks.c.id)
                        )
                        .join(producer, producer.c.id == origin.c.run_id)
                        .where(tasks.c.id == task_id)
                    )
                    .mappings()
                    .one()
                )
                origin_id = custody["origin_task_id"]
                published = [
                    assertion
                    for assertion in page.public_assertions
                    if assertion["selected_task_id"] == task_id
                    and assertion["origin_task_id"] == origin_id
                    and assertion["product_id"] == report.product_id
                    and assertion["cut_id"] == page.cut_id
                ]
                if published:
                    from corpus_structure.semantic.operations import BoundReader
                    from corpus_structure.semantic.structural_admission import structural_claim_id
                    from corpus_structure.semantic.structural_products import RetainedStructuralRef

                    reference = RetainedStructuralRef(
                        product_id=report.product_id,
                        project_id=project_id,
                        run_id=original.run_id,
                        cut_id=page.cut_id,
                        release_id=page.release_id,
                        result_revision=selected_session.binding.data_revision,
                        selected_task_id=task_id,
                        origin_task_id=origin_id,
                        runtime_fingerprint=custody["runtime_fingerprint"],
                    )
                    retained = BoundReader(
                        conn,
                        original.run_id,
                        selected_session.prepared,
                        cut_id=page.cut_id,
                        analysis=False,
                    ).retained_structural_report(reference)
                    statements = {
                        a["assessment_id"]: a["statement"] for a in retained["public_assertions"]
                    }
                    for assertion in published:
                        statement = statements.get(assertion["assertion_id"])
                        if (
                            statement is None
                            or structural_claim_id(statement) != assertion["claim_id"]
                        ):
                            raise SemanticRefusal(
                                "published structural witness differs from exact retained statement"
                            )
                        enriched_assertions[canonical_bytes(assertion)] = dict(
                            assessment_id=assertion["assertion_id"], statement=statement
                        )
                if selection.completeness == "selected_source_closure" and (
                    report.dossier or report.artifact_identity
                ):
                    from corpus_structure.semantic.operations import BoundReader
                    from corpus_structure.semantic.retained_contributions import (
                        RetainedContributionRef,
                    )

                    if report.dossier is not None:
                        references = (
                            *report.dossier.predecessors,
                            *report.dossier.contribution_predecessors,
                        )
                    else:
                        assert report.artifact_identity is not None
                        references = tuple(
                            n.relationship for n in report.artifact_identity.external_nominations
                        )
                    for reference in references:
                        key = (reference.run_id, reference.cut_id)
                        if key not in predecessor_readers:
                            predecessor = bind_completed_result(conn, reference.run_id)
                            predecessor_readers[key] = BoundReader(
                                conn,
                                reference.run_id,
                                predecessor.prepared,
                                cut_id=reference.cut_id,
                                analysis=False,
                            )
                        reader = predecessor_readers[key]
                        if isinstance(reference, RetainedContributionRef):
                            budget.value(reader.retained_source_contribution(reference))
                        else:
                            budget.value(reader.retained_structural_report(reference))
                yield (
                    "structural_products",
                    {
                        "selection_index": index,
                        "selected_task_id": task_id,
                        **custody,
                        "product_id": report.product_id,
                        "report": report.model_dump(mode="json"),
                    },
                )
                if selection.completeness == "inventory":
                    continue
                for ref in report.inputs.sources:
                    if ref.identity in validated_external:
                        continue
                    source_session = bind_completed_result(conn, ref.run_id)
                    if (
                        source_session.binding.release_id != ref.release_id
                        or source_session.binding.data_revision != ref.result_revision
                        or source_session.completed_cut_id != ref.cut_id
                    ):
                        raise SemanticRefusal("structural original run/cut/revision differs")
                    if ref.release_id not in seen_releases:
                        seen_releases.add(ref.release_id)
                        yield "contracts", _contract_row(source_session.prepared)
                    run = table("ops.run")
                    if (
                        conn.scalar(select(run.c.project_id).where(run.c.id == ref.run_id))
                        != ref.project_id
                    ):
                        raise SemanticRefusal("structural original source project differs")
                    refs = {item.id: item for item in selected_source_views(conn, ref.run_id)}
                    bound = refs.get(ref.source_view_id)
                    if (
                        bound is None
                        or bound.native_product.task_id != ref.native_task_id
                        or bound.native_product.product_key != ref.native_product_key
                        or bound.native_product.content_digest != ref.native_content_digest
                        or bound.projection_digest != ref.projection_digest
                        or bound.recipe_digest != ref.recipe_digest
                    ):
                        raise SemanticRefusal("structural original source binding differs")
                    validated_external.add(ref.identity)
                    yield from _capture_sources(
                        conn,
                        {ref.source_view_id},
                        budget,
                        seen_sources,
                        seen_documents,
                        seen_producers,
                        cancellation,
                        coordinate_versions=coordinate_versions,
                    )
                    if ref.coordinate_version != coordinate_versions[ref.source_view_id]:
                        raise SemanticRefusal("structural source coordinate version differs")
                if origin_id not in seen_reports:
                    result, cfg = table("ops.task_result"), table("ops.method_config")
                    producer = table("ops.run")
                    statement = (
                        select(
                            result.c.body,
                            tasks.c.input_hash,
                            tasks.c.run_id.label("origin_run_id"),
                            producer.c.project_id,
                            producer.c.runtime_id.label("runtime_fingerprint"),
                            cfg.c.params.label("configuration"),
                            cfg.c.config_hash,
                        )
                        .join(tasks, tasks.c.id == result.c.task_id)
                        .join(cfg, cfg.c.id == tasks.c.method_config_id)
                        .join(producer, producer.c.id == tasks.c.run_id)
                        .where(result.c.task_id == origin_id)
                    )
                    budget.preflight(conn, statement)
                    raw = dict(conn.execute(statement).mappings().one())
                    budget.value(raw)
                    seen_reports.add(origin_id)
                    yield "reports", {"origin_task_id": origin_id, **raw}
            for assertion in page.public_assertions:
                yield (
                    "structural_public_assertions",
                    {
                        "selection_index": index,
                        **assertion,
                        **enriched_assertions.get(canonical_bytes(assertion), {}),
                    },
                )
            if page.next_after_task_id is None:
                break
            after = page.next_after_task_id


def _capture_sources(
    conn,
    source_ids,
    budget,
    seen_sources,
    seen_documents,
    seen_producers,
    cancellation,
    *,
    coordinate_versions=None,
):
    task, cfg = table("ops.task"), table("ops.method_config")
    for source_id in sorted(source_ids - seen_sources):
        cancellation.check_active()
        source = load_source_view(conn, source_id, analysis=False, read_budget=budget)
        if coordinate_versions is not None:
            coordinate_versions[source_id] = 3 if source.integrated_context is not None else 2
        seen_sources.add(source_id)
        producer_id = source.ref.native_product.task_id
        if producer_id not in seen_producers:
            run = table("ops.run")
            statement = (
                select(
                    task.c.id,
                    task.c.run_id,
                    task.c.release_id,
                    task.c.input_hash,
                    task.c.packet_hash,
                    task.c.result_digest,
                    cfg.c.params.label("configuration"),
                    cfg.c.config_hash,
                    run.c.runtime_id,
                    run.c.dependencies,
                )
                .join(cfg, cfg.c.id == task.c.method_config_id)
                .join(run, run.c.id == task.c.run_id)
                .where(task.c.id == producer_id)
            )
            budget.preflight(conn, statement)
            row = dict(conn.execute(statement).mappings().one())
            budget.value(row)
            seen_producers.add(producer_id)
            yield "source_producers", row
        if source.ref.document_id not in seen_documents:
            document = table("kb.document")
            statement = select(document).where(document.c.id == source.ref.document_id)
            budget.preflight(conn, statement)
            row = dict(conn.execute(statement).mappings().one())
            budget.value(row)
            seen_documents.add(source.ref.document_id)
            yield "documents", row
        yield (
            "sources",
            {
                "source_view_id": source_id,
                "ref": asdict(source.ref),
                "text": source.text,
                "context": source.context(),
                "source_coverage": "selected_projection_only",
                "original_page_map": "unknown_unless_retained_in_native_items",
            },
        )


def _item_source_ids(value: Any) -> set[int]:
    """Read declared pin/anchor slots; lexical values and diagnostics remain opaque."""
    if not isinstance(value, dict):
        return set()
    pins = [value.get("pin")]
    pins.extend(
        anchor.get("pin") for anchor in value.get("anchors", ()) if isinstance(anchor, dict)
    )
    return {
        pin["source_view_id"]
        for pin in pins
        if isinstance(pin, dict) and type(pin.get("source_view_id")) is int
    }


def _report_source_ids(body: Any) -> set[int]:
    if not isinstance(body, dict):
        return set()
    return set().union(
        *(
            _item_source_ids(item)
            for field in ("records", "contributions")
            for item in body.get(field, ())
        )
    )


def _retained_report_ids(report: Mapping[str, Any]) -> set[int]:
    # This is the declared upstream-input ABI of the typed replay operation,
    # not a recursive interpretation of arbitrary returned JSON.
    if report.get("method") != "resolve.m1_readings":
        return set()
    values = report["configuration"].get("retained_source_tasks", ())
    if any(type(value) is not int or value <= 0 for value in values):
        raise SemanticRefusal("retained source task reference is invalid")
    return set(values)


def _frame_source_ids(context: Any) -> set[int]:
    """Only the released source-operation frame's custody slots carry source references."""
    if not isinstance(context, dict) or context.get("protocol") != "source-operation-frame-1":
        return set()
    frame = context["evaluation_frame"]
    pins = [frame["pin"], *frame.get("related_pins", ())]
    pins.extend(scope.get("pin") for scope in frame.get("anchor_scopes", ()))
    pins.extend(item.get("pin") for item in context.get("captured_coordinates", ()))
    return {
        pin["source_view_id"]
        for pin in pins
        if isinstance(pin, dict) and type(pin.get("source_view_id")) is int
    }


def _covers_assessment_unit(selection: ReviewSelection, run_id: int, source_view_id: int) -> bool:
    # A complete grade packet includes the actual producing run/unit inventory,
    # rather than trusting optional provenance strings inside an authored result.
    return any(
        request.run_id == run_id
        and request.source_view_id in (None, source_view_id)
        and not any(
            (
                request.method,
                request.operation_key,
                request.operation_version,
                request.contribution_id,
                request.occurrence_id,
                request.kind,
            )
        )
        for request in selection.selections
    )


def _validate_source(value: dict[str, Any]) -> None:
    # Reuse the production projection/piece validator rather than a parallel checker.
    from corpus_structure.core.method import SourceViewDraft
    from corpus_structure.semantic.product_reference import ProductReference

    ref, context = value["ref"], value["context"]
    draft = SourceViewDraft(
        key=ref["key"],
        document_id=ref["document_id"],
        native_product=ProductReference(**ref["native_product"]),
        section_pointer=ref["section_pointer"],
        membership=ref["membership"],
        text=value["text"],
        pieces=tuple(context["pieces"]),
        items=tuple(item["self_ref"] for item in context["items"]),
        ancestors=tuple(item["self_ref"] for item in context["ancestors"]),
        health=context["health"],
        recipe_bytes=b"",
        analysis_eligible=ref["analysis_eligible"],
    )
    if draft.projection_digest != ref["projection_digest"] or value["source_view_id"] != ref["id"]:
        raise ValueError("review source projection digest differs")


def _schema(selection_digest: str, relation: str) -> pa.Schema:
    return pa.schema(
        [
            pa.field("row_id", pa.int64(), nullable=False),
            pa.field("payload_json", pa.string(), nullable=False),
        ],
        metadata={
            b"cs.review": FORMAT.encode(),
            b"cs.selection": selection_digest.encode(),
            b"cs.relation": relation.encode(),
        },
    )


def write_review_bundle(
    selection: ReviewSelection,
    destination: Path,
    rows: Iterable[tuple[str, Mapping[str, Any]]],
    *,
    cancellation: OperationCancellation | None = None,
) -> dict[str, Any]:
    """Spool an owned row stream and publish only after its generator settles.

    JSON payload columns preserve heterogeneous versioned operation fields exactly;
    the two serializations share one Arrow schema and logical row digest.
    """
    cancellation = cancellation or OperationCancellation()
    cancellation.check_active()
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    selection_value = selection.model_dump(mode="json")
    selection_digest = sha256(canonical_bytes(selection_value)).hexdigest()
    with TemporaryDirectory(prefix=".review-", dir=destination.parent) as temporary:
        root = Path(temporary) / "bundle"
        root.mkdir()
        sinks: dict[str, Any] = {}
        raw_bytes = 0
        primary: BaseException | None = None
        try:
            for name, value in rows:
                cancellation.check_active()
                if not _NAME.fullmatch(name):
                    raise ValueError("invalid review relation name")
                if name not in sinks:
                    schema = _schema(selection_digest, name)
                    sinks[name] = (
                        schema,
                        LogicalRows(schema),
                        (root / (name + ".jsonl")).open("wb"),
                        pq.ParquetWriter(root / (name + ".parquet"), schema),
                        [],
                    )
                schema, logical, stream, writer, pending = sinks[name]
                row = {
                    "row_id": logical.rows + len(pending),
                    "payload_json": canonical_bytes(_json(value)).decode(),
                }
                encoded = canonical_bytes(row) + b"\n"
                raw_bytes += len(encoded)
                if raw_bytes > selection.max_bytes:
                    raise SemanticRefusal("review payload exceeds declared byte budget")
                stream.write(encoded)
                pending.append(row)
                if len(pending) >= 128:
                    batch = pa.RecordBatch.from_pylist(pending, schema=schema)
                    logical.write(batch)
                    writer.write_batch(batch)
                    pending.clear()
            for schema, logical, _, writer, pending in sinks.values():
                if pending:
                    batch = pa.RecordBatch.from_pylist(pending, schema=schema)
                    logical.write(batch)
                    writer.write_batch(batch)
        except BaseException as error:
            primary = error
        finally:
            # Settle every independent owner without replacing the primary failure.
            failures: list[BaseException] = []
            close = getattr(rows, "close", None)
            if close is not None:
                try:
                    close()
                except BaseException as error:
                    failures.append(error)
            for _, _, stream, writer, _ in sinks.values():
                for sink in (stream, writer):
                    try:
                        sink.close()
                    except BaseException as error:
                        failures.append(error)
            if primary is not None:
                for failure in failures:
                    primary.add_note(f"Review cleanup also failed: {failure!r}")
                raise primary
            if failures:
                raise BaseExceptionGroup("review owners failed to settle", failures)
        relations = {}
        for name, (schema, logical, _, _, _) in sinks.items():
            relations[name] = {
                "rows": logical.rows,
                "schema_base64": base64.b64encode(schema.serialize().to_pybytes()).decode(),
                "logical_digest": logical.digest,
                "files": {
                    suffix: {
                        "path": name + "." + suffix,
                        "sha256": _digest(root / (name + "." + suffix)),
                        "bytes": (root / (name + "." + suffix)).stat().st_size,
                    }
                    for suffix in ("jsonl", "parquet")
                },
            }
        manifest = {
            "format": FORMAT,
            "selection": selection_value,
            "selection_digest": selection_digest,
            "relations": relations,
            "completeness": selection.completeness,
            "assessment_scope": (
                "published_admission_witnesses_only_unless_explicit_evaluator_relations"
            ),
            "original_source_completeness": "not_established",
            "scientific_truth": "not_established",
            "protected_cohorts": "excluded_unless_authorized_by_separate_evaluator_capture",
            "raw_serialization": "canonical_retained_values_original_bytes_only_where_retained",
        }
        overview = (
            "# Progressive corpus review\n\n"
            f"Declared scope: `{selection.completeness}`.\n\n"
            "Inspect `manifest.json`; each relation has matching JSONL and Parquet. "
            "Decode payload_json for the versioned source/operation object. "
            "Sources retain projected text, ordered pieces, native items and health.\n\n"
            "This package establishes neither original-corpus completeness "
            "nor scientific truth. "
            "Unassessed contributions remain unassessed. "
            "Protected labels require a separate "
            "authorized evaluator capture.\n\n"
            + "\n".join(
                f"- [{name}]({name}.jsonl): {spec['rows']} rows" for name, spec in relations.items()
            )
            + "\n"
        )
        (root / "README.md").write_text(overview)
        manifest["overview"] = {"path": "README.md", "sha256": _digest(root / "README.md")}
        (root / "manifest.json").write_bytes(canonical_bytes(manifest) + b"\n")
        total = sum(path.stat().st_size for path in root.iterdir())
        if total > selection.max_bytes:
            raise SemanticRefusal("review serializations exceed declared total byte budget")
        verify_review_bundle(root)
        with cancellation.publication():
            _publish_directory(root, destination)
        return manifest


def export_review_bundle(
    selection: ReviewSelection,
    destination: Path,
    settings: Settings,
    *,
    cancellation: OperationCancellation | None = None,
    extra_relations: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    evaluator_capture: Callable[[Any], Mapping[str, Iterable[Mapping[str, Any]]]] | None = None,
) -> dict[str, Any]:
    cancellation = cancellation or OperationCancellation()

    def rows():
        with (
            open_runtime_engine(
                settings, "review-export", purpose="evaluate" if evaluator_capture else "read"
            ) as engine,
            read_snapshot(engine, cancellation=cancellation.postgresql) as conn,
        ):
            yield from capture_review_relations(conn, selection, cancellation)
            if evaluator_capture is not None:
                for name, values in evaluator_capture(conn).items():
                    yield from _named_rows(name, values)
        for name, values in (extra_relations or {}).items():
            yield from _named_rows(name, values)

    from corpus_structure.serve.review_views import compose_review_views

    return write_review_bundle(
        selection, destination, compose_review_views(selection, rows()), cancellation=cancellation
    )


def _named_rows(name, values):
    try:
        for value in values:
            yield name, value
    finally:
        close = getattr(values, "close", None)
        if close is not None:
            close()


def _member(root: Path, name: str) -> Path:
    if Path(name).name != name or name in {"", ".", ".."}:
        raise ValueError("invalid review member path")
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise ValueError("review member missing or not an ordinary file")
    return path


def _verify_dossier_structural_closure(root, manifest, dossiers, products, scopes, assertions):
    """Replay declared structural predecessors across their exact selected snapshots."""
    from corpus_structure.methods.structural_products import derive_dossier_members, dossier_root
    from corpus_structure.semantic.structural_admission import structural_claim_id
    from corpus_structure.semantic.structural_products import StructuralProductReport

    origin_ids = {ref.origin_task_id for report in dossiers for ref in report.dossier.predecessors}
    raw_reports = {}
    spec = manifest["relations"].get("reports")
    if spec is not None:
        with _member(root, spec["files"]["jsonl"]["path"]).open("rb") as stream:
            for line in stream:
                raw = json.loads(json.loads(line)["payload_json"])
                if raw["origin_task_id"] in origin_ids:
                    raw_reports[raw["origin_task_id"]] = raw
    roots = {}
    for report in dossiers:
        references = report.dossier.predecessors
        reference_ids = {ref.product_id for ref in references}
        actual = {
            member.member_id: member
            for member in report.dossier.members
            if member.contribution_ref is None
        }
        if any(member.relation_product_id not in reference_ids for member in actual.values()):
            raise ValueError(
                "dossier predecessor closure missing; member has no declared reference"
            )
        retained = []
        for reference in references:
            expected = reference.model_dump(mode="json")
            candidates = []
            for (
                index,
                selected_id,
                origin_id,
                origin_run_id,
                origin_project,
                runtime,
                predecessor,
            ) in products:
                scope = scopes[index]
                binding = scope.get("binding", {})
                custody = dict(
                    product_id=predecessor.product_id,
                    project_id=scope.get("project_id"),
                    run_id=scope["run_id"],
                    cut_id=scope["cut_id"],
                    release_id=scope["release_id"],
                    result_revision=binding.get("data_revision"),
                    selected_task_id=selected_id,
                    origin_task_id=origin_id,
                    runtime_fingerprint=runtime,
                )
                if binding.get("release_id") == reference.release_id and canonical_bytes(
                    custody
                ) == canonical_bytes(expected):
                    candidates.append((index, origin_run_id, origin_project, predecessor))
            if not candidates:
                raise ValueError(
                    "dossier predecessor closure missing; exact selected custody differs"
                )
            raw = raw_reports.get(reference.origin_task_id)
            if (
                raw is None
                or raw.get("project_id") != candidates[0][2]
                or raw.get("runtime_fingerprint") != reference.runtime_fingerprint
                or raw.get("body", {}).get("release_id") != reference.release_id
                or raw.get("origin_run_id") != candidates[0][1]
                or StructuralProductReport.model_validate(raw["body"].get("structural_product"))
                != candidates[0][3]
            ):
                raise ValueError("dossier predecessor differs from original producer custody")
            indices = {index for index, _, _, _ in candidates}
            retained.append(
                (
                    reference,
                    dict(
                        report=candidates[0][3].model_dump(mode="json"),
                        public_assertions=[
                            assertion
                            for assertion in assertions
                            if assertion["selection_index"] in indices
                            and assertion["product_id"] == reference.product_id
                            and assertion.get("cut_id") == reference.cut_id
                            and assertion.get("selected_task_id") == reference.selected_task_id
                            and assertion.get("origin_task_id") == reference.origin_task_id
                            and assertion.get("assessment_id") == assertion.get("assertion_id")
                            and assertion.get("statement") is not None
                            and assertion.get("claim_id")
                            == structural_claim_id(assertion["statement"])
                        ],
                    ),
                )
            )
        root_ref = report.dossier.root_component
        if root_ref is None:
            raise ValueError("current dossier requires exact root component custody")
        raw = raw_reports.get(root_ref.origin_task_id, {}).get("body", {})
        if (raw.get("method"), raw.get("operation_version")) != (
            root_ref.operation_id,
            root_ref.operation_version,
        ):
            raise ValueError("dossier root differs from its original producer operation")
        component = dossier_root(root_ref, retained)
        roots[report.product_id] = component
        expected_members, expected_facets = derive_dossier_members(
            report.inputs, retained, root=component
        )
        if actual != {member.member_id: member for member in expected_members}:
            raise ValueError(
                "dossier structural membership differs from declared predecessor evidence"
            )
        if {facet.facet_id: facet for facet in report.dossier.supported_facets} != {
            facet.facet_id: facet for facet in expected_facets
        }:
            raise ValueError("dossier supported facets differ from declared predecessor assertions")
    return roots


def _detached_relation(root, manifest, name):
    spec = manifest["relations"].get(name)
    if spec is None:
        return
    with _member(root, spec["files"]["jsonl"]["path"]).open("rb") as stream:
        for line in stream:
            yield json.loads(json.loads(line)["payload_json"])


def _retained_contribution_payloads(root, manifest, requested, scopes, inventory):
    """Read exact selected raw provenance and endpoint closure once for dependent products."""
    from corpus_structure.semantic.contributions import contribution_identity

    if not requested:
        return
    origin_ids = {reference.origin_task_id for _, reference in requested}
    reports = {
        row["origin_task_id"]: row
        for row in _detached_relation(root, manifest, "reports")
        if row["origin_task_id"] in origin_ids
    }
    source_ids = {
        source.source_view_id for report, _ in requested for source in report.inputs.sources
    }
    sources = {}
    for row in _detached_relation(root, manifest, "sources"):
        if row["source_view_id"] not in source_ids:
            continue
        ref = row["ref"]
        sources[row["source_view_id"]] = dict(
            source_view_id=row["source_view_id"],
            pin=dict(
                source=ref["key"],
                native_product_task_id=ref["native_product"]["task_id"],
                product_key=ref["native_product"]["product_key"],
                product_digest=ref["native_product"]["content_digest"],
                projection_digest=ref["projection_digest"],
                recipe_digest=ref["recipe_digest"],
                source_view_id=row["source_view_id"],
            ),
            projection=dict(text=row["text"], pieces=row["context"]["pieces"]),
        )
    for report, reference in requested:
        candidates = [
            index
            for index, scope in scopes.items()
            if scope["run_id"] == reference.run_id
            and scope["cut_id"] == reference.cut_id
            and scope.get("project_id") == reference.project_id
            and scope.get("binding", {}).get("release_id") == reference.release_id
            and scope.get("binding", {}).get("data_revision") == reference.result_revision
        ]
        raw = reports.get(reference.origin_task_id)
        if (
            not candidates
            or raw is None
            or raw.get("runtime_fingerprint") != reference.runtime_fingerprint
            or raw.get("unit_type") != "source_view"
            or raw.get("body", {}).get("release_id") != reference.release_id
        ):
            raise ValueError(
                "retained contribution differs from exact selected raw producer custody"
            )
        available = {row["contribution_id"]: row for row in raw["body"].get("contributions", ())}
        closure, pending = {}, [reference.contribution_id]
        while pending:
            key = pending.pop()
            if key in closure:
                continue
            row = available.get(key)
            if row is None:
                raise ValueError("retained contribution raw endpoint closure missing")
            if not any(
                (
                    captured := inventory.get(
                        (index, reference.selected_task_id, reference.origin_task_id, key)
                    )
                )
                is not None
                and captured.get("origin_project_id") == raw.get("project_id")
                and captured.get("origin_run_id") == raw.get("origin_run_id")
                and captured.get("runtime_fingerprint") == reference.runtime_fingerprint
                for index in candidates
            ):
                raise ValueError("retained contribution selected endpoint inventory missing")
            closure[key] = row
            pending.extend(e["contribution_id"] for e in row.get("endpoints", ()))
            pending.extend(row.get("members", ()))
        source_ids = {
            anchor["pin"]["source_view_id"]
            for row in closure.values()
            for anchor in row.get("anchors", ())
        }
        if not source_ids <= sources.keys():
            raise ValueError("retained contribution original endpoint source missing")
        if any(contribution_identity(row) != key for key, row in closure.items()):
            raise ValueError("retained contribution identity differs from original content")
        yield dict(
            contributions=list(closure.values()),
            sources=[sources[key] for key in sorted(source_ids)],
        )



def _verify_dossier_contribution_closure(root, manifest, members, scopes, inventory, roots):
    from corpus_structure.methods.dossier_contributions import derive_contribution_members

    requested = []
    for report, member in members:
        if member.contribution_ref not in report.dossier.contribution_predecessors:
            raise ValueError("dossier source member lacks its declared contribution predecessor")
        requested.append((report, member.contribution_ref))
    payloads = _retained_contribution_payloads(root, manifest, requested, scopes, inventory)
    for (report, member), payload in zip(members, payloads, strict=True):
        derived = derive_contribution_members(
            report.inputs, member.contribution_ref, payload, root=roots[report.product_id]
        )
        if derived != (member,):
            raise ValueError("dossier source membership differs from original contribution evidence")


def _verify_artifact_nomination_closure(
    root, manifest, artifacts, structural_scopes, contribution_scopes, inventory
):
    from corpus_structure.methods.artifact_identity import (
        ArtifactIdentityMethod,
        retained_artifact_nomination,
    )
    from corpus_structure.semantic.contributions import occurrence_identity
    from corpus_structure.semantic.structural_products import StructuralProductReport

    origin_ids = {item[2] for item in artifacts}
    captured = {}
    for row in _detached_relation(root, manifest, "reports"):
        origin_id = row["origin_task_id"]
        if origin_id in origin_ids:
            if origin_id in captured:
                raise ValueError("artifact producer raw result repeats")
            captured[origin_id] = row

    expected, requested = [], []
    for index, _selected, origin, origin_run, origin_project, runtime, report in artifacts:
        product = report.artifact_identity
        if product is None:
            raise ValueError("artifact nomination closure requires an exact artifact product")
        raw = captured.get(origin, {})
        body = raw.get("body") or {}
        config = raw.get("configuration") or {}
        refs = [n.relationship.model_dump(mode="json") for n in product.external_nominations]
        declared = config.get("external_nomination_refs")
        if (
            raw.get("project_id") != origin_project
            or raw.get("origin_run_id") != origin_run
            or raw.get("runtime_fingerprint") != runtime
            or body.get("release_id") != structural_scopes[index]["release_id"]
            or body.get("method") != ArtifactIdentityMethod.name
            or body.get("operation_version") != ArtifactIdentityMethod.version
            or not isinstance(declared, list)
            or len(declared) != len(refs)
            or sorted(declared, key=canonical_bytes) != sorted(refs, key=canonical_bytes)
            or StructuralProductReport.model_validate(body.get("structural_product")) != report
        ):
            raise ValueError("artifact product differs from original registered producer and nomination configuration")
        for nomination in product.external_nominations:
            expected.append((report, nomination))
            requested.append((report, nomination.relationship))

    payloads = _retained_contribution_payloads(
        root, manifest, requested, contribution_scopes, inventory
    )
    for (report, nomination), payload in zip(expected, payloads, strict=True):
        source_views = {source["source_view_id"]: source for source in payload["sources"]}
        for row in payload["contributions"]:
            if row["kind"] != "occurrence":
                continue
            anchors = row["anchors"]
            if not anchors or occurrence_identity(anchors) != row["occurrence_id"]:
                raise ValueError("artifact nomination endpoint physical identity differs")
            for anchor in anchors:
                view = source_views[anchor["pin"]["source_view_id"]]
                projection = view["projection"]
                pieces = [
                    piece
                    for piece in projection["pieces"]
                    if piece.get("kind") == "native_text"
                    and piece.get("item_ref") == anchor["pointer"]
                    and piece.get("cell_index") is None
                ]
                if (
                    anchor["pin"] != view["pin"]
                    or anchor["space"] != "native"
                    or anchor["precision"] != "exact"
                    or len(pieces) != 1
                ):
                    raise ValueError("artifact nomination endpoint lacks exact native bridge")
                piece = pieces[0]
                start, end = piece["start"] + anchor["start"], piece["start"] + anchor["end"]
                if (
                    not piece["start"] <= start < end <= piece["end"]
                    or projection["text"][start:end] != anchor["source_piece"]
                ):
                    raise ValueError("artifact nomination endpoint differs from original source")
        product = report.artifact_identity
        assert product is not None
        actual = retained_artifact_nomination(
            report.inputs, product.records, nomination.relationship, payload
        )
        if actual != nomination:
            raise ValueError("artifact nomination differs from exact retained endpoints")



def verify_review_bundle(root: Path) -> dict[str, Any]:
    """Offline integrity and JSONL/Parquet equivalence; no database or model access."""
    manifest = json.loads(_member(root, "manifest.json").read_bytes())
    if manifest.get("format") != FORMAT:
        raise ValueError("unsupported review format")
    selection = ReviewSelection.model_validate(manifest["selection"])
    digest = sha256(canonical_bytes(selection.model_dump(mode="json"))).hexdigest()
    if digest != manifest["selection_digest"] or manifest["completeness"] != selection.completeness:
        raise ValueError("review selection differs")
    expected = {"manifest.json", manifest["overview"]["path"]}
    overview = _member(root, manifest["overview"]["path"])
    if _digest(overview) != manifest["overview"]["sha256"]:
        raise ValueError("review overview differs")
    present_sources: set[int] = set()
    needed_sources: set[int] = set()
    needed_reports: set[int] = set()
    present_reports: set[int] = set()
    omitted_reports: set[int] = set()
    bound_selections: set[int] = set()
    bound_structural: set[int] = set()
    structural_reports = []
    structural_refs = {}
    captured_refs = {}
    structural_product_ids: set[str] = set()
    public_product_ids: set[str] = set()
    assessment_units: dict[int, int] = {}
    graded_units: set[tuple[int, int]] = set()
    assessed_product_ids: set[str] = set()
    declared_grade_reports: set[tuple[int, int, int]] = set()
    captured_report_scopes: set[tuple[int, int, int]] = set()
    structural_scopes: dict[int, dict[str, Any]] = {}
    structural_members: set[tuple[int, str]] = set()
    structural_products = []
    structural_assertions = []
    dossier_reports = []
    dossier_source_members = []
    contribution_scopes = {}
    contribution_inventory = {}
    required_contracts: set[str] = set()
    captured_contracts: set[str] = set()
    for name, spec in manifest["relations"].items():
        if not _NAME.fullmatch(name):
            raise ValueError("invalid review relation")
        schema = pa.ipc.read_schema(pa.BufferReader(base64.b64decode(spec["schema_base64"])))
        if not schema.equals(_schema(digest, name), check_metadata=True):
            raise ValueError("review schema binding differs")
        logicals = {}
        for suffix in ("jsonl", "parquet"):
            file = spec["files"][suffix]
            expected.add(file["path"])
            path = _member(root, file["path"])
            if _digest(path) != file["sha256"] or path.stat().st_size != file["bytes"]:
                raise ValueError("review file integrity differs")
            logical = LogicalRows(schema, ("row_id",))
            if suffix == "parquet":
                parquet = pq.ParquetFile(path)
                if not parquet.schema_arrow.equals(schema, check_metadata=True):
                    raise ValueError("review parquet schema differs")
                for batch in parquet.iter_batches(batch_size=128):
                    logical.write(batch)
            else:
                with path.open("rb") as stream:
                    pending = []
                    for line in stream:
                        row = json.loads(line)
                        if row["row_id"] != logical.rows + len(pending):
                            raise ValueError("review row ordering differs")
                        payload = json.loads(row["payload_json"])
                        if name == "selections":
                            index = payload["selection_index"]
                            if index in bound_selections or not 0 <= index < len(
                                selection.selections
                            ):
                                raise ValueError("review selection population differs")
                            if (
                                payload["run_id"] != selection.selections[index].run_id
                                or not payload["cut_id"]
                            ):
                                raise ValueError("review selected run/cut differs")
                            bound_selections.add(index)
                            contribution_scopes[index] = payload
                        if name == "structural_selections":
                            index = payload["selection_index"]
                            if (
                                index in bound_structural
                                or not 0 <= index < len(selection.structural_selections)
                                or payload["run_id"]
                                != (selection.structural_selections[index].run_id)
                                or not payload["cut_id"]
                            ):
                                raise ValueError("structural selected run/cut differs")
                            bound_structural.add(index)
                            structural_scopes[index] = payload
                            required_contracts.add(payload["release_id"])
                        if name == "contracts":
                            captured_contracts.add(payload["release_id"])
                        if name == "structural_public_assertions":
                            public_product_ids.add(payload["product_id"])
                            structural_assertions.append(payload)
                        if name == "assessment_history":
                            value = payload["value"]
                            if payload["kind"] == "unit":
                                assessment_units[value["id"]] = value["source_view_id"]
                                needed_sources.add(value["source_view_id"])
                                for context in value["context"]:
                                    needed_sources.update(_frame_source_ids(context))
                            elif payload["kind"] == "frame":
                                needed_sources.update(_frame_source_ids(value["source_frame"]))
                            elif payload["kind"] == "evaluation":
                                if (
                                    value["result"].get("protocol")
                                    != "source-operation-evaluation-1"
                                ):
                                    raise ValueError("unsupported assessment closure protocol")
                                graded_units.update(
                                    (value["run_id"], unit["unit_id"])
                                    for unit in value["result"]["units"]
                                )
                                for unit in value["result"]["units"]:
                                    for report in unit.get("producer_reports", ()):
                                        needed_reports.add(report["origin_task_id"])
                                        declared_grade_reports.add(
                                            (
                                                value["run_id"],
                                                unit["unit_id"],
                                                report["origin_task_id"],
                                            )
                                        )
                            elif payload["kind"] == "structural_set":
                                frame = value["frame"]
                                needed_sources.update(
                                    ref["source_view_id"] for ref in frame["inputs"]["sources"]
                                )
                                assessed_product_ids.update(frame["product_ids"])
                        if name == "structural_products":
                            from corpus_structure.semantic.structural_products import (
                                StructuralProductReport,
                            )

                            report = StructuralProductReport.model_validate(payload["report"])
                            if report.product_id != payload["product_id"]:
                                raise ValueError("structural product identity differs")
                            structural_product_ids.add(report.product_id)
                            structural_members.add((payload["selection_index"], report.product_id))
                            structural_products.append(
                                (
                                    payload["selection_index"],
                                    payload["selected_task_id"],
                                    payload["origin_task_id"],
                                    payload.get("origin_run_id"),
                                    payload.get("origin_project_id"),
                                    payload.get("runtime_fingerprint"),
                                    report,
                                )
                            )
                            if report.dossier is not None:
                                dossier_reports.append(report)
                                dossier_source_members.extend(
                                    (report, member)
                                    for member in report.dossier.members
                                    if member.contribution_ref is not None
                                )
                            needed_sources.update(
                                ref.source_view_id for ref in report.inputs.sources
                            )
                            structural_refs.update(
                                (ref.identity, ref) for ref in report.inputs.sources
                            )
                            required_contracts.update(
                                ref.release_id for ref in report.inputs.sources
                            )
                            needed_reports.add(payload["origin_task_id"])
                            structural_reports.extend(
                                (
                                    ref.source_view_id,
                                    passage.start,
                                    passage.end,
                                    sha256(passage.text.encode()).hexdigest(),
                                )
                                for passage in report.inputs.passages
                                for ref in report.inputs.sources
                                if ref.identity == passage.source_ref
                            )
                        if name == "sources":
                            _validate_source(payload)
                            if payload["source_view_id"] in present_sources:
                                raise ValueError("review source member repeats")
                            present_sources.add(payload["source_view_id"])
                            captured_refs[payload["source_view_id"]] = payload["ref"]
                        elif name == "reports":
                            needed_sources.update(_report_source_ids(payload["body"]))
                            if payload.get("unit_type") == "source_view":
                                needed_sources.add(payload["origin_unit_id"])
                            needed_reports.update(_retained_report_ids(payload))
                            present_reports.add(payload["origin_task_id"])
                        elif name == "inventory":
                            item = payload["row"]
                            if type(item.get("source_view_id")) is int:
                                needed_sources.add(item["source_view_id"])
                            needed_sources.update(_item_source_ids(item))
                            if payload.get("population") == "contribution":
                                contribution_inventory[
                                    (
                                        payload.get("selection_index"),
                                        item.get("selected_task_id"),
                                        item.get("origin_task_id"),
                                        item.get("contribution_id"),
                                    )
                                ] = item
                            if payload.get("population") == "report":
                                needed_reports.add(item["origin_task_id"])
                                index = payload.get("selection_index")
                                if type(index) is int and 0 <= index < len(selection.selections):
                                    captured_report_scopes.add(
                                        (
                                            selection.selections[index].run_id,
                                            item["source_view_id"],
                                            item["origin_task_id"],
                                        )
                                    )
                        elif name == "omissions" and "origin_task_id" in payload:
                            omitted_reports.add(payload["origin_task_id"])
                        if canonical_bytes(payload).decode() != row["payload_json"]:
                            raise ValueError("review payload is not canonical")
                        pending.append(row)
                        if len(pending) >= 128:
                            logical.write(pa.RecordBatch.from_pylist(pending, schema=schema))
                            pending.clear()
                    if pending:
                        logical.write(pa.RecordBatch.from_pylist(pending, schema=schema))
            if logical.rows != spec["rows"] or logical.digest != spec["logical_digest"]:
                raise ValueError("review row count/logical digest differs")
            logicals[suffix] = logical.digest
        if len(set(logicals.values())) != 1:
            raise ValueError("review serializations disagree")
    if not public_product_ids <= structural_product_ids:
        raise ValueError("public structural witness has no selected product")
    if selection.completeness == "selected_source_closure":
        if not required_contracts <= captured_contracts:
            raise ValueError("structural release contracts are missing")
        if any(index not in structural_scopes for index, _ in structural_members):
            raise ValueError("structural product has no selected snapshot")
        dossier_roots = {}
        if dossier_reports:
            dossier_roots = _verify_dossier_structural_closure(
                root,
                manifest,
                dossier_reports,
                structural_products,
                structural_scopes,
                structural_assertions,
            )
        if dossier_source_members:
            _verify_dossier_contribution_closure(
                root,
                manifest,
                dossier_source_members,
                contribution_scopes,
                contribution_inventory,
                dossier_roots,
            )
        artifacts = [item for item in structural_products if item[-1].artifact_identity is not None]
        if artifacts:
            _verify_artifact_nomination_closure(
                root, manifest, artifacts, structural_scopes, contribution_scopes, contribution_inventory
            )
        for run_id, unit_id in graded_units:
            if unit_id not in assessment_units or not _covers_assessment_unit(
                selection, run_id, assessment_units[unit_id]
            ):
                raise ValueError(
                    "assessment producer closure missing; include its unfiltered run/unit"
                )
        if not assessed_product_ids <= structural_product_ids:
            raise ValueError("assessment structural products are missing")
        for run_id, unit_id, origin_id in declared_grade_reports:
            if (run_id, assessment_units[unit_id], origin_id) not in captured_report_scopes:
                raise ValueError("assessment producer differs from captured run/unit inventory")
        if bound_selections != set(range(len(selection.selections))):
            raise ValueError("review selected snapshot members are missing")
        if bound_structural != set(range(len(selection.structural_selections))):
            raise ValueError("review structural snapshot members are missing")
        if not needed_sources <= present_sources:
            raise ValueError("review required source members are missing")
        for ref in structural_refs.values():
            captured = captured_refs[ref.source_view_id]
            if (
                captured["projection_digest"] != ref.projection_digest
                or captured["recipe_digest"] != ref.recipe_digest
                or captured["native_product"]["task_id"] != ref.native_task_id
                or captured["native_product"]["product_key"] != ref.native_product_key
                or captured["native_product"]["content_digest"] != ref.native_content_digest
            ):
                raise ValueError("structural source differs from exported original pin")
        if structural_reports:
            sources_path = _member(root, manifest["relations"]["sources"]["files"]["jsonl"]["path"])
            pending_sources = {entry[0] for entry in structural_reports}
            with sources_path.open("rb") as source_stream:
                for line in source_stream:
                    source = json.loads(json.loads(line)["payload_json"])
                    for source_id, start, end, digest in structural_reports:
                        if source_id == source["source_view_id"]:
                            if (
                                end > len(source["text"])
                                or sha256(source["text"][start:end].encode()).hexdigest() != digest
                            ):
                                raise ValueError("structural passage differs from exported source")
                            pending_sources.discard(source_id)
            if pending_sources:
                raise ValueError("structural source excerpt members are missing")
        if not needed_reports <= present_reports | omitted_reports:
            raise ValueError("review required report members are missing")
    if {path.name for path in root.iterdir()} != expected:
        raise ValueError("review package has undeclared or missing members")
    return manifest


def inspect_review_bundle(root: Path) -> dict[str, Any]:
    manifest = verify_review_bundle(root)
    return {
        "format": FORMAT,
        "selection": manifest["selection"],
        "completeness": manifest["completeness"],
        "relations": {name: spec["rows"] for name, spec in manifest["relations"].items()},
        "assessment_scope": manifest["assessment_scope"],
        "original_source_completeness": manifest["original_source_completeness"],
    }
