"""Pinned source-record journeys over the released finite projection.

The underlying reader refuses over-budget populations in full. Paging here describes
only presentation of that detached population; it never establishes source coverage,
accepted knowledge, calibration or scientific truth.
"""

from __future__ import annotations

import base64
import json
from dataclasses import asdict, replace
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from sqlalchemy import Connection, select

from corpus_structure.semantic.continuations import decode_continuation, validate_continuation
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_queries import TerminologySelection
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.record_projection import (
    ARTIFACT,
    read_record_projection,
    reconstruct_record,
)
from corpus_structure.semantic.record_queries import (
    CompletedRecordProjection,
    RecordProducerCoverage,
    RecordReadLimit,
    RecordReadSelection,
    read_completed_record_projection,
)
from corpus_structure.semantic.records import source_record_address
from corpus_structure.semantic.refusals import InvalidContinuation, SemanticRefusal
from corpus_structure.serve.journey import params_digest
from corpus_structure.serve.native_source import NativeSourceRequest

PositiveId = Annotated[int, Field(strict=True, gt=0)]
VERSION = "source-record-journey-1"


class RecordRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: PositiveId
    project_id: str | None = None
    source_view_ids: tuple[PositiveId, ...] | None = None
    family: str | None = None
    standing: str | None = None
    record_id: str | None = None
    interpretation_id: str | None = None
    terminology: TerminologySelection | None = None
    include_diagnostics: bool = Field(default=False, strict=True)
    cursor: str | None = None
    limit: int = Field(default=20, strict=True, ge=1, le=100)
    max_records: int = Field(default=10_000, strict=True, ge=1, le=10_000)
    max_rows: int = Field(default=100_000, strict=True, ge=1, le=100_000)
    max_bytes: int = Field(default=32 * 1024**2, strict=True, ge=1, le=32 * 1024**2)
    page_bytes: int = Field(default=1024**2, strict=True, ge=1, le=32 * 1024**2)

    @model_validator(mode="after")
    def normalized_selection(self):
        if self.interpretation_id is not None and self.record_id is None:
            raise ValueError("an interpretation selector requires its record identity")
        if self.source_view_ids is not None:
            if len(set(self.source_view_ids)) != len(self.source_view_ids):
                raise ValueError("duplicate record source-view selector")
            object.__setattr__(self, "source_view_ids", tuple(sorted(self.source_view_ids)))
        return self

    def filters(self) -> dict[str, Any]:
        # Presentation and resource bounds may change without changing the selection.
        return self.model_dump(
            exclude={"cursor", "limit", "max_records", "max_rows", "max_bytes", "page_bytes"}
        )


class RecordAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    record: dict[str, JsonValue]
    admission: tuple[dict[str, JsonValue], ...]
    assertions: tuple[dict[str, JsonValue], ...]
    source_requests: tuple[NativeSourceRequest, ...]
    terminology_reviews: tuple[dict[str, JsonValue], ...] = ()


class RecordPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal["source-record-journey-1"] = VERSION
    run_id: int
    binding: dict[str, JsonValue]
    cut_id: int
    projection_digest: str
    selection: dict[str, JsonValue]
    released_projection: dict[str, JsonValue]
    records: tuple[RecordAnswer, ...]
    reports: tuple[dict[str, JsonValue], ...]
    coverage: tuple[RecordProducerCoverage, ...] = ()
    coverage_diagnostic: str = (
        "sealed producer coverage describes workflow inspection; neither complete inspection "
        "nor empty candidate output establishes completeness of captured knowledge"
    )
    report_source_view_ids: dict[int, int]
    matching_records: int
    returned_records: int
    population_paging_complete: bool
    source_coverage: Literal["not_established_by_record_projection"] = (
        "not_established_by_record_projection"
    )
    next_cursor: str | None = None


def _json(value: Any) -> Any:
    """Use the canonical transport without introducing float numeric conversions."""
    return json.loads(canonical_bytes(value))


def presented_coverage(
    coverage: tuple[RecordProducerCoverage, ...], *, include_diagnostics: bool
) -> tuple[RecordProducerCoverage, ...]:
    """Omit optional bodies explicitly; immutable producer IDs remain their locator."""
    if include_diagnostics:
        if any(not row.diagnostics_included for row in coverage):
            raise SemanticRefusal("detached record coverage did not include requested diagnostics")
        return coverage
    return tuple(
        replace(
            row,
            diagnostics=None,
            diagnostics_included=False,
            diagnostics_available=row.diagnostics_available or row.diagnostics is not None,
        )
        for row in coverage
    )


def _query_identity(projection: CompletedRecordProjection, request: RecordRequest) -> str:
    return _selection_identity(request, projection.cut_id, projection.projection_digest)


def _selection_identity(request: RecordRequest, cut_id: int, projection_digest: str) -> str:
    return params_digest(
        dict(
            version=VERSION,
            selection=request.filters(),
            cut=cut_id,
            projection=projection_digest,
        )
    )


def _cursor(projection: CompletedRecordProjection, query: str, after: tuple[str, str]) -> str:
    return base64.urlsafe_b64encode(
        canonical_bytes(
            dict(
                release=projection.release_id,
                realization=projection.realization_id,
                revision=projection.data_revision,
                query=query,
                after=json.dumps(after, separators=(",", ":")),
            )
        )
    ).decode("ascii")


def _position(body: dict[str, Any]) -> tuple[str, str]:
    try:
        value = json.loads(body["after"])
    except (ValueError, TypeError) as error:
        raise InvalidContinuation("invalid record continuation position") from error
    if not (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(item, str) and item for item in value)
    ):
        raise InvalidContinuation("invalid record continuation position")
    return value[0], value[1]


def present_record_projection(
    projection: CompletedRecordProjection,
    request: RecordRequest,
) -> RecordPage:
    """Present already detached rows; adapters never reconstruct admission policy."""
    if request.run_id != projection.run_id:
        raise SemanticRefusal("record request names another completed run")
    if request.source_view_ids != projection.source_view_ids:
        raise SemanticRefusal("record request source scope differs from detached projection")
    released = read_record_projection(projection.prepared)
    if request.family is not None and request.family not in {
        family["family"] for family in released["families"]
    }:
        raise SemanticRefusal("record family is not declared by the completed release")
    if request.standing is not None and request.standing not in projection.prepared.enum_members(
        "RecordStanding"
    ):
        raise SemanticRefusal("record standing is not declared by the completed release")
    query = _query_identity(projection, request)
    after = None
    if request.cursor is not None:
        body = decode_continuation(request.cursor, kind="primitive")
        validate_continuation(
            projection.prepared,
            body,
            dict(
                release=projection.release_id,
                realization=projection.realization_id,
                revision=projection.data_revision,
                query=query,
            ),
        )
        after = _position(body)
    if projection.selection is not None and projection.selection != RecordReadSelection(
        family=request.family,
        standing=request.standing,
        record_id=request.record_id,
        interpretation_id=request.interpretation_id,
        terminology=request.terminology,
        after=after,
        limit=request.limit,
    ):
        raise SemanticRefusal("record presentation differs from reader-selected roots")

    # The semantic owner indexes the detached projection once per invocation.
    # Nested fields/sets/alternatives never rescan the population or hydrate via DB.
    index = projection.record_index
    keys = sorted(
        (row.record_id, row.interpretation_id)
        for row in projection.rows["source_record"]
        if (request.family is None or row.family == request.family)
        and (
            request.standing is None
            or any(
                a["decision"] == request.standing
                for a in index.rows_for(row.record_id, row.interpretation_id, "record_admission")
            )
        )
        and (request.record_id is None or row.record_id == request.record_id)
        and (
            request.interpretation_id is None or row.interpretation_id == request.interpretation_id
        )
    )
    if projection.selection is None and after is not None and after not in keys:
        raise InvalidContinuation("record continuation position is outside the selected population")
    remaining = (
        keys
        if projection.selection is not None
        else [key for key in keys if after is None or key > after]
    )
    page = remaining[: request.limit]
    answers = []
    for record_id, interpretation_id in page:
        record = reconstruct_record(index, record_id, interpretation_id)
        requests = {}
        for anchor in record["anchors"]:
            pin = anchor["pin"]
            # The full anchor remains authoritative for coordinate space/precision.
            # Cell occurrences open through the parent item and exact cell selector.
            pointer, cell_index = source_record_address(anchor["pointer"])
            native = NativeSourceRequest(
                run_id=projection.run_id,
                task_id=pin["native_product_task_id"],
                product_key=pin["product_key"],
                content_digest=pin["product_digest"],
                view="cell" if cell_index is not None else "item",
                pointer=pointer,
                cell_index=cell_index,
            )
            requests[native.selection_digest()] = native
        answers.append(
            RecordAnswer(
                record=_json(record),
                admission=tuple(
                    _json(dict(row))
                    for row in index.rows_for(record_id, interpretation_id, "record_admission")
                ),
                assertions=tuple(
                    _json(dict(row))
                    for row in index.rows_for(record_id, interpretation_id, "record_assertion")
                ),
                source_requests=tuple(requests[key] for key in sorted(requests)),
                terminology_reviews=tuple(
                    _json(dict(row))
                    for row in projection.terminology_matches
                    if row["record_id"] == record_id
                    and row["interpretation_id"] == interpretation_id
                ),
            )
        )
    more = (
        projection.more_records if projection.selection is not None else len(remaining) > len(page)
    )
    result = RecordPage(
        run_id=projection.run_id,
        binding=_json(asdict(projection.binding)),
        cut_id=projection.cut_id,
        projection_digest=projection.projection_digest,
        selection=_json(request.filters()),
        released_projection=_json(released),
        records=tuple(answers),
        reports=tuple(_json(asdict(row)) for row in projection.rows["record_report"]),
        coverage=presented_coverage(
            projection.coverage, include_diagnostics=request.include_diagnostics
        ),
        report_source_view_ids=dict(projection.report_source_view_ids),
        matching_records=(
            projection.matching_records if projection.matching_records is not None else len(keys)
        ),
        returned_records=len(page),
        population_paging_complete=not more,
        next_cursor=_cursor(projection, query, page[-1]) if more else None,
    )
    if len(result.model_dump_json().encode()) > request.page_bytes:
        raise RecordReadLimit("record page exceeds its response byte budget; narrow the selection")
    return result


def read_record_result_projection(
    conn: Connection, request: RecordRequest
) -> CompletedRecordProjection:
    """Use the caller's existing read-only session and its completed-result pin."""
    from corpus_structure.semantic.query import bind_completed_result

    session = bind_completed_result(conn, request.run_id)
    after = None
    if request.cursor is not None:
        body = decode_continuation(request.cursor, kind="primitive")
        # Validate identity before using an untrusted cursor to select any root.
        # The immutable cut lookup returns one scalar, never record payloads.
        completed = table("ops.completed_result")
        cut_id = conn.execute(
            select(completed.c.cut_id).where(completed.c.run_id == request.run_id)
        ).scalar_one()
        artifact = next(
            (item for item in session.prepared.artifacts if item.kind == ARTIFACT), None
        )
        if artifact is None:
            raise SemanticRefusal("completed release has no supported record projection")
        validate_continuation(
            session.prepared,
            body,
            dict(
                release=session.binding.release_id,
                realization=session.binding.realization_id,
                revision=session.binding.data_revision,
                query=_selection_identity(request, cut_id, artifact.digest),
            ),
        )
        after = _position(body)
    projection = read_completed_record_projection(
        conn,
        run_id=request.run_id,
        project_id=request.project_id,
        source_view_ids=request.source_view_ids,
        max_records=request.max_records,
        max_rows=request.max_rows,
        max_bytes=request.max_bytes,
        selection=RecordReadSelection(
            family=request.family,
            standing=request.standing,
            record_id=request.record_id,
            interpretation_id=request.interpretation_id,
            terminology=request.terminology,
            after=after,
            limit=request.limit,
        ),
        include_diagnostics=request.include_diagnostics,
    )
    validate_continuation(
        projection.prepared,
        dict(
            release=projection.release_id,
            realization=projection.realization_id,
            revision=projection.data_revision,
        ),
        dict(
            release=session.binding.release_id,
            realization=session.binding.realization_id,
            revision=session.binding.data_revision,
        ),
    )
    return projection


def serve_record_results(conn: Connection, request: RecordRequest) -> RecordPage:
    return present_record_projection(read_record_result_projection(conn, request), request)
