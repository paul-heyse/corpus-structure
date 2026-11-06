"""Frozen eligible concept inventories and exact PostgreSQL candidate retrieval.

This is distinct from source-view search. The compiled/native owner supplies an authenticated
relation; this module never creates storage or authorizes a source/inventory selection.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from typing import Any, Literal

from sqlalchemy import any_, func, literal, select
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.engine import Connection
from sqlalchemy.sql.selectable import FromClause

from corpus_structure.methods.contextual_embeddings import (
    EncodedVector,
    identity,
    numeric_identity,
    validate_vector,
)


@dataclass(frozen=True)
class TargetRepresentation:
    target_id: str
    representation_digest: str
    source_binding: str
    label: str
    description: str
    aliases: tuple[str, ...] = ()
    type_name: str | None = None
    parent: str | None = None
    scope: str = "global"
    effective_version: str | None = None

    def __post_init__(self):
        if not all(
            (
                self.target_id,
                self.representation_digest,
                self.source_binding,
                self.label,
                self.description,
                self.scope,
            )
        ):
            raise ValueError("target representation requires identity, source and description")
        meaning = asdict(self)
        del meaning["representation_digest"]
        if self.representation_digest != identity("target-description", meaning):
            raise ValueError("target representation digest differs from declared description")
        if not isinstance(self.aliases, tuple) or any(not alias for alias in self.aliases):
            raise ValueError("aliases must be nonempty immutable strings")


def target_representation(
    target_id: str,
    source_binding: str,
    label: str,
    description: str,
    *,
    aliases: tuple[str, ...] = (),
    type_name: str | None = None,
    parent: str | None = None,
    scope: str = "global",
    effective_version: str | None = None,
) -> TargetRepresentation:
    meaning = dict(
        target_id=target_id,
        source_binding=source_binding,
        label=label,
        description=description,
        aliases=aliases,
        type_name=type_name,
        parent=parent,
        scope=scope,
        effective_version=effective_version,
    )
    return TargetRepresentation(
        representation_digest=identity("target-description", meaning), **meaning
    )


@dataclass(frozen=True)
class SemanticTargetGroup:
    """Inventory-local equality of authenticated target meaning, retaining every origin."""

    target_id: str
    member_target_ids: tuple[str, ...]
    meaning: dict[str, Any]


type _MeaningValue = (
    str | int | float | bool | list[_MeaningValue] | dict[str, _MeaningValue] | None
)


def _meaning_value(value: object) -> _MeaningValue:
    if isinstance(value, dict):
        return _meaning(value)
    if isinstance(value, (tuple, list)):
        return [_meaning_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("semantic target meaning requires JSON values")


def _meaning(value: Mapping[str, Any]) -> dict[str, _MeaningValue]:
    return {key: _meaning_value(item) for key, item in value.items() if item is not None}


def semantic_target_groups(
    targets: Sequence[TargetRepresentation],
    semantic_targets: Mapping[str, Mapping[str, Any]],
) -> tuple[SemanticTargetGroup, ...]:
    groups: dict[str, tuple[dict[str, _MeaningValue], list[str]]] = {}
    for target in targets:
        if target.source_binding.startswith("definition-component:"):
            if target.target_id not in semantic_targets:
                raise ValueError(
                    "component inventory requires authenticated semantic target meaning"
                )
            meaning = _meaning(semantic_targets[target.target_id])
            if not {
                "term",
                "content",
                "interpretation",
                "scope",
            } <= meaning.keys() or meaning.keys() - {
                "term",
                "content",
                "interpretation",
                "scope",
                "effective_version",
            }:
                raise ValueError(
                    "component target meaning requires its exclusive source-resolved variant"
                )
        else:
            meaning = _meaning(dict(curated_target=asdict(target)))
        target_id = identity("semantic-target", meaning)
        if target_id not in groups:
            groups[target_id] = (meaning, [])
        groups[target_id][1].append(target.target_id)
    return tuple(
        SemanticTargetGroup(target_id, tuple(sorted(members)), meaning)
        for target_id, (meaning, members) in sorted(groups.items())
    )


@dataclass(frozen=True)
class FrozenInventory:
    inventory_id: str
    source_selection: str
    scope: str
    effective_version: str | None
    targets: tuple[TargetRepresentation, ...]
    reliable_type: str | None = None
    parent: str | None = None
    semantic_groups: tuple[SemanticTargetGroup, ...] = ()

    @property
    def target_ids(self) -> tuple[str, ...]:
        return tuple(target.target_id for target in self.targets)


def freeze_inventory(
    targets: Sequence[TargetRepresentation],
    *,
    source_selection: str,
    scope: str,
    effective_version: str | None = None,
    reliable_type: str | None = None,
    parent: str | None = None,
    semantic_targets: Mapping[str, Mapping[str, Any]] | None = None,
) -> FrozenInventory:
    if not source_selection or not scope:
        raise ValueError("inventory requires exact source selection and scope")
    if len({target.target_id for target in targets}) != len(targets):
        raise ValueError("duplicate target identity; equal labels never merge targets")
    eligible = tuple(
        sorted(
            (
                target
                for target in targets
                if target.scope in {scope, "global"}
                and (
                    effective_version is None
                    or target.effective_version in {None, effective_version}
                )
                and (reliable_type is None or target.type_name in {None, reliable_type})
                and (parent is None or target.parent in {None, parent})
            ),
            key=lambda target: target.target_id,
        )
    )
    groups = semantic_target_groups(eligible, semantic_targets or {})
    dimensions = dict(
        source_selection=source_selection,
        scope=scope,
        effective_version=effective_version,
        reliable_type=reliable_type,
        parent=parent,
        targets=[asdict(target) for target in eligible],
        policy="eligible-concepts-2",
        semantic_groups=[asdict(group) for group in groups],
    )
    return FrozenInventory(
        identity("concept-inventory", dimensions),
        source_selection,
        scope,
        effective_version,
        eligible,
        reliable_type,
        parent,
        groups,
    )


@dataclass(frozen=True)
class ChannelHit:
    target_id: str
    score: float
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChannelEvidence:
    channel: str
    rank: int
    raw_score: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Candidate:
    target_id: str
    rank: int
    fusion_score: float
    channels: tuple[ChannelEvidence, ...]


@dataclass(frozen=True)
class ChannelResult:
    channel: str
    hits: tuple[ChannelHit, ...]


@dataclass(frozen=True)
class CandidateList:
    list_id: str
    occurrence_id: str
    query_vector_id: str
    profile_id: str
    inventory_id: str
    policy_id: str
    unique_target_budget: int
    channel_budget: int
    candidates: tuple[Candidate, ...]
    eligible_target_count: int
    outcome: Literal["succeeded", "empty"]
    channel_results: tuple[ChannelResult, ...]
    lexical_query: str


RETRIEVAL_POLICY = "exact-alias-postgresql-english-cosine-rrf60-1"


def fuse_candidates(
    *,
    occurrence_id: str,
    query: EncodedVector,
    inventory: FrozenInventory,
    channels: Mapping[str, Sequence[ChannelHit]],
    budget: int = 10,
    channel_budget: int = 30,
    lexical_query: str = "",
) -> CandidateList:
    if query.object_id != occurrence_id:
        raise ValueError("query vector belongs to another occurrence")
    if not occurrence_id or not query.vector_id or not query.profile_id:
        raise ValueError("candidate list requires occurrence and vector identities")
    if (
        type(budget) is not int
        or type(channel_budget) is not int
        or not 1 <= budget <= channel_budget
    ):
        raise ValueError("candidate budgets require positive bounded overfetch")
    if not channels or not set(channels) <= {"alias", "lexical", "dense"}:
        raise ValueError("candidate retrieval requires explicit supported channels")
    eligible = set(inventory.target_ids)
    by_target: dict[str, list[ChannelEvidence]] = {}
    for channel, hits in sorted(channels.items()):
        if len(hits) > channel_budget:
            raise ValueError("channel exceeds declared overfetch budget")
        seen = set()
        for rank, hit in enumerate(hits, 1):
            if hit.target_id not in eligible or not math.isfinite(hit.score):
                raise ValueError("channel contains foreign target or nonfinite score")
            if hit.target_id in seen:
                raise ValueError("one target may contribute only once per channel")
            seen.add(hit.target_id)
            by_target.setdefault(hit.target_id, []).append(
                ChannelEvidence(channel, rank, hit.score, hit.evidence)
            )
    scores = {
        target: sum(1 / (60 + value.rank) for value in evidence)
        for target, evidence in by_target.items()
    }
    ordered = sorted(by_target, key=lambda target: (-scores[target], target))[:budget]
    candidates = tuple(
        Candidate(target, rank, scores[target], tuple(by_target[target]))
        for rank, target in enumerate(ordered, 1)
    )
    result = CandidateList(
        "",
        occurrence_id,
        query.vector_id,
        query.profile_id,
        inventory.inventory_id,
        RETRIEVAL_POLICY,
        budget,
        channel_budget,
        candidates,
        len(eligible),
        "succeeded" if candidates else "empty",
        tuple(ChannelResult(name, tuple(hits)) for name, hits in sorted(channels.items())),
        lexical_query,
    )
    meaning = {key: value for key, value in asdict(result).items() if key != "list_id"}
    return replace(result, list_id=numeric_identity("concept-candidates", meaning))


def retrieve_candidates(
    conn: Connection,
    *,
    occurrence_id: str,
    query: EncodedVector,
    inventory: FrozenInventory,
    relation: FromClause,
    lexical_query: str,
    dimension: int,
    budget: int = 10,
    channel_budget: int = 30,
) -> CandidateList:
    """Score one authenticated frozen eligible relation, set-wise, without Python all-pairs.

    Required columns: inventory_id, profile_id, target_id, vector, search_text, exact_forms.
    A MATERIALIZED eligible CTE prevents an ANN index from changing exact neighbor membership.
    The caller retains its owned read snapshot/cancellation and authenticates selected membership.
    """
    vector = validate_vector(query.values, dimension)
    if not lexical_query.strip():
        raise ValueError("retrieval lexical query cannot be empty")
    if (
        type(budget) is not int
        or type(channel_budget) is not int
        or not 1 <= budget <= channel_budget
    ):
        raise ValueError("candidate budgets require positive bounded overfetch")
    if not inventory.targets:
        return fuse_candidates(
            occurrence_id=occurrence_id,
            query=query,
            inventory=inventory,
            channels={"alias": (), "lexical": (), "dense": ()},
            budget=budget,
            channel_budget=channel_budget,
            lexical_query=lexical_query,
        )
    eligible = (
        select(relation)
        .where(
            relation.c.inventory_id == inventory.inventory_id,
            relation.c.profile_id == query.profile_id,
            relation.c.target_id.in_(inventory.target_ids),
        )
        .cte("eligible_concept_vectors")
        .prefix_with("MATERIALIZED")
    )
    # Storage uniqueness and complete profile coverage are native admission obligations;
    # refuse an incomplete projection instead of treating missing vectors as retrieval misses.
    actual = tuple(
        conn.execute(select(eligible.c.target_id).order_by(eligible.c.target_id)).scalars()
    )
    if actual != inventory.target_ids:
        raise ValueError("eligible inventory vector membership is incomplete or duplicated")
    distance = eligible.c.vector.cosine_distance(list(vector))
    config = literal("english").cast(REGCONFIG)
    tsquery = func.websearch_to_tsquery(config, lexical_query)
    tsvector = func.to_tsvector(config, eligible.c.search_text)
    lexical_score = func.ts_rank_cd(tsvector, tsquery)
    statements = {
        "dense": select(eligible.c.target_id, (1 - distance).label("score"))
        .order_by(distance, eligible.c.target_id)
        .limit(channel_budget),
        "lexical": select(eligible.c.target_id, lexical_score.label("score"))
        .where(tsvector.op("@@")(tsquery))
        .order_by(lexical_score.desc(), eligible.c.target_id)
        .limit(channel_budget),
        "alias": select(eligible.c.target_id, literal(1.0).label("score"))
        .where(func.lower(literal(lexical_query)) == any_(eligible.c.exact_forms))
        .order_by(eligible.c.target_id)
        .limit(channel_budget),
    }
    channels = {
        name: tuple(ChannelHit(row.target_id, float(row.score)) for row in conn.execute(statement))
        for name, statement in statements.items()
    }
    return fuse_candidates(
        occurrence_id=occurrence_id,
        query=query,
        inventory=inventory,
        channels=channels,
        budget=budget,
        channel_budget=channel_budget,
        lexical_query=lexical_query,
    )
