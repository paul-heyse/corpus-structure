"""Opt-in governed reads over native coverage and an exact retained cut."""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from ._data_operation_wire import WireReadGovernedSelectionRequest
from .continuation_codec import DEMAND_MEMBER_CURSOR, DEMAND_ROW_CURSOR, decode_demand_cursor
from .data_operation_json import json_bytes
from .data_operation_storage import DataOperationStorage
from .demand_queries import DemandQueryRequest, DemandView


class GovernedDemandQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    project_id: str = Field(min_length=1)
    selection_name: str = Field(min_length=1)
    mode: Literal["current", "last-settled"] = "current"
    view: DemandView = "members"
    operation_id: str | None = None
    subject: str | None = None
    original_source: str | None = None
    analyzed_scope: Any = None
    kind_contract: str | None = None
    record_type: str | None = None
    family: str | None = None
    containers_only: bool = False
    product_id: str | None = None
    member_id: str | None = None
    cursor: str | None = Field(default=None, max_length=32768)
    limit: int = Field(default=100, strict=True, ge=1, le=1000)
    max_bytes: int = Field(default=1048576, strict=True, ge=1024, le=67108864)

    def selection(self):
        selected = self.model_dump(exclude={"cursor", "limit", "max_bytes"})
        if "original_source" not in self.model_fields_set:
            selected.pop("original_source")
        if "analyzed_scope" not in self.model_fields_set:
            selected.pop("analyzed_scope")
        return selected


def governed_scope(request):
    scope = {
        name: getattr(request, name)
        for name in ("operation_id", "subject")
        if getattr(request, name) is not None
    }
    for name in ("original_source", "analyzed_scope"):
        if name in request.model_fields_set:
            scope[name] = getattr(request, name)
    if request.product_id is not None:
        scope["product_ids"] = [request.product_id]
    return scope


def serve_governed_demand_query(connection, request: GovernedDemandQueryRequest):
    from .demand_queries import demand_cursor_selection, serve_demand_query

    selection = request.selection()
    cursor = None if request.cursor is None else decode_demand_cursor(request.cursor)
    if cursor is not None:
        generation = cursor.get("generation")
        version = DEMAND_MEMBER_CURSOR if request.view == "members" else DEMAND_ROW_CURSOR
        if (
            generation is None
            or cursor["version"] != version
            or cursor["selection"] != demand_cursor_selection(request, selection, generation)
        ):
            raise ValueError("cursor differs from the exact governed selection")
    native_request: dict[str, Any] = dict(
        project_id=request.project_id,
        selection_name=request.selection_name,
        scope=governed_scope(request),
        mode=request.mode,
    )
    if cursor is not None:
        native_request["read_id"] = cursor["read_id"]
        native_request["selection_generation"] = cursor["generation"]
    freshness = DataOperationStorage(connection).read_governed_selection(
        cast(WireReadGovernedSelectionRequest, native_request)
    )
    if freshness["read_id"] is None:
        result = dict(
            version="governed-demand-query-v1",
            cut_id=None,
            freshness=freshness,
            selection=selection,
            items=[],
            continuation=None,
            page_complete=True,
            knowledge="unknown",
        )
        if len(json_bytes(result)) > request.max_bytes:
            raise ValueError("complete governed answer exceeds max_bytes")
        return result
    demand_id = freshness["demand_id"]
    if demand_id is None or freshness["selection_generation"] is None:
        raise ValueError("acquired governed read requires its exact demand and generation")
    if cursor is not None and (
        freshness["read_id"] != cursor["read_id"]
        or freshness["selection_generation"] != cursor["generation"]
    ):
        raise ValueError("governed continuation differs from its acquired read or generation")
    values = request.model_dump(exclude={"selection_name", "mode", "cursor"})
    for name in ("original_source", "analyzed_scope"):
        if name not in request.model_fields_set:
            values.pop(name)
    exact = DemandQueryRequest(
        **values,
        demand_id=demand_id,
        cursor=request.cursor,
    )

    governance = dict(
        project_id=request.project_id,
        selection_name=request.selection_name,
        mode=request.mode,
        generation=freshness["selection_generation"],
    )
    return serve_demand_query(
        connection,
        exact,
        read_id=freshness["read_id"],
        freshness=freshness,
        governance=governance,
        resource_request=selection,
    )
