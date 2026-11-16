"""Current frozen candidate interpretation and native vector input projections."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from pydantic import TypeAdapter

from corpus_structure.methods.contextual_embeddings import EncodedVector, numeric_identity, validate_vector
from corpus_structure.semantic.contextual_retrieval import CandidateList, FrozenInventory, TargetRepresentation


@dataclass(frozen=True)
class InterpretationCandidateTarget:
    target_id: str
    label: str
    description: str
    source_binding: str
    representation_digest: str
    rank: int
    type_name: str | None


@dataclass(frozen=True)
class InterpretationCandidateSet:
    list_id: str
    inventory_id: str
    occurrence_id: str
    targets: tuple[InterpretationCandidateTarget, ...]
    anchors: tuple[Mapping[str, Any], ...]


_CANDIDATE_LIST = TypeAdapter(CandidateList)


_TARGET_REPRESENTATIONS = TypeAdapter(tuple[TargetRepresentation, ...])


def project_interpretation_candidates(
    selected: Mapping[str, Any],
    inventory: Mapping[str, Any],
    list_id: str,
    occurrence_id: str,
    anchors: tuple[Mapping[str, Any], ...],
) -> InterpretationCandidateSet:
    """Exact ordered alternatives from the current selected candidate and inventory products."""
    if selected["occurrence_id"] != occurrence_id:
        raise ValueError("frozen candidate list differs from selected occurrence")
    candidate_list = _CANDIDATE_LIST.validate_python(
        {"profile_id": None, "query_vector_id": None, **selected}
    )
    meaning = {
        key: value
        for key, value in asdict(candidate_list).items()
        if key != "list_id" and value is not None
    }
    if numeric_identity("concept-candidates", meaning) != list_id:
        raise ValueError("frozen candidate list identity differs from its report")
    if inventory["inventory_id"] != candidate_list.inventory_id:
        raise ValueError("frozen candidate list inventory differs from selected inventory")
    targets = _TARGET_REPRESENTATIONS.validate_python(inventory["targets"])
    by_id = {target.target_id: target for target in targets}
    ids = [c.target_id for c in candidate_list.candidates]
    if (
        len(by_id) != len(targets)
        or len(targets) != candidate_list.eligible_target_count
        or len(set(ids)) != len(ids)
        or not set(ids) <= by_id.keys()
        or tuple(c.rank for c in candidate_list.candidates) != tuple(range(1, len(ids) + 1))
    ):
        raise ValueError("frozen candidate alternatives differ from the eligible inventory")
    return InterpretationCandidateSet(
        list_id,
        candidate_list.inventory_id,
        occurrence_id,
        tuple(
            InterpretationCandidateTarget(
                target.target_id,
                target.label,
                target.description,
                target.source_binding,
                target.representation_digest,
                rank,
                target.type_name,
            )
            for rank, target in enumerate((by_id[id_] for id_ in ids), 1)
        ),
        anchors,
    )


def lexical_target_rows(inventory):
    """Exact lexical projection under Python's declared Unicode case semantics."""
    return tuple(
        dict(
            target_id=target.target_id,
            search_text=" ".join((target.label, target.description, *target.aliases)),
            exact_forms=[target.label.lower(), *(alias.lower() for alias in target.aliases)],
        )
        for target in inventory.targets
    )


def transient_vector_relation(
    inventory: FrozenInventory, vectors: Sequence[EncodedVector], *, profile_id: str, dimension: int
):
    """Bound set input for the initial retrieval, before the same report is atomically sealed.

    PostgreSQL scores the complete selected inventory. No temporary table, scalar query per
    target or Python all-pairs computation is introduced.
    """
    from pgvector.sqlalchemy import VECTOR
    from sqlalchemy import Text, bindparam, cast, column, select, values
    from sqlalchemy.dialects.postgresql import ARRAY

    rows = []
    lexical = {row["target_id"]: row for row in lexical_target_rows(inventory)}
    for target in inventory.targets:
        matches = [
            v
            for v in vectors
            if v.object_id == target.target_id
            and v.representation_digest == target.representation_digest
            and v.profile_id == profile_id
        ]
        if not matches:
            raise ValueError("target has no exact representation vector")
        for vector in matches:
            rows.append(
                (
                    inventory.inventory_id,
                    vector.profile_id,
                    target.target_id,
                    cast(
                        bindparam(
                            None,
                            list(validate_vector(vector.values, dimension)),
                            type_=VECTOR(dimension),
                        ),
                        VECTOR(dimension),
                    ),
                    lexical[target.target_id]["search_text"],
                    lexical[target.target_id]["exact_forms"],
                )
            )
    raw = values(
        column("inventory_id", Text),
        column("profile_id", Text),
        column("target_id", Text),
        column("vector", VECTOR(dimension)),
        column("search_text", Text),
        column("exact_forms", ARRAY(Text)),
        name="detached_target_vectors",
    ).data(rows)
    return select(
        raw.c.inventory_id,
        raw.c.profile_id,
        raw.c.target_id,
        raw.c.vector,
        raw.c.search_text,
        raw.c.exact_forms,
    ).subquery("contextual_vector_inputs")
