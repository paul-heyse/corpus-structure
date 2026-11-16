"""Current two-phase contextual acquisition on the existing native demand owner.

First produce query and target observations under their own source contexts. Then
acquire exact selected products and freeze one ordinary assembly/retrieval demand.
No vector cache, scheduling service or inferred original producing episode exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .data_operation_source_sets import FrozenSourceSet, SourceSetEntry

if TYPE_CHECKING:
    from .data_operation_model import SubjectContext
    from .demand_results import CutSelection


@dataclass(frozen=True)
class ContextualSelectedProduct:
    demand_id: str
    product_id: str
    read_id: str | None = None
    expected_cut: str | None = None


def contextual_target_discovery(producer):
    from .data_operation_demands import DiscoverySelection

    if producer not in {
        "retrieve.contextual_targets/curated",
        "retrieve.contextual_targets/components",
    }:
        raise ValueError("contextual target discovery requires its declared source owner")
    # The first edge authenticates which exact parent member the projection may
    # consume. The second expands the dependent encoder under that target's context.
    return (
        DiscoverySelection(
            producer,
            "result",
            "retrieve.contextual_target/declared",
            "contextual-targets",
            target_role="target",
        ),
        DiscoverySelection(
            producer, "result", "retrieve.contextual_target_vector/declared", "contextual-targets"
        ),
    )


def freeze_contextual_target_demand(
    model,
    *,
    roots,
    producer,
    replicate,
    inference,
    execution_profile,
    original_sources=(),
    source_sets=(),
):
    """Freeze real project-curated or original-source component target work."""
    from .data_operation_demands import OperationSelection, freeze_demand

    if producer == "retrieve.contextual_targets/curated" and any(
        root.original_source is not None for root in roots
    ):
        raise ValueError("curated target demand cannot inherit a query original")
    if producer == "retrieve.contextual_targets/components" and any(
        root.original_source is None for root in roots
    ):
        raise ValueError("component target demand requires its actual original source")
    return freeze_demand(
        model,
        roots=roots,
        targets=(producer,),
        selections=(
            OperationSelection("retrieve.contextual_target_vector/declared", replicate=replicate),
        ),
        discovery=contextual_target_discovery(producer),
        inference=inference,
        execution_profile=execution_profile,
        original_sources=original_sources,
        source_sets=source_sets,
    )


def _selected_product(connection, selection, *, project_id, kind_name):
    from .data_operation_identity import decode_semantic_value
    from .data_operation_json import json_bytes
    from .data_operation_model import SubjectContext
    from .data_product_reference import DataProductReference
    from .demand_results import selected_record_index

    with selected_record_index(
        connection,
        selection.demand_id,
        project_id=project_id,
        scope={"product_ids": [selection.product_id]},
        read_id=selection.read_id,
        expected_cut=selection.expected_cut,
        capture_frontier=True,
        max_total_bytes=64 * 1024 * 1024,
    ) as (cut, index):
        uses = {
            row["derivation_id"]
            for row in index.frontier_rows("uses")
            if row["fate"] == "fulfilled"
        }
        outputs = [
            row
            for row in index.rows("ops.data_derivation_output")
            if row["product_id"] == selection.product_id and row["derivation_id"] in uses
        ]
        if not outputs:
            raise ValueError("contextual selection is not an actual selected fulfilled output")
        product = index.mapping("kb.data_product", ("id",))[selection.product_id]
        contracts = index.mapping("sem.data_kind_contract", ("kind_contract",))
        contract = contracts[product["kind_contract"]]
        if (
            contract["kind"]
            != "https://corpus-structure.dev/semantic/data-operation-contextual/" + kind_name
        ):
            raise ValueError("contextual selection has a different native nominal contract")
        context = SubjectContext(
            project_id,
            product["subject"],
            product["original_source"],
            json_bytes(product["analyzed_scope"]),
            subject_definition=product["subject_definition"],
        )
        entry = SourceSetEntry.from_semantic_source(
            DataProductReference(selection.product_id), context=context
        )
        return decode_semantic_value(product["canonical_body"]), entry, cut


@dataclass(frozen=True)
class ContextualVectorSelection:
    """Exact selected inputs; fresh demand admission rechecks their live support."""

    source_sets: tuple[FrozenSourceSet, ...]
    cuts: tuple[CutSelection, ...]
    query_context: SubjectContext


def acquire_contextual_vector_selection(
    connection, *, project_id, inventory, query, query_vector, targets
):
    """Check complete inventory closure before freezing the final selected demand.

    Empty targets are explicit and succeed only for an actually empty inventory.
    Unavailable/missing/ambiguous target selections never become empty observations.
    """
    from .contextual_operations import prepare_contextual_retrieval
    from .contextual_target_products import selected_vector_frame
    from .observations import source_value

    inventory_body, inventory_entry, inventory_cut = _selected_product(
        connection, inventory, project_id=project_id, kind_name="DdoContextualInventory"
    )
    query_body, query_entry, query_cut = _selected_product(
        connection, query, project_id=project_id, kind_name="DdoContextualQuery"
    )
    vector_body, vector_entry, vector_cut = _selected_product(
        connection, query_vector, project_id=project_id, kind_name="DdoContextualQueryVector"
    )
    selected = tuple(
        _selected_product(
            connection, value, project_id=project_id, kind_name="DdoContextualTargetVector"
        )
        for value in targets
    )
    frame = selected_vector_frame(
        inventory_body, vector_body, tuple(body for body, _, _ in selected)
    )
    # Reuse the real membership/source/query/profile checks without opening a
    # retrieval connection or manufacturing relationship/absence evidence.
    prepare_contextual_retrieval(
        query_body,
        inventory_body,
        frame,
        dict(constraints=source_value([]), witnesses=source_value([]), exclusions=source_value([])),
    )
    from .data_operation_model import SubjectContext, json_context_meaning

    context = SubjectContext(
        project_id,
        query_entry.subject,
        query_entry.original_source,
        query_entry.analyzed_scope,
        subject_definition=query_entry.subject_definition,
    )
    for entry in (vector_entry, inventory_entry):
        if (
            entry.subject,
            entry.subject_definition,
            entry.original_source,
            json_context_meaning(entry.analyzed_scope),
        ) != (
            context.subject,
            context.subject_definition,
            context.original_source,
            json_context_meaning(context.analyzed_scope),
        ):
            raise ValueError(
                "contextual query/inventory selection belongs to another exact context"
            )
    return ContextualVectorSelection(
        (
            FrozenSourceSet("contextual-inventory", (inventory_entry,)),
            FrozenSourceSet("contextual-query", (query_entry,)),
            FrozenSourceSet("contextual-query-vector", (vector_entry,)),
            FrozenSourceSet("contextual-target-vectors", tuple(entry for _, entry, _ in selected)),
        ),
        (inventory_cut, query_cut, vector_cut, *(cut for _, _, cut in selected)),
        context,
    )


def freeze_contextual_retrieval_demand(
    model, selection, *, inference, execution_profile, original_sources=(), source_sets=()
):
    from .data_operation_demands import RootSubject, freeze_demand

    context = selection.query_context
    return freeze_demand(
        model,
        roots=(RootSubject(context.subject, context.original_source, context.analyzed_scope),),
        targets=("retrieve.contextual_vectors/selection", "retrieve.contextual/declared"),
        inference=inference,
        execution_profile=execution_profile,
        source_sets=(*selection.source_sets, *source_sets),
        original_sources=original_sources,
    )
