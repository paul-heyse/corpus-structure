"""Declared-scope portable review over pinned retained products.

The bundle is a detached reading, not admission or original-document completeness.
Public capture never opens an evaluator connection. Authorized assessment owners may
supply separately captured relations; callers retain responsibility for exposure.
"""

from __future__ import annotations

import base64
import json
import os
import re
import stat
import sys
from collections.abc import Callable, Iterable, Mapping
from contextlib import ExitStack, closing, contextmanager
from dataclasses import asdict, dataclass
from hashlib import file_digest, sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Connection, func, select, text

from corpus_structure.core.db.cancellation import OperationCancellation
from corpus_structure.semantic.capture_storage import LogicalRows
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import (
    PreparedSourceView,
    load_source_view,
    selected_source_views,
)
from corpus_structure.serve.companion_export import _publish_directory
from corpus_structure.serve.contextual_navigation import (
    SourceDecisionRequest,
    capture_source_decision,
    source_decision_capture_from_body,
    source_decision_from_capture,
)
from corpus_structure.serve.contributions import ContributionRequest, _contributions
from corpus_structure.serve.source_decision_journey import (
    SourceDecisionJourneyParams,
    capture_source_decision_journey,
    source_decision_journey,
)
from corpus_structure.serve.structural_gaps import GapRequest, gap_capture, gap_page
from corpus_structure.serve.structural_products import (
    StructuralExportRequest,
    read_structural_export_page,
)
from corpus_structure.settings import Settings

FORMAT = "progressive-review-bundle-2"
_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
SECTION_PACKET_INPUT = "execution/implementation/operations/section-packets.json"
_PREDICATE_QUALIFIER_SCHEMA = "predicate_qualifier_schema"


class ReviewComparison(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    baseline_evaluation_id: int = Field(strict=True, gt=0)
    revised_evaluation_id: int = Field(strict=True, gt=0)


class ReviewSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    selections: tuple[ContributionRequest, ...] = ()
    structural_selections: tuple[StructuralExportRequest, ...] = ()
    source_decision_selections: tuple[SourceDecisionRequest, ...] = Field(
        default=(), max_length=64, exclude_if=lambda value: not value
    )
    source_decision_journeys: tuple[SourceDecisionJourneyParams, ...] = Field(
        default=(), max_length=16, exclude_if=lambda value: not value
    )
    structural_gap_selections: tuple[GapRequest, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    require_original_gap_reports: bool = Field(default=False, exclude_if=lambda value: not value)
    selected_evaluation_ids: tuple[int, ...] = ()
    comparisons: tuple[ReviewComparison, ...] = ()
    completeness: Literal["selected_source_closure", "inventory"] = "selected_source_closure"
    max_bytes: int = Field(default=134_217_728, strict=True, gt=0)
    max_source_rows: int = Field(default=100_000, strict=True, gt=0)

    @model_validator(mode="after")
    def full_selections(self):
        if not (
            self.selections
            or self.structural_selections
            or self.structural_gap_selections
            or self.source_decision_selections
            or self.source_decision_journeys
        ):
            raise ValueError("review requires a contribution or structural selection")
        backing_tasks = {
            (request.run_id, request.selected_task_id)
            for request in (*self.selections, *self.structural_selections)
        }
        if self.source_decision_selections and self.completeness != "selected_source_closure":
            raise ValueError("source decision review requires exact retained source closure")
        if any(
            (request.run_id, request.task_id) not in backing_tasks
            for request in self.source_decision_selections
        ):
            raise ValueError("source decision review requires its exact retained task selection")
        if self.source_decision_journeys and (
            self.completeness != "selected_source_closure"
            or any(
                (layer.run_id, layer.task_id) not in backing_tasks
                for journey in self.source_decision_journeys
                for layer in journey.layers
            )
        ):
            raise ValueError("source-decision journeys require exact retained layer selections")
        if any(item.cursor is not None for item in self.structural_gap_selections):
            raise ValueError("gap review cannot begin at a continuation")
        if any(item.after_task_id for item in self.structural_selections):
            raise ValueError("structural review cannot begin after a task")
        if len(set(self.selected_evaluation_ids)) != len(self.selected_evaluation_ids) or any(
            type(value) is not int or value < 1 for value in self.selected_evaluation_ids
        ):
            raise ValueError("selected evaluations must have distinct positive identifiers")
        if any(item.cursor is not None for item in self.selections):
            raise ValueError("review selection cannot begin at a continuation")
        if any(item.include_scope_coverage for item in self.selections):
            raise ValueError("detached review does not yet authenticate the PM2 scope worklist")
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


def _contract_row(conn, prepared):
    from corpus_structure.methods.model_observation import MODEL_OBSERVATION_INPUT
    from corpus_structure.semantic.contributions import contribution_payload_contracts

    from .review_source_projection import SECTION_TEXT_INPUT

    row: dict[str, Any] = {
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
    if payload_contracts := contribution_payload_contracts(prepared.definitions):
        row["contribution_payload_contracts"] = {
            semantic_type: dict(contract=contract, schema=prepared.json_schema(contract))
            for semantic_type, contract in payload_contracts.items()
        }
    qualifier_class = "PredicateQualifierComponent"
    row[_PREDICATE_QUALIFIER_SCHEMA] = (
        prepared.json_schema(qualifier_class)
        if qualifier_class in prepared.index.definitions
        else None
    )
    dependencies = dict(json.loads(prepared.manifest).get("dependencies", ()))
    for input_name, field in (
        (SECTION_PACKET_INPUT, "section_packets"),
        (MODEL_OBSERVATION_INPUT, "model_observation_policy"),
        (SECTION_TEXT_INPUT, "section_text_policy"),
    ):
        expected = dependencies.get(input_name)
        if expected is None:
            continue
        inputs = table("sem.input")
        content = bytes(
            conn.execute(
                select(inputs.c.content).where(
                    inputs.c.release_id == prepared.release_id,
                    inputs.c.input_kind == "dependency",
                    inputs.c.input_name == input_name,
                )
            ).scalar_one()
        )
        if sha256(content).hexdigest() != expected:
            raise SemanticRefusal(f"archived {field} differs from release")
        row[field] = {
            "manifest_base64": base64.b64encode(prepared.manifest).decode(),
            "input_base64": base64.b64encode(content).decode(),
        }
    return row


def _section_source_refs(report):
    if report.get("method") != "retrieve.contextual":
        return ()
    from corpus_structure.semantic.structural_products import ExternalSourceRef

    config = report.get("configuration") or {}
    return tuple(
        ExternalSourceRef.model_validate(ref)
        for field in ("section_sources", "section_catalog_sources")
        for ref in config.get(field, ())
    )


def _structural_predecessors(report):
    if report.clause_classification is not None:
        return (), tuple(row.selection.frame for row in report.clause_classification.readings)
    if report.dossier is not None:
        return report.dossier.predecessors, report.dossier.contribution_predecessors
    if report.artifact_identity is not None:
        return (), tuple(n.relationship for n in report.artifact_identity.external_nominations)
    if report.comparison is not None and report.comparison.left_reading is not None:
        return (), (report.comparison.left_reading, report.comparison.right_reading)
    return (), ()


def _dossier_relationship_refs(report):
    return (
        tuple(
            dict.fromkeys(
                selection.relationship_ref for selection in report.dossier.comparison_selections
            )
        )
        if report.dossier is not None
        else ()
    )


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
    seen_proofs = set()
    validated_external: set[str] = set()
    predecessor_readers = {}
    origin_metadata = {}
    budget = PublishedReadBudget(selection.max_source_rows, selection.max_bytes)
    journey_views: dict[int, PreparedSourceView | None] = {
        request.opportunity.source.source_view_id: None
        for request in selection.source_decision_journeys
    }
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
            yield "contracts", _contract_row(conn, session.prepared)
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
                original.contribution_ids,
                original.selected_task_id,
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
            for alias in report["configuration"].get("definition_alias_refs", ()):
                if report["method"] != "retrieve.contextual" or alias["project_id"] != project_id:
                    raise SemanticRefusal("definition alias differs from the selected project")
                budget.value(
                    conn.scalar(
                        text(
                            "SELECT ops.resolve_retained_source_contribution(CAST(:ref AS jsonb))"
                        ),
                        {"ref": canonical_bytes(alias).decode()},
                    )
                )
            for ref in _section_source_refs(report):
                if ref.project_id != project_id:
                    raise SemanticRefusal("section source belongs to another project")
                external = bind_completed_result(conn, ref.run_id)
                if (
                    external.completed_cut_id != ref.cut_id
                    or external.binding.release_id != ref.release_id
                    or external.binding.data_revision != ref.result_revision
                ):
                    raise SemanticRefusal("section source differs from original run/cut/revision")
                # The native validator checks exact cut membership, projection and source pins.
                conn.execute(
                    text("SELECT ops.validate_structural_source(CAST(:source AS jsonb))"),
                    {"source": ref.model_dump_json()},
                )
                source_ids.add(ref.source_view_id)
                permitted.add(ref.source_view_id)
                if ref.release_id not in seen_releases:
                    seen_releases.add(ref.release_id)
                    yield "contracts", _contract_row(conn, external.prepared)
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
            seen_releases=seen_releases,
            seen_proofs=seen_proofs,
            coordinate_versions=coordinate_versions,
            retained_sources=journey_views,
        )
    for index, original in enumerate(selection.structural_selections):
        selected_session = bind_completed_result(conn, original.run_id)
        run = table("ops.run")
        project_id = conn.scalar(select(run.c.project_id).where(run.c.id == original.run_id))
        if selected_session.binding.release_id not in seen_releases:
            seen_releases.add(selected_session.binding.release_id)
            yield "contracts", _contract_row(conn, selected_session.prepared)
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
                    report.dossier
                    or report.artifact_identity
                    or (report.comparison and report.comparison.left_reading)
                ):
                    from corpus_structure.semantic.operations import BoundReader
                    from corpus_structure.semantic.retained_contributions import (
                        RetainedContributionRef,
                    )

                    structural, contributions = _structural_predecessors(report)
                    for reference in (*structural, *contributions):
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
                        yield "contracts", _contract_row(conn, source_session.prepared)
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
                        seen_releases=seen_releases,
                        seen_proofs=seen_proofs,
                        coordinate_versions=coordinate_versions,
                        retained_sources=journey_views,
                    )
                    if ref.coordinate_version != coordinate_versions[ref.source_view_id]:
                        raise SemanticRefusal("structural source coordinate version differs")
                if report.definition_components:
                    for dependency in _capture_definition_annotations(
                        conn, report, seen_reports, budget
                    ):
                        yield "reports", dependency
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

    for index, original in enumerate(selection.structural_gap_selections):
        cancellation.check_active()
        gap_request = original.model_copy(
            update={"max_bytes": min(original.max_bytes, selection.max_bytes)}
        )
        captured = gap_capture(conn, gap_request)
        budget.value(captured)
        yield "structural_gap_sources", {"selection_index": index, **captured}
        if selection.require_original_gap_reports:
            from .structural_gaps import gap_review_custody, gap_review_source_ids

            custody = gap_review_custody(conn, captured, budget)
            budget.value(custody)
            yield "structural_gap_custody", {"selection_index": index, **custody}
            yield from _capture_sources(
                conn,
                gap_review_source_ids(custody),
                budget,
                seen_sources,
                seen_documents,
                seen_producers,
                cancellation,
                seen_releases=seen_releases,
                seen_proofs=seen_proofs,
            )
        while True:
            cancellation.check_active()
            page = gap_page(gap_request, captured)
            yield "structural_gaps", {"selection_index": index, **page.model_dump(mode="json")}
            if page.next_cursor is None:
                break
            gap_request = gap_request.model_copy(update={"cursor": page.next_cursor})

    for index, request in enumerate(selection.source_decision_selections):
        cancellation.check_active()
        cut = bind_completed_result(conn, request.run_id).completed_cut_id
        if request.cut_id is not None and request.cut_id != cut:
            raise SemanticRefusal("diagnosis selection differs from its exact completed cut")
        evidence = capture_source_decision(conn, request, cut)
        budget.value(evidence)
        yield "source_decision_evidence", {"selection_index": index, **evidence}
        answer = source_decision_from_capture(request, evidence)
        yield "source_decisions", {"selection_index": index, **answer.model_dump(mode="json")}

    def journey_source(source_id):
        view = journey_views[source_id]
        if view is None:
            view = load_source_view(conn, source_id, analysis=False, read_budget=budget)
            journey_views[source_id] = view
        return {"ref": asdict(view.ref), "text": view.text, "context": view.context()}

    for index, journey in enumerate(selection.source_decision_journeys):
        cancellation.check_active()
        source, tasks = capture_source_decision_journey(
            conn, journey, source_loader=journey_source, budget=budget
        )
        yield from _capture_sources(
            conn,
            {journey.opportunity.source.source_view_id},
            budget,
            seen_sources,
            seen_documents,
            seen_producers,
            cancellation,
            seen_releases=seen_releases,
            seen_proofs=seen_proofs,
            retained_sources=journey_views,
        )
        custody = {layer: pin for layer, (pin, _) in tasks.items()}
        budget.value(custody)
        yield "source_journey_custody", {"selection_index": index, "layers": custody}
        answer = source_decision_journey(journey, source, tasks)
        yield (
            "source_decision_journeys",
            {"selection_index": index, **answer.model_dump(mode="json")},
        )


def _capture_sources(
    conn,
    source_ids,
    budget,
    seen_sources,
    seen_documents,
    seen_producers,
    cancellation,
    *,
    seen_releases,
    seen_proofs,
    coordinate_versions=None,
    retained_sources=None,
):
    from corpus_structure.semantic.releases import open_release

    from .review_source_projection import capture_source_projection, capture_source_proof

    task, cfg = table("ops.task"), table("ops.method_config")
    for source_id in sorted(source_ids - seen_sources):
        cancellation.check_active()
        source = retained_sources.get(source_id) if retained_sources is not None else None
        if source is None:
            source = load_source_view(conn, source_id, analysis=False, read_budget=budget)
            if retained_sources is not None and source_id in retained_sources:
                retained_sources[source_id] = source
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
        consumer_release = capture_source_projection(conn, source, budget)
        if consumer_release not in seen_releases or source.ref.native_product not in seen_proofs:
            prepared = open_release(conn, consumer_release)
            if consumer_release not in seen_releases:
                seen_releases.add(consumer_release)
                yield "contracts", _contract_row(conn, prepared)
            if source.ref.native_product not in seen_proofs:
                seen_proofs.add(source.ref.native_product)
                yield from _named_rows(
                    "source_proofs",
                    capture_source_proof(conn, source.ref.native_product, prepared, cancellation),
                )
        yield (
            "sources",
            {
                "source_view_id": source_id,
                "ref": asdict(source.ref),
                "text": source.text,
                "context": source.context(),
                "consumer_release": consumer_release,
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
    source_ids = set().union(
        *(
            _item_source_ids(item)
            for field in ("records", "contributions")
            for item in body.get(field, ())
        )
    )
    structural = body.get("structural_product") or {}
    if structural.get("kind") == "definition_components":
        source_ids.update(
            s["source_view_id"]
            for s in (structural.get("inputs") or {}).get("sources", ())
            if type(s.get("source_view_id")) is int
        )
    return source_ids


def _capture_definition_annotations(conn, report, seen_reports, budget):
    """Capture the exact annotation bodies selected by current definition witnesses."""
    result, config, method = (
        table("ops.task_result"),
        table("ops.method_config"),
        table("ops.method"),
    )
    origin, run = table("ops.task"), table("ops.run")
    member, selected = table("ops.cut_task"), origin.alias("definition_annotation_selected")
    passages = {p.passage_id: p for p in report.inputs.passages}
    sources = {source.identity: source for source in report.inputs.sources}
    witnessed = {
        (
            component.witness.annotation_task_id,
            sources[passages[component.term.passage_id].source_ref],
        )
        for component in report.definition_components.components
        if component.witness is not None
    }
    for identity, source in sorted(witnessed, key=lambda pair: (pair[0], pair[1].identity)):
        query = (
            select(
                result.c.body,
                origin.c.input_hash,
                origin.c.method_config_id,
                origin.c.run_id.label("origin_run_id"),
                origin.c.unit_type,
                origin.c.unit_id.label("origin_unit_id"),
                origin.c.status.label("task_status"),
                origin.c.error.label("task_error"),
                run.c.project_id,
                run.c.runtime_id.label("runtime_fingerprint"),
                config.c.params.label("configuration"),
                config.c.config_hash,
                method.c.name.label("method"),
            )
            .select_from(member)
            .join(selected, selected.c.id == member.c.task_id)
            .join(origin, origin.c.id == member.c.origin_task_id)
            .join(result, result.c.task_id == origin.c.id)
            .join(config, config.c.id == origin.c.method_config_id)
            .join(method, method.c.id == config.c.method_id)
            .join(run, run.c.id == origin.c.run_id)
            .where(
                member.c.cut_id == source.cut_id,
                selected.c.run_id == source.run_id,
                selected.c.unit_type == "source_view",
                selected.c.unit_id == source.source_view_id,
                selected.c.status.in_(("done", "reused")),
                origin.c.id == func.coalesce(selected.c.reused_task_id, selected.c.id),
                origin.c.id == identity,
                origin.c.release_id == source.release_id,
                method.c.name == "extract.m1_annotations",
                method.c.version == "2",
            )
        )
        budget.preflight(conn, query)
        row = conn.execute(query).mappings().one_or_none()
        if row is None:
            raise SemanticRefusal("definition witness annotation is outside the original cut")
        if identity not in seen_reports:
            budget.value(dict(row))
            seen_reports.add(identity)
            yield {"origin_task_id": identity, **dict(row)}


def _predicate_annotation_origin_ids(body: Mapping[str, Any]) -> set[int]:
    return {
        op["annotation_origin_task_id"]
        for op in body.get("contribution_operations", ())
        if "annotation_origin_task_id" in op
        and op.get("question") in {"source_predicate_frames", "source_predicate_interpretation"}
    }


def _retained_report_ids(report: Mapping[str, Any]) -> set[int]:
    # This is the declared upstream-input ABI of the typed replay operation,
    # not a recursive interpretation of arbitrary returned JSON.
    if report.get("method") == "resolve.m1_readings":
        values = report["configuration"].get("retained_source_tasks", ())
    elif report.get("method") == "structure.scoped_relations":
        body = report.get("body") or {}
        values = (
            tuple(_predicate_annotation_origin_ids(body))
            + tuple(
                op["annotation_origin_task_id"]
                for op in body.get("contribution_operations", ())
                if op.get("question") == "source_named_links" and "annotation_origin_task_id" in op
            )
            + tuple(
                ref["origin_task_id"]
                for ref in report["configuration"].get("classification_refs", ())
            )
        )
    elif report.get("method") == "structure.definition_components":
        product = (report.get("body") or {}).get("structural_product") or {}
        values = tuple(
            component["witness"]["annotation_task_id"]
            for component in (product.get("definition_components") or {}).get("components", ())
            if component.get("witness") is not None
        )
    elif report.get("method") == "structure.clause_classification":
        values = tuple(
            focus["frame"]["origin_task_id"] for focus in report["configuration"]["focuses"]
        )
    elif report.get("method") == "locate.definition_terms":
        values = tuple(
            role["report"]["origin_task_id"]
            for role in report["configuration"].get("role_refs", ())
        )
    elif report.get("method") == "retrieve.contextual":
        from .contextual_query_replay import retained_query_selection
        from .contextual_witness_replay import witness_origin_ids

        body, config = report.get("body") or {}, report["configuration"]
        query_context = (
            retained_query_selection(report["method"], body.get("operation_version"), config)
            if body
            else None
        )
        values = witness_origin_ids(body, config) | (
            {binding.evidence.origin_task_id for binding in query_context.bindings}
            if query_context is not None
            else set()
        )
    else:
        return set()
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


def _exact_closure(
    conn, selection: ReviewSelection, cancellation: OperationCancellation
) -> tuple[ReviewSelection, list[dict[str, Any]]]:
    """Extend the selection with its authenticated retained predecessors."""
    from corpus_structure.semantic.observations import source_python
    from corpus_structure.semantic.operations import BoundReader
    from corpus_structure.semantic.structural_products import RetainedDefinitionRoleRef
    from corpus_structure.serve.contribution_composition import interpretation_predecessors

    from .contextual_query_replay import query_context_dependency, retained_query_selection

    if selection.completeness != "selected_source_closure":
        raise SemanticRefusal("exact closure requires selected_source_closure")
    pending = list(selection.structural_selections)
    seen_scopes = set(pending)
    readers: dict[tuple[int, int], BoundReader] = {}
    contribution_groups: dict[tuple[int, int], set[str]] = {}
    dependency_origins: set[int] = set()
    seen_references = set()
    reasons: list[dict[str, Any]] = []
    budget = PublishedReadBudget(selection.max_source_rows, selection.max_bytes)

    def reader_for(reference):
        key = (reference.run_id, reference.cut_id)
        if key not in readers:
            session = bind_completed_result(conn, reference.run_id)
            readers[key] = BoundReader(
                conn, reference.run_id, session.prepared, cut_id=reference.cut_id, analysis=False
            )
        return readers[key]

    def include_structural(reference):
        if reference in seen_references:
            return
        seen_references.add(reference)
        retained = reader_for(reference).retained_structural_report(reference)
        budget.value(retained)
        dependency = StructuralExportRequest(
            run_id=reference.run_id,
            cut_id=reference.cut_id,
            selected_task_id=reference.selected_task_id,
            include_publication=bool(retained["public_assertions"]),
            include_support=bool(retained["public_assertions"]),
        )
        if dependency not in seen_scopes:
            pending.append(dependency)
            seen_scopes.add(dependency)

    def include_contribution(reference):
        if reference in seen_references:
            return
        seen_references.add(reference)
        retained = reader_for(reference).retained_source_contribution(reference)
        budget.value(retained)
        dependency_origins.add(reference.origin_task_id)
        group = contribution_groups.setdefault(
            (reference.run_id, reference.selected_task_id), set()
        )
        group.update(row["contribution_id"] for row in retained["contributions"])
        if len(group) > 1000:
            raise SemanticRefusal(
                "exact closure exceeds one producer's contribution selection limit"
            )

    def record_reason(reason):
        budget.value(reason)
        reasons.append(reason)
        if len(reasons) > selection.max_source_rows:
            raise SemanticRefusal("exact closure exceeds declared predecessor budget")

    def record_dependency(identity, reference):
        record_reason(
            {
                "required_by": identity,
                "reason": "declared_retained_predecessor",
                "reference": reference.model_dump(mode="json"),
            }
        )

    for request in selection.selections:
        if request.method not in (None, "extract.pm2_d1"):
            continue
        cancellation.check_active()
        page = _contributions(
            conn,
            request.model_copy(
                update={
                    "method": "extract.pm2_d1",
                    "include_details": True,
                    "include_interpretation": False,
                    "include_publication": False,
                    "include_support": False,
                    "include_assessment": False,
                    "include_relationships": False,
                    "max_bytes": min(request.max_bytes, selection.max_bytes),
                }
            ),
            paginate=False,
        )
        for item in page.items:
            if item["population"] != "contribution":
                continue
            row = item["row"]
            if not isinstance(row, dict) or not isinstance(
                semantic_type := row.get("semantic_type"), str
            ):
                raise SemanticRefusal("retained contribution lacks a typed meaning")
            if not semantic_type.startswith("interpretation."):
                continue
            identity, task, value = (
                row.get("contribution_id"),
                row.get("selected_task_id"),
                row.get("value"),
            )
            if (
                not isinstance(identity, str)
                or type(task) is not int
                or not isinstance(value, dict)
            ):
                raise SemanticRefusal("retained interpretation lacks exact selected custody")
            references, _ = interpretation_predecessors(source_python(value))
            for reference in references:
                record_dependency(identity, reference)
                include_contribution(reference)
            members = row.get("members")
            if members and (request.contribution_ids or request.contribution_id or request.kind):
                # Exact-ID selections need the local source members in the detached inventory too.
                if not isinstance(members, list):
                    raise SemanticRefusal("retained interpretation has invalid selected members")
                group = contribution_groups.setdefault((request.run_id, task), set())
                for member in members:
                    if not isinstance(member, str):
                        raise SemanticRefusal(
                            "retained interpretation has invalid selected members"
                        )
                    group.add(member)
                if len(group) > 1000:
                    raise SemanticRefusal(
                        "exact closure exceeds one producer's contribution selection limit"
                    )

    for request in selection.selections:
        if request.method not in (None, "locate.definition_terms"):
            continue
        cancellation.check_active()
        page = _contributions(
            conn,
            request.model_copy(
                update={
                    "method": "locate.definition_terms",
                    "include_details": True,
                    "include_publication": False,
                    "include_support": False,
                    "include_assessment": False,
                    "include_relationships": False,
                }
            ),
            paginate=False,
        )
        origins = {
            identity
            for item in page.items
            if item["population"] == "report"
            and isinstance(row := item["row"], dict)
            and type(identity := row.get("origin_task_id")) is int
        }
        if origins:
            task, config = table("ops.task"), table("ops.method_config")
            rows = conn.scalars(
                select(config.c.params)
                .join(task, task.c.method_config_id == config.c.id)
                .where(task.c.id.in_(origins))
            )
            for params in rows:
                for raw_ref in params.get("role_refs", ()):
                    include_structural(RetainedDefinitionRoleRef.model_validate(raw_ref).report)

    for request in pending:
        after = 0
        while True:
            cancellation.check_active()
            page = read_structural_export_page(
                conn,
                request.model_copy(
                    update={
                        "after_task_id": after,
                        "max_bytes": min(request.max_bytes, selection.max_bytes - budget.bytes),
                    }
                ),
            )
            if request.selected_task_id is not None and not page.reports and after == 0:
                raise SemanticRefusal(
                    f"exact structural task {request.selected_task_id} is unavailable "
                    f"in run {request.run_id}, cut {page.cut_id}"
                )
            for report in page.reports:
                cancellation.check_active()
                budget.value(report)
                structural, contributions = _structural_predecessors(report)
                for reference in (*structural, *contributions):
                    record_dependency(report.product_id, reference)
                for reference in structural:
                    include_structural(reference)
                for reference in contributions:
                    include_contribution(reference)
                for reference in _dossier_relationship_refs(report):
                    if reference in seen_references:
                        continue
                    seen_references.add(reference)
                    budget.value(reader_for(reference).retained_relationship_decision(reference))
                    identifiers = contribution_groups.setdefault(
                        (reference.run_id, reference.selected_task_id), set()
                    )
                    identifiers.add(reference.occurrence_contribution_id)
                    if len(identifiers) > 1000:
                        raise SemanticRefusal(
                            "exact closure exceeds one producer's contribution selection limit"
                        )
            if page.next_after_task_id is None:
                break
            after = page.next_after_task_id
    for request in selection.selections:
        if request.method not in (None, "retrieve.contextual"):
            continue
        cancellation.check_active()
        page = _contributions(
            conn,
            request.model_copy(
                update={
                    "method": "retrieve.contextual",
                    "include_details": False,
                    "include_publication": False,
                    "include_support": False,
                    "include_interpretation": False,
                    "include_assessment": False,
                    "include_relationships": False,
                    "max_bytes": min(request.max_bytes, selection.max_bytes),
                }
            ),
            paginate=False,
        )
        dependency_origins.update(
            identity
            for item in page.items
            if item["population"] == "report"
            and isinstance(row := item["row"], dict)
            and row.get("cut_member") is True
            and row.get("operations_present") is True
            and type(identity := row.get("origin_task_id")) is int
        )
    if dependency_origins:
        task, config, method, run = map(
            table, ("ops.task", "ops.method_config", "ops.method", "ops.run")
        )
        query = (
            select(task.c.id, task.c.release_id, run.c.project_id, config.c.params)
            .select_from(task)
            .join(config, config.c.id == task.c.method_config_id)
            .join(method, method.c.id == config.c.method_id)
            .join(run, run.c.id == task.c.run_id)
            .where(
                task.c.id.in_(dependency_origins),
                method.c.name == "retrieve.contextual",
                method.c.version == "11",
            )
            .order_by(task.c.id)
        )
        budget.preflight(conn, query)
        for origin, release, project, config in conn.execute(query).all():
            budget.value(config)
            selection_context = retained_query_selection("retrieve.contextual", "11", config)
            assert selection_context is not None
            references = dict.fromkeys(binding.evidence for binding in selection_context.bindings)
            for reference in references:
                if (reference.project_id, reference.release_id) != (project, release):
                    raise SemanticRefusal(
                        "query context predecessor differs from its project or release"
                    )
                record_reason(query_context_dependency(origin, reference))
                include_contribution(reference)
    extras = (
        ContributionRequest(
            run_id=run,
            selected_task_id=task,
            contribution_ids=tuple(sorted(identifiers)),
            max_bytes=min(selection.max_bytes, 134_217_728),
        )
        for (run, task), identifiers in sorted(contribution_groups.items())
    )
    return selection.model_copy(
        update={
            "selections": tuple(dict.fromkeys((*selection.selections, *extras))),
            "structural_selections": tuple(pending),
        }
    ), reasons


def export_review_bundle(
    selection: ReviewSelection,
    destination: Path,
    settings: Settings,
    *,
    cancellation: OperationCancellation | None = None,
    extra_relations: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    evaluator_capture: Callable[[Any], Mapping[str, Iterable[Mapping[str, Any]]]] | None = None,
    exact_closure: bool = False,
    retain_binding: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    cancellation = cancellation or OperationCancellation()
    cancellation.check_active()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    from corpus_structure.serve.review_views import compose_review_views

    # Resolve expansion and capture under the same snapshot. The row owner closes
    # the snapshot before write_review_bundle verifies and publishes the bundle.
    with ExitStack() as snapshot:
        engine = snapshot.enter_context(
            open_runtime_engine(
                settings, "review-export", purpose="evaluate" if evaluator_capture else "read"
            )
        )
        conn = snapshot.enter_context(read_snapshot(engine, cancellation=cancellation.postgresql))
        if retain_binding is not None:
            retain_binding(_review_binding(conn, selection))
        reasons = []
        if exact_closure:
            selection, reasons = _exact_closure(conn, selection, cancellation)
        if (
            selection.structural_gap_selections
            and selection.completeness == "selected_source_closure"
        ):
            selection = selection.model_copy(update={"require_original_gap_reports": True})

        def rows():
            try:
                yield from capture_review_relations(conn, selection, cancellation)
                yield from _named_rows("closure_dependencies", reasons)
                if evaluator_capture is not None:
                    for name, values in evaluator_capture(conn).items():
                        yield from _named_rows(name, values)
            except BaseException:
                snapshot.__exit__(*sys.exc_info())
                raise
            else:
                snapshot.close()
            for name, values in (extra_relations or {}).items():
                yield from _named_rows(name, values)

        return write_review_bundle(
            selection,
            destination,
            compose_review_views(selection, rows()),
            cancellation=cancellation,
        )


def _review_binding(conn: Connection, selection: ReviewSelection) -> str:
    """Identify the acquired database and immutable completed roots in this snapshot."""
    completed = table("ops.completed_result")
    run_ids = sorted(
        {
            request.run_id
            for request in (
                *selection.selections,
                *selection.structural_selections,
                *selection.structural_gap_selections,
                *selection.source_decision_selections,
            )
        }
        | {
            request.binding_task.run_id
            for request in selection.structural_gap_selections
            if request.binding_task is not None
        }
        | {request.opportunity.source.run_id for request in selection.source_decision_journeys}
        | {
            layer.run_id
            for request in selection.source_decision_journeys
            for layer in request.layers
        }
    )
    rows = (
        conn.execute(
            select(completed).where(completed.c.run_id.in_(run_ids)).order_by(completed.c.run_id)
        )
        .mappings()
        .all()
    )
    if len(rows) != len(run_ids):
        raise SemanticRefusal("review requires a completed result for every selected run")
    database = conn.exec_driver_sql(
        "SELECT current_database(), d.oid, current_setting('port'), "
        "CASE WHEN has_function_privilege('pg_catalog.pg_control_system()', 'EXECUTE') "
        "THEN (SELECT system_identifier FROM pg_catalog.pg_control_system()) END "
        "FROM pg_catalog.pg_database d WHERE d.datname = current_database()"
    ).one()
    driver = conn.connection.driver_connection
    if driver is None:
        raise SemanticRefusal("review source connection is unavailable")
    endpoint = driver.info
    return sha256(
        canonical_bytes(
            _json(
                {
                    "database": list(database),
                    "host": endpoint.hostaddr or endpoint.host,
                    "roots": [dict(row) for row in rows],
                }
            )
        )
    ).hexdigest()


def _named_rows(name, values):
    try:
        for value in values:
            yield name, value
    finally:
        close = getattr(values, "close", None)
        if close is not None:
            close()


@contextmanager
def _member(
    root: int,
    name: str,
    *,
    digest: str | None = None,
    size: int | None = None,
):
    if Path(name).name != name or name in {"", ".", ".."}:
        raise ValueError("invalid review member path")
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
    except OSError as error:
        raise ValueError("review member missing or not an ordinary file") from error
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("review member missing or not an ordinary file")
        if size is not None and before.st_size != size:
            raise ValueError("review file integrity differs")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            if digest is not None:
                if file_digest(stream, "sha256").hexdigest() != digest:
                    raise ValueError("review file integrity differs")
                stream.seek(0)
            yield stream
            after = os.fstat(fd)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise ValueError("review member changed during verification")
    finally:
        os.close(fd)


def _relation_member(root: int, file: Mapping[str, Any]):
    return _member(root, file["path"], digest=file["sha256"], size=file["bytes"])


def _verify_dossier_structural_closure(
    root, manifest, dossiers, products, scopes, assertions, contribution_scopes, inventory
):
    """Replay declared structural predecessors across their exact selected snapshots."""
    from corpus_structure.methods.structural_products import derive_dossier_members, dossier_root
    from corpus_structure.semantic.structural_admission import structural_claim_id
    from corpus_structure.semantic.structural_products import StructuralProductReport

    dossier_ids = {report.product_id for report in dossiers}
    origins = {
        product.product_id: origin
        for _, _, origin, *_, product in products
        if product.product_id in dossier_ids
    }
    origin_ids = {ref.origin_task_id for report in dossiers for ref in report.dossier.predecessors}
    origin_ids.update(origins.values())
    origin_ids.update(
        ref.origin_task_id for report in dossiers for ref in _dossier_relationship_refs(report)
    )
    raw_reports = {}
    spec = manifest["relations"].get("reports")
    if spec is not None:
        with _relation_member(root, spec["files"]["jsonl"]) as stream:
            for line in stream:
                raw = json.loads(json.loads(line)["payload_json"])
                if raw["origin_task_id"] in origin_ids:
                    raw_reports[raw["origin_task_id"]] = raw
    roots = {}
    relationships = _detached_dossier_relationships(
        root, manifest, dossiers, raw_reports, contribution_scopes, inventory
    )
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
        selections = report.dossier.comparison_selections
        own = raw_reports.get(origins[report.product_id], {})
        frozen = (own.get("configuration") or {}).get("comparison_selections", [])
        if canonical_bytes(frozen) != canonical_bytes(
            [s.model_dump(mode="json") for s in selections]
        ):
            raise ValueError("dossier comparison bindings differ from frozen configuration")
        expected_members, expected_facets = derive_dossier_members(
            report.inputs,
            retained,
            root=component,
            root_ref=root_ref,
            comparison_selections=selections,
            relationships=relationships,
            require_comparison_focus=(own.get("body") or {}).get("operation_version") == "3",
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


def _detached_dossier_relationships(root, manifest, dossiers, raw_reports, scopes, inventory):
    from corpus_structure.semantic.retained_contributions import RetainedContributionRef

    requested = {}
    for report in dossiers:
        for ref in _dossier_relationship_refs(report):
            requested.setdefault(ref, report)
    payloads = _retained_contribution_payloads(
        root,
        manifest,
        [
            (
                report,
                RetainedContributionRef(
                    contribution_id=ref.occurrence_contribution_id,
                    **ref.model_dump(
                        exclude={
                            "operation_key",
                            "decision_id",
                            "edge_id",
                            "occurrence_contribution_id",
                        }
                    ),
                ),
            )
            for ref, report in requested.items()
        ],
        scopes,
        inventory,
    )
    relationships = {}
    for ref, payload in zip(requested, payloads, strict=True):
        body = raw_reports[ref.origin_task_id]["body"]
        (operation,) = [
            row
            for row in body["contribution_operations"]
            if row["operation_key"] == ref.operation_key
        ]
        product = operation["contextual_enrichment"]
        (decision,) = [
            row
            for row in product["relationship_decisions"]
            if row["decision_id"] == ref.decision_id
        ]
        (edge,) = [row for row in decision["selected_edges"] if row["edge_id"] == ref.edge_id]
        (occurrence,) = [
            row
            for row in payload["contributions"]
            if row["contribution_id"] == ref.occurrence_contribution_id
        ]
        if (
            product["version"] != "contextual-enrichment-2"
            or occurrence["semantic_type"] != "contextual.located_mention"
            or occurrence["occurrence_id"] != decision["occurrence_id"]
            or not any(
                ref.occurrence_contribution_id in w["evidence_ids"] for w in edge["witnesses"]
            )
        ):
            raise ValueError("dossier binding differs from the actual retained relationship")
        (source,) = payload["sources"]
        projection = source["projection"]
        located = []
        for anchor in occurrence["anchors"]:
            (piece,) = [
                p
                for p in projection["pieces"]
                if p["kind"] == "native_text"
                and anchor["pointer"]
                == p["item_ref"]
                + ("/data/table_cells/" + str(p["cell_index"]) if "cell_index" in p else "")
            ]
            start, end = piece["start"] + anchor["start"], piece["start"] + anchor["end"]
            if (
                anchor["pin"] != source["pin"]
                or (anchor["space"], anchor["precision"]) != ("native", "exact")
                or not piece["start"] <= start < end <= piece["end"]
                or projection["text"][start:end] != anchor["source_piece"]
            ):
                raise ValueError("dossier relationship location differs from original source")
            located.append(dict(start=start, end=end, text=anchor["source_piece"]))
        relationships[ref] = dict(
            decision=decision,
            edge=edge,
            component_targets=product["component_targets"],
            source_view_id=source["source_view_id"],
            located_occurrence=sorted(
                located, key=lambda row: (row["start"], row["end"], row["text"])
            ),
        )
    return relationships


def _detached_relation(root, manifest, name):
    spec = manifest["relations"].get(name)
    if spec is None:
        return
    with _relation_member(root, spec["files"]["jsonl"]) as stream:
        for line in stream:
            yield json.loads(json.loads(line)["payload_json"])


def _verify_source_projections(root, manifest):
    from corpus_structure.semantic.product_reference import ProductReference

    from .review_source_projection import (
        archived_projection_policy,
        load_source_proofs,
        open_proof_index,
        verify_source_projection,
    )

    if not {"sources", "source_proofs"} & manifest["relations"].keys():
        return set()
    contracts = {row["release_id"]: row for row in _detached_relation(root, manifest, "contracts")}
    with (
        TemporaryDirectory(prefix="corpus-review-proof-") as temporary,
        closing(open_proof_index(Path(temporary) / "records.sqlite")) as database,
    ):
        proofs = load_source_proofs(database, _detached_relation(root, manifest, "source_proofs"))
        used = set()
        originals = set()
        policies = {}
        for row in _detached_relation(root, manifest, "sources"):
            ref = row["ref"]
            native = ProductReference(**ref["native_product"])
            release = row.get("consumer_release")
            if native not in proofs or release not in contracts:
                raise ValueError("review source requires an exact native proof and archived policy")
            if release not in policies:
                policies[release] = archived_projection_policy(contracts[release])
            original = verify_source_projection(row, policies[release], proofs[native])
            used.add(native)
            originals.add((ref["document_id"], original))
        if set(proofs) != used:
            raise ValueError("review native proof is outside the selected source closure")
        return originals


def _verify_source_decision_journeys(root, manifest, selection, reports, selected_origins):
    from .source_decision_journey import METHODS

    custody = iter(_detached_relation(root, manifest, "source_journey_custody"))
    answers = iter(_detached_relation(root, manifest, "source_decision_journeys"))
    if selection.source_decision_journeys:
        source_ids = {
            request.opportunity.source.source_view_id
            for request in selection.source_decision_journeys
        }
        sources = {
            row["source_view_id"]: row
            for row in _detached_relation(root, manifest, "sources")
            if row["source_view_id"] in source_ids
        }
        for index, request in enumerate(selection.source_decision_journeys):
            original = request.opportunity.source
            scope = next(custody, None)
            if (
                scope is None
                or scope["selection_index"] != index
                or scope["layers"].keys() != {layer.layer for layer in request.layers}
                or original.source_view_id not in sources
            ):
                raise ValueError("detached source-decision journey lacks its selected custody")
            tasks = {}
            for layer in request.layers:
                pin = scope["layers"][layer.layer]
                if (
                    pin["run_id"],
                    pin["cut_id"],
                    pin["selected_task_id"],
                    pin["project_id"],
                    pin["method"],
                ) != (
                    layer.run_id,
                    layer.cut_id,
                    layer.task_id,
                    original.project_id,
                    METHODS[layer.layer],
                ):
                    raise ValueError("detached journey layer differs from its requested producer")
                origin = pin["origin_task_id"]
                member = (layer.run_id, layer.cut_id, layer.task_id, origin)
                if pin["cut_member"] != (member in selected_origins):
                    raise ValueError("detached journey layer differs from exact selected origin")
                report = reports.get(origin)
                body = None
                if pin["cut_member"] and pin["task_status"] in {"done", "empty", "reused"}:
                    if report is None or (
                        report.get("project_id"),
                        report.get("method", (report.get("body") or {}).get("method")),
                        report.get("runtime_fingerprint"),
                    ) != (pin["project_id"], pin["method"], pin["runtime_fingerprint"]):
                        raise ValueError("detached journey layer lacks its original report")
                    body = report["body"]
                    if (
                        body.get("release_id") != pin["release_id"]
                        or body.get("outcome") != pin["operation_outcome"]
                    ):
                        raise ValueError(
                            "detached journey report differs from its original outcome"
                        )
                tasks[layer.layer] = pin, body
            expected = source_decision_journey(request, sources[original.source_view_id], tasks)
            if next(answers, None) != {
                "selection_index": index,
                **expected.model_dump(mode="json"),
            }:
                raise ValueError("detached journey differs from original selected evidence")
    if next(custody, None) is not None or next(answers, None) is not None:
        raise ValueError("detached review contains an unrequested source-decision journey")


def _verify_structural_gaps(root, manifest, selection):
    from corpus_structure.serve.structural_gaps import (
        METHODS,
        gap_review_source_ids,
        verify_gap_review_custody,
    )

    captured = {}
    for row in _detached_relation(root, manifest, "structural_gap_sources"):
        index = row.pop("selection_index")
        if index in captured:
            raise ValueError("duplicate detached gap evidence selection")
        captured[index] = row
    if captured.keys() != set(range(len(selection.structural_gap_selections))):
        raise ValueError("detached gap evidence differs from requested selections")
    pages = iter(_detached_relation(root, manifest, "structural_gaps"))
    custody_rows = list(_detached_relation(root, manifest, "structural_gap_custody"))
    originals = iter(custody_rows)
    source_ids = {
        identity
        for row in custody_rows
        if "bindings" in row
        for identity in gap_review_source_ids(row)
    }
    sources = (
        {
            row["source_view_id"]: row
            for row in _detached_relation(root, manifest, "sources")
            if row["source_view_id"] in source_ids
        }
        if source_ids
        else {}
    )
    for index, original in enumerate(selection.structural_gap_selections):
        evidence = captured[index]
        producer = evidence["producer"]
        binding = evidence["binding_producer"]
        if (
            (producer["run_id"], producer["selected_task_id"], producer["method"])
            != (original.run_id, original.task_id, METHODS[original.report])
            or (original.cut_id is not None and original.cut_id != producer["cut_id"])
            or (original.binding_task is None) != (binding is None)
        ):
            raise ValueError("detached gap producer differs from selected custody")
        if binding is not None and (
            (binding["run_id"], binding["selected_task_id"], binding["method"])
            != (original.binding_task.run_id, original.binding_task.task_id, "structure.dossier")
            or (
                original.binding_task.cut_id is not None
                and original.binding_task.cut_id != binding["cut_id"]
            )
        ):
            raise ValueError("detached gap binding producer differs from selected custody")
        request = original.model_copy(
            update={"max_bytes": min(original.max_bytes, selection.max_bytes)}
        )
        if selection.require_original_gap_reports:
            custody = next(originals, None)
            if custody is None or custody["selection_index"] != index:
                raise ValueError("detached gap selection is missing its original producer reports")
            verify_gap_review_custody(evidence, custody, request, sources)
        while True:
            expected = gap_page(request, evidence)
            if next(pages, None) != {"selection_index": index, **expected.model_dump(mode="json")}:
                raise ValueError("detached structural gap differs from selected producer evidence")
            if expected.next_cursor is None:
                break
            request = request.model_copy(update={"cursor": expected.next_cursor})
    if next(pages, None) is not None:
        raise ValueError("detached gap report includes unrequested results")
    if next(originals, None) is not None:
        raise ValueError("detached gap report includes unrequested original reports")


def _retained_contribution_payloads(
    root,
    manifest,
    requested,
    scopes,
    inventory,
    *,
    origin_sources=False,
    require_cut_member=False,
    origin_reports=None,
):
    """Read exact selected raw provenance and endpoint closure once for dependent products."""
    from jsonschema import Draft202012Validator

    from corpus_structure.methods.pm2_products import PARSER_PROVIDER, validate_parser_members
    from corpus_structure.methods.structural_products import comparison_host_evidence
    from corpus_structure.semantic.contributions import (
        bound_contribution_semantics,
        contribution_identity,
    )

    if not requested:
        return
    contracts = None
    origin_ids = {reference.origin_task_id for _, reference in requested}
    reports = (
        origin_reports
        if origin_reports is not None
        else {
            row["origin_task_id"]: row
            for row in _detached_relation(root, manifest, "reports")
            if row["origin_task_id"] in origin_ids
        }
    )
    source_ids = (
        set()
        if origin_sources
        else {source.source_view_id for report, _ in requested for source in report.inputs.sources}
    )
    sources = {}
    for row in _detached_relation(root, manifest, "sources"):
        if not origin_sources and row["source_view_id"] not in source_ids:
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
    for _report, reference in requested:
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
        component = available.get(reference.contribution_id, {}).get("component", {})
        if component.get("kind") == "predicate_reading":
            frame_id = component["frame"]
            frame = available.get(frame_id, {}).get("component", {})
            pending.extend(
                key
                for key, row in available.items()
                if comparison_host_evidence(row.get("component", {}), frame, frame_id)
            )
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
                and (not require_cut_member or captured.get("cut_member") is True)
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
        parser_rows = [row for row in closure.values() if row["semantic_type"] in PARSER_PROVIDER]
        if parser_rows:
            if contracts is None:
                contracts = {
                    row["release_id"]: row.get("contribution_payload_contracts", {})
                    for row in _detached_relation(root, manifest, "contracts")
                }
            selected = contracts.get(reference.release_id, {})
            operations = {
                op["operation_key"]: op["question"]
                for op in raw["body"].get("contribution_operations", ())
            }
            for row in parser_rows:
                contract = selected.get(row["semantic_type"])
                named_contract = row.get("contract")
                if contract is None and named_contract in {None, "RetainedContributionSemantics"}:
                    continue  # Older releases used the generic private contract.
                question = operations.get(row["operation_key"])
                if (
                    contract is None
                    or named_contract != contract["contract"]
                    or question is None
                    or not Draft202012Validator(contract["schema"]).is_valid(
                        bound_contribution_semantics(row, question=question)
                    )
                ):
                    raise ValueError("retained parser payload differs from its released contract")
                validate_parser_members(row, closure)
        yield dict(
            contributions=list(closure.values()),
            sources=[sources[key] for key in sorted(source_ids)],
        )


def _verify_interpretation_closure(root, manifest, scopes, inventory):
    """Replay the exact source-part and candidate references retained by d1."""
    from corpus_structure.semantic.contextual_storage import interpretation_candidates
    from corpus_structure.semantic.observations import source_python
    from corpus_structure.semantic.retained_contributions import RetainedContributionRef
    from corpus_structure.serve.contribution_composition import interpretation_predecessors

    readings = {}
    for (index, task, origin, identity), row in inventory.items():
        if not row.get("semantic_type", "").startswith("interpretation."):
            continue
        scope = scopes[index]
        reference = RetainedContributionRef(
            contribution_id=identity,
            project_id=scope["project_id"],
            run_id=scope["run_id"],
            cut_id=scope["cut_id"],
            release_id=scope["binding"]["release_id"],
            result_revision=scope["binding"]["data_revision"],
            selected_task_id=task,
            origin_task_id=origin,
            runtime_fingerprint=row["runtime_fingerprint"],
        )
        if row.get("method") != "extract.pm2_d1" or not row.get("cut_member"):
            raise ValueError("interpretation differs from exact producing method or cut")
        readings[reference] = row
    if not readings:
        return set()

    needed = {}
    reasons = set()
    for own, row in readings.items():
        value = source_python(row["value"])
        references, retrieval = interpretation_predecessors(value)
        needed[own] = (value, references, retrieval)
        for reference in references:
            if (reference.project_id, reference.release_id) != (own.project_id, own.release_id):
                raise ValueError("interpretation predecessor belongs to another project or release")
            reasons.add(
                canonical_bytes(
                    {
                        "required_by": own.contribution_id,
                        "reason": "declared_retained_predecessor",
                        "reference": reference.model_dump(mode="json"),
                    }
                )
            )
    refs = tuple(
        dict.fromkeys((*readings, *(ref for _, group, _ in needed.values() for ref in group)))
    )
    payloads = dict(
        zip(
            refs,
            _retained_contribution_payloads(
                root,
                manifest,
                [(None, ref) for ref in refs],
                scopes,
                inventory,
                origin_sources=True,
            ),
            strict=True,
        )
    )
    roots = {
        ref: next(
            row for row in payload["contributions"] if row["contribution_id"] == ref.contribution_id
        )
        for ref, payload in payloads.items()
    }
    retrieval_origins = {
        retrieval.carrier.origin_task_id
        for _, _, retrieval in needed.values()
        if retrieval is not None
    }
    retrieval_reports = (
        {
            row["origin_task_id"]: row
            for row in _detached_relation(root, manifest, "reports")
            if row["origin_task_id"] in retrieval_origins
        }
        if retrieval_origins
        else {}
    )

    for own, (value, references, retrieval) in needed.items():
        actual = roots[own]
        if any(readings[own].get(key) != item for key, item in actual.items()):
            raise ValueError("detached interpretation differs from original retained contents")
        if any(roots[ref]["pin"] != actual["pin"] for ref in references):
            raise ValueError("detached interpretation predecessor differs from original source")
        for candidate in value.get("candidates", ()):
            if "reference" in candidate:
                candidate_ref = RetainedContributionRef.model_validate(candidate["reference"])
                if roots[candidate_ref]["semantic_type"] != candidate["semantic_type"]:
                    raise ValueError(
                        "detached interpretation candidate differs from its retained type"
                    )
        if retrieval is None:
            continue
        carrier = roots[retrieval.carrier]
        origin = retrieval_reports[retrieval.carrier.origin_task_id]
        operations = [
            operation
            for operation in origin["body"]["contribution_operations"]
            if operation["operation_key"] == retrieval.operation_key
        ]
        if (
            origin["method"] != "retrieve.contextual"
            or carrier["semantic_type"] != "contextual.located_mention"
            or carrier["operation_key"] != retrieval.operation_key
            or not carrier.get("anchors")
            or len(operations) != 1
            or not operations[0].get("contextual_enrichment")
        ):
            raise ValueError("detached interpretation candidate list differs from its carrier")
        frozen = interpretation_candidates(
            operations[0]["contextual_enrichment"],
            retrieval.list_id,
            carrier["occurrence_id"],
            tuple(carrier["anchors"]),
        )
        actual_targets = tuple(
            (
                candidate["key"],
                candidate["semantic_type"],
                candidate["target_id"],
                candidate["representation_digest"],
            )
            for candidate in value["candidates"]
            if "target_id" in candidate
        )
        expected_targets = tuple(
            (
                "target_" + sha256(target.target_id.encode()).hexdigest(),
                target.type_name,
                target.target_id,
                target.representation_digest,
            )
            for target in frozen.targets
        )
        if actual_targets != expected_targets:
            raise ValueError(
                "detached interpretation alternatives differ from the exact candidate list"
            )
    return reasons


def _verify_comparison_closure(root, manifest, products, structural_scopes, scopes, inventory):
    from corpus_structure.core.evidence import config_key
    from corpus_structure.methods.structural_products import (
        StructuralComparisonConfig,
        StructuralComparisonMethod,
        compare_clauses,
        read_retained_clause,
    )
    from corpus_structure.semantic.structural_products import StructuralProductReport

    origins = {item[2] for item in products}
    captured = {}
    for raw in _detached_relation(root, manifest, "reports"):
        origin = raw["origin_task_id"]
        if (
            origin in origins
            and (raw.get("body") or {}).get("method") == StructuralComparisonMethod.name
        ):
            if origin in captured:
                raise ValueError("comparison producer raw result repeats")
            captured[origin] = raw

    reports = []
    for index, _selected, origin, origin_run, origin_project, runtime, report in products:
        comparison = report.comparison
        raw = captured.get(origin)
        if comparison is None and raw is None:
            continue
        if raw is None or comparison is None:
            raise ValueError("comparison lacks its exact registered producer result")
        body = raw["body"]
        config = raw.get("configuration")
        version = body.get("operation_version")
        if (
            not isinstance(config, dict)
            or version not in {"2", "3", "4", "5"}
            or raw.get("project_id") != origin_project
            or raw.get("origin_run_id") != origin_run
            or raw.get("runtime_fingerprint") != runtime
            or body.get("release_id") != structural_scopes[index]["release_id"]
            or body.get("outcome") != "produced"
            or body.get("configuration_hash")
            != config_key(StructuralComparisonMethod.name, version, config)
            or body.get("configuration_hash") != raw.get("config_hash")
            or not raw.get("input_hash")
            or body.get("input_hash") != raw["input_hash"]
            or StructuralProductReport.model_validate(body.get("structural_product")) != report
        ):
            raise ValueError("comparison differs from its registered producer result")
        if version == "2":
            if comparison.left_reading is not None or (
                {"left_reading", "right_reading"} & config.keys()
            ):
                raise ValueError("archived singleton comparison has a current reading binding")
            continue
        configured = StructuralComparisonConfig.model_validate(config)
        if (
            comparison.left_reading is None
            or comparison.right_reading is None
            or configured.inputs != report.inputs
            or configured.left_id != comparison.left_id
            or configured.right_id != comparison.right_id
            or configured.left_reading != comparison.left_reading
            or configured.right_reading != comparison.right_reading
        ):
            raise ValueError("comparison differs from its registered predicate readings")
        reports.append((report, version))

    requests = [
        (report, reference)
        for report, _version in reports
        for reference in (report.comparison.left_reading, report.comparison.right_reading)
    ]
    payloads = _retained_contribution_payloads(root, manifest, requests, scopes, inventory)
    for (report, version), (left_payload, right_payload) in zip(
        reports, zip(payloads, payloads, strict=True), strict=True
    ):
        comparison = report.comparison
        passages = {passage.passage_id: passage for passage in report.inputs.passages}
        sources = {source.identity: source for source in report.inputs.sources}
        left, right = passages[comparison.left_id], passages[comparison.right_id]
        predicate_version = version if version in {"4", "5"} else None
        expected = compare_clauses(
            report.inputs,
            left=read_retained_clause(
                left,
                sources[left.source_ref],
                comparison.left_reading,
                left_payload,
                predicate_version=predicate_version,
            ),
            right=read_retained_clause(
                right,
                sources[right.source_ref],
                comparison.right_reading,
                right_payload,
                predicate_version=predicate_version,
            ),
            left_reading=comparison.left_reading,
            right_reading=comparison.right_reading,
            typed_groups=version in {"4", "5"},
        )
        if comparison != expected.comparison:
            raise ValueError("comparison differs from its exact retained predicate evidence")


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
            raise ValueError(
                "dossier source membership differs from original contribution evidence"
            )


def _verify_artifact_nomination_closure(
    root, manifest, artifacts, structural_scopes, contribution_scopes, inventory
):
    from types import SimpleNamespace

    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.methods.artifact_identity import (
        ArtifactIdentityConfig,
        ArtifactIdentityMethod,
    )
    from corpus_structure.semantic.proposals import native_source_frame
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
            or body.get("operation_version") not in {"3", ArtifactIdentityMethod.version}
            or not isinstance(declared, list)
            or len(declared) != len(refs)
            or sorted(declared, key=canonical_bytes) != sorted(refs, key=canonical_bytes)
            or StructuralProductReport.model_validate(body.get("structural_product")) != report
        ):
            raise ValueError(
                "artifact product differs from its registered producer and nomination configuration"
            )
        cfg = ArtifactIdentityConfig.model_validate(config)
        if cfg.inputs != report.inputs:
            raise ValueError("artifact configuration differs from exact selected cohort inputs")
        expected.append((report, cfg, body["operation_version"]))
        requested.extend((report, n.relationship) for n in product.external_nominations)

    payloads = dict(
        zip(
            (ref for _, ref in requested),
            _retained_contribution_payloads(
                root, manifest, requested, contribution_scopes, inventory, origin_sources=True
            ),
            strict=True,
        )
    )
    selected_ids = {s.source_view_id for report, _, _ in expected for s in report.inputs.sources}
    sources = {
        row["source_view_id"]: row
        for row in _detached_relation(root, manifest, "sources")
        if row["source_view_id"] in selected_ids
    }

    def source_frame(inputs, source_ref):
        selected = next(s for s in inputs.sources if s.identity == source_ref)
        return native_source_frame(
            _retained_review_source_view(sources[selected.source_view_id]), ()
        )

    context = SimpleNamespace(
        check_active=lambda: None,
        reader=SimpleNamespace(
            structural_source_frame=source_frame, retained_source_contribution=payloads.__getitem__
        ),
    )
    for report, cfg, version in expected:
        method = ArtifactIdentityMethod()
        method.version = version
        (result,) = method.run(
            (SimpleNamespace(ref=UnitRef(TaskUnitType.RUN, unit_key=report.inputs.identity)),),
            cfg,
            context,
        )
        if StructuralProductReport.model_validate(result.structural_product) != report:
            raise ValueError(
                "artifact cohort, nominations or scores differ from detached source replay"
            )


def _retained_review_source_view(source):
    from corpus_structure.core.method import SourceViewRef
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.source_views import PreparedSourceView

    descriptor = dict(source["ref"])
    descriptor["native_product"] = ProductReference(**descriptor["native_product"])
    context = source["context"]
    return PreparedSourceView(
        SourceViewRef(**descriptor),
        source["text"],
        tuple(context["pieces"]),
        tuple(context["items"]),
        tuple(context["ancestors"]),
        context["health"],
        integrated_context=(
            json.loads(context["integrated_context_json"])
            if "integrated_context_json" in context
            else None
        ),
    )


def _verify_predicate_closure(root, manifest):
    """Replay predicate evidence against the retained annotations and physical source pieces."""
    from jsonschema import Draft202012Validator

    from corpus_structure.ingest.annotations import AnnotationProfile, restore_annotations
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.predicate_contributions import (
        INCOMPATIBLE_QUALIFIER,
        MISSING_QUALIFIER,
        predicate_results,
        publish_predicate_evidence,
    )
    from corpus_structure.semantic.observations import source_python
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import (
        NativeSourceContext,
        SourceSlice,
        record_source_pin,
    )
    from corpus_structure.semantic.structural_products import StructuralInput

    if "reports" not in manifest["relations"]:
        return
    scoped, producers = [], {}
    for row in _detached_relation(root, manifest, "reports"):
        body = row["body"] or {}
        if row.get("method") == "extract.m1_annotations":
            producers[row["origin_task_id"]] = row
        elif row.get("method") == "structure.scoped_relations" and any(
            contribution["semantic_type"] == "structural.predicate_frame"
            or contribution["semantic_type"] == "structural.predicate_cue"
            for contribution in body.get("contributions", ())
        ):
            scoped.append(row)
    if not scoped:
        return
    qualifier_schemas = {
        row["release_id"]: row[_PREDICATE_QUALIFIER_SCHEMA]
        for row in _detached_relation(root, manifest, "contracts")
        if _PREDICATE_QUALIFIER_SCHEMA in row
    }
    source_ids = {row["origin_unit_id"] for row in scoped}
    sources = {
        row["source_view_id"]: row
        for row in _detached_relation(root, manifest, "sources")
        if row["source_view_id"] in source_ids
    }
    for row in scoped:
        (producer_id,) = _predicate_annotation_origin_ids(row["body"])
        producer = producers.get(producer_id)
        if (
            producer is None
            or producer["origin_unit_id"] != row["origin_unit_id"]
            or producer["project_id"] != row["project_id"]
            or producer["body"].get("operation_version") != "2"
        ):
            raise ValueError("predicate evidence lacks the exact annotation producer")
        source = sources[row["origin_unit_id"]]
        view = _retained_review_source_view(source)
        ref = view.ref
        frame = native_source_frame(view, ())
        details = source_python(producer["body"]["parse_detail"])
        configuration = row["configuration"]
        profile = AnnotationProfile(
            SentenceConfig.model_validate(configuration.get("sentences", {}))
        )
        annotation = restore_annotations(details["annotations"], source=frame, profile=profile)
        configured = configuration.get("inputs")
        passages = None
        if configured is not None:
            inputs = StructuralInput.model_validate(configured)
            (external,) = tuple(ref for ref in inputs.sources if ref.source_view_id == view.ref.id)
            passages = tuple(p for p in inputs.passages if p.source_ref == external.identity)
        context = NativeSourceContext(
            frame,
            (),
            (SourceSlice(ref.id, 0, len(view.text)),),
            "native structural composition",
            "scoped-source-joins-1",
            "selected source",
            max_chars=max(1, len(view.text)),
            max_pieces=max(1, len(view.pieces)),
        )
        method_version = row["body"].get("operation_version")
        version = {"4": "2", "5": "3", "6": "3", "7": "3", "8": "3", "9": "4", "10": "5"}.get(
            method_version
        )
        predicate_operations = [
            op
            for op in row["body"].get("contribution_operations", ())
            if op["question"] in {"source_predicate_frames", "source_predicate_interpretation"}
        ]
        if version is None or {op["operation_version"] for op in predicate_operations} != {version}:
            raise ValueError("unsupported retained predicate replay version")
        replay = []
        released_qualifier = row["body"]["release_id"] in qualifier_schemas
        qualifier_schema = qualifier_schemas.get(row["body"]["release_id"])
        validator = Draft202012Validator(qualifier_schema) if qualifier_schema is not None else None

        def qualifier_preflight(component, validator=validator):
            if validator is None:
                return MISSING_QUALIFIER
            return (
                None
                if validator.is_valid(json.loads(canonical_bytes(component)))
                else INCOMPATIBLE_QUALIFIER
            )

        replay_operations = publish_predicate_evidence(
            frame,
            context,
            record_source_pin(frame),
            "native:" + str(ref.native_product.task_id),
            predicate_results(
                frame, annotation, view.pieces, {item["self_ref"]: item for item in view.items}
            ),
            tuple(details.get("annotation_errors", ())),
            producer_id,
            passages,
            replay,
            {},
            version=version,
            qualifier_preflight=qualifier_preflight if released_qualifier else None,
        )
        actual = {
            c["contribution_id"]: canonical_bytes(c)
            for c in row["body"]["contributions"]
            if c["semantic_type"].startswith("structural.predicate_")
        }
        expected = {c["contribution_id"]: canonical_bytes(c) for c in replay}
        if actual != expected:
            raise ValueError(
                "predicate evidence differs from retained source and annotation replay"
            )
        if released_qualifier:
            fields = ("question", "outcome", "emitted_count", "reason")
            if {tuple(op.get(key) for key in fields) for op in predicate_operations} != {
                tuple(op.get(key) for key in fields) for op in replay_operations
            }:
                raise ValueError("predicate outcomes differ from released attachment replay")


@dataclass(frozen=True, slots=True)
class _VerifiedReview:
    manifest: dict[str, Any]
    selected_bindings: list[dict[str, Any]]


_REVIEW_BINDING_LIMIT = 8


def verify_review_bundle(root: Path | int, *, manifest_digest: str | None = None) -> dict[str, Any]:
    """Verify a detached path or borrow an authenticated directory descriptor."""
    return _verified_review(root, manifest_digest).manifest


def _verified_review(root: Path | int, manifest_digest: str | None) -> _VerifiedReview:
    if isinstance(root, int):
        return _verify_review_bundle(root, manifest_digest)
    try:
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    except OSError as error:
        raise ValueError("review member missing or not an ordinary file") from error
    try:
        return _verify_review_bundle(descriptor, manifest_digest)
    finally:
        os.close(descriptor)


def _verify_review_bundle(root: int, manifest_digest: str | None) -> _VerifiedReview:
    with _member(root, "manifest.json", digest=manifest_digest) as stream:
        manifest = json.load(stream)
    if manifest.get("format") != FORMAT:
        raise ValueError("unsupported review format")
    selection = ReviewSelection.model_validate(manifest["selection"])
    digest = sha256(canonical_bytes(selection.model_dump(mode="json"))).hexdigest()
    if digest != manifest["selection_digest"] or manifest["completeness"] != selection.completeness:
        raise ValueError("review selection differs")
    expected = {"manifest.json", manifest["overview"]["path"]}
    with _member(root, manifest["overview"]["path"]) as overview:
        if file_digest(overview, "sha256").hexdigest() != manifest["overview"]["sha256"]:
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
    document_originals: set[tuple[int, str]] = set()
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
    report_inventory = {}
    required_contracts: set[str] = set()
    captured_contracts: set[str] = set()
    closure_reasons: set[bytes] = set()
    exact_contributions = any(
        request.selected_task_id is not None or request.contribution_ids
        for request in selection.selections
    )
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
            logical = LogicalRows(schema, ("row_id",))
            if suffix == "parquet":
                with _relation_member(root, file) as stream:
                    parquet = pq.ParquetFile(stream)
                    if not parquet.schema_arrow.equals(schema, check_metadata=True):
                        raise ValueError("review parquet schema differs")
                    for batch in parquet.iter_batches(batch_size=128):
                        logical.write(batch)
            else:
                with _relation_member(root, file) as stream:
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
                                or (
                                    (cut_id := selection.structural_selections[index].cut_id)
                                    is not None
                                    and payload["cut_id"] != cut_id
                                )
                            ):
                                raise ValueError("structural selected run/cut differs")
                            bound_structural.add(index)
                            structural_scopes[index] = payload
                            required_contracts.add(payload["release_id"])
                        if name == "contracts":
                            captured_contracts.add(payload["release_id"])
                        if name == "closure_dependencies":
                            closure_reasons.add(canonical_bytes(payload))
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

                            index = payload["selection_index"]
                            if type(index) is not int or not 0 <= index < len(
                                selection.structural_selections
                            ):
                                raise ValueError("structural product has no selected snapshot")
                            selected_task = selection.structural_selections[index].selected_task_id
                            if (
                                selected_task is not None
                                and payload["selected_task_id"] != selected_task
                            ):
                                raise ValueError(
                                    "structural product differs from exact selected task"
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
                        elif name == "documents" and isinstance(payload.get("content_hash"), str):
                            document_originals.add((payload["id"], payload["content_hash"]))
                        elif name == "reports":
                            needed_sources.update(_report_source_ids(payload["body"]))
                            for ref in _section_source_refs(payload):
                                needed_sources.add(ref.source_view_id)
                                structural_refs[ref.identity] = ref
                                required_contracts.add(ref.release_id)
                            if payload.get("unit_type") == "source_view":
                                needed_sources.add(payload["origin_unit_id"])
                            needed_reports.update(_retained_report_ids(payload))
                            present_reports.add(payload["origin_task_id"])
                        elif name == "inventory":
                            item = payload["row"]
                            index = payload.get("selection_index")
                            if type(index) is int and 0 <= index < len(selection.selections):
                                request = selection.selections[index]
                                if (
                                    request.selected_task_id is not None
                                    and item.get("selected_task_id") != request.selected_task_id
                                ):
                                    raise ValueError(
                                        "contribution row differs from exact selected task"
                                    )
                                if (
                                    payload.get("population") == "contribution"
                                    and request.contribution_ids
                                    and item.get("contribution_id") not in request.contribution_ids
                                ):
                                    raise ValueError(
                                        "contribution row is outside exact selected IDs"
                                    )
                            elif exact_contributions:
                                raise ValueError("contribution row has no selected scope")
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
                                    origin = item["origin_task_id"]
                                    task = item.get("selected_task_id")
                                    report_inventory[(index, task, origin)] = item
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
    interpretation_reasons = (
        _verify_interpretation_closure(root, manifest, contribution_scopes, contribution_inventory)
        if selection.completeness == "selected_source_closure"
        else set()
    )
    from .contextual_query_replay import verify_contextual_query_closure

    query_context_reasons = (
        verify_contextual_query_closure(
            root, manifest, contribution_scopes, contribution_inventory, report_inventory
        )
        if selection.completeness == "selected_source_closure"
        else set()
    )
    if "closure_dependencies" in manifest["relations"]:
        declared_reasons = {
            canonical_bytes(
                {
                    "required_by": product.product_id,
                    "reason": "declared_retained_predecessor",
                    "reference": reference.model_dump(mode="json"),
                }
            )
            for *_, product in structural_products
            for group in _structural_predecessors(product)
            for reference in group
        }
        if closure_reasons != declared_reasons | interpretation_reasons | query_context_reasons:
            raise ValueError("review closure reasons differ from declared retained predecessors")
    if not public_product_ids <= structural_product_ids:
        raise ValueError("public structural witness has no selected product")
    if selection.completeness == "selected_source_closure":
        from .inline_formula_replay import verify_inline_formula_closure
        from .model_observation_replay import (
            verify_model_concordance_closure,
            verify_model_observation_closure,
            verify_projected_definition_roles,
        )
        from .table_correspondence_replay import verify_table_correspondence_closure

        _verify_predicate_closure(root, manifest)
        verify_table_correspondence_closure(root, manifest)
        verify_inline_formula_closure(root, manifest)
        from .contextual_witness_replay import verify_contextual_witness_closure

        verify_contextual_witness_closure(root, manifest)
        verify_model_observation_closure(
            root, manifest, structural_products, contribution_scopes, contribution_inventory
        )
        verify_projected_definition_roles(root, manifest, structural_products, structural_scopes)
        verify_model_concordance_closure(root, manifest)
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
                contribution_scopes,
                contribution_inventory,
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
                root,
                manifest,
                artifacts,
                structural_scopes,
                contribution_scopes,
                contribution_inventory,
            )
        if structural_products:
            _verify_comparison_closure(
                root,
                manifest,
                structural_products,
                structural_scopes,
                contribution_scopes,
                contribution_inventory,
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
        if not _verify_source_projections(root, manifest) <= document_originals:
            raise ValueError("review source projection original differs from its retained document")
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
            sources = manifest["relations"]["sources"]["files"]["jsonl"]
            pending_sources = {entry[0] for entry in structural_reports}
            with _relation_member(root, sources) as source_stream:
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
    if set(os.listdir(root)) != expected:
        raise ValueError("review package has undeclared or missing members")
    _verify_structural_gaps(root, manifest, selection)
    decision_evidence = iter(_detached_relation(root, manifest, "source_decision_evidence"))
    decisions = iter(_detached_relation(root, manifest, "source_decisions"))
    reports = {}
    selected_origins = set()
    if selection.source_decision_selections or selection.source_decision_journeys:
        reports = {
            row["origin_task_id"]: row for row in _detached_relation(root, manifest, "reports")
        }
        selected_origins = {
            (scope["run_id"], scope["cut_id"], row["selected_task_id"], row["origin_task_id"])
            for payload in _detached_relation(root, manifest, "inventory")
            if (scope := contribution_scopes.get(payload.get("selection_index"))) is not None
            if (row := payload["row"]).get("cut_member")
        }
        selected_origins.update(
            (scope["run_id"], scope["cut_id"], row["selected_task_id"], row["origin_task_id"])
            for row in _detached_relation(root, manifest, "structural_products")
            if (scope := structural_scopes.get(row["selection_index"])) is not None
        )
        for index, request in enumerate(selection.source_decision_selections):
            evidence = next(decision_evidence, None)
            if evidence is None or evidence["selection_index"] != index:
                raise ValueError("detached source decision evidence is missing")
            origin = evidence["origin_task_id"]
            if (request.run_id, request.cut_id, request.task_id, origin) not in selected_origins:
                raise ValueError("detached source decision has no exact selected origin")
            expected_evidence = source_decision_capture_from_body(
                request, request.cut_id, origin, reports[origin]["body"]
            )
            if evidence != {"selection_index": index, **expected_evidence}:
                raise ValueError("detached diagnosis evidence differs from the retained report")
            expected = source_decision_from_capture(request, expected_evidence).model_dump(
                mode="json"
            )
            if next(decisions, None) != {"selection_index": index, **expected}:
                raise ValueError("detached diagnosis differs from the retained evidence")
    _verify_source_decision_journeys(root, manifest, selection, reports, selected_origins)
    if next(decision_evidence, None) is not None or next(decisions, None) is not None:
        raise ValueError("detached review contains unrequested source diagnoses")

    bindings = []
    remaining = _REVIEW_BINDING_LIMIT
    for kind, requests, scopes in (
        ("contribution", selection.selections, contribution_scopes),
        ("structural", selection.structural_selections, structural_scopes),
    ):
        visible = min(remaining, len(requests))
        for index in range(visible):
            if (scope := scopes.get(index)) is not None:
                bindings.append(
                    {
                        "kind": kind,
                        "index": index,
                        "run_id": scope["run_id"],
                        "cut_id": scope["cut_id"],
                    }
                )
        remaining -= visible
    return _VerifiedReview(manifest, bindings)


def inspect_review_bundle(
    root: Path | int, *, manifest_digest: str | None = None
) -> dict[str, Any]:
    verified = _verified_review(root, manifest_digest)
    manifest = verified.manifest
    return {
        "format": FORMAT,
        "selection": manifest["selection"],
        "selected_bindings": verified.selected_bindings,
        "completeness": manifest["completeness"],
        "relations": {name: spec["rows"] for name, spec in manifest["relations"].items()},
        "assessment_scope": manifest["assessment_scope"],
        "original_source_completeness": manifest["original_source_completeness"],
    }
