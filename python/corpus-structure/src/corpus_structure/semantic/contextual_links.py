"""Source-supported scoped relationship selection, never canonical identity assignment.

Witnesses are inputs authenticated by the operation/native custody boundary, not predictions
manufactured from cosine. All accepted alternatives remain attributable to the same fixed list.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from typing import Literal

from corpus_structure.methods.contextual_embeddings import identity
from corpus_structure.semantic.contextual_retrieval import CandidateList, FrozenInventory

RelationKind = Literal[
    "denotes", "alias-of", "defined-by", "specializes", "compared-with", "participates-in"
]
RELATIONS = {"denotes", "alias-of", "defined-by", "specializes", "compared-with", "participates-in"}


@dataclass(frozen=True)
class RelationshipWitness:
    witness_id: str
    occurrence_id: str
    target_id: str
    relation: RelationKind
    source_binding: str
    scope: str
    effective_version: str | None
    evidence_ids: tuple[str, ...]
    basis: Literal["explicit_source_cue"]

    def __post_init__(self):
        if (
            not all(
                (
                    self.witness_id,
                    self.occurrence_id,
                    self.target_id,
                    self.source_binding,
                    self.scope,
                )
            )
            or not self.evidence_ids
            or any(not e for e in self.evidence_ids)
        ):
            raise ValueError("relationship witness requires exact endpoints and source evidence")
        if self.relation not in RELATIONS or self.basis != "explicit_source_cue":
            raise ValueError("similarity and model scores are not relationship witnesses")


@dataclass(frozen=True)
class ProposalWitness:
    witness_id: str
    occurrence_id: str
    inventory_id: str
    source_binding: str
    scope: str
    effective_version: str | None
    proposal_id: str
    kind: Literal["local_sense", "new_concept"]
    examined_targets: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    reason: str

    def __post_init__(self):
        if not all(
            (
                self.witness_id,
                self.occurrence_id,
                self.inventory_id,
                self.source_binding,
                self.scope,
                self.proposal_id,
                self.reason,
            )
        ):
            raise ValueError("proposal requires source-grounded reason and exact inventory")
        if self.kind not in {"local_sense", "new_concept"} or not self.evidence_ids:
            raise ValueError("proposal requires explicit kind and evidence")


@dataclass(frozen=True)
class ScopedExclusion:
    left: str
    right: str


@dataclass(frozen=True)
class RelationshipDecision:
    decision_id: str
    candidate_list_id: str
    occurrence_id: str
    scope: str
    effective_version: str | None
    policy_id: str
    exclusion_snapshot: str
    outcome: Literal["selected", "ambiguous", "local_sense", "new_concept", "insufficient_evidence"]
    alternatives: tuple[RelationshipWitness, ...]
    proposal: ProposalWitness | None
    reason: str | None
    source_binding: str
    exclusions: tuple[ScopedExclusion, ...]


def relationship_compatible(
    relation: RelationKind,
    *,
    occurrence_id: str,
    target_id: str,
    exclusions: frozenset[tuple[str, str]],
) -> bool:
    if relation not in RELATIONS:
        raise ValueError("unsupported relationship kind")
    if occurrence_id == target_id:
        return False
    # Exclusion prevents denotation/alias assignment, not an assertion that two distinct
    # concepts are compared or participate together. No transitive closure occurs here.
    excluded = (occurrence_id, target_id) in exclusions or (target_id, occurrence_id) in exclusions
    return not (excluded and relation in {"denotes", "alias-of"})


def select_relationships(
    *,
    candidates: CandidateList,
    inventory: FrozenInventory,
    source_binding: str,
    scope: str,
    effective_version: str | None,
    witnesses: Sequence[RelationshipWitness] = (),
    exclusions: frozenset[tuple[str, str]] = frozenset(),
    exclusion_snapshot: str | None = None,
    proposal: ProposalWitness | None = None,
    insufficient_reason: str = "source evidence is insufficient",
    policy_id: str = "source-supported-scoped-links-1",
) -> RelationshipDecision:
    if candidates.inventory_id != inventory.inventory_id:
        raise ValueError("selector inventory differs from frozen candidate list")
    if inventory.scope != scope or inventory.effective_version != effective_version:
        raise ValueError("selector scope/version differs from inventory")
    if policy_id != "source-supported-scoped-links-1":
        raise ValueError("unsupported relationship policy")
    expected_snapshot = identity("scoped-exclusions", sorted(exclusions))
    if exclusion_snapshot is not None and exclusion_snapshot != expected_snapshot:
        raise ValueError("exclusion snapshot differs from exact serialized constraints")
    exclusion_snapshot = expected_snapshot
    if not all((source_binding, scope, exclusion_snapshot, policy_id)):
        raise ValueError("selector requires source, policy and exclusion snapshot")
    available = {candidate.target_id for candidate in candidates.candidates}
    retained = []
    version_unestablished = False
    targets = {target.target_id: target for target in inventory.targets}
    seen = set()
    for witness in witnesses:
        if (
            witness.occurrence_id != candidates.occurrence_id
            or witness.target_id not in available
            or witness.source_binding != source_binding
            or witness.scope != scope
            or witness.effective_version != effective_version
        ):
            raise ValueError("relationship witness differs from selected source/endpoints/scope")
        if witness.witness_id in seen:
            raise ValueError("duplicate relationship witness")
        seen.add(witness.witness_id)
        if effective_version is None and targets[witness.target_id].effective_version is not None:
            version_unestablished = True
            continue
        if relationship_compatible(
            witness.relation,
            occurrence_id=witness.occurrence_id,
            target_id=witness.target_id,
            exclusions=exclusions,
        ):
            retained.append(witness)
    alternatives = tuple(sorted(retained, key=lambda w: (w.target_id, w.relation, w.witness_id)))
    distinct = {(w.target_id, w.relation) for w in alternatives}
    if proposal is not None:
        if alternatives:
            raise ValueError("proposal cannot silently override supported relationships")
        if (
            proposal.inventory_id != inventory.inventory_id
            or proposal.occurrence_id != candidates.occurrence_id
            or proposal.source_binding != source_binding
            or proposal.scope != scope
            or proposal.effective_version != effective_version
            or set(proposal.examined_targets) != available
            or len(set(proposal.examined_targets)) != len(proposal.examined_targets)
        ):
            raise ValueError("proposal differs from source or examined fixed candidate population")
        outcome = proposal.kind
        reason = proposal.reason
    elif distinct:
        outcome = "selected" if len(distinct) == 1 else "ambiguous"
        reason = None
    else:
        if version_unestablished:
            insufficient_reason = (
                "source effective version is unestablished for version-specific targets"
            )
        if not insufficient_reason:
            raise ValueError("insufficient evidence requires its actual limitation")
        outcome, reason = "insufficient_evidence", insufficient_reason
    result = RelationshipDecision(
        "",
        candidates.list_id,
        candidates.occurrence_id,
        scope,
        effective_version,
        policy_id,
        exclusion_snapshot,
        outcome,
        alternatives,
        proposal,
        reason,
        source_binding,
        tuple(ScopedExclusion(left, right) for left, right in sorted(exclusions)),
    )
    meaning = {key: value for key, value in asdict(result).items() if key != "decision_id"}
    return replace(result, decision_id=identity("scoped-relationship", meaning))
