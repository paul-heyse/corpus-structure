"""Bounded PostgreSQL text search over explicitly selected native PDF sources."""

from __future__ import annotations

import base64
import json
import math
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.refusal_types import InvalidContinuation
from corpus_structure.serve.native_source import NativeSourceRequest
from corpus_structure.serve.selected_pdf import (
    SelectedPdfSourceReference,
    acquire_selected_pdf_source,
)


class SourceSearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[5] = 5
    project_id: str = Field(min_length=1)
    demand_id: str = Field(min_length=1)
    read_id: str = Field(min_length=1)
    sources: tuple[SelectedPdfSourceReference, ...] = Field(min_length=1, max_length=100)
    sections: tuple[str, ...] = ()
    membership: Literal["direct", "descendants"] = "direct"
    text: str = Field(min_length=1, max_length=4096)
    limit: int = Field(default=20, ge=1, le=100)
    max_rows: int = Field(default=10000, strict=True, ge=1, le=10000)
    max_bytes: int = Field(default=1048576, strict=True, ge=1, le=8388608)
    cursor: str | None = None

    @model_validator(mode="after")
    def exact_population(self):
        expected = self.project_id, self.demand_id, self.read_id
        if any(
            (source.project_id, source.demand_id, source.read_id) != expected
            for source in self.sources
        ):
            raise ValueError("source search population must belong to one explicit pinned cut")
        keys = [source.model_dump_json() for source in self.sources]
        if len(set(keys)) != len(keys) or len(set(self.sections)) != len(self.sections):
            raise ValueError("source search repeats a source or section selector")
        return self


class SourceSearchHit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: SelectedPdfSourceReference
    original_source: str
    source_digest: str
    projection_digest: str
    selection: NativeSourceRequest
    excerpt: str
    score: float


class SourceSearchResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal["selected-source-search-1"] = "selected-source-search-1"
    cut: dict
    rows: list[SourceSearchHit]
    next_cursor: str | None = None
    population_complete: bool


def _continuation(request):
    if request.cursor is None:
        return None
    try:
        if len(request.cursor.encode()) > 8192:
            raise ValueError("oversized search cursor")
        body = json.loads(base64.b64decode(request.cursor, altchars=b"-_", validate=True))
        if (
            not isinstance(body, dict)
            or set(body) != {"version", "selection", "score", "key"}
            or body["version"] != 1
            or not isinstance(body["selection"], str)
        ):
            raise ValueError("invalid search cursor binding")
        score = float.fromhex(body["score"])
        if not math.isfinite(score) or score < 0 or not isinstance(body["key"], str):
            raise ValueError("invalid search position")
        return dict(selection=body["selection"], score=score, key=body["key"])
    except (ValueError, TypeError, KeyError) as error:
        raise InvalidContinuation(
            "invalid or stale source search continuation", reason="invalid_continuation"
        ) from error


def _position(request, selection):
    body = _continuation(request)
    if body is None:
        return None
    if body["selection"] != selection:
        raise InvalidContinuation(
            "search cursor belongs to another source population", reason="invalid_continuation"
        )
    return body["score"], body["key"]


def search_source(connection, request: SourceSearchRequest) -> SourceSearchResponse:
    from corpus_structure.semantic._data_operation_wire import WireRankPdfSearchProjectionRequest
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
    from corpus_structure.semantic.pdf_source_search import (
        ensure_search_projection,
        population_identity,
        projection_recipe,
    )
    from corpus_structure.semantic.refusal_types import ReadLimit

    after = _continuation(request)
    sources, recipes, cut = [], [], None
    for reference in request.sources:
        source = acquire_selected_pdf_source(connection, reference)
        if cut is not None and source.cut.content != cut.content:
            raise ValueError("source search pins differ in current interpretation or trust")
        cut = source.cut
        recipe, policy = projection_recipe(connection, source)
        sources.append(source)
        recipes.append((recipe, policy))
    if cut is None:
        raise ValueError("source search requires its explicit source population")
    # Locks survive the producer call until commit. Canonical order avoids A/B
    # versus B/A deadlocks across multi-publication first searches.
    for index in sorted(
        range(len(sources)), key=lambda i: population_identity(sources[i], recipes[i][0])
    ):
        recipe, policy = recipes[index]
        ensure_search_projection(connection, sources[index], recipe=recipe, policy=policy)
    payload = dict(
        binding=request.model_dump(mode="json", exclude={"cursor", "limit"}),
        cut_id=cut.identity,
        sources=[
            dict(source=source.reference.model_dump(), recipe=recipe)
            for source, (recipe, _) in zip(sources, recipes, strict=True)
        ],
        limit=min(request.limit, request.max_rows),
    )
    if after is not None:
        payload["after"] = after
    try:
        ranked = DataOperationStorage(connection).rank_pdf_search_projection(
            cast(WireRankPdfSearchProjectionRequest, payload)
        )
    except DBAPIError as error:
        if after is not None and getattr(error.orig, "sqlstate", None) == "22023":
            raise InvalidContinuation(
                "invalid or stale source search continuation", reason="invalid_continuation"
            ) from error
        raise
    _position(request, ranked["selection"])
    budget = PublishedReadBudget(request.max_rows, request.max_bytes)
    rows = []
    for result in ranked["rows"]:
        source = sources[result["source_index"]]
        hit = SourceSearchHit(
            source=source.reference,
            original_source=source.original_source,
            source_digest=source.receipt.publication.source_digest,
            projection_digest=result["projection_digest"],
            selection=NativeSourceRequest(
                **source.reference.model_dump(),
                section_pointer=result["section_pointer"],
                membership=result["membership"],
                projection_digest=result["projection_digest"],
                max_rows=request.max_rows,
                max_bytes=request.max_bytes,
            ),
            excerpt=result["excerpt"],
            score=result["score"],
        )
        budget.reserve_rows(1)
        budget.value(hit.model_dump(mode="json"))
        rows.append(hit)
    cursor = None
    if ranked["more"]:
        last = ranked["rows"][-1]
        cursor = base64.urlsafe_b64encode(
            canonical_bytes(
                dict(
                    version=1,
                    selection=ranked["selection"],
                    score=float(last["score"]).hex(),
                    key=last["key"],
                )
            )
        ).decode()
    response = SourceSearchResponse(
        cut=cut.record, rows=rows, next_cursor=cursor, population_complete=not ranked["more"]
    )
    if len(canonical_bytes(response.model_dump(mode="json"))) > request.max_bytes:
        raise ReadLimit(
            "complete source search envelope exceeds max_bytes", reason="oversized_item"
        )
    return response
