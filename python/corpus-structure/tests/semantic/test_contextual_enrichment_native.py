"""Real protected report completion and exact pgvector retrieval on controlled source inputs."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from corpus_structure.methods.contextual_embeddings import (
    identity,
    numeric_identity,
)
from corpus_structure.semantic.contextual_registry import RegistryTarget, registry_input
from corpus_structure.semantic.contextual_retrieval import (
    retrieve_candidates,
)
from corpus_structure.semantic.contextual_storage import (
    cached_target_vectors,
    eligible_vector_relation,
)
from corpus_structure.semantic.metadata import table
from semantic.native_record_fixtures import private_source as private_source
from semantic.native_record_fixtures import private_source_options as private_source_options

from .native_record_fixtures import (
    bypass_contributions as bypass,
)
from .native_record_fixtures import (
    complete_contributions as complete,
)
from .native_record_fixtures import (
    contextual_result,
    curated_case,
)
from .native_record_fixtures import (
    contribution_envelope as envelope,
)


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
        report["relationship_decisions"][0]["selected_edges"] = []
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
        meaning["semantic_groups"] = inv["semantic_groups"]
        meaning["policy"] = "eligible-concepts-2"
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
    meaning["semantic_groups"] = inv["semantic_groups"]
    meaning["policy"] = "eligible-concepts-2"
    inv["inventory_id"] = identity("concept-inventory", meaning)
    with (
        case.writer.begin() as conn,
        pytest.raises(DBAPIError, match="contextual target source or eligibility differs"),
        conn.begin_nested(),
    ):
        bypass(case, conn, raw)


@pytest.mark.parametrize(
    "private_source", [{"additional_methods": ("private.contextual",)}], indirect=True
)
def test_genuine_competing_senses_are_retained_natively(private_source):
    case = curated_case(private_source)
    result, _, _ = contextual_result(case, competing=True)
    decision = envelope(case, result)["contribution_operations"][0]["contextual_enrichment"][
        "relationship_decisions"
    ][0]
    assert decision["outcome"] == "ambiguous"
    assert not decision["selected_edges"]
    assert len(decision["alternative_groups"][0]["edges"]) == 2
    with case.writer.begin() as conn:
        complete(case, conn, result)
        body = conn.scalar(
            select(table("ops.task_result").c.body).where(
                table("ops.task_result").c.task_id == case.task
            )
        )
    assert (
        body["contribution_operations"][0]["contextual_enrichment"]["relationship_decisions"][0]
        == decision
    )
