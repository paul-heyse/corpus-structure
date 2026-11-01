"""Search the selected PDF source without requiring a completed knowledge result."""

from __future__ import annotations

import base64
import json
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection, and_, func, literal_column, or_, select

from corpus_structure.serve.native_source import NativeSourceRequest


class SourceSearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: int = Field(gt=0)
    text: str = Field(min_length=1)
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None


class SourceSearchHit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_view_id: int
    projection_digest: str
    source_uri: str
    selection: NativeSourceRequest
    excerpt: str
    score: float


class SourceSearchResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: str = "integrated-source-3"
    run_id: int
    rows: list[SourceSearchHit]
    next_cursor: str | None = None


def source_search_rows(
    conn: Connection,
    *,
    run_id: int,
    text: str,
    limit: int,
    after_score: float | None = None,
    after_id: int | None = None,
) -> list[SourceSearchHit]:
    """One common source query for CLI/query/MCP; excerpts never replace retrievable sections."""
    from corpus_structure.semantic.metadata import table

    view, selected, document = map(table, ("kb.source_view", "ops.run_source_view", "kb.document"))
    newer = selected.alias("newer_search_source")
    config = literal_column("'english'::regconfig")
    query = func.websearch_to_tsquery(config, text)
    source_text = view.c.projection["text"].as_string()
    vector = func.to_tsvector(config, source_text)
    score = func.ts_rank_cd(vector, query)
    statement = (
        select(
            view.c.id,
            view.c.native_task_id,
            view.c.native_product_key,
            view.c.native_content_digest,
            view.c.section_pointer,
            view.c.membership,
            view.c.projection_digest,
            document.c.source_uri,
            func.ts_headline(config, source_text, query, "MaxWords=45,MinWords=15").label(
                "excerpt"
            ),
            score.label("score"),
        )
        .join(selected, selected.c.source_view_id == view.c.id)
        .join(document, document.c.id == view.c.document_id)
        .where(
            selected.c.run_id == run_id,
            ~select(newer.c.source_view_id)
            .where(newer.c.run_id == run_id, newer.c.supersedes_source_view_id == view.c.id)
            .exists(),
            vector.op("@@")(query),
        )
    )
    if after_score is not None and after_id is not None:
        statement = statement.where(
            or_(score < after_score, and_(score == after_score, view.c.id > after_id))
        )
    rows = conn.execute(statement.order_by(score.desc(), view.c.id).limit(limit)).mappings()
    return [
        SourceSearchHit(
            source_view_id=row["id"],
            projection_digest=row["projection_digest"],
            source_uri=row["source_uri"],
            selection=NativeSourceRequest(
                run_id=run_id,
                task_id=row["native_task_id"],
                product_key=row["native_product_key"],
                content_digest=row["native_content_digest"],
                section_pointer=row["section_pointer"],
                membership=row["membership"],
            ),
            excerpt=row["excerpt"],
            score=float(row["score"]),
        )
        for row in rows
    ]


def search_source(conn: Connection, request: SourceSearchRequest) -> SourceSearchResponse:
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_run
    from corpus_structure.semantic.source_views import selected_source_views

    context = pdf_context_for_run(conn, request.run_id)
    context.execution.require_operation("read_source_view")
    refs = selected_source_views(conn, request.run_id)
    selection = sha256(
        canonical_bytes(
            [
                request.run_id,
                request.text,
                [(ref.id, ref.native_product.values(), ref.projection_digest) for ref in refs],
            ]
        )
    ).hexdigest()
    after_score = after_id = None
    if request.cursor is not None:
        try:
            cursor = json.loads(base64.urlsafe_b64decode(request.cursor))
            if cursor["selection"] != selection:
                raise ValueError("source search selection changed")
            after_score, after_id = float(cursor["score"]), int(cursor["id"])
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError("invalid or stale source search continuation") from error
    rows = source_search_rows(
        conn,
        run_id=request.run_id,
        text=request.text,
        limit=request.limit + 1,
        after_score=after_score,
        after_id=after_id,
    )
    more, rows = len(rows) > request.limit, rows[: request.limit]
    continuation = None
    if more:
        continuation = base64.urlsafe_b64encode(
            json.dumps(
                dict(selection=selection, score=str(rows[-1].score), id=rows[-1].source_view_id)
            ).encode()
        ).decode()
    return SourceSearchResponse(run_id=request.run_id, rows=rows, next_cursor=continuation)
