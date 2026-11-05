"""Released contextual operation reports and their native-owned vector read projection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

from sqlalchemy import select

from corpus_structure.methods.contextual_embeddings import (
    EncodedVector,
    EncoderProfile,
    identity,
    validate_vector,
)
from corpus_structure.semantic.contextual_links import RelationshipDecision, select_relationships
from corpus_structure.semantic.contextual_retrieval import (
    CandidateList,
    FrozenInventory,
    freeze_inventory,
    fuse_candidates,
)


@dataclass(frozen=True)
class VectorReuse:
    vector_id: str
    origin_task_id: int
    origin_runtime_id: str
    result_digest: str


@dataclass(frozen=True)
class CachedTargetVector:
    vector: EncodedVector
    reuse: VectorReuse


def enrichment_report(
    *,
    profiles: Sequence[EncoderProfile],
    vectors: Sequence[EncodedVector],
    inventories: Sequence[FrozenInventory] = (),
    candidate_lists: Sequence[CandidateList] = (),
    relationship_decisions: Sequence[RelationshipDecision] = (),
    curated_registry_id: str | None = None,
    vector_reuse: Sequence[VectorReuse] = (),
) -> dict:
    """A typed report payload for SourceContributionOperation.contextual_enrichment.

    The ordinary bind_report/completion owner validates its released shape and native source
    closure, then projects it atomically. This function does not write rows or grant authority.
    """
    profile_map = {p.profile_id: p for p in profiles}
    if len(profile_map) != len(profiles):
        raise ValueError("duplicate contextual profile")
    if len({v.vector_id for v in vectors}) != len(vectors):
        raise ValueError("duplicate contextual vector")
    vector_map = {v.vector_id: v for v in vectors}
    for vector in vectors:
        if vector.profile_id not in profile_map:
            raise ValueError("vector profile is not in report")
        validate_vector(vector.values, profile_map[vector.profile_id].dimension)
        expected_id = identity(
            "context-vector",
            [
                vector.object_id,
                vector.source_binding,
                vector.profile_id,
                vector.input_digest,
                vector.representation_digest,
            ],
        )
        if vector.vector_id != expected_id:
            raise ValueError("vector identity differs from input/representation/profile")
    if len({r.vector_id for r in vector_reuse}) != len(vector_reuse) or any(
        r.vector_id not in vector_map for r in vector_reuse
    ):
        raise ValueError("vector reuse needs distinct retained vector identities")
    inventory_map = {i.inventory_id: i for i in inventories}
    if len(inventory_map) != len(inventories):
        raise ValueError("duplicate contextual inventory")
    for inventory in inventories:
        for target in inventory.targets:
            for profile in profiles:
                matches = [
                    v
                    for v in vectors
                    if v.object_id == target.target_id and v.profile_id == profile.profile_id
                ]
                if (
                    len(matches) != 1
                    or matches[0].representation_digest != target.representation_digest
                ):
                    raise ValueError(
                        "inventory target vector is missing or uses a different representation"
                    )
        expected = freeze_inventory(
            inventory.targets,
            source_selection=inventory.source_selection,
            scope=inventory.scope,
            effective_version=inventory.effective_version,
            reliable_type=inventory.reliable_type,
            parent=inventory.parent,
        )
        if expected != inventory:
            raise ValueError("frozen inventory identity or eligibility differs")
    lists = {c.list_id: c for c in candidate_lists}
    if len(lists) != len(candidate_lists):
        raise ValueError("duplicate contextual candidate list")
    for candidate_list in candidate_lists:
        inventory = inventory_map.get(candidate_list.inventory_id)
        vector = vector_map.get(candidate_list.query_vector_id)
        if inventory is None or vector is None or vector.profile_id != candidate_list.profile_id:
            raise ValueError("candidate list has unavailable inventory or query vector")
        if vector.object_id != candidate_list.occurrence_id:
            raise ValueError("candidate query vector belongs to another occurrence")
        channels = {c.channel: c.hits for c in candidate_list.channel_results}
        if len(channels) != len(candidate_list.channel_results):
            raise ValueError("duplicate candidate channel")
        expected = fuse_candidates(
            occurrence_id=candidate_list.occurrence_id,
            query=vector,
            inventory=inventory,
            channels=channels,
            budget=candidate_list.unique_target_budget,
            channel_budget=candidate_list.channel_budget,
            lexical_query=candidate_list.lexical_query,
        )
        if expected != candidate_list:
            raise ValueError("candidate identity/ranks/fusion differ from declared channels")
        if any(c.target_id not in inventory.target_ids for c in candidate_list.candidates):
            raise ValueError("candidate list has foreign target")
    for decision in relationship_decisions:
        candidate_list = lists.get(decision.candidate_list_id)
        if candidate_list is None or candidate_list.occurrence_id != decision.occurrence_id:
            raise ValueError("relationship decision has unavailable candidate list")
        expected = select_relationships(
            candidates=candidate_list,
            inventory=inventory_map[candidate_list.inventory_id],
            source_binding=decision.source_binding,
            scope=decision.scope,
            effective_version=decision.effective_version,
            witnesses=decision.alternatives,
            exclusions=frozenset((e.left, e.right) for e in decision.exclusions),
            exclusion_snapshot=decision.exclusion_snapshot,
            proposal=decision.proposal,
            insufficient_reason=decision.reason or "source evidence is insufficient",
            policy_id=decision.policy_id,
        )
        if expected != decision:
            raise ValueError("relationship identity or declared selection semantics differ")

    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if v is not None}
        if isinstance(value, (tuple, list)):
            return tuple(clean(v) for v in value)
        return value

    cleaned = clean(
        dict(
            version="contextual-enrichment-1",
            curated_registry_id=curated_registry_id,
            vector_reuse=[asdict(r) for r in vector_reuse],
            product_counts=dict(
                profiles=len(profiles),
                vectors=len(vectors),
                inventories=len(inventories),
                candidate_lists=len(candidate_lists),
                relationship_decisions=len(relationship_decisions),
            ),
            profiles=[dict(profile_id=p.profile_id, **asdict(p)) for p in profiles],
            vectors=[asdict(v) for v in vectors],
            inventories=[asdict(i) for i in inventories],
            candidate_lists=[asdict(c) for c in candidate_lists],
            relationship_decisions=[asdict(d) for d in relationship_decisions],
        )
    )
    assert isinstance(cleaned, dict)
    return cleaned


def eligible_vector_relation(task_id: int):
    """Owned task pin prevents a foreign run's inventory ID from changing retrieval inputs."""
    from corpus_structure.semantic.metadata import table

    relation = table("kb.contextual_target_vector")
    if type(task_id) is not int or task_id <= 0:
        raise ValueError("vector relation requires an actual producing task")
    return select(relation).where(relation.c.task_id == task_id).subquery("owned_target_vectors")


def transient_vector_relation(inventory: FrozenInventory, vectors: Sequence[EncodedVector]):
    """Bound set input for the initial retrieval, before the same report is atomically sealed.

    PostgreSQL scores the complete selected inventory. No temporary table, scalar query per
    target or Python all-pairs computation is introduced.
    """
    from pgvector.sqlalchemy import VECTOR
    from sqlalchemy import Text, cast, column, select, values
    from sqlalchemy.dialects.postgresql import ARRAY

    rows = []
    for target in inventory.targets:
        matches = [
            v
            for v in vectors
            if v.object_id == target.target_id
            and v.representation_digest == target.representation_digest
        ]
        if not matches:
            raise ValueError("target has no exact representation vector")
        for vector in matches:
            rows.append(
                (
                    inventory.inventory_id,
                    vector.profile_id,
                    target.target_id,
                    str(list(vector.values)),
                    " ".join((target.label, target.description, *target.aliases)),
                    [target.label.lower(), *(a.lower() for a in target.aliases)],
                )
            )
    raw = values(
        column("inventory_id", Text),
        column("profile_id", Text),
        column("target_id", Text),
        column("vector_text", Text),
        column("search_text", Text),
        column("exact_forms", ARRAY(Text)),
        name="detached_target_vectors",
    ).data(rows)
    return select(
        raw.c.inventory_id,
        raw.c.profile_id,
        raw.c.target_id,
        cast(raw.c.vector_text, VECTOR()).label("vector"),
        raw.c.search_text,
        raw.c.exact_forms,
    ).subquery("contextual_vector_inputs")


def cached_target_vectors(conn, *, run_id: int, profile_id: str, targets, read_budget=None):
    """Reuse only original sealed vector observations under the exact same runtime and release."""
    from sqlalchemy import cast, func, literal, tuple_
    from sqlalchemy.dialects.postgresql import JSONPATH

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget

    runs, tasks, vectors, results = map(
        table, ("ops.run", "ops.task", "kb.contextual_vector", "ops.task_result")
    )
    current = conn.execute(
        select(runs.c.project_id, runs.c.release_id, runs.c.runtime_id).where(runs.c.id == run_id)
    ).one()
    if current.runtime_id is None or not targets:
        return ()
    expected = {t.target_id: t for t in targets}
    query = (
        select(vectors.c.object_id, func.min(vectors.c.task_id).label("task_id"))
        .join(tasks, tasks.c.id == vectors.c.task_id)
        .join(runs, runs.c.id == tasks.c.run_id)
        .where(
            runs.c.project_id == current.project_id,
            runs.c.release_id == current.release_id,
            runs.c.runtime_id == current.runtime_id,
            tasks.c.status.in_(("done", "empty")),
            tasks.c.reused_task_id.is_(None),
            vectors.c.profile_id == profile_id,
            tuple_(vectors.c.object_id, vectors.c.source_binding).in_(
                [(t.target_id, t.source_binding) for t in targets]
            ),
        )
        .group_by(vectors.c.object_id)
    )
    owners = query.subquery("target_vector_owners")
    groups = (
        select(owners.c.task_id, func.array_agg(owners.c.object_id).label("objects"))
        .group_by(owners.c.task_id)
        .subquery("owned_cached_objects")
    )
    selector = cast(
        literal(
            "$.contribution_operations[*].contextual_enrichment.vectors[*] ? "
            "(@.profile_id == $profile && @.object_id == $objects[*])"
        ),
        JSONPATH,
    )
    variables = func.jsonb_build_object(
        "profile", profile_id, "objects", func.to_jsonb(groups.c.objects)
    )
    projected = func.jsonb_path_query_array(results.c.body, selector, variables).label("vectors")
    reused_ids = func.jsonb_path_query_array(
        results.c.body,
        cast(
            literal(
                "$.contribution_operations[*].contextual_enrichment.vector_reuse[*] ? "
                "(@.vector_id == $selected[*].vector_id).vector_id"
            ),
            JSONPATH,
        ),
        func.jsonb_build_object("selected", projected),
    ).label("reused_ids")
    body_query = (
        select(
            results.c.task_id,
            projected,
            reused_ids,
            func.encode(
                func.sha256(func.convert_to(func.data.canonical_json(results.c.body), "UTF8")),
                "hex",
            ).label("digest"),
        )
        .join(groups, groups.c.task_id == results.c.task_id)
        .order_by(results.c.task_id)
    )
    budget = read_budget or PublishedReadBudget(256, 8 * 1024 * 1024)
    budget.preflight(conn, body_query)
    found = {}
    for row in conn.execute(body_query):
        budget.value(dict(row._mapping))
        reused = set(row.reused_ids)
        for raw in row.vectors:
            target = expected.get(raw["object_id"])
            if target is None or raw["object_id"] in found or raw["vector_id"] in reused:
                continue
            if (
                raw["profile_id"] != profile_id
                or raw["source_binding"] != target.source_binding
                or raw.get("representation_digest") != target.representation_digest
            ):
                continue
            value = EncodedVector(
                raw["vector_id"],
                raw["object_id"],
                raw["source_binding"],
                raw["profile_id"],
                raw["input_digest"],
                tuple(raw["values"]),
                raw["representation_digest"],
            )
            found[raw["object_id"]] = CachedTargetVector(
                value, VectorReuse(value.vector_id, row.task_id, current.runtime_id, row.digest)
            )
    return tuple(found[key] for key in sorted(found))
