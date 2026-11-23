"""Selected member/operation query projections over one explicit native CutSelection."""

from __future__ import annotations

from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_results import (
    CutSelection,
    read_demand_result,
    read_selected_answer,
)

from .continuation_codec import decode_demand_cursor, encode_cursor
from .demand_query_projection import prepare_demand_projection_inputs, selected_query_rows
from .demand_wire import decode_wire_demand_request
from .page_envelope import PageEnvelope
from .selected_pages import byte_bounded_page
from .serving_code import capture_page_refusal

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


def serve_demand_query(
    connection,
    request: DemandQueryRequest,
    *,
    read_id: str | None = None,
    freshness=None,
    governance=None,
    resource_request=None,
) -> dict:
    from .serving_identity import installed_read_implementation

    if request.view == "members":
        with installed_read_implementation(
            type(request),
            entry="corpus_structure.semantic.demand_queries",
            profile="demand-query-v3",
            callables=(
                "corpus_structure.semantic.demand_queries._serve_selected_members",
                "corpus_structure.semantic.demand_results.read_selected_answer",
                "corpus_structure.semantic.continuation_codec.decode_demand_cursor",
            ),
        ) as implementation:
            return _serve_selected_members(
                connection,
                request,
                implementation,
                read_id=read_id,
                freshness=freshness,
                governance=governance,
                resource_request=resource_request,
            )

    with installed_read_implementation(
        type(request),
        entry="corpus_structure.semantic.demand_query_projection",
        profile="demand-query-v2",
        callables=(
            "corpus_structure.semantic.demand_query_projection.prepare_demand_projection_inputs",
            "corpus_structure.semantic.demand_query_projection.selected_query_rows",
            "corpus_structure.semantic.selected_pages.byte_bounded_page",
            "corpus_structure.semantic.continuation_codec.encode_cursor",
            "corpus_structure.semantic.continuation_codec.decode_demand_cursor",
        ),
    ) as implementation:
        return _serve_demand_query(
            connection,
            request,
            implementation,
            read_id=read_id,
            freshness=freshness,
            governance=governance,
            resource_request=resource_request,
        )


def _serve_selected_members(
    connection,
    request,
    implementation,
    *,
    read_id,
    freshness,
    governance,
    resource_request,
):
    from .data_operation_values import decode_semantic_value

    version = "demand-query-v3"
    selection = request.selection()
    digest = sha256(json_bytes([selection, governance])).hexdigest()
    scope = {
        name: selection[name]
        for name in ("operation_id", "subject", "original_source")
        if name in selection and (selection[name] is not None or name == "original_source")
    }
    if request.product_id is not None:
        scope["product_ids"] = [request.product_id]
    cursor = None if request.cursor is None else decode_demand_cursor(request.cursor)
    if cursor is not None:
        if (
            cursor["version"] != version
            or cursor["selection"] != digest
            or cursor["implementation"] != implementation
            or cursor.get("governance") != governance
            or cursor["request"].get("scope") != scope
            or not cursor["request"].get("read_id")
            or (read_id is not None and read_id != cursor["request"].get("read_id"))
        ):
            raise ValueError("cursor differs from the exact public selection")
        read_id = cursor["request"]["read_id"]
    after = None if cursor is None else cursor["request"].get("answer_after")
    filters = {
        name: selection[name]
        for name in ("kind_contract", "product_id", "member_id", "record_type", "family")
        if selection[name] is not None
    }
    answer = read_selected_answer(
        connection,
        "read_selected_outputs",
        request.demand_id,
        project_id=request.project_id,
        read_id=read_id,
        scope=scope,
        after=after,
        limit=request.limit,
        max_bytes=request.max_bytes,
        body=True,
        containers_only=request.containers_only,
        **filters,
    )
    cut = CutSelection.from_native(answer["cut"])
    if cursor is not None and cursor["cut"] != cut.identity:
        raise ValueError("cursor belongs to another cut/trust assessment")

    def token(key):
        native_request = dict(
            project_id=request.project_id,
            demand_id=request.demand_id,
            scope=scope,
            read_id=cut.record["read_id"],
        )
        if key is not None:
            native_request["answer_after"] = key
        return encode_cursor(
            dict(
                version=version,
                implementation=implementation,
                selection=digest,
                cut=cut.identity,
                request=native_request,
                ordinal=0,
                **({"governance": governance} if governance is not None else {}),
            )
        )

    header = dict(
        version=version,
        implementation=str(implementation),
        cut_id=cut.identity,
        cut=cut.record,
        selection=selection if resource_request is None else resource_request,
        resource_handle=encode_cursor(
            dict(
                selection if resource_request is None else resource_request,
                cursor=token(after),
                limit=request.limit,
                max_bytes=request.max_bytes,
            )
        ),
        **({"freshness": freshness} if freshness is not None else {}),
    )
    items = []
    for row in answer["rows"]:
        item = {
            name: row[name]
            for name in (
                "use_id",
                "derivation_id",
                "product_id",
                "role",
                "output_member_id",
                "position",
                "multiplicity",
                "member_id",
                "kind_contract",
                "subject",
                "subject_definition",
                "original_source",
                "analyzed_scope",
                "meaning_body",
            )
        }
        item["body"] = decode_semantic_value(item["meaning_body"])
        items.append(item)
    continuation = answer["answer_after"]
    while True:
        report = dict(
            header,
            items=items,
            continuation=None if continuation is None else token(continuation),
            knowledge="observed" if items else "unknown",
            page_complete=continuation is None,
        )
        if len(json_bytes(report)) <= request.max_bytes:
            refusal = capture_page_refusal()
            if refusal is not None:
                from .page_envelope import apply_page_reuse_refusal

                report = apply_page_reuse_refusal(report, refusal)
                if len(json_bytes(report)) > request.max_bytes:
                    raise ValueError("complete selected answer envelope exceeds max_bytes")
            return report
        if len(items) <= 1:
            raise ValueError("one complete selected answer and its envelope exceeds max_bytes")
        items.pop()
        last = answer["rows"][len(items) - 1]
        continuation = [
            last["obligation_id"],
            last["use_id"],
            last["role"],
            last["position"],
            last["product_id"],
            last["member_id"] or "",
        ]


def _serve_demand_query(
    connection,
    request,
    implementation,
    *,
    read_id=None,
    freshness=None,
    governance=None,
    resource_request=None,
):
    from .selected_query_cache import (
        SELECTED_QUERY_CACHE,
        bounded_rows,
        served_key,
        uncached_rows_from,
    )
    from .value_codec import decimal_digit_limit

    selection = request.selection()
    selection_content = json_bytes(selection)
    decimal_fixed_point_digits = decimal_digit_limit()
    # This limit bounds the native inputs as well as presentation.
    digest = sha256(
        json_bytes(
            [selection, request.max_bytes]
            if governance is None
            else [selection, request.max_bytes, governance]
        )
    ).hexdigest()
    cursor = None if request.cursor is None else decode_demand_cursor(request.cursor)
    if cursor is not None and (
        not isinstance(cursor, dict)
        or set(cursor)
        != (
            {"version", "implementation", "selection", "request", "cut", "ordinal"}
            | ({"governance"} if governance is not None else set())
        )
        or cursor.get("governance") != governance
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
    if read_id is not None:
        if native_request is None:
            native_request = dict(demand_id=request.demand_id, scope=scope, read_id=read_id)
        elif native_request.get("read_id") != read_id:
            raise ValueError("cursor belongs to another acquired read")
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
        key = served_key(
            connection,
            "demand",
            implementation=implementation,
            basis=page.cut.identity,
            selection=[
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
            ],
        )
        with SELECTED_QUERY_CACHE.loading(key) as entry:
            if entry is None:
                whole_request = dict(
                    decode_wire_demand_request(page.request, demand_id=request.demand_id),
                    view="products",
                    read_id=native["read_id"],
                )
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
                entry, remaining = bounded_rows(
                    selected_query_rows(
                        prepare_demand_projection_inputs(
                            whole,
                            selection_content,
                            decimal_fixed_point_digits=decimal_fixed_point_digits,
                        )
                    ),
                    {},
                )
                if entry is not None:
                    SELECTED_QUERY_CACHE.put(key, entry)
        rows = entry.rows(offset) if entry is not None else uncached_rows_from(remaining, offset)
    else:
        rows = uncached_rows_from(
            selected_query_rows(
                prepare_demand_projection_inputs(
                    page,
                    selection_content,
                    decimal_fixed_point_digits=decimal_fixed_point_digits,
                )
            ),
            offset,
        )
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
        for key, value in decode_wire_demand_request(
            page.request, demand_id=request.demand_id
        ).items()
        if key not in {"selection", "trust_snapshot", "limit", "max_bytes", "recheck_bodies"}
    }
    current_request.update(
        demand_id=request.demand_id, view=native_view, read_id=native["read_id"], scope=scope
    )

    def token_for(selected_request, ordinal):
        if selected_request is None:
            return None
        selected_request = {
            key: value
            for key, value in selected_request.items()
            if key not in {"selection", "trust_snapshot", "limit", "max_bytes", "recheck_bodies"}
        }
        selected_request.update(
            demand_id=request.demand_id, view=native_view, read_id=native["read_id"], scope=scope
        )
        return encode_cursor(
            dict(
                version="demand-query-v2",
                implementation=implementation,
                selection=digest,
                request=selected_request,
                cut=page.cut.identity,
                ordinal=ordinal,
                **({"governance": governance} if governance is not None else {}),
            )
        )

    following_cursor = (
        token_for(dict(current_request, support_after=native["support_page"]["after"]), 0)
        if native_view == "support" and native["support_page"]["after"] is not None
        else token_for(page.continuation, 0)
    )
    current_cursor = token_for(current_request, 0)
    assert current_cursor is not None
    presentation = PageEnvelope(
        reuse_refusal=capture_page_refusal(),
        header=dict(
            version="demand-query-v2",
            implementation=implementation,
            cut_id=page.cut.identity,
            cut=page.cut.record,
            selection=selection if resource_request is None else resource_request,
            **({"freshness": freshness} if freshness is not None else {}),
            obligations=native["obligations"],
            uses=uses,
            populations=native["populations"],
            resource_handle=encode_cursor(
                dict(
                    selection if resource_request is None else resource_request,
                    limit=request.limit,
                    max_bytes=request.max_bytes,
                    cursor=token_for(current_request, offset),
                )
            ),
        ),
        cursor_basis=decode_demand_cursor(current_cursor),
        following_cursor=following_cursor,
        include_knowledge=True,
        include_page_complete=True,
    )

    try:
        return byte_bounded_page(
            rows,
            offset=offset,
            limit=request.limit,
            max_bytes=request.max_bytes,
            presentation=presentation,
        )
    finally:
        if remaining is not None:
            remaining.close()
