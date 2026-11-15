"""Bounded catalogs of checked source kinds in one genuine selected demand cut."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.semantic.data_operation_json import DdoJsonValue, json_bytes
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
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


def read_source_catalog(connection, request: SourceCatalogRequest, *, cancellation=None):
    """Reuse the selected query's bounded pagination, exact read and unknown standing.

    Classification uses archived nominal kind inheritance. A publication additionally
    passes the existing native selected-PDF receipt guard before its header is read.
    No run, task, operation name or current registry spelling grants membership.
    """
    from corpus_structure.semantic.releases import open_release

    # The current selected-query cursor is bound to this exact projection as well as
    # to its demand. A source-kind filter never turns an empty page into absence.
    page = serve_demand_query(connection, DemandQueryRequest(
        project_id=request.project_id, demand_id=request.demand_id,
        view="members", containers_only=request.view == "publications",
        cursor=request.cursor, limit=request.limit, max_bytes=request.max_bytes,
    ))
    prepared = open_release(connection, page["cut"]["release_id"])
    kinds = _kind_contracts(prepared, "DdoPdfPublication" if request.view == "publications" else "DdoSelectedNativeSource")
    rows = []
    for row in page["items"]:
        nominal = kinds.get(row["kind_contract"])
        if nominal is None:
            continue
        checked = prepared.validate_json(nominal, json_bytes(row["body"])).model_dump(mode="python", exclude_unset=True)
        selection = dict(
            project_id=request.project_id, demand_id=request.demand_id,
            read_id=page["cut"]["read_id"], use_id=row["use_id"],
            product_id=row["product_id"], derivation_id=row["derivation_id"],
        )
        item = {key: row[key] for key in (
            "member_id", "kind_contract", "subject", "subject_definition", "original_source", "analyzed_scope",
        )}
        item["selection"] = selection
        if request.view == "publications":
            inspected = inspect_native_source(connection, NativeSourceRequest(
                **selection, view="products", limit=1, max_bytes=request.max_bytes,
            ), cancellation=cancellation)
            if inspected.cut != page["cut"]:
                raise ValueError("publication catalog differs from its exact selected read")
            if len(inspected.rows) != 1 or inspected.next_cursor is not None:
                raise ValueError("publication catalog requires its one complete native header")
            item.update(publication=checked, native=inspected.rows[0], health=inspected.health, release_id=inspected.release_id)
        else:
            item.update(source=checked["source"], selectors=checked["selectors"])
        rows.append(item)
    response = SourceCatalogResponse(
        selection=request, cut=page["cut"], rows=rows,
        obligations=page["obligations"], uses=page["uses"], populations=page["populations"],
        next_cursor=page["continuation"], page_complete=page["page_complete"],
    )
    if len(json_bytes(response.model_dump(mode="python"))) > request.max_bytes:
        raise ValueError("complete source catalog envelope exceeds max_bytes")
    return response
