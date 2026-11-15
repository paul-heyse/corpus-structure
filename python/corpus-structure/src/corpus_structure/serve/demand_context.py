"""Pinned query12 projections from actual selected source and primary members."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.methods.contextual_query import (
    DeclaredQueryContextBinding, DeclaredQueryContextSelection, resolve_query_contexts,
)
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_product_reference import DataProductMemberReference, DataProductReference
from corpus_structure.semantic.declared_formal_readings import DeclaredFormalInventory
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource, DeclaredRecordSource
from corpus_structure.semantic.demand_results import selected_record_index
from corpus_structure.semantic.source_contexts import PreparedNativeSources

from .demand_journey import _cursor


class DemandContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    demand_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    source_product_id: str = Field(min_length=1)
    source_member_id: str | None = None
    primary_product_id: str = Field(min_length=1)
    primary_member_id: str = Field(min_length=1)
    focal_product_id: str = Field(min_length=1)
    focal_member_id: str | None = None
    recipe: Literal["located-frame-2", "located-referent-2", "located-discourse-neighbor-2"]
    read_id: str | None = None
    expected_cut: str | None = None
    max_bytes: int = Field(default=1048576, strict=True, ge=1024, le=67108864)


class _Inventories(Mapping):
    """Lazy pinned native product inventories; disk owns the full required closure."""
    def __init__(self, products):
        self.products = products

    def __getitem__(self, reference):
        if not isinstance(reference, DataProductReference):
            raise KeyError(reference)
        record = self.products[reference.product_id]
        body = decode_semantic_value(record["canonical_body"])
        if not isinstance(body, dict) or not {"source", "selectors", "members"} <= body.keys():
            raise ValueError("selected primary dependency is not a declared characterization")
        names = dict(occurrence="occurrences", annotation="annotations", membership="memberships", role="roles", term="terms", choice="choices")
        inventory = {name: [] for name in names.values()}
        for packet in body["members"]:
            member = packet["body"]
            if member.get("record_type") in names:
                inventory[names[member["record_type"]]].append(member)
        inventory.update(source=body["source"], selectors=body["selectors"], dependencies=body.get("dependencies", []))
        return DeclaredFormalInventory(reference, json_bytes(inventory))

    def __iter__(self):
        return (DataProductReference(key) for key in self.products)

    def __len__(self):
        return len(self.products)


def inspect_demand_context(connection, request: DemandContextRequest):
    """Project retained facts under an explicit recipe; perform no recognition or encoding."""
    selected_products = sorted({request.source_product_id, request.primary_product_id, request.focal_product_id})
    scope = {"product_ids": selected_products}
    with selected_record_index(connection, request.demand_id, project_id=request.project_id,
        scope=scope, read_id=request.read_id, expected_cut=request.expected_cut,
        max_bytes=request.max_bytes) as (cut, index):
        products = index.mapping("kb.data_product", ("id",))
        members = index.mapping("kb.data_product_member", ("product_id", "member_id"))
        def selected(product, member):
            row = products.get(product) if member is None else members.get((product, member))
            if row is None:
                return None, None
            return row, decode_semantic_value(row["canonical_body" if member is None else "body"])
        source_row, source_body = selected(request.source_product_id, request.source_member_id)
        focal_row, focal_body = selected(request.focal_product_id, request.focal_member_id)
        if source_row is None or focal_row is None or request.primary_product_id not in products:
            return dict(format="selected-query-context-v1", availability="unavailable", reason="requested semantic references are outside the selected cut closure", cut_id=cut.identity, cut=cut.record, recipe=request.recipe, inference="not_run")
        coordinate = source_body["source"]
        address = DeclaredRecordSource(coordinate["document"], coordinate["projection"], coordinate["section_pointer"], coordinate["membership"], SubjectContext(request.project_id, source_row["subject"], source_row["original_source"], json_bytes(source_row["analyzed_scope"])), request.source_product_id, request.source_member_id, source_row["kind_contract"])
        source = DeclaredNativeFrameSource(json_bytes(source_body).decode(), json_bytes(address.pin()).decode())
        if not isinstance(focal_body, dict) or not {"occurrence_id", "anchors"} <= focal_body.keys():
            raise ValueError("focal selected member is not an exact located source contribution")
        reference = DataProductMemberReference(DataProductReference(request.primary_product_id), request.primary_member_id)
        selection = DeclaredQueryContextSelection(request.recipe, (DeclaredQueryContextBinding(focal_body["occurrence_id"], reference),))
        contexts = resolve_query_contexts(selection, _Inventories(products), (focal_body,), source, preparation=PreparedNativeSources((source,)))
        result = contexts[focal_body["occurrence_id"]]
        pinned = request.model_copy(update=dict(read_id=cut.record["read_id"], expected_cut=cut.identity))
        report = dict(format="selected-query-context-v1", availability="available", cut_id=cut.identity, cut=cut.record,
                      source=address.pin(), focal=dict(product_id=request.focal_product_id, member_id=request.focal_member_id),
                      primary=reference.values(), recipe=request.recipe, context=result.report(),
                      rendered=result.rendered, representation_digest=result.representation_digest,
                      inference="not_run", resource_handle=_cursor(pinned.model_dump(mode="python")))
        if len(json_bytes(report)) > request.max_bytes:
            raise ValueError("complete selected context response exceeds max_bytes")
        return report
