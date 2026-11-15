"""Bounded PostgreSQL text search over explicitly selected native PDF sources."""

from __future__ import annotations

import base64
import json
import math
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Double, Text, and_, column, func, literal_column, or_, select, values

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.refusals import InvalidContinuation
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


def _position(request, selection):
    if request.cursor is None:
        return None
    try:
        if len(request.cursor.encode()) > 8192:
            raise ValueError("oversized search cursor")
        body = json.loads(base64.b64decode(request.cursor, altchars=b"-_", validate=True))
        if (
            set(body) != {"version", "selection", "score", "key"}
            or body["version"] != 1
            or body["selection"] != selection
        ):
            raise ValueError("search cursor belongs to another source population")
        score = float.fromhex(body["score"])
        if not math.isfinite(score) or score < 0 or not isinstance(body["key"], str):
            raise ValueError("invalid search position")
        return score, body["key"]
    except (ValueError, TypeError, KeyError) as error:
        raise InvalidContinuation(
            "invalid or stale source search continuation", reason="invalid_continuation"
        ) from error


def _rank_sections(connection, texts, text, *, position, limit):
    """Keep the established English PostgreSQL ranking and excerpt semantics."""
    if not texts:
        return ()
    source = values(
        column("key", Text()), column("text", Text()), name="selected_source_text"
    ).data(texts)
    config = literal_column("'english'::regconfig")
    query = func.websearch_to_tsquery(config, text)
    vector = func.to_tsvector(config, source.c.text)
    # Widen the server's real value before transport. A shortened real text
    # spelling can otherwise lose equality with the server's tie boundary.
    score = func.ts_rank_cd(vector, query).cast(Double())
    statement = select(
        source.c.key,
        func.ts_headline(config, source.c.text, query, "MaxWords=45,MinWords=15").label("excerpt"),
        score.label("score"),
    ).where(vector.op("@@")(query))
    if position is not None:
        previous_score, previous_key = position
        statement = statement.where(
            or_(
                score < previous_score,
                and_(score == previous_score, source.c.key.collate("C") > previous_key),
            )
        )
    return tuple(
        connection.execute(
            statement.order_by(score.desc(), source.c.key.collate("C")).limit(limit)
        ).mappings()
    )


def search_source(connection, request: SourceSearchRequest) -> SourceSearchResponse:
    from corpus_structure.ingest.pdf_section_views import published_section_projections
    from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader, PublishedReadBudget
    from corpus_structure.semantic.refusals import ReadLimit
    from corpus_structure.semantic.source_products import FrozenNativeSource

    budget = PublishedReadBudget(request.max_rows, request.max_bytes)
    population, cut = {}, None
    for reference in request.sources:
        source = acquire_selected_pdf_source(connection, reference)
        if cut is not None and source.cut.content != cut.content:
            raise ValueError("source search pins differ in current interpretation or trust")
        cut = source.cut
        reader = PublishedPdfReader(
            connection, source.physical, projection_context=source.prepared, read_budget=budget
        )
        for row in published_section_projections(
            reader,
            selections=request.sections,
            membership=request.membership,
            scope=None,
        ):
            projected = FrozenNativeSource.from_projection(
                source.prepared,
                document=source.original_source,
                section_pointer=row.section_pointer,
                membership=row.membership,
                text=row.text,
                pieces=row.pieces,
                items=row.items,
                ancestors=row.ancestors,
                recognition=row.health.get("formula_outcomes", ()),
            )
            digest = projected.value["source"]["projection"]
            key = canonical_bytes(
                [reference.model_dump(), row.section_pointer, row.membership, digest]
            ).decode()
            # The publication is selected; the derived search projection claims no
            # additional product admission, standing or completeness of knowledge.
            population[key] = source, row, digest
            budget.value(dict(key=key, text=row.text))
    if cut is None:
        raise ValueError("source search requires its explicit source population")
    selection = sha256(
        canonical_bytes(
            [
                request.model_dump(exclude={"cursor", "limit"}),
                cut.identity,
                sorted(population),
            ]
        )
    ).hexdigest()
    position = _position(request, selection)
    ranked = _rank_sections(
        connection,
        [(key, row.text) for key, (_, row, _) in population.items()],
        request.text,
        position=position,
        limit=request.limit + 1,
    )
    more = len(ranked) > request.limit
    selected = ranked[: request.limit]
    rows = []
    for result in selected:
        source, row, digest = population[result["key"]]
        rows.append(
            SourceSearchHit(
                source=source.reference,
                original_source=source.original_source,
                source_digest=source.receipt.publication.source_digest,
                projection_digest=digest,
                selection=NativeSourceRequest(
                    **source.reference.model_dump(),
                    section_pointer=row.section_pointer,
                    membership=row.membership,
                    max_rows=request.max_rows,
                    max_bytes=request.max_bytes,
                ),
                excerpt=result["excerpt"],
                score=result["score"],
            )
        )
    cursor = None
    if more:
        last = selected[-1]
        cursor = base64.urlsafe_b64encode(
            canonical_bytes(
                dict(
                    version=1,
                    selection=selection,
                    score=float(last["score"]).hex(),
                    key=last["key"],
                )
            )
        ).decode()
    response = SourceSearchResponse(
        cut=cut.record, rows=rows, next_cursor=cursor, population_complete=not more
    )
    if len(canonical_bytes(response.model_dump(mode="json"))) > request.max_bytes:
        raise ReadLimit(
            "complete source search envelope exceeds max_bytes", reason="oversized_item"
        )
    return response
