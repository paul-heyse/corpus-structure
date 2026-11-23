"""Bounded catalogs of checked source kinds in one genuine selected demand cut."""

from __future__ import annotations

from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.semantic.continuation_codec import decode_rich_cursor, encode_cursor
from corpus_structure.semantic.data_operation_json import DdoJsonValue, json_bytes
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
from corpus_structure.semantic.demand_results import (
    CutSelection,
    read_demand_result,
    read_selected_answer,
)
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source


class SourceCatalogRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    project_id: str = Field(min_length=1)
    demand_id: str = Field(min_length=1)
    view: Literal["publications", "views"] = "publications"
    cursor: str | None = Field(default=None, max_length=32768)
    limit: int = Field(default=100, ge=1, le=1000)
    max_bytes: int = Field(default=1048576, ge=1024, le=8388608)


class SourceCatalogResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal["selected-source-catalog-1"] = "selected-source-catalog-1"
    selection: SourceCatalogRequest
    cut: dict[str, DdoJsonValue]
    rows: list[dict[str, DdoJsonValue]]
    obligations: list[dict[str, DdoJsonValue]]
    uses: list[dict[str, DdoJsonValue]]
    populations: list[dict[str, DdoJsonValue]]
    next_cursor: str | None
    page_complete: bool


def _kind_contracts(prepared, root):
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

    identities = {
        identity.owner: identity.key
        for identity in bound_data_operation_model(prepared).identities
        if identity.domain == "kind"
    }

    return {
        identities[definition.iri]: definition.name
        for definition in prepared.index.definitions.values()
        if definition.iri in identities
        and (definition.name == root or root in definition.ancestors)
    }


def _catalog_frontier(connection, request, cut, rows):
    """Acquire context from the same pinned frontier without reopening bodies."""
    obligation_ids = tuple(
        dict.fromkeys(row["obligation_id"] for row in rows if row.get("obligation_id") is not None)
    ) or (None,)
    context = {name: {} for name in ("obligations", "uses", "populations")}
    identities = {"obligations": "obligation_id", "uses": "use_id", "populations": "population_id"}
    for obligation in obligation_ids:
        continuation = dict(
            demand_id=request.demand_id, read_id=cut.record["read_id"], scope={}, view="frontier"
        )
        if obligation is not None:
            continuation["obligation_id"] = obligation
        page = read_demand_result(
            connection,
            request.demand_id,
            project_id=request.project_id,
            continuation=continuation,
            cut=cut,
            scope={},
            view="frontier",
            limit=1,
            max_bytes=request.max_bytes,
        )
        if page.cut.content != cut.content:
            raise ValueError("source catalog frontier differs from its exact selected read")
        for name, key in identities.items():
            for row in page.record[name]:
                context[name][
                    json_bytes(row) if name == "populations" else row.get(key, json_bytes(row))
                ] = row
    return {name: list(rows.values()) for name, rows in context.items()}


def _source_view_catalog(connection, request):
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.serving_identity import installed_read_implementation

    selection = request.model_dump(exclude={"cursor", "limit", "max_bytes"})
    digest = sha256(json_bytes(selection)).hexdigest()
    with installed_read_implementation(
        SourceCatalogRequest,
        entry="corpus_structure.serve.source_catalog",
        profile="selected-source-views-v2",
        callables=(
            "corpus_structure.serve.source_catalog._source_view_catalog",
            "corpus_structure.serve.source_catalog._catalog_frontier",
            "corpus_structure.semantic.demand_results.read_selected_answer",
        ),
    ) as implementation:
        cursor = None if request.cursor is None else decode_rich_cursor(request.cursor)
        if cursor is not None and (
            set(cursor) != {"version", "selection", "implementation", "cut", "request", "ordinal"}
            or cursor["version"] != "selected-source-views-v2"
            or cursor["selection"] != digest
            or cursor["implementation"] != implementation
            or not isinstance(cursor["request"], dict)
            or set(cursor["request"]) != {"read_id", "answer_after"}
            or not isinstance(cursor["request"]["read_id"], str)
            or not cursor["request"]["read_id"]
            or not isinstance(cursor["request"]["answer_after"], list)
        ):
            raise ValueError("source catalog cursor differs from its exact selection")
        pins = None if cursor is None else cursor["request"]
        first = read_selected_answer(
            connection,
            "read_selected_outputs",
            request.demand_id,
            project_id=request.project_id,
            read_id=None if pins is None else pins["read_id"],
            limit=1,
            max_bytes=request.max_bytes,
        )
        cut = CutSelection.from_native(first["cut"])
        if cursor is not None and cursor["cut"] != cut.identity:
            raise ValueError("source catalog cursor differs from its exact selected read")
        prepared = open_release(connection, cut.record["release_id"])
        kinds = _kind_contracts(prepared, "DdoSelectedNativeSource")
        answer = read_selected_answer(
            connection,
            "read_selected_outputs",
            request.demand_id,
            project_id=request.project_id,
            read_id=cut.record["read_id"],
            after=None if pins is None else pins.get("answer_after"),
            kind_contracts=list(kinds),
            source_metadata=True,
            limit=request.limit,
            max_bytes=request.max_bytes,
        )
        if CutSelection.from_native(answer["cut"]).content != cut.content:
            raise ValueError("source catalog answer differs from its exact selected read")
        rows = []
        for row in answer["rows"]:
            item = {
                name: row[name]
                for name in (
                    "member_id",
                    "kind_contract",
                    "subject",
                    "subject_definition",
                    "original_source",
                    "analyzed_scope",
                )
            }
            item["selection"] = dict(
                project_id=request.project_id,
                demand_id=request.demand_id,
                read_id=cut.record["read_id"],
                use_id=row["use_id"],
                product_id=row["product_id"],
                derivation_id=row["derivation_id"],
            )
            item.update(
                source=decode_semantic_value(row["source"]),
                selectors=decode_semantic_value(row["selectors"]),
            )
            rows.append(item)
        after = answer["answer_after"]
        following = (
            None
            if after is None
            else encode_cursor(
                dict(
                    version="selected-source-views-v2",
                    implementation=str(implementation),
                    selection=digest,
                    cut=cut.identity,
                    ordinal=0,
                    request={"read_id": cut.record["read_id"], "answer_after": after},
                )
            )
        )
        context = _catalog_frontier(connection, request, cut, answer["rows"])
        response = SourceCatalogResponse(
            selection=request,
            cut=cut.record,
            rows=rows,
            obligations=context["obligations"],
            uses=context["uses"],
            populations=context["populations"],
            next_cursor=following,
            page_complete=after is None,
        )
        if len(json_bytes(response.model_dump(mode="python"))) > request.max_bytes:
            raise ValueError("complete source catalog envelope exceeds max_bytes")
        return response


def read_source_catalog(connection, request: SourceCatalogRequest, *, cancellation=None):
    """Reuse the selected query's bounded pagination, exact read and unknown standing.

    Classification uses archived nominal kind inheritance. A publication additionally
    passes the existing native selected-PDF receipt guard before its header is read.
    No run, task, operation name or current registry spelling grants membership.
    """
    from corpus_structure.semantic.releases import open_release

    if request.view == "views":
        return _source_view_catalog(connection, request)

    # The current selected-query cursor is bound to this exact projection as well as
    # to its demand. A source-kind filter never turns an empty page into absence.
    page = serve_demand_query(
        connection,
        DemandQueryRequest(
            project_id=request.project_id,
            demand_id=request.demand_id,
            view="members",
            containers_only=request.view == "publications",
            cursor=request.cursor,
            limit=request.limit,
            max_bytes=request.max_bytes,
        ),
    )
    prepared = open_release(connection, page["cut"]["release_id"])
    kinds = _kind_contracts(
        prepared,
        "DdoPdfPublication" if request.view == "publications" else "DdoSelectedNativeSource",
    )
    rows = []
    for row in page["items"]:
        nominal = kinds.get(row["kind_contract"])
        if nominal is None:
            continue
        checked = prepared.validate_json(nominal, json_bytes(row["body"])).model_dump(
            mode="python", exclude_unset=True
        )
        selection = dict(
            project_id=request.project_id,
            demand_id=request.demand_id,
            read_id=page["cut"]["read_id"],
            use_id=row["use_id"],
            product_id=row["product_id"],
            derivation_id=row["derivation_id"],
        )
        item = {
            key: row[key]
            for key in (
                "member_id",
                "kind_contract",
                "subject",
                "subject_definition",
                "original_source",
                "analyzed_scope",
            )
        }
        item["selection"] = selection
        if request.view == "publications":
            inspected = inspect_native_source(
                connection,
                NativeSourceRequest(
                    **selection,
                    view="products",
                    limit=1,
                    max_bytes=request.max_bytes,
                ),
                cancellation=cancellation,
            )
            if inspected.cut != page["cut"]:
                raise ValueError("publication catalog differs from its exact selected read")
            if len(inspected.rows) != 1 or inspected.next_cursor is not None:
                raise ValueError("publication catalog requires its one complete native header")
            item.update(
                publication=checked,
                native=inspected.rows[0],
                health=inspected.health,
                release_id=inspected.release_id,
            )
        else:
            item.update(source=checked["source"], selectors=checked["selectors"])
        rows.append(item)
    context = (
        {name: page[name] for name in ("obligations", "uses", "populations")}
        if all(name in page for name in ("obligations", "uses", "populations"))
        else _catalog_frontier(
            connection, request, CutSelection.from_native(page["cut"]), page["items"]
        )
    )
    response = SourceCatalogResponse(
        selection=request,
        cut=page["cut"],
        rows=rows,
        obligations=context["obligations"],
        uses=context["uses"],
        populations=context["populations"],
        next_cursor=page["continuation"],
        page_complete=page["page_complete"],
    )
    if len(json_bytes(response.model_dump(mode="python"))) > request.max_bytes:
        raise ValueError("complete source catalog envelope exceeds max_bytes")
    return response
