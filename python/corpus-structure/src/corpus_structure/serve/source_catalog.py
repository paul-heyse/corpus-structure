"""Bounded catalogs of checked source kinds in one genuine selected demand cut."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.semantic.continuation_codec import (
    decode_pinned_cursor,
    encode_cursor,
    pinned_cursor_basis,
    require_cursor_cut,
    require_cursor_implementation,
    selection_digest,
)
from corpus_structure.semantic.data_operation_json import DdoJsonValue, json_bytes
from corpus_structure.semantic.demand_results import (
    CutSelection,
    read_demand_result,
    read_selected_answer,
)
from corpus_structure.serve.native_source import (
    NativeSourceRequest,
    inspect_native_source_product_headers,
)

_CURSOR_VERSION = "selected-source-catalog-cursor-3"


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


def read_source_catalog(connection, request: SourceCatalogRequest, *, cancellation=None):
    """Page checked source kinds by native address in one exact selected cut."""
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.serving_identity import installed_read_implementation

    digest = selection_digest(request.model_dump(exclude={"cursor", "limit", "max_bytes"}))
    with installed_read_implementation(
        SourceCatalogRequest,
        entry="corpus_structure.serve.source_catalog",
        profile=_CURSOR_VERSION,
        callables=(
            "corpus_structure.serve.source_catalog.read_source_catalog",
            "corpus_structure.serve.source_catalog._catalog_frontier",
            "corpus_structure.serve.native_source.inspect_native_source_product_headers",
            "corpus_structure.semantic.demand_results.read_selected_answer",
            "corpus_structure.semantic.continuation_codec.decode_pinned_cursor",
        ),
    ) as implementation:
        cursor = None
        if request.cursor is not None:
            cursor = decode_pinned_cursor(
                request.cursor, version=_CURSOR_VERSION, selection=digest, keyset="native-output"
            )
            require_cursor_implementation(cursor, implementation)
        first = read_selected_answer(
            connection,
            "read_selected_outputs",
            request.demand_id,
            project_id=request.project_id,
            read_id=None if cursor is None else cursor["read_id"],
            limit=1,
            max_bytes=request.max_bytes,
        )
        cut = CutSelection.from_native(first["cut"])
        if cursor is not None:
            require_cursor_cut(cursor, cut)
        prepared = open_release(connection, cut.record["release_id"])
        publications = request.view == "publications"
        kinds = _kind_contracts(
            prepared, "DdoPdfPublication" if publications else "DdoSelectedNativeSource"
        )
        answer = read_selected_answer(
            connection,
            "read_selected_outputs",
            request.demand_id,
            project_id=request.project_id,
            read_id=cut.record["read_id"],
            after=None if cursor is None else cursor["position"],
            kind_contracts=list(kinds),
            containers_only=publications,
            body=publications,
            source_metadata=not publications,
            limit=request.limit,
            max_bytes=request.max_bytes,
        )
        if CutSelection.from_native(answer["cut"]).content != cut.content:
            raise ValueError("source catalog answer differs from its exact selected read")
        rows, selections = [], []
        for row in answer["rows"]:
            nominal = kinds.get(row["kind_contract"])
            if nominal is None:
                continue
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
            selection = dict(
                project_id=request.project_id,
                demand_id=request.demand_id,
                read_id=cut.record["read_id"],
                use_id=row["use_id"],
                product_id=row["product_id"],
                derivation_id=row["derivation_id"],
            )
            item["selection"] = selection
            if publications:
                item["publication"] = prepared.validate_json(
                    nominal, json_bytes(decode_semantic_value(row["meaning_body"]))
                ).model_dump(mode="python", exclude_unset=True)
                selections.append(
                    NativeSourceRequest(
                        **selection, view="products", limit=1, max_bytes=request.max_bytes
                    )
                )
            else:
                item.update(
                    source=decode_semantic_value(row["source"]),
                    selectors=decode_semantic_value(row["selectors"]),
                )
            rows.append(item)
        if publications:
            _attach_publication_headers(connection, rows, selections, cut, cancellation)
        after = answer["answer_after"]
        following = (
            None
            if after is None
            else encode_cursor(
                pinned_cursor_basis(_CURSOR_VERSION, digest, cut, implementation, position=after)
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


def _attach_publication_headers(connection, rows, selections, cut, cancellation):
    """Resolve selected native publication receipts without re-acquiring each cut."""
    headers = inspect_native_source_product_headers(
        connection, tuple(selections), cancellation=cancellation
    )
    for item, inspected in zip(rows, headers, strict=True):
        if inspected.cut != cut.record:
            raise ValueError("publication catalog differs from its exact selected read")
        if len(inspected.rows) != 1 or inspected.next_cursor is not None:
            raise ValueError("publication catalog requires its one complete native header")
        item.update(
            native=inspected.rows[0], health=inspected.health, release_id=inspected.release_id
        )
