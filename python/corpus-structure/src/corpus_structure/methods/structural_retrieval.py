"""Actual bounded E5/PostgreSQL retrieval over attributed source passages.

Prepare sources with the owned structural source reader first. Encoder work runs
without a DB snapshot; candidate scoring then borrows a fresh bounded snapshot.
Selection readings are explicit upstream source interpretations, never cosine facts.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict

from corpus_structure.methods.contextual_embeddings import (
    E5,
    ContextInput,
    encode_contexts,
    identity,
)
from corpus_structure.methods.structural_products import definition_applicability
from corpus_structure.semantic.contextual_retrieval import freeze_inventory, retrieve_candidates
from corpus_structure.semantic.contextual_storage import (
    enrichment_report,
    transient_vector_relation,
)
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.structural_products import (
    DefinitionReading,
    StructuralInput,
    StructuralProductReport,
    source_target,
)


def retrieve_source_definitions(
    engine,
    inputs: StructuralInput,
    *,
    usage_id: str,
    target_ids: Sequence[str],
    readings: Sequence[DefinitionReading] = (),
    budget: int = 10,
    channel_budget: int = 30,
    cached_vectors: Sequence = (),
    check_active: Callable[[], None] | None = None,
) -> StructuralProductReport:
    """Return independently inspectable nominations and supplied applicability readings.

    Inputs come from prepare_structural_sources. Completion reauthenticates their
    original pins after retrieval. Readings outside the resulting shortlist remain
    unselected; independently authored references diagnose those retrieval omissions.
    """
    passages = {p.passage_id: p for p in inputs.passages}
    if usage_id not in passages or usage_id in target_ids:
        raise ValueError("definition retrieval requires a distinct anchored usage")
    if len(set(target_ids)) != len(target_ids) or not set(target_ids) <= set(passages):
        raise ValueError("definition targets must be distinct original source passages")
    if not 1 <= len(target_ids) < E5.max_items:
        raise ValueError("definition target population exceeds actual encoder bound")
    if not 1 <= budget <= channel_budget <= 256:
        raise ValueError("definition candidate budgets require bounded overfetch")
    usage = passages[usage_id]
    targets = tuple(source_target(passages[t]) for t in target_ids)
    selection = identity("source-definition-selection", [asdict(t) for t in targets])
    inventory = freeze_inventory(
        targets,
        source_selection=selection,
        scope=inputs.scope,
        effective_version=usage.effective_version,
    )
    if inputs.inventory_id != inventory.inventory_id:
        raise ValueError("source-first input inventory must be frozen before producer execution")
    if check_active is not None:
        check_active()
    contexts = [
        ContextInput(
            usage_id,
            "source-passage:" + usage.identity,
            "query",
            usage.text,
            usage.text,
            0,
            len(usage.text),
            parent=usage.parent or "",
        )
    ]
    for target in inventory.targets:
        contexts.append(
            ContextInput(
                target.target_id,
                target.source_binding,
                "document",
                target.label,
                target.description,
                0,
                len(target.label),
                parent=target.parent or "",
                type_name=target.type_name,
                representation_digest=target.representation_digest,
            )
        )
    encoded = encode_contexts(
        contexts, E5, check_active=check_active, cached_vectors=cached_vectors
    )
    all_vectors = (
        *encoded.vectors,
        *(v for v in cached_vectors if v.vector_id in encoded.reused_vector_ids),
    )
    vectors = {v.object_id: v for v in all_vectors}
    target_vectors = tuple(vectors[t.target_id] for t in inventory.targets)
    if check_active is not None:
        check_active()
    with read_snapshot(engine) as conn:
        candidates = retrieve_candidates(
            conn,
            occurrence_id=usage_id,
            query=vectors[usage_id],
            inventory=inventory,
            relation=transient_vector_relation(inventory, target_vectors),
            lexical_query=usage.text,
            dimension=E5.dimension,
            budget=budget,
            channel_budget=channel_budget,
        )
    if check_active is not None:
        check_active()
    selected = tuple(c.target_id for c in candidates.candidates)
    if len({r.target_id for r in readings}) != len(readings):
        raise ValueError("duplicate upstream definition reading")
    if not {r.target_id for r in readings} <= set(target_ids):
        raise ValueError("upstream definition reading outside declared target inventory")
    contextual = enrichment_report(
        profiles=(E5,), vectors=all_vectors, inventories=(inventory,), candidate_lists=(candidates,)
    )
    result = definition_applicability(
        inputs,
        usage_id=usage_id,
        candidate_list_id=candidates.list_id,
        eligible_targets=inventory.target_ids,
        candidate_targets=selected,
        readings=tuple(r for r in readings if r.target_id in selected),
    )
    return StructuralProductReport.model_validate(
        {**result.model_dump(mode="python"), "retrieval_report": contextual}
    )


def source_definition_inventory(
    inputs: StructuralInput, *, target_ids: Sequence[str], effective_version: str | None = None
):
    """Freeze source-target membership before any embedding or relationship output."""
    passages = {p.passage_id: p for p in inputs.passages}
    if len(set(target_ids)) != len(target_ids) or not set(target_ids) <= set(passages):
        raise ValueError("definition inventory contains duplicate or foreign target passages")
    targets = tuple(source_target(passages[t]) for t in target_ids)
    selection = identity("source-definition-selection", [asdict(t) for t in targets])
    return freeze_inventory(
        targets, source_selection=selection, scope=inputs.scope, effective_version=effective_version
    )


def replay_source_definition_candidates(
    report: StructuralProductReport, *, budget: int, readings: Sequence[DefinitionReading] = ()
) -> StructuralProductReport:
    """Refuse new channel work; re-fuse a retained exact source inventory/list.

    The result is a new candidate-list/product identity. Original raw scores,
    vectors and source-first population remain unchanged. This is not a new
    encoder/provider execution or a claim of independent semantic quality.
    """
    from pydantic import TypeAdapter

    from corpus_structure.methods.contextual_embeddings import EncodedVector
    from corpus_structure.semantic.contextual_retrieval import (
        ChannelHit,
        TargetRepresentation,
        fuse_candidates,
    )
    from corpus_structure.semantic.identity import canonical_bytes

    if report.definition is None or report.retrieval_report is None:
        raise ValueError("candidate replay requires retained source definition retrieval")
    raw = report.retrieval_report
    if len(raw["profiles"]) != 1 or raw["profiles"][0]["profile_id"] != E5.profile_id:
        raise ValueError("candidate replay requires the selected E5 source profile")
    previous = next(
        c for c in raw["candidate_lists"] if c["list_id"] == report.definition.candidate_list_id
    )
    selected = next(i for i in raw["inventories"] if i["inventory_id"] == previous["inventory_id"])
    target_adapter = TypeAdapter(TargetRepresentation)
    targets = tuple(
        target_adapter.validate_json(canonical_bytes(target), strict=True)
        for target in selected["targets"]
    )
    inventory = freeze_inventory(
        targets,
        source_selection=selected["source_selection"],
        scope=selected["scope"],
        effective_version=selected.get("effective_version"),
        reliable_type=selected.get("reliable_type"),
        parent=selected.get("parent"),
    )
    if (
        inventory.inventory_id != selected["inventory_id"]
        or inventory.inventory_id != report.inputs.inventory_id
    ):
        raise ValueError("retained candidate inventory differs from frozen input")
    vector_adapter = TypeAdapter(EncodedVector)
    vectors = tuple(
        vector_adapter.validate_json(canonical_bytes(vector), strict=True)
        for vector in raw["vectors"]
    )
    query = next(v for v in vectors if v.vector_id == previous["query_vector_id"])
    channels = {
        c["channel"]: tuple(
            ChannelHit(h["target_id"], h["score"], tuple(h.get("evidence", ()))) for h in c["hits"]
        )
        for c in previous["channel_results"]
    }
    candidates = fuse_candidates(
        occurrence_id=previous["occurrence_id"],
        query=query,
        inventory=inventory,
        channels=channels,
        budget=budget,
        channel_budget=previous["channel_budget"],
        lexical_query=previous["lexical_query"],
    )
    # Verify that reconstructing the predecessor preserves its full intrinsic ID.
    old = fuse_candidates(
        occurrence_id=previous["occurrence_id"],
        query=query,
        inventory=inventory,
        channels=channels,
        budget=previous["unique_target_budget"],
        channel_budget=previous["channel_budget"],
        lexical_query=previous["lexical_query"],
    )
    if old.list_id != previous["list_id"]:
        raise ValueError("retained channel scores do not reconstruct predecessor list")
    updated = enrichment_report(
        profiles=(E5,), vectors=vectors, inventories=(inventory,), candidate_lists=(candidates,)
    )
    available = tuple(c.target_id for c in candidates.candidates)
    if len({r.target_id for r in readings}) != len(readings) or not {
        r.target_id for r in readings
    } <= set(inventory.target_ids):
        raise ValueError("replayed source readings differ from target inventory")
    result = definition_applicability(
        report.inputs,
        usage_id=report.definition.usage_id,
        candidate_list_id=candidates.list_id,
        eligible_targets=inventory.target_ids,
        candidate_targets=available,
        readings=tuple(r for r in readings if r.target_id in available),
        inventory_gap=report.definition.inventory_coverage == "known_gap",
    )
    return StructuralProductReport.model_validate(
        {**result.model_dump(mode="python"), "retrieval_report": updated}
    )
