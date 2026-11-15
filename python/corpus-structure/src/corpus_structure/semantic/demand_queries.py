"""Selected member/operation query projections over one explicit native CutSelection."""
from __future__ import annotations

from collections.abc import Mapping

import base64
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads
from corpus_structure.semantic.demand_results import read_demand_result


class DemandQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    demand_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    view: Literal["members", "operations", "sources", "support", "coverage"] = "members"
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
        return self.model_dump(mode="python", exclude={"cursor", "limit", "max_bytes"})


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


def serve_demand_query(connection, request: DemandQueryRequest) -> dict:
    """Bound the examined native page and returned items independently.

    Unknown, failed and empty populations remain in operation rows. A filtered
    empty page never establishes absence; selected witnesses are separate rows.
    """
    selection = request.selection()
    digest = sha256(json_bytes(selection)).hexdigest()
    cursor = None if request.cursor is None else _decode(request.cursor)
    if cursor is not None and (cursor.get("selection") != digest or set(cursor) != {"selection", "request", "cut", "offset"}):
        raise ValueError("cursor differs from the exact public selection")
    scope: dict[str, Any] = {key: value for key, value in dict(operation_id=request.operation_id, subject=request.subject, original_source=request.original_source).items() if value is not None}
    if request.product_id is not None:
        scope["product_ids"] = [request.product_id]
    native_request = None if cursor is None else cursor["request"]
    # One operation per native page allows a member cursor to retain a whole group
    # without silently skipping a large or zero-output operation.
    native_view = "frontier" if request.view == "operations" else "support" if request.view in {"sources", "support"} else "products"
    page = read_demand_result(connection, request.demand_id, project_id=request.project_id,
                              continuation=native_request, limit=1, max_bytes=request.max_bytes,
                              scope=scope, view=native_view)
    if cursor is not None and cursor["cut"] != page.cut.identity:
        raise ValueError("cursor belongs to another cut/trust assessment")
    native = page.record
    offset = 0 if cursor is None else cursor["offset"]
    if type(offset) is not int or offset < 0:
        raise ValueError("invalid selected member cursor position")
    if request.view == "operations":
        rows = tuple(dict(obligation=obligation, uses=[use for use in native["uses"] if use["obligation_id"] == obligation["obligation_id"]]) for obligation in native["obligations"])
    elif request.view in {"sources", "support"}:
        rows = tuple(row for row in native["support_page"]["records"] if request.view == "support" or row["relation"] == "ops.original_source_admission")
    elif request.view == "coverage":
        rows = tuple(dict(product_id=row["product_id"], use_id=row["use_id"], derivation_id=row["derivation_id"], source=row["body"]["source"], coverage=coverage) for row in page.members() if row["member_id"] is None and isinstance(row["body"], dict) and "source" in row["body"] for coverage in row["body"].get("coverage", ()))
    else:
        rows = page.members()
    def body_field(row,name):
        body=row.get("body",row.get("coverage"))
        return body.get(name) if isinstance(body,Mapping) else None
    member_filters=dict(kind_contract=request.kind_contract,member_id=request.member_id)
    if request.view in {"members","coverage"}:
        member_filters["product_id"]=request.product_id
    filtered = tuple(row for row in rows if (not request.containers_only or row.get("member_id") is None) and (request.record_type is None or body_field(row,"record_type") == request.record_type) and (request.family is None or body_field(row,"family") == request.family) and all(value is None or row.get(key) == value for key,value in member_filters.items()))
    if offset > len(filtered):
        raise ValueError("cursor is outside the pinned member population")
    uses = [{**use, "products": [{key: value for key, value in product.items() if key != "body"} for product in use["products"]]} for use in native["uses"]]
    output = []
    position = offset
    while position < len(filtered) and len(output) < request.limit:
        row = filtered[position]
        # Body values stay tagged in the native packet; json_bytes preserves exact
        # Decimal in the public decoded view rather than widening it to float.
        candidate = dict(version="demand-query-v1", cut_id=page.cut.identity, cut=page.cut.record,
                         selection=selection, items=[*output, row], obligations=native["obligations"],
                         uses=uses, populations=native["populations"], continuation=None)
        if len(json_bytes(candidate)) > request.max_bytes - min(4096, request.max_bytes // 4):
            if not output:
                raise ValueError("one complete selected member and its envelope exceed max_bytes")
            break
        output.append(row)
        position += 1
    next_request = None
    next_offset = 0
    if position < len(filtered):
        next_request = wire_json_loads(page.request)
        next_offset = position
    elif native_view == "support" and native["support_page"]["after"] is not None:
        next_request = wire_json_loads(page.request)
        next_request["support_after"] = native["support_page"]["after"]
        next_offset = 0
    elif page.continuation is not None:
        next_request = page.continuation
        next_offset = 0
    token = None
    if next_request is not None:
        # Immutable demand + exact acquired read pin replace repeated frozen model
        # bytes in a resource handle. Native rechecks stored scope and trust.
        next_request = {key: value for key, value in next_request.items() if key not in {"selection", "trust_snapshot", "limit", "max_bytes"}}
        next_request.update(view=native_view, read_id=native["read_id"], scope=scope)
        token = _cursor(dict(selection=digest, request=next_request, cut=page.cut.identity, offset=next_offset))
    report = dict(version="demand-query-v1", cut_id=page.cut.identity, cut=page.cut.record,
                  selection=selection, items=output, obligations=native["obligations"],
                  uses=uses, populations=native["populations"],
                  knowledge="observed" if output else "unknown", continuation=token,
                  page_complete=token is None)
    resource_request = wire_json_loads(page.request)
    resource_request = {key: value for key, value in resource_request.items() if key not in {"selection", "trust_snapshot", "limit", "max_bytes"}}
    resource_request.update(view=native_view, read_id=native["read_id"], scope=scope)
    resource_cursor = _cursor(dict(selection=digest, request=resource_request, cut=page.cut.identity, offset=offset))
    report["resource_handle"] = _cursor(dict(request.model_dump(mode="python"), cursor=resource_cursor))
    if len(json_bytes(report)) > request.max_bytes:
        raise ValueError("complete selected result envelope exceeds max_bytes")
    return report
