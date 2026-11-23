"""Selected member/operation query projections over one explicit native CutSelection."""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_results import (
    CutSelection,
    read_demand_result,
    read_selected_answer,
)

from .continuation_codec import (
    DEMAND_MEMBER_CURSOR,
    DEMAND_ROW_CURSOR,
    DEMAND_SEEK_FIELDS,
    decode_demand_cursor,
    encode_cursor,
    pinned_cursor_basis,
    require_cursor_cut,
    selection_digest,
)
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
        selected = self.model_dump(mode="python", exclude={"cursor", "limit", "max_bytes"})
        if "original_source" not in self.model_fields_set:
            selected.pop("original_source")
        if "analyzed_scope" not in self.model_fields_set:
            selected.pop("analyzed_scope")
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
                "corpus_structure.semantic.continuation_codec.require_cursor_cut",
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
            "corpus_structure.semantic.continuation_codec.require_cursor_cut",
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


def demand_cursor_selection(request, public_selection, generation):
    """Bind the explicit query, keeping its native body budget where applicable."""
    determinants = [public_selection, generation]
    if request.view != "members":
        determinants.append(request.max_bytes)
    return selection_digest(determinants)


def _query_cursor(request, *, version, digest, generation, implementation, read_id):
    if request.cursor is None:
        return None
    cursor = decode_demand_cursor(request.cursor)
    if (
        cursor["version"] != version
        or cursor["selection"] != digest
        or cursor["implementation"] != implementation
        or cursor.get("generation") != generation
        or (read_id is not None and cursor["read_id"] != read_id)
    ):
        raise ValueError("cursor differs from the exact public selection or acquired read")
    return cursor


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
    public_selection = selection if resource_request is None else resource_request
    generation = None if governance is None else governance["generation"]
    digest = demand_cursor_selection(request, public_selection, generation)
    scope = {
        name: selection[name]
        for name in ("operation_id", "subject", "original_source", "analyzed_scope")
        if name in selection
        and (selection[name] is not None or name in ("original_source", "analyzed_scope"))
    }
    if request.product_id is not None:
        scope["product_ids"] = [request.product_id]
    cursor = _query_cursor(
        request,
        version=DEMAND_MEMBER_CURSOR,
        digest=digest,
        generation=generation,
        implementation=implementation,
        read_id=read_id,
    )
    if cursor is not None:
        read_id = cursor["read_id"]
    after = None if cursor is None else cursor["position"]
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
    if cursor is not None:
        require_cursor_cut(cursor, cut)

    cursor_basis = pinned_cursor_basis(DEMAND_MEMBER_CURSOR, digest, cut, implementation)
    if generation is not None:
        cursor_basis["generation"] = generation

    def token(key):
        return encode_cursor(dict(cursor_basis, position=key))

    header = dict(
        version=version,
        implementation=str(implementation),
        cut_id=cut.identity,
        cut=cut.record,
        selection=public_selection,
        resource_handle=encode_cursor(
            dict(
                public_selection,
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
    public_selection = selection if resource_request is None else resource_request
    generation = None if governance is None else governance["generation"]
    digest = demand_cursor_selection(request, public_selection, generation)
    cursor = _query_cursor(
        request,
        version=DEMAND_ROW_CURSOR,
        digest=digest,
        generation=generation,
        implementation=implementation,
        read_id=read_id,
    )
    offset = 0 if cursor is None else cursor["position"]
    seek = {} if cursor is None else cursor["seek"]
    if cursor is not None:
        read_id = cursor["read_id"]
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
    if "analyzed_scope" in request.model_fields_set:
        scope["analyzed_scope"] = request.analyzed_scope
    if request.product_id is not None:
        scope["product_ids"] = [request.product_id]
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
        if read_id is None
        else dict(
            demand_id=request.demand_id,
            read_id=read_id,
            scope=scope,
            view="frontier" if body_rows else native_view,
            **seek,
        )
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
    if cursor is not None:
        require_cursor_cut(cursor, page.cut)
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
                seek,
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
    cursor_basis = pinned_cursor_basis(DEMAND_ROW_CURSOR, digest, page.cut, implementation)
    if generation is not None:
        cursor_basis["generation"] = generation

    def token_for(position, ordinal):
        return encode_cursor(dict(cursor_basis, seek=position, position=ordinal))

    following_cursor = None
    native_continuation = native["continuation"]
    if native_view == "support" and native["support_page"]["after"] is not None:
        following_cursor = token_for(dict(seek, support_after=native["support_page"]["after"]), 0)
    elif native_continuation is not None:
        next_seek = {
            name: native_continuation[name]
            for name in DEMAND_SEEK_FIELDS
            if name in native_continuation
        }
        following_cursor = token_for(next_seek, 0)
    presentation = PageEnvelope(
        reuse_refusal=capture_page_refusal(),
        header=dict(
            version="demand-query-v2",
            implementation=implementation,
            cut_id=page.cut.identity,
            cut=page.cut.record,
            selection=public_selection,
            **({"freshness": freshness} if freshness is not None else {}),
            obligations=native["obligations"],
            uses=uses,
            populations=native["populations"],
            resource_handle=encode_cursor(
                dict(
                    public_selection,
                    limit=request.limit,
                    max_bytes=request.max_bytes,
                    cursor=token_for(seek, offset),
                )
            ),
        ),
        cursor_basis=dict(cursor_basis, seek=seek),
        position_field="position",
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
