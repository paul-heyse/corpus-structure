"""Source-supported scoped relationship selection, never canonical identity assignment.

Witnesses are inputs authenticated by the operation/native custody boundary, not predictions
manufactured from cosine. All accepted alternatives remain attributable to the same fixed list.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.methods.contextual_embeddings import identity
from corpus_structure.semantic.contextual_retrieval import CandidateList, FrozenInventory

class RetainedRelationshipDecisionRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    """Original custody of one selected edge, without caller-authored semantic premises."""

    project_id: Annotated[str, Field(min_length=1)]
    run_id: Annotated[int, Field(strict=True, gt=0)]
    cut_id: Annotated[int, Field(strict=True, gt=0)]
    release_id: Annotated[str, Field(min_length=1)]
    result_revision: int = Field(strict=True, ge=0)
    selected_task_id: Annotated[int, Field(strict=True, gt=0)]
    origin_task_id: Annotated[int, Field(strict=True, gt=0)]
    runtime_fingerprint: Annotated[str, Field(min_length=1)]
    operation_key: Annotated[str, Field(min_length=1)]
    decision_id: Annotated[str, Field(min_length=1)]
    edge_id: Annotated[str, Field(min_length=1)]
    occurrence_contribution_id: Annotated[str, Field(min_length=1)]



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
    basis: Literal["explicit_source_cue", "producer_group", "geometry", "model_reading", "admitted_derivation"]
    support_state: Literal["supported", "unsupported", "unassessed", "ambiguous"] = "unassessed"

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
        if self.relation not in RELATIONS or self.basis not in {"explicit_source_cue", "producer_group", "geometry", "model_reading", "admitted_derivation"}:
            raise ValueError("unsupported relationship kind or witness basis")
        if self.support_state not in {"supported", "unsupported", "unassessed", "ambiguous"}:
            raise ValueError("unsupported witness assessment state")


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
class RelationshipConstraint:
    constraint_id: str
    relation_kinds: tuple[RelationKind, ...]
    occurrence_role: str
    target_role: str
    multiplicity: Literal["one", "many"]
    exhaustive: bool = False

    def __post_init__(self):
        if not all((self.constraint_id, self.occurrence_role, self.target_role, self.relation_kinds)):
            raise ValueError("relationship constraint requires named roles and relation kinds")
        if self.multiplicity not in {"one", "many"} or not isinstance(self.exhaustive, bool):
            raise ValueError("unsupported constraint multiplicity or exhaustive premise")
        if len(set(self.relation_kinds)) != len(self.relation_kinds) or not set(self.relation_kinds) <= RELATIONS:
            raise ValueError("constraint has duplicate or unsupported relationship kinds")


@dataclass(frozen=True)
class RelationshipEdge:
    edge_id: str
    constraint_id: str
    occurrence_id: str
    target_id: str
    relation: RelationKind
    witnesses: tuple[RelationshipWitness, ...]
    selection: Literal["forced", "preferred"]


@dataclass(frozen=True)
class AlternativeGroup:
    constraint_id: str
    edges: tuple[RelationshipEdge, ...]
    reason: str


@dataclass(frozen=True)
class RelationshipDecision:
    decision_id: str
    candidate_list_id: str
    occurrence_id: str
    scope: str
    effective_version: str | None
    policy_id: str
    exclusion_snapshot: str
    outcome: Literal["selected", "partial", "ambiguous", "local_sense", "new_concept", "insufficient_evidence"]
    constraints: tuple[RelationshipConstraint, ...]
    witnesses: tuple[RelationshipWitness, ...]
    selected_edges: tuple[RelationshipEdge, ...]
    alternative_groups: tuple[AlternativeGroup, ...]
    unresolved_constraints: tuple[str, ...]
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
    constraints: Sequence[RelationshipConstraint],
    witnesses: Sequence[RelationshipWitness] = (),
    exclusions: frozenset[tuple[str, str]] = frozenset(),
    exclusion_snapshot: str | None = None,
    proposal: ProposalWitness | None = None,
    insufficient_reason: str = "source evidence is insufficient",
    policy_id: str = "source-supported-scoped-links-2",
) -> RelationshipDecision:
    if candidates.inventory_id != inventory.inventory_id:
        raise ValueError("selector inventory differs from frozen candidate list")
    if inventory.scope != scope or inventory.effective_version != effective_version:
        raise ValueError("selector scope/version differs from inventory")
    if policy_id != "source-supported-scoped-links-2":
        raise ValueError("unsupported relationship policy")
    expected_snapshot = identity("scoped-exclusions", sorted(exclusions))
    if exclusion_snapshot is not None and exclusion_snapshot != expected_snapshot:
        raise ValueError("exclusion snapshot differs from exact serialized constraints")
    exclusion_snapshot = expected_snapshot
    if not all((source_binding, scope, exclusion_snapshot, policy_id)):
        raise ValueError("selector requires source, policy and exclusion snapshot")
    available = {candidate.target_id for candidate in candidates.candidates}
    ordered_constraints = tuple(sorted(constraints, key=lambda q: q.constraint_id))
    if not ordered_constraints or len({q.constraint_id for q in ordered_constraints}) != len(ordered_constraints):
        raise ValueError("selection requires distinct declared relationship constraints")
    owners = {}
    for constraint in ordered_constraints:
        for kind in constraint.relation_kinds:
            if kind in owners:
                raise ValueError("relationship kind competes in multiple constraints")
            owners[kind] = constraint
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
        if witness.relation not in owners:
            raise ValueError("witness has no declared relationship constraint")
        seen.add(witness.witness_id)
        if effective_version is None and targets[witness.target_id].effective_version is not None:
            version_unestablished = True
            continue
        if witness.support_state in {"unsupported", "ambiguous"}:
            continue
        if relationship_compatible(
            witness.relation,
            occurrence_id=witness.occurrence_id,
            target_id=witness.target_id,
            exclusions=exclusions,
        ):
            retained.append(witness)
    selected, groups, unresolved = [], [], []
    for constraint in ordered_constraints:
        pairs = sorted({(w.target_id, w.relation) for w in retained if w.relation in constraint.relation_kinds})
        edges = []
        for target_id, relation in pairs:
            evidence = tuple(sorted((w for w in retained if w.target_id == target_id and w.relation == relation), key=lambda w: w.witness_id))
            meaning = dict(constraint_id=constraint.constraint_id, occurrence_id=candidates.occurrence_id,
                           target_id=target_id, relation=relation, witnesses=tuple(asdict(w) for w in evidence),
                           selection="forced" if constraint.exhaustive else "preferred")
            edges.append(RelationshipEdge(identity("scoped-edge", meaning), constraint.constraint_id,
                                          candidates.occurrence_id, target_id, relation, evidence,
                                          "forced" if constraint.exhaustive else "preferred"))
        if not edges:
            unresolved.append(constraint.constraint_id)
        if constraint.multiplicity == "one" and len(edges) > 1:
            unresolved.append(constraint.constraint_id)
            groups.append(AlternativeGroup(constraint.constraint_id, tuple(edges), "competing senses under declared exclusive constraint"))
        else:
            selected.extend(edges)
    if proposal is not None:
        if selected or groups:
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
    elif selected:
        outcome = "partial" if unresolved else "selected"
        reason = "some relationship constraints remain unresolved" if unresolved else None
    elif groups:
        outcome, reason = "ambiguous", "competing alternatives remain unresolved"
    else:
        if version_unestablished:
            insufficient_reason = "source effective version is unestablished for version-specific targets"
        if not insufficient_reason:
            raise ValueError("insufficient evidence requires its actual limitation")
        outcome, reason = "insufficient_evidence", insufficient_reason
    result = RelationshipDecision(
        "", candidates.list_id, candidates.occurrence_id, scope, effective_version, policy_id,
        exclusion_snapshot, outcome, ordered_constraints,
        tuple(sorted(witnesses, key=lambda w: w.witness_id)), tuple(selected), tuple(groups), tuple(unresolved),
        proposal, reason, source_binding,
        tuple(ScopedExclusion(left, right) for left, right in sorted(exclusions)),
    )
    meaning = {key: value for key, value in asdict(result).items() if key != "decision_id"}
    return replace(result, decision_id=identity("scoped-relationship", meaning))
