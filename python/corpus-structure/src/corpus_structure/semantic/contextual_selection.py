"""Current two-phase contextual acquisition on the existing native demand owner.

First produce query and target observations under their own source contexts. Then
acquire exact selected products and freeze one ordinary assembly/retrieval demand.
No vector cache, scheduling service or inferred original producing episode exists.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .data_operation_source_sets import FrozenSourceSet, selected_source_entries

if TYPE_CHECKING:
    from .data_operation_model import SubjectContext
    from .demand_results import CutSelection


@dataclass(frozen=True)
class ContextualSelectedProduct:
    demand_id: str
    product_id: str
    read_id: str | None = None
    expected_cut: str | None = None
    member_id: str | None = None


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


def _selected_product_with_kind(connection, selection, *, project_id, kind_name):
    from .data_operation_source_sets import SelectedSourceSetEntry
    from .data_operation_values import decode_semantic_value
    from .demand_results import CutSelection, read_selected_answer

    filters = {"product_id": selection.product_id}
    if selection.member_id is not None:
        filters["member_id"] = selection.member_id
    answer = read_selected_answer(
        connection,
        "read_selected_outputs",
        selection.demand_id,
        project_id=project_id,
        scope={"product_ids": [selection.product_id]},
        read_id=selection.read_id,
        body=True,
        containers_only=selection.member_id is None,
        limit=2,
        max_bytes=64 * 1024 * 1024,
        **filters,
    )
    cut = CutSelection.from_native(answer["cut"])
    if selection.expected_cut is not None and cut.identity != selection.expected_cut:
        raise ValueError("contextual selection differs from its exact selected read")
    if len(answer["rows"]) != 1 or answer["answer_after"] is not None:
        raise ValueError("contextual selection requires one exact selected fulfilled output proof")
    (header,) = answer["rows"]
    if (header["product_id"], header["member_id"]) != (
        selection.product_id, selection.member_id
    ):
        raise ValueError("contextual selection differs from its exact selected output address")
    expected_kind = (
        kind_name
        if ":" in kind_name
        else "https://corpus-structure.dev/semantic/data-operation-contextual/" + kind_name
    )
    if header["kind"] != expected_kind:
        raise ValueError("contextual selection has a different native nominal contract")
    selected_entry = SelectedSourceSetEntry.from_selected_header(header, cut)
    return (
        decode_semantic_value(header["meaning_body"]),
        selected_entry,
        cut,
        header["kind_contract"],
    )


def _selected_product(connection, selection, *, project_id, kind_name):
    body, entry, cut, _ = _selected_product_with_kind(
        connection, selection, project_id=project_id, kind_name=kind_name
    )
    return body, entry, cut


@dataclass(frozen=True)
class ContextualQuerySelection:
    """One exact source/carrier pair, including their actual selected producing proofs."""

    source_sets: tuple[FrozenSourceSet, ...]
    cuts: tuple[CutSelection, ...]
    query_context: SubjectContext


def acquire_contextual_query_selection(connection, *, project_id, source, occurrence):
    from .data_operation_model import SubjectContext, json_context_meaning
    from .declared_record_sources import DeclaredRecordSource

    source_body, source_entry, source_cut, source_kind = _selected_product_with_kind(
        connection,
        source,
        project_id=project_id,
        kind_name="https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
    )
    occurrence_body, occurrence_entry, occurrence_cut = _selected_product(
        connection,
        occurrence,
        project_id=project_id,
        kind_name="https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
    )
    address = source_entry.entry
    context = SubjectContext(
        project_id,
        address.subject,
        address.original_source,
        address.analyzed_scope,
        subject_definition=address.subject_definition,
    )
    coordinate = source_body["source"]
    pin = DeclaredRecordSource(
        coordinate["document"],
        coordinate["projection"],
        coordinate["section_pointer"],
        coordinate["membership"],
        context,
        address.product,
        address.member,
        source_kind,
    ).pin()
    carrier = occurrence_entry.entry
    if (
        carrier.subject != context.subject
        or carrier.subject_definition != context.subject_definition
        or carrier.original_source != context.original_source
        or json_context_meaning(carrier.analyzed_scope)
        != json_context_meaning(context.analyzed_scope)
        or occurrence_body["pin"] != pin
    ):
        raise ValueError("contextual carrier differs from its exact selected native source/context")
    return ContextualQuerySelection(
        (
            FrozenSourceSet.from_selected("contextual-query-source", (source_entry,)),
            FrozenSourceSet.from_selected("contextual-query-occurrence", (occurrence_entry,)),
        ),
        (source_cut, occurrence_cut),
        context,
    )


def freeze_contextual_query_demand(
    model,
    selection,
    *,
    replicate,
    inference,
    execution_profile,
    context_selection=None,
    source_sets=(),
):
    from .data_operation_demands import OperationSelection, RootSubject, freeze_demand
    from .data_operation_json import json_bytes

    context = selection.query_context
    operation = (
        "retrieve.contextual_query/declared"
        if context_selection is None
        else "retrieve.contextual_query/selected-context"
    )
    return freeze_demand(
        model,
        roots=(RootSubject(context.subject, context.original_source, context.analyzed_scope),),
        targets=(operation,),
        selections=(
            OperationSelection(
                operation,
                replicate=replicate,
                parameters=json_bytes(
                    {} if context_selection is None else dict(context_selection=context_selection)
                ),
            ),
        ),
        inference=inference,
        execution_profile=execution_profile,
        source_sets=(*selection.source_sets, *source_sets),
    )


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
        dict(constraints=source_value([]), exclusions=source_value([])),
    )
    from .data_operation_model import SubjectContext, json_context_meaning

    context = SubjectContext(
        project_id,
        query_entry.entry.subject,
        query_entry.entry.original_source,
        query_entry.entry.analyzed_scope,
        subject_definition=query_entry.entry.subject_definition,
    )
    for selected_entry in (vector_entry, inventory_entry):
        entry = selected_entry.entry
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
            FrozenSourceSet.from_selected("contextual-inventory", (inventory_entry,)),
            FrozenSourceSet.from_selected("contextual-query", (query_entry,)),
            FrozenSourceSet.from_selected("contextual-query-vector", (vector_entry,)),
            FrozenSourceSet.from_selected(
                "contextual-target-vectors", tuple(entry for _, entry, _ in selected)
            ),
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


def acquire_contextual_witness_selection(connection, selection, *, project_id, query, cues):
    """Bind explicitly cited cues from the query's exact selected support closure.

    A missing carrier or a cue outside that closure is a refusal. Callers never
    replace those cases with an empty witness population or a newer source read.
    """
    from .data_operation_json import json_bytes
    from .data_operation_model import SubjectContext, json_context_meaning
    from .data_operation_values import decode_semantic_value
    from .declared_structural_references import DeclaredContributionRef, DeclaredProductRef
    from .demand_results import selected_record_index

    selected_query = next(
        value for value in selection.source_sets if value.name == "contextual-query"
    )
    from .selected_support import SelectedSupportAcquisition

    if not isinstance(selected_query.acquisition, SelectedSupportAcquisition):
        raise ValueError("witness acquisition requires the exact previously selected query")
    (query_read,) = selected_query.acquisition.reads
    pin = query_read.selection
    if query.demand_id != pin.demand_id or (
        query.read_id is not None
        and (query.read_id != pin.read_id or query.expected_cut != pin.cut_id)
    ):
        raise ValueError("witness acquisition differs from the previously selected query read")
    body, query_entry, cut = _selected_product(
        connection,
        replace(query, read_id=pin.read_id, expected_cut=pin.cut_id),
        project_id=project_id,
        kind_name="DdoContextualQuery",
    )
    if selected_query != FrozenSourceSet.from_selected("contextual-query", (query_entry,)):
        raise ValueError("witness acquisition requires the exact previously selected query")
    refs = tuple(DeclaredContributionRef.model_validate(value) for value in cues)
    carrier = DeclaredContributionRef.model_validate(body["carrier"])
    if not refs or carrier not in refs or len(set(refs)) != len(refs):
        raise ValueError(
            "witness acquisition requires distinct cues including its exact query carrier"
        )
    if any(ref.member_id is None for ref in refs):
        raise ValueError("witness cues require true admitted contribution members")
    # Bind stable labels for this frozen selection irrespective of the caller's list order.
    cue_refs = sorted(refs, key=lambda ref: (ref.product_id, ref.member_id or ""))
    pin = body["source_pin"]
    source = DeclaredProductRef(
        product_id=pin["source_product"],
        member_id=pin.get("source_member"),
        kind_contract=pin["kind_contract"],
        project_id=pin["project_id"],
        subject=pin["subject"],
        subject_definition=pin["subject_definition"],
        original_source=pin["original_source"],
        analyzed_scope_meaning=pin["analyzed_scope_meaning"],
    )
    with selected_record_index(
        connection,
        query.demand_id,
        project_id=project_id,
        scope={"product_ids": [query.product_id]},
        read_id=cut.record["read_id"],
        expected_cut=cut.identity,
        capture_frontier=True,
        max_total_bytes=64 * 1024 * 1024,
    ) as (_, index):
        products = index.mapping("kb.data_product", ("id",))
        members = index.mapping("kb.data_product_member", ("product_id", "member_id"))

        def entry(ref):
            parent = products.get(ref.product_id)
            row = parent if ref.member_id is None else members.get((ref.product_id, ref.member_id))
            if parent is None or row is None:
                raise ValueError(
                    "witness reference is unavailable or outside the selected query closure"
                )
            context = SubjectContext(
                parent["project_id"],
                row["subject"],
                row["original_source"],
                json_bytes(row["analyzed_scope"]),
                subject_definition=row["subject_definition"],
            )
            actual = DeclaredProductRef(
                product_id=ref.product_id,
                member_id=ref.member_id,
                kind_contract=row["kind_contract"],
                project_id=context.project_id,
                subject=context.subject,
                subject_definition=context.subject_definition,
                original_source=context.original_source,
                analyzed_scope_meaning=json_context_meaning(context.analyzed_scope).decode(),
            )
            if actual != DeclaredProductRef.model_validate(
                ref.model_dump(exclude={"contribution_id"})
            ):
                raise ValueError(
                    "witness reference differs from its actual selected qualified context"
                )
            value = decode_semantic_value(
                row["canonical_body"] if ref.member_id is None else row["body"]
            )
            if isinstance(ref, DeclaredContributionRef) and (
                value.get("contribution_id") != ref.contribution_id or value.get("pin") != pin
            ):
                raise ValueError("witness cue differs from its selected body/source")
            candidates = selected_source_entries(
                index,
                query_entry.read,
                product_id=ref.product_id,
                member_id=ref.member_id,
                anchor_use_id=query_entry.proof.anchor_use_id,
            )
            if len(candidates) != 1:
                raise ValueError("witness reference requires one exact selected producing proof")
            (selected_entry,) = candidates
            return selected_entry

        source_entry = entry(source)
        cue_entries = []
        for ordinal, ref in enumerate(cue_refs):
            selected = entry(ref)
            cue_entries.append(
                replace(
                    selected,
                    entry=replace(selected.entry, occurrence_label=f"cue:{ordinal}"),
                )
            )
    return ContextualVectorSelection(
        (
            *selection.source_sets,
            FrozenSourceSet.from_selected("contextual-witness-source", (source_entry,)),
            FrozenSourceSet.from_selected("contextual-witness-cues", cue_entries),
        ),
        (*selection.cuts, cut),
        selection.query_context,
    )


def freeze_contextual_witnessed_retrieval_demand(
    model, selection, *, inference, execution_profile, original_sources=(), source_sets=()
):
    """Freeze the actual private authored-binding producer and its retrieval consumer."""
    from .data_operation_demands import RootSubject, freeze_demand

    names = {value.name for value in selection.source_sets}
    if not {"contextual-witness-source", "contextual-witness-cues"} <= names:
        raise ValueError("witnessed retrieval requires exact selected source and cue closure")
    context = selection.query_context
    return freeze_demand(
        model,
        roots=(RootSubject(context.subject, context.original_source, context.analyzed_scope),),
        targets=("retrieve.contextual_vectors/selection", "retrieve.contextual/with-witnesses"),
        inference=inference,
        execution_profile=execution_profile,
        source_sets=(*selection.source_sets, *source_sets),
        original_sources=original_sources,
    )
