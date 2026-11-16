"""Real current demands and native refusal controls with an untrained local model.

The PDF converter and finite source grammar are controlled. Source registration,
CPU inference/replies, native claims/intents/publications and selected cuts are real.
This module supplies no external provider qualification.
"""

from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.contextual_encoder import ContextualEncoderSelection
from corpus_structure.semantic.contextual_selection import (
    ContextualSelectedProduct,
    ContextualVectorSelection,
)
from corpus_structure.semantic.data_operation_identity import decode_semantic_value, semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.observations import source_python, source_value
from semantic.current_contextual_support import (
    contextual_recipe,
    controlled_encoder,
    final_selection,
    inventory_intent,
    retained_products,
    retrieval_intent,
    run_intent,
    target_intent,
)
from semantic.current_pdf_source_support import (
    PROJECT,
    CurrentPdfSource,
    _current_pdf_source,
    _section_stream,
    admit_current_target,
)
from semantic.data_operation_kernel_support import Kernel
from semantic.structural_admission_native_support import (
    Product,
    build_inventory,
    execute,
    request,
    source_products,
)
from semantic.structural_native_fixture import TEXT


@dataclass(frozen=True)
class ContextualCase:
    kernel: Kernel
    query_demand: str
    query: Product
    query_vector: Product
    target_demand: str
    targets: tuple[Product, ...]
    inventory_demand: str
    inventory: Product
    selection: ContextualVectorSelection
    encoder: ContextualEncoderSelection
    directory: Path
    source: CurrentPdfSource


@pytest.fixture(scope="module")
def current_contextual_case(scenario_seeds, tmp_path_factory):
    directory = tmp_path_factory.mktemp("current-contextual")
    rows = (("text", TEXT, TEXT, None), ("text", TEXT, TEXT, None))
    def stream(worker, original, **options):
        return _section_stream(rows, worker, original, **options)
    with (
        pytest.MonkeyPatch.context() as patch,
        _current_pdf_source(
            scenario_seeds, directory, patch, stream=stream, sections=("#/groups/0", "#/groups/1")
        ) as source,
    ):
        encoder = controlled_encoder(directory / "encoder")
        kernel = admit_current_target(
            source, contextual_recipe(directory, encoder), directory / "contextual-release"
        )
        original, _ = source_products(source)
        build_inventory(kernel, original)
        from corpus_structure.semantic.data_operation_service import DemandOperationSelection

        pending = request(
            kernel,
            ("retrieve.contextual_query/declared",),
            original.context,
            selections=(
                DemandOperationSelection(
                    operation="retrieve.contextual_query/declared",
                    replicate="actual-scalar-query-A",
                ),
            ),
            inference="exact-retained-source-occurrences",
        )
        query_retained, _ = execute(kernel, pending)
        query_demand = query_retained["demand_id"]
        (query,) = [
            value
            for value in retained_products(kernel, query_demand, "DdoContextualQuery")
            if value.body["lexical_query"] == "Ada"
        ]
        (query_vector,) = [
            value
            for value in retained_products(kernel, query_demand, "DdoContextualQueryVector")
            if value.body["vector"]["vector_id"] == query.body["query_vector_id"]
        ]
        target_demand, _ = run_intent(
            kernel, target_intent(kernel, ("one", "two"), replicate="actual-target-observation-A")
        )
        targets = retained_products(kernel, target_demand, "DdoContextualTargetVector")
        assert len(targets) == 2
        inventory_demand, _ = run_intent(kernel, inventory_intent(kernel, query, ("one", "two")))
        (inventory,) = retained_products(kernel, inventory_demand, "DdoContextualInventory")
        selection = final_selection(
            kernel,
            query_demand,
            query,
            query_vector,
            target_demand,
            targets,
            inventory_demand,
            inventory,
        )
        yield ContextualCase(
            kernel,
            query_demand,
            query,
            query_vector,
            target_demand,
            targets,
            inventory_demand,
            inventory,
            selection,
            encoder,
            directory,
            source,
        )


def test_current_contextual_native_positive_ranking_source_scope_and_private_standing(
    current_contextual_case,
):
    case = current_contextual_case
    demand, _ = run_intent(case.kernel, retrieval_intent(case.kernel, case.selection, budget=2))
    (product,) = retained_products(case.kernel, demand, "DdoContextualRetrievalProduct")
    candidates = source_python(product.body["candidate_list"])
    assert [(value["target_id"], value["rank"]) for value in candidates["candidates"]] == [
        ("one", 1),
        ("two", 2),
    ]
    assert candidates["eligible_target_count"] == 2
    assert all(
        [hit["target_id"] for hit in channel["hits"]] == ["one", "two"]
        for channel in candidates["channel_results"]
    )
    assert (
        source_python(product.body["relationship_decision"])["outcome"] == "insufficient_evidence"
    )
    assert source_python(product.body["relationship_decision"])["selected_edges"] == []
    assert product.body["source_pin"] == case.query.body["source_pin"]
    assert product.body["anchors"] == case.query.body["anchors"]
    assert product.body["source_pin"]["subject_definition"] == "original-source-view"
    assert product.context.subject_definition == "selected-native-source"
    assert all(value.context.original_source is None for value in case.targets)
    with case.kernel.engine.connect() as connection:
        for role in ("retrieve.contextual_scores/declared", "retrieve.contextual/declared"):
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM ops.data_derivation d JOIN ops.data_request r ON r.id=d.request_id JOIN ops.data_publication_receipt p ON p.derivation_id=d.id WHERE r.operation_id=:operation"
                    ),
                    {"operation": role},
                )
                >= 1
            )


def test_native_score_currentness_detects_known_linguistic_change_without_replacing_observations(
    current_contextual_case,
):
    """A rolled-back catalog change exercises the actual ordinary support guard."""
    case = current_contextual_case
    demand, _ = run_intent(case.kernel, retrieval_intent(case.kernel, case.selection, budget=17))
    (scores,) = retained_products(case.kernel, demand, "DdoContextualNativeScores")
    score_episode = scores.row["derivation_id"]
    target_episode = case.targets[0].row["derivation_id"]
    valid = text("SELECT ops.ddo_support_valid(:episode)")
    payload = text(
        "SELECT i.payload FROM ops.data_completion_intent i JOIN ops.data_derivation d "
        "ON d.intent_id=i.id WHERE d.id=:episode"
    )
    with case.kernel.engine.connect() as connection:
        transaction = connection.begin()
        try:
            assert connection.scalar(valid, {"episode": score_episode}) is True
            assert connection.scalar(valid, {"episode": target_episode}) is True
            original = connection.scalar(payload, {"episode": score_episode})
            changed = connection.execute(
                text(
                    "UPDATE pg_catalog.pg_ts_dict SET dictinitoption = "
                    "dictinitoption || ', controlled_option = ''different''' "
                    "WHERE dictname='english_stem' AND dictnamespace='pg_catalog'::regnamespace"
                )
            )
            assert changed.rowcount == 1
            assert connection.scalar(valid, {"episode": score_episode}) is False
            assert connection.scalar(valid, {"episode": target_episode}) is True
            assert connection.scalar(payload, {"episode": score_episode}) == original
        finally:
            transaction.rollback()
    with case.kernel.engine.connect() as connection:
        assert connection.scalar(valid, {"episode": score_episode}) is True


def test_changed_registry_reuses_actual_original_target_episodes_and_keeps_profile_boundary(
    current_contextual_case,
):
    case = current_contextual_case
    demand, _ = run_intent(
        case.kernel,
        target_intent(
            case.kernel, ("one", "two", "three"), replicate="actual-target-observation-A"
        ),
    )
    next_targets = retained_products(case.kernel, demand, "DdoContextualTargetVector")
    by_id = {value.body["vector"]["object_id"]: value for value in next_targets}
    assert set(by_id) == {"one", "two", "three"}
    for before in case.targets:
        after = by_id[before.body["vector"]["object_id"]]
        assert before.row["product_id"] == after.row["product_id"]
        assert before.row["derivation_id"] == after.row["derivation_id"]
        assert json_bytes(before.body) == json_bytes(after.body)
    with case.kernel.engine.connect() as connection:
        original_runtimes = {
            connection.scalar(
                text("SELECT runtime_id FROM ops.data_derivation WHERE id=:id"),
                {"id": value.row["derivation_id"]},
            )
            for value in case.targets
        }
        reused_runtimes = {
            connection.scalar(
                text("SELECT runtime_id FROM ops.data_derivation WHERE id=:id"),
                {"id": by_id[value.body["vector"]["object_id"]].row["derivation_id"]},
            )
            for value in case.targets
        }
    assert original_runtimes == reused_runtimes == {case.kernel.runtime}
    expanded_inventory_demand, _ = run_intent(
        case.kernel, inventory_intent(case.kernel, case.query, ("one", "two", "three"))
    )
    (expanded_inventory,) = retained_products(
        case.kernel, expanded_inventory_demand, "DdoContextualInventory"
    )
    assert (
        source_python(expanded_inventory.body["inventory"])["inventory_id"]
        != source_python(case.inventory.body["inventory"])["inventory_id"]
    )
    expanded_selection = final_selection(
        case.kernel,
        case.query_demand,
        case.query,
        case.query_vector,
        demand,
        next_targets,
        expanded_inventory_demand,
        expanded_inventory,
    )
    expanded_demand, _ = run_intent(
        case.kernel, retrieval_intent(case.kernel, expanded_selection, budget=3)
    )
    (assembly,) = retained_products(case.kernel, expanded_demand, "DdoContextualVectors")
    assert len(source_python(assembly.body["vectors"])) == 4
    assert {row["object_id"] for row in source_python(assembly.body["vectors"])} == {
        "one",
        "two",
        "three",
        case.query.body["occurrence_id"],
    }
    # A different real prompt/profile has actual separately produced vector observations.
    changed = replace(
        case.encoder, profile=replace(case.encoder.profile, document_prompt="different passage: ")
    )
    other = admit_current_target(
        case.source,
        contextual_recipe(case.directory, changed),
        case.directory / "different-profile-release",
    )
    different_demand, _ = run_intent(
        other, target_intent(other, ("one", "two"), replicate="actual-target-observation-A")
    )
    different = retained_products(other, different_demand, "DdoContextualTargetVector")
    assert {value.body["vector"]["profile_id"] for value in different}.isdisjoint(
        {value.body["vector"]["profile_id"] for value in case.targets}
    )
    from corpus_structure.semantic.contextual_selection import acquire_contextual_vector_selection

    def chosen(demand_id, value):
        return ContextualSelectedProduct(demand_id, value.row["product_id"])

    with (
        case.kernel.purpose("read").begin() as connection,
        pytest.raises(ValueError, match="complete encoder profile"),
    ):
        acquire_contextual_vector_selection(
            connection,
            project_id=PROJECT,
            inventory=chosen(case.inventory_demand, case.inventory),
            query=chosen(case.query_demand, case.query),
            query_vector=chosen(case.query_demand, case.query_vector),
            targets=tuple(chosen(different_demand, value) for value in different),
        )


CORRUPTIONS = (
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
)


def _corrupt(payload, corruption):
    bad = deepcopy(payload)
    completion = bad["completion"]
    if corruption == "omit_registry":
        assert any(value.get("kind") == "authored" for value in completion["support"])
        completion["support"] = [
            value for value in completion["support"] if value.get("kind") != "authored"
        ]
        return bad
    body = decode_semantic_value(completion["outputs"][0]["product"]["body"])
    if corruption == "vector_dimension":
        body["vector"]["values"].append(0.0)
    elif corruption == "stale_representation":
        body["vector"]["representation_digest"] = "stale-description"
    elif corruption in {"forge_type", "forge_parent"}:
        descriptor = source_python(body["target"]["descriptor"])
        descriptor["type_name" if corruption == "forge_type" else "parent"] = "invented"
        body["target"]["descriptor"] = source_value(descriptor)
    elif corruption in {"wrong_rank", "wrong_channel"}:
        assert body["hits"]
        body["hits"][0]["rank" if corruption == "wrong_rank" else "channel"] = (
            2 if corruption == "wrong_rank" else "dense"
        )
    else:
        field = (
            "inventory"
            if corruption == "foreign_inventory"
            else "relationship_decision"
            if corruption in {"empty_selected", "wrong_decision"}
            else "candidate_list"
        )
        value = source_python(body[field])
        if corruption == "foreign_inventory":
            value["inventory_id"] = "foreign-inventory"
        elif corruption == "empty_selected":
            value.update(outcome="selected", selected_edges=[])
        elif corruption == "wrong_occurrence":
            value["occurrence_id"] = "another-occurrence"
        elif corruption == "wrong_policy":
            value["policy_id"] = "another-policy"
        elif corruption == "wrong_fusion":
            value["candidates"][0]["fusion_score"] += 0.5
        elif corruption == "wrong_decision":
            value["decision_id"] = "another-decision"
        body[field] = source_value(value)
    completion["outputs"][0]["product"]["body"] = semantic_value(body)
    return bad


@pytest.mark.parametrize("corruption", CORRUPTIONS)
def test_current_native_contextual_refusals_are_atomic_with_actual_cpu_and_native_claims(
    current_contextual_case, monkeypatch, corruption
):
    case = current_contextual_case
    target_cases = {"vector_dimension", "stale_representation", "forge_type", "forge_parent"}
    operation = (
        "retrieve.contextual_targets/curated"
        if corruption == "omit_registry"
        else (
            "retrieve.contextual_target_vector/declared"
            if corruption in target_cases
            else "retrieve.contextual_scores/declared"
            if corruption in {"wrong_rank", "wrong_channel"}
            else "retrieve.contextual/declared"
        )
    )
    attempted = []
    retain = DataOperationStorage.retain_data_completion_intent

    def intercepted(storage, payload):
        with case.kernel.engine.connect() as admin:
            actual_operation = admin.scalar(
                text("SELECT operation_id FROM ops.data_request WHERE id=:id"),
                {"id": payload["request_id"]},
            )
            before = admin.execute(
                text(
                    "SELECT (SELECT count(*) FROM ops.data_completion_intent),(SELECT count(*) FROM kb.data_product),(SELECT count(*) FROM ops.data_derivation),(SELECT count(*) FROM ops.data_publication_receipt)"
                )
            ).one()
        if actual_operation == operation and not attempted:
            altered = _corrupt(payload, corruption)
            # Preserve the actual CPU reply, receipt, runtime and live producer fence.
            assert altered["completion"].get("execution_evidence") == payload["completion"].get(
                "execution_evidence"
            )
            with pytest.raises(DBAPIError), storage.connection.begin_nested():
                retain(storage, altered)
            with case.kernel.engine.connect() as admin:
                after = admin.execute(
                    text(
                        "SELECT (SELECT count(*) FROM ops.data_completion_intent),(SELECT count(*) FROM kb.data_product),(SELECT count(*) FROM ops.data_derivation),(SELECT count(*) FROM ops.data_publication_receipt)"
                    )
                ).one()
            assert before == after
            attempted.append(payload["request_id"])
        return retain(storage, payload)

    monkeypatch.setattr(DataOperationStorage, "retain_data_completion_intent", intercepted)
    if corruption == "omit_registry":
        intent = target_intent(
            case.kernel, ("one", "two", "three", "four"), replicate="unused", discovery_only=True
        )
    elif corruption in target_cases:
        intent = target_intent(
            case.kernel, ("one",), replicate="actual-independent-target-observation:" + corruption
        )
    else:
        # Capacity is an actual declared policy determinant, not a nonce/run key.
        intent = retrieval_intent(
            case.kernel, case.selection, budget=3 + CORRUPTIONS.index(corruption)
        )
    _, result = run_intent(case.kernel, intent)
    assert result.receipt_count >= 1 and len(attempted) == 1
    with case.kernel.engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM ops.data_completion_intent WHERE request_id=:id"),
                {"id": attempted[0]},
            )
            == 1
        )
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM ops.data_publication_receipt p JOIN ops.data_derivation d ON d.id=p.derivation_id WHERE d.request_id=:id"
                ),
                {"id": attempted[0]},
            )
            == 1
        )
