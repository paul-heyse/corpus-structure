"""Selected member/operation query projections over one explicit native CutSelection."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads
from corpus_structure.semantic.demand_results import read_demand_result

DemandView = Literal["members", "operations", "sources", "support", "coverage"]


class DemandQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    demand_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    view: DemandView = "members"
    operation_id: str | None = None
    subject: str | None = None
    original_source: str | None = None
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
        selected = self.model_dump(mode="python", exclude={"cursor", "limit", "max_bytes"})
        if "original_source" not in self.model_fields_set:
            selected.pop("original_source")
        return selected


def _cursor(value):
    encoded = base64.urlsafe_b64encode(json_bytes(value)).decode()
    if len(encoded) > 32768:
        raise ValueError("selected cursor exceeds the supported encoded bound")
    return encoded


def _decode(value):
    try:
        return wire_json_loads(base64.b64decode(value, altchars=b"-_", validate=True))
    except (ValueError, TypeError) as error:
        raise ValueError("invalid selected-result cursor") from error


def _selected_query_rows(page, request):
    native = page.record
    if request.view == "operations":
        rows = (
            dict(
                obligation=obligation,
                uses=[
                    use
                    for use in native["uses"]
                    if use["obligation_id"] == obligation["obligation_id"]
                ],
            )
            for obligation in native["obligations"]
        )
    elif request.view in {"sources", "support"}:
        rows = (
            row
            for row in native["support_page"]["records"]
            if request.view == "support" or row["relation"] == "ops.original_source_admission"
        )
    elif request.view == "coverage":
        rows = (
            dict(
                product_id=row["product_id"],
                use_id=row["use_id"],
                derivation_id=row["derivation_id"],
                source=row["body"]["source"],
                coverage=coverage,
            )
            for row in page.members()
            if row["member_id"] is None
            and isinstance(row["body"], dict)
            and "source" in row["body"]
            for coverage in row["body"].get("coverage", ())
        )
    else:
        rows = page.members()
    filters = dict(kind_contract=request.kind_contract, member_id=request.member_id)
    if request.view in {"members", "coverage"}:
        filters["product_id"] = request.product_id
    for row in rows:
        body = row.get("body", row.get("coverage"))
        if (
            (not request.containers_only or row.get("member_id") is None)
            and (
                request.record_type is None
                or (isinstance(body, Mapping)
                and body.get("record_type") == request.record_type)
            )
            and (
                request.family is None
                or (isinstance(body, Mapping)
                and body.get("family") == request.family)
            )
            and all(value is None or row.get(key) == value for key, value in filters.items())
        ):
            yield row


def serve_demand_query(connection, request: DemandQueryRequest) -> dict:
    from corpus_structure.serve.rich_queries import installed_read_implementation

    sources = (
        "_query_custody.py",
        "semantic/demand_queries.py",
        "semantic/demand_results.py",
        "semantic/selected_query_cache.py",
        "semantic/data_operation_json.py",
        "semantic/native_source_view.py",
    )
    with installed_read_implementation(
        type(request), sources=sources, profile="demand-query-v2"
    ) as implementation:
        return _serve_demand_query(connection, request, implementation)


def _serve_demand_query(connection, request, implementation):
    from .selected_query_cache import (
        SELECTED_QUERY_CACHE,
        bounded_rows,
        byte_bounded_page,
        uncached_rows_from,
    )

    selection = request.selection()
    digest = sha256(json_bytes(selection)).hexdigest()
    cursor = None if request.cursor is None else _decode(request.cursor)
    if cursor is not None and (
        not isinstance(cursor, dict)
        or set(cursor) != {"version", "implementation", "selection", "request", "cut", "ordinal"}
        or cursor["version"] != "demand-query-v2"
        or cursor["implementation"] != implementation
        or cursor["selection"] != digest
    ):
        raise ValueError("cursor differs from the exact public selection")
    offset = 0 if cursor is None else cursor["ordinal"]
    if type(offset) is not int or offset < 0:
        raise ValueError("invalid selected member cursor position")
    scope = {
        key: value
        for key, value in dict(
            operation_id=request.operation_id,
            subject=request.subject,
            original_source=request.original_source,
        ).items()
        if value is not None
    }
    if "original_source" in request.model_fields_set:
        scope["original_source"] = request.original_source
    if request.product_id is not None:
        scope["product_ids"] = [request.product_id]
    native_request = None if cursor is None else cursor["request"]
    native_view = (
        "frontier"
        if request.view == "operations"
        else "support"
        if request.view in {"sources", "support"}
        else "products"
    )
    body_rows = native_view == "products"
    acquisition = (
        None
        if native_request is None
        else dict(native_request, view="frontier" if body_rows else native_view)
    )
    page = read_demand_result(
        connection,
        request.demand_id,
        project_id=request.project_id,
        continuation=acquisition,
        limit=1,
        max_bytes=request.max_bytes,
        scope=scope,
        view="frontier" if body_rows else native_view,
        recheck_bodies=body_rows,
    )
    if cursor is not None and cursor["cut"] != page.cut.identity:
        raise ValueError("cursor belongs to another cut/trust assessment")
    native = page.record
    remaining = None
    entry = None
    if body_rows:
        # max_bytes is also this API's examined native-body bound, not just its
        # output bound. A cache populated under a larger input budget cannot bypass it.
        key = json_bytes(
            [
                "demand",
                page.cut.identity,
                implementation,
                digest,
                request.max_bytes,
                sha256(page.content).hexdigest(),
                {
                    name: (acquisition or {}).get(name)
                    for name in ("after", "support_after", "obligation_id")
                },
            ]
        )
        entry = SELECTED_QUERY_CACHE.get(key)
        if entry is None:
            whole_request = dict(wire_json_loads(page.request), view="products")
            whole_request.pop("recheck_bodies", None)
            whole = read_demand_result(
                connection,
                request.demand_id,
                project_id=request.project_id,
                continuation=whole_request,
                cut=page.cut,
                limit=1,
                max_bytes=request.max_bytes,
                scope=scope,
                view="products",
            )
            entry, remaining = bounded_rows(_selected_query_rows(whole, request), {})
            if entry is not None:
                SELECTED_QUERY_CACHE.put(key, entry)
        rows = entry.rows(offset) if entry is not None else uncached_rows_from(remaining, offset)
    else:
        rows = uncached_rows_from(_selected_query_rows(page, request), offset)
    uses = [
        {
            **use,
            "products": [
                {key: value for key, value in product.items() if key != "body"}
                | ({"body_state": "present"} if body_rows else {})
                for product in use["products"]
            ],
        }
        for use in native["uses"]
    ]
    current_request = {
        key: value
        for key, value in wire_json_loads(page.request).items()
        if key not in {"selection", "trust_snapshot", "limit", "max_bytes", "recheck_bodies"}
    }
    current_request.update(view=native_view, read_id=native["read_id"], scope=scope)

    def token_for(selected_request, ordinal):
        if selected_request is None:
            return None
        selected_request = {
            key: value
            for key, value in selected_request.items()
            if key not in {"selection", "trust_snapshot", "limit", "max_bytes", "recheck_bodies"}
        }
        selected_request.update(view=native_view, read_id=native["read_id"], scope=scope)
        return _cursor(
            dict(
                version="demand-query-v2",
                implementation=implementation,
                selection=digest,
                request=selected_request,
                cut=page.cut.identity,
                ordinal=ordinal,
            )
        )

    def report(end, values, more):
        if more:
            continuation = token_for(current_request, end)
        elif native_view == "support" and native["support_page"]["after"] is not None:
            continuation = token_for(
                dict(current_request, support_after=native["support_page"]["after"]), 0
            )
        else:
            continuation = token_for(page.continuation, 0)
        return dict(
            version="demand-query-v2",
            implementation=implementation,
            cut_id=page.cut.identity,
            cut=page.cut.record,
            selection=selection,
            items=values,
            obligations=native["obligations"],
            uses=uses,
            populations=native["populations"],
            knowledge="observed" if values else "unknown",
            continuation=continuation,
            page_complete=continuation is None,
            resource_handle=_cursor(
                dict(
                    selection,
                    limit=request.limit,
                    max_bytes=request.max_bytes,
                    cursor=token_for(current_request, offset),
                )
            ),
        )

    try:
        return byte_bounded_page(
            rows, offset=offset, limit=request.limit, max_bytes=request.max_bytes, report=report
        )
    finally:
        if remaining is not None:
            remaining.close()
