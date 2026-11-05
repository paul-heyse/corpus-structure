"""Real protected report completion and exact pgvector retrieval on controlled source inputs."""

from dataclasses import replace
from math import sqrt
from types import SimpleNamespace

import pytest
from pydantic import create_model
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from corpus_structure.methods.contextual_candidates import _phase_operation, denotation_contribution
from corpus_structure.methods.contextual_embeddings import (
    EncodedVector,
    EncoderProfile,
    identity,
    numeric_identity,
)
from corpus_structure.semantic.contextual_links import RelationshipWitness, select_relationships
from corpus_structure.semantic.contextual_registry import RegistryTarget, registry_input
from corpus_structure.semantic.contextual_retrieval import (
    ChannelHit,
    freeze_inventory,
    fuse_candidates,
    retrieve_candidates,
)
from corpus_structure.semantic.contextual_storage import (
    cached_target_vectors,
    eligible_vector_relation,
    enrichment_report,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import claim_tasks, create_task, record_method
from semantic.test_contributions_native import bypass, complete, drafts, envelope
from semantic.test_private_records import private_source as private_source


def curated_case(original, *, extra_targets=(), config_hash="private-config", target_version=None):
    targets = (
        RegistryTarget(
            target_id="t1",
            label="12",
            description="The numeral twelve printed in the supplied cell.",
            type_name="numeral",
            parent="numbers",
        ),
        RegistryTarget(
            target_id="t2",
            label="7",
            description="The numeral seven as a different source-reported number.",
            type_name="numeral",
            parent="numbers",
        ),
    )
    if target_version is not None:
        targets = tuple(t.model_copy(update={"effective_version": target_version}) for t in targets)
    targets = (*targets, *extra_targets)
    method = SimpleNamespace(**vars(original.method))
    method.name = "private.contextual"
    method.Config = create_model(
        "PrivateContextualConfig", registry_targets=(tuple[RegistryTarget, ...], ...)
    )
    params = dict(registry_targets=[t.model_dump(mode="json") for t in targets])
    with original.writer.begin() as conn:
        config = record_method(
            conn, method, "default", params, config_hash, prepared=original.prepared
        )
        task = create_task(
            conn,
            run_id=original.run,
            config_id=config,
            stage="record",
            unit_type="source_view",
            unit_id=original.view,
            unit_key="private-unit",
            input_hash="private-input-hash",
        )
        held = claim_tasks(conn, run_id=original.run, config_id=config, holder="records")[0]
        task_row = dict(
            conn.execute(select(table("ops.task")).where(table("ops.task").c.id == task))
            .mappings()
            .one()
        )
    return SimpleNamespace(
        **(
            vars(original)
            | dict(
                method=method,
                task=task,
                held=held,
                task_row=task_row,
                registry_targets=targets,
                configuration_hash=config_hash,
            )
        )
    )


def contextual_result(case, *, cached=(), effective_version=None, denotation=False):
    result = drafts(case)
    assert result.contributions is not None
    assert result.contribution_operations is not None
    occurrence_id = result.contributions[0]["occurrence_id"]
    evidence = result.contributions[0]["contribution_id"]
    profile = EncoderProfile(
        "constructed/native-contract", "a" * 40, 2, "query: ", "passage: ", "mean"
    )

    registry_id, targets = registry_input(case.registry_targets)

    def vector(object_id, values, representation_digest="", source_binding="private-unit"):
        digest = "b" * 64
        vector_id = identity(
            "context-vector",
            [object_id, source_binding, profile.profile_id, digest, representation_digest],
        )
        return EncodedVector(
            vector_id,
            object_id,
            source_binding,
            profile.profile_id,
            digest,
            values,
            representation_digest,
        )

    query = vector(occurrence_id, (1.0, 0.0))
    inv = freeze_inventory(
        targets, source_selection=registry_id, scope="chapter5", effective_version=effective_version
    )
    target_vectors = {item.vector.object_id: item.vector for item in cached}
    for index, target in enumerate(targets):
        if target.target_id not in target_vectors:
            values = (
                (1.0, 0.0) if index == 0 else ((0.0, 1.0) if index == 1 else (sqrt(0.5), sqrt(0.5)))
            )
            target_vectors[target.target_id] = vector(
                target.target_id, values, target.representation_digest, target.source_binding
            )
    ranked = sorted(target_vectors.values(), key=lambda v: (-v.values[0], v.object_id))
    lists = fuse_candidates(
        occurrence_id=occurrence_id,
        query=query,
        inventory=inv,
        channels={"dense": tuple(ChannelHit(v.object_id, v.values[0]) for v in ranked)},
    )
    witness = RelationshipWitness(
        "w",
        occurrence_id,
        "t1",
        "denotes",
        "private-unit",
        "chapter5",
        effective_version,
        (evidence,),
        "explicit_source_cue",
    )
    decision = select_relationships(
        candidates=lists,
        inventory=inv,
        source_binding="private-unit",
        scope="chapter5",
        effective_version=effective_version,
        witnesses=(witness,),
    )
    report = enrichment_report(
        curated_registry_id=registry_id,
        profiles=(profile,),
        vectors=(query, *target_vectors.values()),
        vector_reuse=tuple(item.reuse for item in cached),
        inventories=(inv,),
        candidate_lists=(lists,),
        relationship_decisions=(decision,),
    )
    operations = tuple(
        dict(op, **({"contextual_enrichment": report} if i == 0 else {}))
        for i, op in enumerate(result.contribution_operations)
    )
    contributions = result.contributions
    if denotation:
        phase = _phase_operation(
            "relationship selection",
            occurrence_id,
            (lists.list_id,),
            result_id=decision.decision_id,
        )
        proposal = denotation_contribution(
            decision, contributions[0], registry_id, inv, phase["operation_key"]
        )
        assert proposal is not None
        phase["emitted_count"] = 1
        phase["computation_dependencies"] = proposal["computation_dependencies"]
        operations = (*operations, phase)
        contributions = (*contributions, proposal)
    return (
        replace(result, contribution_operations=operations, contributions=contributions),
        query,
        inv,
    )


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
def test_selected_denotation_is_independently_addressable(private_source):
    case = curated_case(private_source)
    result, _, _ = contextual_result(case, denotation=True)
    with case.writer.begin() as conn:
        complete(case, conn, result)
        body = conn.scalar(
            select(table("ops.task_result").c.body).where(
                table("ops.task_result").c.task_id == case.task
            )
        )
        proposals = [
            c for c in body["contributions"] if c["semantic_type"] == "contextual.denotation"
        ]
        assert len(proposals) == 1
        assert proposals[0]["score_state"] == "missing"


@pytest.mark.parametrize(
    "corruption", ["target_id", "scope", "effective_version", "decision", "members"]
)
@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
def test_native_denotation_cannot_relabel_its_retained_decision(private_source, corruption):
    from corpus_structure.semantic.contributions import contribution_identity

    case = curated_case(private_source)
    result, _, _ = contextual_result(case, denotation=True)
    raw = envelope(case, result)
    proposal = next(
        c for c in raw["contributions"] if c["semantic_type"] == "contextual.denotation"
    )
    if corruption == "members":
        proposal["members"] = [raw["contributions"][1]["contribution_id"]]
    elif corruption == "decision":
        proposal["computation_dependencies"][2] = "forged"
    else:
        key = corruption
        field = next(f for f in proposal["value"]["fields"] if f["name"] == key)
        field["value"] = {"kind": "text", "text": "forged"}
    proposal["contribution_id"] = contribution_identity(proposal)
    with (
        case.writer.begin() as conn,
        pytest.raises(DBAPIError, match="denotation proposal"),
        conn.begin_nested(),
    ):
        bypass(case, conn, raw)


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
def test_native_contextual_report_projection_and_exact_pgvector(private_source):
    case = curated_case(private_source)
    result, query, inv = contextual_result(case)
    with case.writer.begin() as conn:
        complete(case, conn, result)
        vectors = table("kb.contextual_vector")
        assert len(conn.execute(select(vectors).where(vectors.c.task_id == case.task)).all()) == 3
        actual = retrieve_candidates(
            conn,
            occurrence_id=query.object_id,
            query=query,
            inventory=inv,
            relation=eligible_vector_relation(case.task),
            lexical_query="12",
            dimension=2,
        )
        assert [candidate.target_id for candidate in actual.candidates] == ["t1", "t2"]
        by_channel = {e.channel: e.raw_score for e in actual.candidates[0].channels}
        assert by_channel["dense"] == pytest.approx(1)
        assert "alias" in by_channel and "lexical" in by_channel


@pytest.mark.parametrize(
    "corruption",
    [
        "vector_dimension",
        "foreign_inventory",
        "empty_selected",
        "wrong_occurrence",
        "wrong_policy",
        "wrong_rank",
        "wrong_fusion",
        "wrong_channel",
        "wrong_decision",
        "stale_representation",
        "omit_registry",
        "forge_type",
        "forge_parent",
    ],
)
@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
def test_native_contextual_refusal_is_atomic(private_source, corruption):
    case = curated_case(private_source)
    result, _, _ = contextual_result(case)
    raw = envelope(case, result)
    report = raw["contribution_operations"][0]["contextual_enrichment"]
    if corruption == "vector_dimension":
        report["vectors"][0]["values"] = [1.0]
    elif corruption == "foreign_inventory":
        report["inventories"][0]["targets"][0]["label"] = "changed under same identity"
    elif corruption == "empty_selected":
        report["relationship_decisions"][0]["alternatives"] = []
    elif corruption == "wrong_occurrence":
        value = report["vectors"][0]
        value["object_id"] = "foreign-occurrence"
        value["vector_id"] = identity(
            "context-vector",
            [
                value[k]
                for k in (
                    "object_id",
                    "source_binding",
                    "profile_id",
                    "input_digest",
                    "representation_digest",
                )
            ],
        )
        report["candidate_lists"][0]["query_vector_id"] = value["vector_id"]
    elif corruption == "wrong_policy":
        report["candidate_lists"][0]["policy_id"] = "invented-policy"
    elif corruption == "wrong_rank":
        report["candidate_lists"][0]["candidates"][0]["rank"] = 99
    elif corruption == "wrong_fusion":
        report["candidate_lists"][0]["candidates"][0]["fusion_score"] = 0.9
    elif corruption == "wrong_channel":
        report["candidate_lists"][0]["channel_results"][0]["hits"][0]["score"] = 0.1
    elif corruption == "wrong_decision":
        report["relationship_decisions"][0]["decision_id"] = "forged-decision"
    elif corruption == "stale_representation":
        report["vectors"][1]["representation_digest"] = "old-description"
    elif corruption == "omit_registry":
        report.pop("curated_registry_id")
    else:
        inv = report["inventories"][0]
        inv["reliable_type" if corruption == "forge_type" else "parent"] = "incompatible"
        meaning = {
            k: inv.get(k)
            for k in ("source_selection", "scope", "effective_version", "reliable_type", "parent")
        }
        meaning["targets"] = [
            t | {k: t.get(k) for k in ("type_name", "parent", "effective_version")}
            for t in inv["targets"]
        ]
        meaning["policy"] = "eligible-concepts-1"
        inv["inventory_id"] = identity("concept-inventory", meaning)
    if corruption in {
        "wrong_occurrence",
        "wrong_policy",
        "wrong_rank",
        "wrong_fusion",
        "wrong_channel",
    }:
        value = report["candidate_lists"][0]
        value["list_id"] = numeric_identity(
            "concept-candidates", {k: v for k, v in value.items() if k != "list_id"}
        )
    with case.writer.begin() as conn:
        with pytest.raises(DBAPIError), conn.begin_nested():
            bypass(case, conn, raw)
        assert conn.execute(select(table("kb.contextual_vector"))).first() is None
        assert conn.execute(select(table("kb.source_contribution"))).first() is None


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
def test_changed_registry_reuses_original_same_runtime_vectors(private_source):
    first = curated_case(private_source)
    result, query, original_inventory = contextual_result(first)
    with first.writer.begin() as conn:
        complete(first, conn, result)
    addition = RegistryTarget(
        target_id="t3",
        label="99",
        description="The numeral ninety-nine.",
        type_name="numeral",
        parent="numbers",
    )
    second = curated_case(private_source, extra_targets=(addition,), config_hash="extended-config")
    _registry_id, targets = registry_input(second.registry_targets)
    with second.writer.connect() as conn:
        cached = cached_target_vectors(
            conn, run_id=second.run, profile_id=query.profile_id, targets=targets
        )
        assert [item.vector.object_id for item in cached] == ["t1", "t2"]
        assert {item.reuse.origin_task_id for item in cached} == {first.task}
        assert len({item.reuse.origin_runtime_id for item in cached}) == 1
        assert (
            cached_target_vectors(
                conn, run_id=second.run, profile_id="different-profile", targets=targets
            )
            == ()
        )
    next_result, _, next_inventory = contextual_result(second, cached=cached)
    assert original_inventory.inventory_id != next_inventory.inventory_id
    assert original_inventory.targets[0].representation_digest == targets[0].representation_digest
    raw = envelope(second, next_result)
    raw["configuration_hash"] = "extended-config"
    report = raw["contribution_operations"][0]["contextual_enrichment"]
    assert report["product_counts"]["vectors"] == 4
    assert len(report["vector_reuse"]) == 2
    with second.writer.begin() as conn:
        bypass(second, conn, raw)
        assert (
            conn.scalar(
                select(table("ops.task").c.status).where(table("ops.task").c.id == second.task)
            )
            == "done"
        )


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
def test_unversioned_targets_are_eligible_in_known_source_version(private_source):
    case = curated_case(private_source)
    result, _, inventory = contextual_result(case, effective_version="v1")
    assert inventory.effective_version == "v1" and all(
        t.effective_version is None for t in inventory.targets
    )
    with case.writer.begin() as conn:
        complete(case, conn, result)


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
def test_native_known_version_excludes_conflicting_target_version(private_source):
    case = curated_case(private_source, target_version="v2")
    result, _, _ = contextual_result(case)
    raw = envelope(case, result)
    report = raw["contribution_operations"][0]["contextual_enrichment"]
    inv = report["inventories"][0]
    inv["effective_version"] = "v1"
    meaning = {
        k: inv.get(k)
        for k in ("source_selection", "scope", "effective_version", "reliable_type", "parent")
    }
    meaning["targets"] = [
        t | {k: t.get(k) for k in ("type_name", "parent", "effective_version")}
        for t in inv["targets"]
    ]
    meaning["policy"] = "eligible-concepts-1"
    inv["inventory_id"] = identity("concept-inventory", meaning)
    with (
        case.writer.begin() as conn,
        pytest.raises(DBAPIError, match="contextual target source or eligibility differs"),
        conn.begin_nested(),
    ):
        bypass(case, conn, raw)
