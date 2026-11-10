"""Released contextual operation reports and their native-owned vector read projection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator
from sqlalchemy import Connection, select
from sqlalchemy.sql.selectable import FromClause

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
    candidate_list = _CANDIDATE_LIST.validate_python(
        {"profile_id": None, "query_vector_id": None, **selected[0]}
    )
    meaning = {
        key: value
        for key, value in asdict(candidate_list).items()
        if key != "list_id" and value is not None
    }
    if numeric_identity("concept-candidates", meaning) != list_id:
        raise ValueError("frozen candidate list identity differs from its report")
    inventories = [
        row for row in report["inventories"] if row["inventory_id"] == candidate_list.inventory_id
    ]
    if len(inventories) != 1:
        raise ValueError("frozen candidate list inventory is unavailable")
    targets = _TARGET_REPRESENTATIONS.validate_python(inventories[0]["targets"])
    by_id = {target.target_id: target for target in targets}
    definition_bindings = {
        target.reference.component_id: "definition-component:" + target.reference.identity
        for row in report.get("component_targets", ())
        for target in (ExtractedComponentTarget.model_validate(row),)
    }
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


def read_interpretation_candidates(
    conn: Connection,
    ref: RetainedCandidateListRef,
    *,
    source_pin: Mapping[str, Any],
    project_id: str,
    release_id: str,
) -> InterpretationCandidateSet:
    """Resolve the exact native carrier and report in the caller's owned read snapshot."""
    from .contribution_queries import read_source_contributions
    from .operations import BoundReader
    from .query import bind_completed_result

    carrier = ref.carrier
    if (carrier.project_id, carrier.release_id) != (project_id, release_id):
        raise ValueError("frozen candidate selection belongs to another project or release")
    session = bind_completed_result(conn, carrier.run_id)
    if (
        session.completed_cut_id != carrier.cut_id
        or session.binding.release_id != release_id
        or session.binding.data_revision != carrier.result_revision
    ):
        raise ValueError("frozen candidate selection differs from completed cut or revision")
    retained = BoundReader(
        conn, carrier.run_id, session.prepared, carrier.cut_id, analysis=False
    ).retained_source_contribution(carrier)
    rows = [
        row
        for row in retained["contributions"]
        if row["contribution_id"] == carrier.contribution_id
    ]
    if len(rows) != 1:
        raise ValueError("frozen candidate selection has no unique native occurrence carrier")
    (occurrence,) = rows
    if (
        occurrence["operation_key"] != ref.operation_key
        or occurrence["semantic_type"] != "contextual.located_mention"
        or occurrence["pin"] != source_pin
        or not occurrence.get("anchors")
    ):
        raise ValueError("frozen candidate carrier differs from exact source or operation")
    inventory = read_source_contributions(
        conn,
        prepared=session.prepared,
        run_id=carrier.run_id,
        cut_id=carrier.cut_id,
        source_view_id=source_pin["source_view_id"],
        selected_task_id=carrier.selected_task_id,
        method="retrieve.contextual",
        operation_key=ref.operation_key,
        contribution_id=carrier.contribution_id,
        limit=1,
        include_details=True,
    )
    if len(inventory.operations) != 1 or inventory.more:
        raise ValueError("frozen candidate operation is unavailable or ambiguous")
    (operation,) = inventory.operations
    if (
        not operation["cut_member"]
        or operation["origin_task_id"] != carrier.origin_task_id
        or not operation.get("contextual_enrichment")
    ):
        raise ValueError("frozen candidate operation differs from exact producing task")
    return interpretation_candidates(
        operation["contextual_enrichment"],
        ref.list_id,
        occurrence["occurrence_id"],
        tuple(occurrence["anchors"]),
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
    vector_reuse: Sequence[VectorReuse] = (),
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


@dataclass(frozen=True)
class PreparedContextualInventory:
    binding: tuple[int, int | None, str, str | None]
    inventory: FrozenInventory
    vectors: tuple[EncodedVector, ...]
    profile_id: str
    dimension: int
    relation: FromClause

    def matches(self, binding, inventory, vectors, profile_id, dimension):
        return (
            self.binding == binding
            and self.inventory is inventory
            and self.vectors is vectors
            and self.profile_id == profile_id
            and self.dimension == dimension
        )


def prepare_contextual_inventory(binding, inventory, vectors, *, profile_id, dimension):
    """Own one deeply immutable input preparation, without a borrowed database handle."""
    if type(inventory) is not FrozenInventory or type(inventory.inventory_id) is not str:
        raise ValueError("contextual preparation requires immutable inventory")
    if type(inventory.targets) is not tuple or type(vectors) is not tuple:
        raise ValueError("contextual preparation requires immutable tuples")
    for target in inventory.targets:
        if type(target) is not TargetRepresentation:
            raise ValueError("contextual preparation requires immutable target records")
        if type(target.aliases) is not tuple or any(type(a) is not str for a in target.aliases):
            raise ValueError("contextual preparation requires immutable aliases")
        if any(
            type(getattr(target, name)) is not str
            for name in (
                "target_id",
                "representation_digest",
                "source_binding",
                "label",
                "description",
            )
        ):
            raise ValueError("contextual preparation requires immutable target fields")
    for vector in vectors:
        if type(vector) is not EncodedVector:
            raise ValueError("contextual preparation requires immutable vector records")
        if type(vector.values) is not tuple or any(
            type(v) not in (int, float) for v in vector.values
        ):
            raise ValueError("contextual preparation requires immutable vector values")
        if any(
            type(getattr(vector, name)) is not str
            for name in (
                "vector_id",
                "object_id",
                "source_binding",
                "profile_id",
                "input_digest",
                "representation_digest",
            )
        ):
            raise ValueError("contextual preparation requires immutable vector fields")
    relation = transient_vector_relation(
        inventory, vectors, profile_id=profile_id, dimension=dimension
    )
    return PreparedContextualInventory(binding, inventory, vectors, profile_id, dimension, relation)


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
                    " ".join((target.label, target.description, *target.aliases)),
                    [target.label.lower(), *(a.lower() for a in target.aliases)],
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
