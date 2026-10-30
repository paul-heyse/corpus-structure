"""Pinned source inspection shared by CLI and read-only MCP consumers."""
from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from pydantic_core import to_jsonable_python
from sqlalchemy import Connection, func, select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationConflict
from corpus_structure.semantic.parsing_products import read_parsing_product
from corpus_structure.semantic import parsing_queries
from corpus_structure.semantic.releases import open_release


class SourceRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: int = Field(gt=0)
    rendition_id: int = Field(gt=0)
    producing_task_id: int | None = Field(default=None, gt=0)
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
    runs, tasks, builds, selected = map(table, ("ops.run", "ops.task", "ops.rendition_build", "ops.run_rendition"))
    release_id = conn.execute(select(runs.c.release_id).where(runs.c.id == request.run_id)).scalar_one()
    prepared = open_release(conn, release_id)
    candidates = conn.execute(
        select(builds.c.task_id).join_from(tasks, builds, builds.c.task_id == func.coalesce(tasks.c.reused_task_id, tasks.c.id))
        .join(selected, (selected.c.run_id == tasks.c.run_id) & (selected.c.document_id == builds.c.document_id) & (selected.c.rendition_id == builds.c.rendition_id))
        .where(tasks.c.run_id == request.run_id, builds.c.rendition_id == request.rendition_id).distinct()
    ).scalars().all()
    if request.producing_task_id is not None:
        candidates = [t for t in candidates if t == request.producing_task_id]
    if len(candidates) > 1:
        raise OperationConflict("multiple source builds; pin producing_task_id")
    task_id = candidates[0] if candidates else None
    product = None if task_id is None else read_parsing_product(conn, task_id=task_id)
    base = dict(run_id=request.run_id, rendition_id=request.rendition_id, producing_task_id=task_id, release_id=release_id, product_digest=product.digest if product else None)
    if product is None:
        return SourceResponse(**base, outcome="unavailable", rows=[], diagnostics=["No retained source product for this selection; rebuild under an admitted source recipe."])
    assert task_id is not None
    values = product.values()
    if request.view == "products":
        return SourceResponse(**base, outcome="available", rows=[{**{k:v for k,v in values.items() if k not in {"representations", "components", "nodes", "relationships", "endpoints", "mappings", "mapping_endpoints", "dependencies"}}, "representations": [{k:v for k,v in r.items() if k not in {"text_content", "text_content_utf8_base64"}} for r in values["representations"]]}])
    if request.view == "relationships":
        if request.relationship_id is None:
            raise ValueError("relationship inspection requires relationship_id")
        rows = parsing_queries.relationship_endpoints(conn, task_id=task_id, relationship_id=request.relationship_id, limit=request.limit)
        return SourceResponse(**base, outcome="complete", rows=[asdict(row) for row in rows])
    representation = next((r for r in values["representations"] if r["representation_id"] == request.representation_id), None)
    if representation is None:
        raise ValueError("representation is not present in the selected source product")
    end = representation["extent_length"] if request.end is None else request.end
    if request.view == "components":
        rows = parsing_queries.components(conn, task_id=task_id, representation_id=request.representation_id, start=request.start, end=end, category=request.category, limit=request.limit)
        return SourceResponse(**base, outcome=representation["partition_state"], rows=[asdict(row) for row in rows])
    traced = parsing_queries.trace_origins(conn, task_id=task_id, representation_id=request.representation_id, start=request.start, end=end, mapping_limit=request.limit)
    rows = [to_jsonable_python(asdict(row)) for row in traced.contributions]
    if request.require_exact and (traced.outcome != "complete" or any(step.fidelity != "exact" for row in traced.contributions for step in row.path)):
        raise OperationConflict("exact origin is unavailable for this transformed or incomplete contribution; inspect the qualified trace")
    return SourceResponse(**base, outcome=traced.outcome, rows=rows)
