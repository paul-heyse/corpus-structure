"""Typed knowledge reads from one actual selected native admission.

The demand reader owns authority and current trust. This adapter decodes only the
explicit selected whole product; historical source references remain provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.demand_results import CutSelection, read_demand_result
from corpus_structure.semantic.demand_wire import decode_wire_demand_result
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.rich_knowledge_contracts import DdoRichSelectedMember
from corpus_structure.semantic.rich_query_projection import (
    RichFrontierInput,
    RichQueryInput,
    frontier_content_witness,
)


@dataclass(frozen=True)
class SelectedRichReference:
    cut: CutSelection
    read_request: bytes
    reference: DdoRichSelectedMember
    context: SubjectContext
    content_witness: str | None = field(default=None, kw_only=True)


@dataclass(frozen=True)
class SelectedRichKnowledge(SelectedRichReference):
    inputs: RichQueryInput


def read_selected_rich_reference(
    connection,
    demand_id: str,
    *,
    project_id: str,
    product_id: str,
    continuation: dict | None = None,
    cut: CutSelection | None = None,
    max_bytes: int = 8 * 1024 * 1024,
    content_witness: bool = False,
    _bodies: bool = False,
) -> SelectedRichReference:
    """Read a whole admitted graph under its genuine producing support and cut.

    One native obligation is enough to establish this explicitly addressed value.
    No corpus completeness or absence follows from this selected graph. Repeated
    equal-value uses retain the first actual selected support in native order.
    """
    if not product_id:
        raise ValueError("knowledge reads require an explicit selected product")
    scope = {"operation_id": "rich.admit", "product_ids": [product_id]}
    page = read_demand_result(
        connection,
        demand_id,
        project_id=project_id,
        continuation=continuation,
        cut=cut,
        limit=1,
        max_bytes=max_bytes,
        view="products" if _bodies else "frontier",
        recheck_bodies=not _bodies,
        scope=scope,
    )
    native = page.record
    obligations = {item["obligation_id"]: item for item in native["obligations"]}
    selected = []
    for use in native["uses"]:
        obligation = obligations[use["obligation_id"]]
        if obligation["operation_id"] != "rich.admit":
            raise ValueError("knowledge selection differs from its native admission owner")
        if use["fate"] != "fulfilled" or use["completion_state"] != "success":
            continue
        for product in use["products"]:
            if product["product_id"] == product_id and product["member_id"] is None:
                selected.append((use, product))
    if len(selected) != 1:
        raise ValueError("selected knowledge lacks one current whole native admission")
    use, product = selected[0]
    if not use["derivation_id"]:
        raise ValueError("selected knowledge lacks its actual producing derivation")
    context = SubjectContext(
        project_id,
        product["subject"],
        product["original_source"],
        json_bytes(product["analyzed_scope"]),
        subject_definition=product["subject_definition"],
    )
    reference = DdoRichSelectedMember(
        product_id=product_id,
        member_id=None,
        kind_contract=product["kind_contract"],
        support_references=(
            ComputationalSupportReference(
                derivation_id=use["derivation_id"],
                admission_use_id=use["use_id"],
            ),
        ),
    )
    # Reacquiring this same read preserves visibility and rechecks current trust;
    # it never follows a latest result or substitutes a different admission use.
    request = json_bytes(
        {
            "demand_id": demand_id,
            "read_id": native["read_id"],
            "view": "products" if _bodies else "frontier",
            "scope": scope,
        }
    )
    if not _bodies:
        witness = None
        if content_witness:
            frontier = decode_wire_demand_result(page.content)
            witness = frontier_content_witness(RichFrontierInput(frontier, json_bytes(frontier)))
        return SelectedRichReference(page.cut, request, reference, context, content_witness=witness)
    prepared = open_release(connection, native["release_id"])
    model = bound_data_operation_model(prepared)
    inputs = RichQueryInput(
        prepared,
        model,
        context,
        json_bytes(reference.model_dump(mode="python")),
        json_bytes(product["body"]),
    )
    return SelectedRichKnowledge(page.cut, request, reference, context, inputs)


def read_selected_rich_knowledge(
    connection,
    demand_id,
    *,
    project_id,
    product_id,
    continuation=None,
    cut=None,
    max_bytes=8 * 1024 * 1024,
) -> SelectedRichKnowledge:
    selected = read_selected_rich_reference(
        connection,
        demand_id,
        project_id=project_id,
        product_id=product_id,
        continuation=continuation,
        cut=cut,
        max_bytes=max_bytes,
        _bodies=True,
    )
    if not isinstance(selected, SelectedRichKnowledge):
        raise RuntimeError("whole rich read lacks its validated graph")
    return selected
