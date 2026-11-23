"""Acquire the real PDF publication behind one pinned semantic selection.

The native owner proves selection, producing support and sealed publication.
Physical task/build addresses returned here are execution evidence, not aliases
for semantic products, subjects or demand identities.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.product_reference import ProductReference

if TYPE_CHECKING:
    from corpus_structure.semantic.pdf_observations import PdfObservationExecutionReceipt
    from corpus_structure.semantic.pdf_publication import PdfExecutionReceipt
    from corpus_structure.semantic.types import PreparedRelease


class SelectedPdfSourceReference(BaseModel):
    """Selected PDF product address; the native read operation proves its kind."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    project_id: str = Field(min_length=1)
    demand_id: str = Field(min_length=1)
    read_id: str = Field(min_length=1)
    use_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    derivation_id: str = Field(min_length=1)


@dataclass(frozen=True)
class SelectedPdfSource:
    reference: SelectedPdfSourceReference
    cut: CutSelection
    receipt: PdfExecutionReceipt
    prepared: PreparedRelease
    original_source: str

    @property
    def physical(self) -> ProductReference:
        publication = self.receipt.publication
        return ProductReference(
            publication.task_id, publication.product_key, publication.logical_digest
        )


@dataclass(frozen=True)
class SelectedPdfObservations:
    reference: SelectedPdfSourceReference
    cut: CutSelection
    receipt: PdfObservationExecutionReceipt
    prepared: PreparedRelease
    original_source: str


def acquire_selected_pdf_observations(
    connection, reference: SelectedPdfSourceReference
) -> SelectedPdfObservations:
    """Open an exact observation set without granting sealed publication standing."""
    from corpus_structure.semantic._data_operation_wire import WireReadSelectedPdfSourceRequest
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.data_operation_wire import validate_native_wire
    from corpus_structure.semantic.pdf_observations import PdfObservationExecutionReceipt
    from corpus_structure.semantic.releases import open_release

    request = cast(
        WireReadSelectedPdfSourceRequest,
        validate_native_wire(
            "read_selected_pdf_observations", "input", reference.model_dump(mode="python")
        ),
    )
    result = DataOperationStorage(connection).read_selected_pdf_observations(request)
    cut = CutSelection(json_bytes(result["cut"]))
    pins = cut.record
    if (pins["project_id"], pins["demand_id"], pins["read_id"]) != (
        reference.project_id,
        reference.demand_id,
        reference.read_id,
    ):
        raise ValueError("selected observation receipt belongs to another pinned read")
    receipt = PdfObservationExecutionReceipt.model_validate_json(json_bytes(result["receipt"]))
    return SelectedPdfObservations(
        reference,
        cut,
        receipt,
        open_release(connection, pins["release_id"]),
        result["original_source"],
    )


def _pdf_source_request(reference: SelectedPdfSourceReference):
    from corpus_structure.semantic._data_operation_wire import WireReadSelectedPdfSourceRequest
    from corpus_structure.semantic.data_operation_wire import validate_native_wire

    return cast(
        WireReadSelectedPdfSourceRequest,
        validate_native_wire(
            "read_selected_pdf_source",
            "input",
            reference.model_dump(include=set(SelectedPdfSourceReference.model_fields)),
        ),
    )


def _selected_pdf_source(reference, result, prepare):
    from corpus_structure.semantic.pdf_publication import PdfExecutionReceipt

    cut = CutSelection(json_bytes(result["cut"]))
    pins = cut.record
    if (pins["project_id"], pins["demand_id"], pins["read_id"]) != (
        reference.project_id,
        reference.demand_id,
        reference.read_id,
    ):
        raise ValueError("selected PDF receipt belongs to another pinned read")
    receipt = TypeAdapter(PdfExecutionReceipt).validate_json(
        json_bytes(result["receipt"]), strict=True
    )
    return SelectedPdfSource(
        reference, cut, receipt, prepare(pins["release_id"]), result["original_source"]
    )


def acquire_selected_pdf_source(
    connection, reference: SelectedPdfSourceReference
) -> SelectedPdfSource:
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.releases import open_release

    reference = SelectedPdfSourceReference.model_validate(
        reference.model_dump(include=set(SelectedPdfSourceReference.model_fields))
    )
    result = DataOperationStorage(connection).read_selected_pdf_source(
        _pdf_source_request(reference)
    )
    return _selected_pdf_source(
        reference, result, lambda release: open_release(connection, release)
    )


def acquire_selected_pdf_sources(
    connection, references: tuple[SelectedPdfSourceReference, ...]
) -> tuple[SelectedPdfSource, ...]:
    """Acquire all catalog receipts together, retaining each exact semantic address."""
    from corpus_structure.semantic.releases import open_release

    releases = {}

    def prepare(release):
        if release not in releases:
            releases[release] = open_release(connection, release)
        return releases[release]

    requests = [_pdf_source_request(reference) for reference in references]
    results = _read_selected_pdf_source_batch(connection, requests)
    return tuple(
        _selected_pdf_source(reference, result, prepare)
        for reference, result in zip(references, results, strict=True)
    )


def _read_selected_pdf_source_batch(connection, requests):
    """Invoke the installed receipt guard once per address in one SQL statement."""
    from corpus_structure.semantic.ordered_native_answers import read_ordered_native_answers

    return cast(
        tuple[dict[str, Any], ...],
        read_ordered_native_answers(connection, "read_selected_pdf_source", requests),
    )


def published_catalog_rows(conn, references, *, cancellation, max_bytes):
    """Acquire revisions and bounded header envelopes using the released read ports."""
    from sqlalchemy import BigInteger, Integer, Text, bindparam, column, func, literal, select
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.sql.elements import BindParameter, ClauseElement
    from sqlalchemy.sql.visitors import replacement_traverse

    from corpus_structure.semantic._pdf_native_calls import (
        materialize_read_pdf_published_revision,
        materialize_read_pdf_record_rows,
        prepare_read_pdf_published_revision,
        prepare_read_pdf_record_rows,
    )
    from corpus_structure.semantic.pdf_record_reader import _record_envelope, _record_parameters
    from corpus_structure.semantic.refusal_types import ReadLimit

    if not references:
        return ()

    request_rows = [
        dict(ordinal=ordinal, **_record_parameters(ref)) for ordinal, ref in enumerate(references)
    ]
    columns = (
        column("ordinal", Integer()),
        column("task_id", BigInteger()),
        column("product_key", Text()),
        column("content_digest", Text()),
    )
    inputs = (
        func.jsonb_to_recordset(bindparam("catalog_pins", request_rows, type_=JSONB))
        .table_valued(*columns)
        .render_derived(name="pdf_catalog_pins", with_types=True)
    )
    sample = _record_parameters(references[0])

    def across_pins(statement, name):
        def replace_parameter(element: ClauseElement, **kw: Any) -> ClauseElement | None:
            if isinstance(element, BindParameter):
                key = "content_digest" if element.key == "logical_digest" else element.key
                if key in ("task_id", "product_key", "content_digest"):
                    return inputs.c[key]
            return None

        query = replacement_traverse(statement, {}, replace_parameter).lateral(name)
        return select(inputs.c.ordinal, *query.c).select_from(inputs.join(query, literal(True)))

    revisions = across_pins(
        prepare_read_pdf_published_revision(
            task_id=sample["task_id"],
            product_key=sample["product_key"],
            logical_digest=sample["content_digest"],
        ),
        "catalog_revision",
    )
    # Retain one extra row for each uniqueness check, as the scalar reader does.
    health = across_pins(
        prepare_read_pdf_record_rows(
            **sample, family="companion", filters={"family": "health"}, after=None, limit=3
        ),
        "catalog_health",
    )
    runtime = across_pins(
        prepare_read_pdf_record_rows(
            **sample,
            family="companion",
            filters={"family": "native_metadata", "kind": "runtime_report"},
            after=None,
            limit=2,
        ),
        "catalog_runtime",
    )

    # The materialized rows are private SQL execution state. Refuse oversized
    # responses before transfer, without running the native read a second time.
    def bounded(statement):
        selected = statement.cte("catalog_header_rows").prefix_with("MATERIALIZED")
        size = sum(
            (func.coalesce(func.octet_length(field.cast(Text)), 0) for field in selected.c),
            literal(0),
        )
        allowed = (
            select(func.coalesce(func.sum(size), 0) <= 2 * max_bytes)
            .select_from(selected)
            .scalar_subquery()
        )
        guarded = select(allowed.label("allowed")).subquery()
        return select(guarded.c.allowed, *selected.c).select_from(
            guarded.outerjoin(selected, guarded.c.allowed)
        )

    def group[Row](statement, decode: Callable[[list[Any]], Row]) -> list[list[Row]]:
        groups: list[list[Row]] = [[] for _ in references]
        # The guard always supplies a row, including when the batch is absent.
        with conn.execute(bounded(statement)) as rows:
            for allowed, ordinal, *row in rows:
                if not allowed:
                    raise ReadLimit("native source byte-work budget exhausted", reason="work_limit")
                if ordinal is not None:
                    groups[ordinal].append(decode(row))
        cancellation.check_active()
        return groups

    def envelope(row):
        return _record_envelope(materialize_read_pdf_record_rows(row))

    def revision_envelope(row):
        return materialize_read_pdf_published_revision(row).model_dump(mode="python")

    with cancellation.borrow(conn):
        revision_rows = group(revisions, revision_envelope)
        health_rows = group(health, envelope)
        runtime_rows = group(runtime, envelope)
    result = []
    for revision, health, runtime in zip(revision_rows, health_rows, runtime_rows, strict=True):
        if len(revision) != 1:
            raise ValueError("native source requires one exact published record")
        result.append((revision[0], health, runtime))
    return tuple(result)
