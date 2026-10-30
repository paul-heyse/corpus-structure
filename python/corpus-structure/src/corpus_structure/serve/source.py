"""Pinned source inspection shared by CLI and read-only MCP consumers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from pydantic_core import to_jsonable_python
from sqlalchemy import Connection, select

from corpus_structure.semantic import parsing_queries
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationConflict


class SourceRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: int = Field(gt=0)
    rendition_id: int = Field(gt=0)
    producing_task_id: int | None = Field(default=None, gt=0)
    product_key: str | None = None
    root_task_id: int | None = Field(default=None, gt=0)
    view: Literal["products", "components", "relationships", "trace"] = "products"
    representation_id: str = "canonical"
    start: int = Field(default=0, ge=0)
    end: int | None = Field(default=None, ge=0)
    category: str | None = None
    relationship_id: str | None = None
    limit: int = Field(default=1000, ge=1, le=10000)
    require_exact: bool = False


class SourceResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: int
    rendition_id: int
    producing_task_id: int | None
    release_id: str
    product_digest: str | None
    outcome: str
    rows: list[dict[str, JsonValue]]
    diagnostics: list[str] = Field(default_factory=list)


def inspect_source(conn: Connection, request: SourceRequest) -> SourceResponse:
    """Read a selected product; absence is explicit and never initiates interpretation."""
    from corpus_structure.semantic.parsing_products import (
        select_layered_products,
        verified_product_header,
    )

    runs = table("ops.run")
    release_id = conn.execute(
        select(runs.c.release_id).where(runs.c.id == request.run_id)
    ).scalar_one()
    import json

    from corpus_structure.semantic.contracts import execution_payload, require_bound_operation
    from corpus_structure.semantic.releases import open_release

    prepared = open_release(conn, release_id)
    payload = execution_payload(prepared)
    if payload is None or not any(
        operation["id"] == "read_parsing_product" for operation in json.loads(payload)["operations"]
    ):
        return SourceResponse(
            run_id=request.run_id,
            rendition_id=request.rendition_id,
            producing_task_id=None,
            release_id=release_id,
            product_digest=None,
            outcome="unavailable",
            rows=[],
            diagnostics=[
                "This archived release has no source-product capability; "
                "rebuild in an explicitly selected current parsing realization."
            ],
        )
    require_bound_operation(prepared, "read_parsing_product")
    selected = select_layered_products(
        conn,
        run_id=request.run_id,
        rendition_id=request.rendition_id,
        product_key=request.product_key or (None if request.view == "products" else "source"),
        root_task_id=request.root_task_id,
        producing_task_id=request.producing_task_id,
        limit=request.limit,
    )
    base = dict(
        run_id=request.run_id,
        rendition_id=request.rendition_id,
        producing_task_id=selected[0].reference.task_id if len(selected) == 1 else None,
        release_id=release_id,
        product_digest=selected[0].reference.content_digest if len(selected) == 1 else None,
    )
    if not selected:
        return SourceResponse(
            **base,
            outcome="unavailable",
            rows=[],
            diagnostics=[
                "No retained product for this selection; rebuild or request the "
                "required capability under its admitted recipe."
            ],
        )
    verified = []
    for candidate in selected:
        header = verified_product_header(conn, candidate.reference)
        if header is None:
            raise OperationConflict("selected retained product is unavailable")
        verified.append(header)
    selected = tuple(verified)
    if request.view == "products":
        return SourceResponse(
            **base, outcome="available", rows=[to_jsonable_python(asdict(row)) for row in selected]
        )
    if len(selected) != 1:
        raise OperationConflict("inspection requires one explicitly pinned product")
    reference = selected[0].reference
    header = selected[0]
    if request.view == "trace":
        rep = parsing_queries.representation_header(conn, reference=reference,
                                                    representation_id=request.representation_id)
        traced = parsing_queries.trace_layered_origins(
            conn,
            reference=reference,
            representation_id=request.representation_id,
            start=request.start,
            end=rep["extent_length"] if request.end is None else request.end,
            limit=request.limit,
        )
        rows = to_jsonable_python(traced["contributions"])
        if request.require_exact and (
            traced["outcome"] != "complete"
            or any(step["fidelity"] != "exact" for row in rows for step in row["path"])
        ):
            raise OperationConflict(
                "exact origin is unavailable for this transformed or incomplete contribution; "
                "inspect the qualified trace"
            )
        return SourceResponse(**base, outcome=traced["outcome"], rows=rows)
    if header.kind == "source":
        if request.view == "relationships":
            if request.relationship_id is None:
                raise ValueError("relationship inspection requires relationship_id")
            rows = parsing_queries.relationship_endpoints(
                conn,
                task_id=reference.task_id,
                relationship_id=request.relationship_id,
                limit=request.limit,
            )
            return SourceResponse(**base, outcome="complete", rows=[asdict(row) for row in rows])
        rep = parsing_queries.representation_header(conn, reference=reference,
                                                    representation_id=request.representation_id)
        rows = parsing_queries.components(
            conn,
            task_id=reference.task_id,
            representation_id=request.representation_id,
            start=request.start,
            end=rep["extent_length"] if request.end is None else request.end,
            category=request.category,
            limit=request.limit,
        )
        return SourceResponse(
            **base, outcome=rep["partition_state"], rows=[asdict(row) for row in rows]
        )
    if request.view == "relationships":
        if request.relationship_id is None:
            raise ValueError("relationship inspection requires relationship_id")
        relation = table("kb.parsing_layer_endpoint")
        query = (
            select(relation)
            .where(
                relation.c.task_id == reference.task_id,
                relation.c.product_key == reference.product_key,
                relation.c.relationship_id == request.relationship_id,
            )
            .order_by(relation.c.ordinal)
        )
    else:
        rep = parsing_queries.representation_header(conn, reference=reference,
                                                    representation_id=request.representation_id)
        end = rep["extent_length"] if request.end is None else request.end
        if not 0 <= request.start <= end <= rep["extent_length"]:
            raise ValueError("inspection range is outside its representation")
        if request.start == end:
            return SourceResponse(**base, outcome=rep["partition_state"], rows=[])
        relation = table("kb.parsing_layer_component")
        query = (
            select(relation)
            .where(
                relation.c.task_id == reference.task_id,
                relation.c.product_key == reference.product_key,
                relation.c.representation_id == request.representation_id,
                relation.c.start_offset < end,
                relation.c.end_offset > request.start,
            )
            .order_by(relation.c.ordinal)
        )
        if request.category is not None:
            query = query.where(relation.c.category == request.category)
    rows = [
        {str(name): value for name, value in row.items()}
        for row in conn.execute(query.limit(request.limit + 1)).mappings()
    ]
    if len(rows) > request.limit:
        raise parsing_queries.ParsingReadLimit("inspection exceeds its declared answer bound")
    return SourceResponse(**base, outcome=header.coverage, rows=rows)
