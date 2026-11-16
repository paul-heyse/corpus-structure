"""Released contextual operation reports and their native-owned vector read projection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator
from sqlalchemy import select

from corpus_structure.methods.contextual_embeddings import (
    EncodedVector,
    EncoderProfile,
    identity,
    numeric_identity,
    validate_vector,
)
from corpus_structure.semantic.contextual_links import RelationshipDecision, select_relationships
from corpus_structure.semantic.contextual_registry import (
    ExtractedComponentTarget,
    SectionHeadingTarget,
    section_target_input,
)
from corpus_structure.semantic.contextual_retrieval import (
    CandidateList,
    FrozenInventory,
    TargetRepresentation,
    freeze_inventory,
    fuse_candidates,
)
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.structural_products import ExternalSourceRef


class RetainedCandidateListRef(BaseModel):
    """The custody of a frozen inventory read, without caller-authored target labels."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    carrier: RetainedContributionRef
    operation_key: str = Field(pattern=r"^contribution-operation:[0-9a-f]{64}$")
    list_id: str = Field(pattern=r"^concept-candidates:[0-9a-f]{64}$")


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


def interpretation_candidates(
    report: Mapping[str, Any],
    list_id: str,
    occurrence_id: str,
    anchors: tuple[Mapping[str, Any], ...],
) -> InterpretationCandidateSet:
    """Project ordered alternatives from a source-bound, already admitted report."""
    if report.get("version") != "contextual-enrichment-2":
        raise ValueError("candidate report has unsupported meaning")
    selected = [row for row in report["candidate_lists"] if row["list_id"] == list_id]
    if len(selected) != 1 or selected[0]["occurrence_id"] != occurrence_id:
        raise ValueError("frozen candidate list differs from selected occurrence")
    inventories = [
        row for row in report["inventories"] if row["inventory_id"] == selected[0]["inventory_id"]
    ]
    if len(inventories) != 1:
        raise ValueError("frozen candidate list inventory is unavailable")
    definition_bindings = {
        target.reference.component_id: "definition-component:" + target.reference.identity
        for row in report.get("component_targets", ())
        for target in (ExtractedComponentTarget.model_validate(row),)
    }
    return project_interpretation_candidates(
        selected[0],
        inventories[0],
        list_id,
        occurrence_id,
        anchors,
        definition_bindings=definition_bindings,
    )


def project_interpretation_candidates(
    selected: Mapping[str, Any],
    inventory: Mapping[str, Any],
    list_id: str,
    occurrence_id: str,
    anchors: tuple[Mapping[str, Any], ...],
    *,
    definition_bindings: Mapping[str, str] | None = None,
) -> InterpretationCandidateSet:
    """One exact ordered projection for current native and retained sealed reports."""
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
    definition_bindings = {} if definition_bindings is None else definition_bindings
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
                "definition"
                if definition_bindings.get(target.target_id) == target.source_binding
                else target.type_name,
            )
            for rank, target in enumerate((by_id[id_] for id_ in ids), 1)
        ),
        anchors,
    )


class SectionCitationResolution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    occurrence_id: str = Field(min_length=1)
    designator: str = Field(pattern=r"^[0-9]+(?:\.[0-9]+)+$")
    outcome: Literal[
        "selected",
        "ambiguous",
        "unavailable_representation",
        "no_compatible_candidate",
        "insufficient_evidence",
        "witness_budget_exceeded",
        "outside_inventory",
    ]
    eligible_target_ids: tuple[str, ...]

    @model_validator(mode="after")
    def ordered_eligible_targets(self):
        if tuple(sorted(set(self.eligible_target_ids))) != self.eligible_target_ids:
            raise ValueError("section citation requires distinct, stably ordered target identities")
        return self


def enrichment_report(
    *,
    profiles: Sequence[EncoderProfile],
    vectors: Sequence[EncodedVector],
    inventories: Sequence[FrozenInventory] = (),
    candidate_lists: Sequence[CandidateList] = (),
    relationship_decisions: Sequence[RelationshipDecision] = (),
    curated_registry_id: str | None = None,
    component_targets: Sequence[dict] = (),
    section_sources: Sequence[ExternalSourceRef] = (),
    section_catalog_sources: Sequence[ExternalSourceRef] = (),
    section_source_origin_task_id: int | None = None,
    section_targets: Sequence[SectionHeadingTarget] = (),
    section_resolutions: Sequence[dict] = (),
) -> dict:
    """A typed report payload for SourceContributionOperation.contextual_enrichment.

    The ordinary bind_report/completion owner validates its released shape and native source
    closure, then projects it atomically. This function does not write rows or grant authority.
    """
    section_payload = {}
    if section_sources:
        if component_targets or curated_registry_id is not None:
            raise ValueError("section heading inventory has exclusive source authority")
        if type(section_source_origin_task_id) is not int or section_source_origin_task_id <= 0:
            raise ValueError("section heading report lacks original scoped producer custody")
        registry, representations, meanings = section_target_input(section_sources, section_targets)
        if len(inventories) != 1:
            raise ValueError("heading report requires one exact inventory")
        (inventory,) = inventories
        if inventory != freeze_inventory(
            representations,
            source_selection=registry,
            scope=inventory.scope,
            effective_version=inventory.effective_version,
            reliable_type="section-heading",
            semantic_targets=meanings,
        ):
            raise ValueError("heading inventory differs from authenticated target representation")
        resolutions = tuple(
            SectionCitationResolution.model_validate(row) for row in section_resolutions
        )
        by_occurrence = {decision.occurrence_id: decision for decision in relationship_decisions}
        occurrences = [row.occurrence_id for row in resolutions]
        if occurrences != sorted(set(occurrences)) or set(occurrences) != by_occurrence.keys():
            raise ValueError("section resolutions must cover every distinct citation decision")
        for row in resolutions:
            expected_outcome = (
                row.outcome if row.outcome in {"selected", "ambiguous"} else "insufficient_evidence"
            )
            if by_occurrence[row.occurrence_id].outcome != expected_outcome or not set(
                row.eligible_target_ids
            ) <= set(inventory.target_ids):
                raise ValueError("section coverage disagrees with its contextual decision")
        section_payload = dict(
            section_sources=[ref.model_dump(mode="json") for ref in section_sources],
            section_source_origin_task_id=section_source_origin_task_id,
            section_targets=[t.model_dump(mode="json") for t in section_targets],
            section_resolutions=[row.model_dump(mode="json") for row in resolutions],
        )
        if section_catalog_sources:
            section_payload["section_catalog_sources"] = [
                ref.model_dump(mode="json") for ref in section_catalog_sources
            ]
    elif (
        section_catalog_sources
        or section_targets
        or section_resolutions
        or section_source_origin_task_id is not None
    ):
        raise ValueError("heading report requires original selected source references")
    if component_targets:
        from .contextual_registry import component_target_input

        if curated_registry_id is not None:
            raise ValueError("component targets cannot use curated registry attribution")
        _, authenticated_targets = component_target_input(
            tuple(ExtractedComponentTarget.model_validate(t) for t in component_targets)
        )
        if any(t not in authenticated_targets for i in inventories for t in i.targets):
            raise ValueError("inventory target differs from authenticated component representation")
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
            semantic_targets={
                member: group.meaning
                for group in inventory.semantic_groups
                for member in group.member_target_ids
            },
        )
        if expected != inventory:
            raise ValueError("frozen inventory identity or eligibility differs")
    lists = {c.list_id: c for c in candidate_lists}
    if len(lists) != len(candidate_lists):
        raise ValueError("duplicate contextual candidate list")
    for candidate_list in candidate_lists:
        inventory = inventory_map.get(candidate_list.inventory_id)
        vector_id = candidate_list.query_vector_id
        vector = vector_map.get(vector_id) if vector_id is not None else None
        if inventory is None or (vector_id is not None and vector is None):
            raise ValueError("candidate list has unavailable inventory or query vector")
        if vector is not None and (
            vector.object_id != candidate_list.occurrence_id
            or vector.profile_id != candidate_list.profile_id
        ):
            raise ValueError("candidate query vector differs from selected occurrence/profile")
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
            constraints=decision.constraints,
            witnesses=decision.witnesses,
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
            version="contextual-enrichment-2",
            curated_registry_id=curated_registry_id,
            component_targets=tuple(component_targets),
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
            **section_payload,
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
