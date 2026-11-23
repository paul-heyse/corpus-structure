"""Current private authored bindings with real demands, CPU replies and native fences.

The local untrained model is controlled contract evidence, with no provider claim.
"""

from copy import deepcopy

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.contextual_operations import contextual_relationship_decision
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
from corpus_structure.semantic.observations import source_python
from semantic.current_contextual_support import (
    final_selection,
    inventory_intent,
    retained_products,
    retrieval_intent,
    run_intent,
    target_intent,
    witnessed_retrieval_intent,
)
from semantic.test_current_contextual_native import (
    current_contextual_case as current_contextual_case,
)


def hypotheses(case, targets, *, relation="denotes"):
    return [
        dict(
            hypothesis_id="explicit-source-reading:" + relation + ":" + target,
            target_id=target,
            relation=relation,
            asserted_basis="explicit_source_cue",
            cue_refs=[case.query.body["carrier"]],
        )
        for target in targets
    ]


@pytest.mark.parametrize(
    "targets,outcome",
    [((), "insufficient_evidence"), (("one",), "selected"), (("one", "two"), "ambiguous")],
)
def test_actual_private_source_binding_retains_authorship_and_competing_alternatives(
    current_contextual_case, targets, outcome, tmp_path
):
    case = current_contextual_case

    def retrieve(assertions):
        return run_intent(
            case.kernel,
            witnessed_retrieval_intent(
                case.kernel,
                case.selection,
                case.query_demand,
                case.query,
                hypotheses=assertions,
                budget=2,
            ),
        )

    prior_demand = retrieve([])[0] if outcome == "selected" else None
    submitted = hypotheses(case, targets)
    demand, result = retrieve(submitted)
    assert result.receipt_count >= 1
    (product,) = retained_products(case.kernel, demand, "DdoContextualWitnessedRetrievalProduct")
    (binding,) = retained_products(case.kernel, demand, "DdoContextualWitnessBindings")
    assert binding.body["author_assertion"] == "controlled contextual test author"
    carrier = {
        "variant": "member",
        "role": "cues",
        "occurrence": "cue:0",
        "member_id": case.query.body["carrier"]["member_id"],
    }
    assert binding.body["carrier_input"] == carrier
    assert binding.body["hypotheses"] == [
        {**hypothesis, "cue_refs": [carrier]} for hypothesis in submitted
    ]
    assert binding.body["support_state"] == product.body["support_state"] == "unassessed"
    assert product.body["witness_standing"] == "private_authored_source_binding_hypotheses"
    assert binding.body["query_input"] == {"variant": "product", "role": "query"}
    assert binding.body["inventory_input"] == {"variant": "product", "role": "inventory"}
    assert product.body["witness_input"] == {"variant": "product", "role": "witnesses"}
    assert source_python(binding.body["authored_support"])
    decision = contextual_relationship_decision(product.body)
    assert decision.outcome == outcome
    if outcome == "selected":
        assert prior_demand is not None and prior_demand != demand
        (score,) = retained_products(case.kernel, demand, "DdoContextualNativeScores")
        (prior_score,) = retained_products(case.kernel, prior_demand, "DdoContextualNativeScores")
        assert score.row["derivation_id"] == prior_score.row["derivation_id"]
        with case.kernel.engine.connect() as connection:
            admissions = connection.execute(
                text(
                    "SELECT id, source_reference, product_id FROM ops.original_source_admission "
                    "WHERE selection_name='contextual-policy' AND demand_id IN (:prior, :current)"
                ),
                {"prior": prior_demand, "current": demand},
            ).all()
        (first_policy, current_policy) = admissions
        assert first_policy.id != current_policy.id
        assert first_policy.source_reference == current_policy.source_reference
        assert first_policy.product_id == current_policy.product_id
        (edge,) = decision.selected_edges
        assert edge.member_target_ids == ("one",)
        assert edge.witnesses[0].evidence_ids == (case.query.body["carrier"]["contribution_id"],)
        from corpus_structure.serve.demand_export import (
            export_demand_result,
            verified_demand_export,
        )
        from semantic.current_pdf_source_support import PROJECT

        destination = tmp_path / "selected-witnessed-retrieval"
        with case.kernel.purpose("read").begin() as connection:
            receipt = export_demand_result(
                connection,
                demand,
                project_id=PROJECT,
                destination=destination,
                format="parquet",
                scope={"product_ids": [product.row["product_id"]]},
            )
        digest = receipt.manifest_digest
        assert isinstance(digest, str)
        with verified_demand_export(destination, manifest_digest=digest) as (
            _manifest,
            _prepared,
            _models,
            index,
        ):
            rows = index.mapping("kb.data_product", ("id",))
            for retained, field in (
                (binding, "query_input"),
                (binding, "carrier_input"),
                (binding, "hypotheses"),
                (product, "witness_input"),
            ):
                body = decode_semantic_value(rows[retained.row["product_id"]]["canonical_body"])
                assert body[field] == retained.body[field]
            packet = index.mapping("kb.data_product_member", ("product_id", "member_id"))[
                product.row["product_id"], edge.edge_id
            ]
            assert decode_semantic_value(packet["body"]) == product.body["members"][0]["body"]
    elif outcome == "ambiguous":
        assert decision.selected_edges == ()
        assert {
            edge.member_target_ids[0]
            for group in decision.alternative_groups
            for edge in group.edges
        } == {"one", "two"}
    else:
        assert decision.selected_edges == ()
        assert source_python(binding.body["witnesses"]) == []


@pytest.mark.parametrize("corruption", ["promote-standing", "invent-author", "substitute-carrier"])
def test_native_binding_refuses_changed_claims_atomically_with_original_cpu_receipt(
    current_contextual_case, monkeypatch, corruption
):
    case = current_contextual_case
    retained = DataOperationStorage.retain_data_completion_intent
    attempted = []

    def intercept(storage, payload):
        with case.kernel.engine.connect() as connection:
            operation = connection.scalar(
                text("SELECT operation_id FROM ops.data_request WHERE id=:id"),
                {"id": payload["request_id"]},
            )
        if operation == "retrieve.contextual_witnesses/declared" and not attempted:
            bad = deepcopy(payload)
            body = decode_semantic_value(bad["completion"]["outputs"][0]["product"]["body"])
            if corruption == "promote-standing":
                body["support_state"] = "supported"
            elif corruption == "invent-author":
                body["author_assertion"] = "invented independent provider"
            else:
                body["hypotheses"][0]["cue_refs"][0]["occurrence"] = "missing-cue"
            bad["completion"]["outputs"][0]["product"]["body"] = semantic_value(body)
            assert (
                bad["completion"]["execution_evidence"]
                == payload["completion"]["execution_evidence"]
            )
            counts = text(
                "SELECT (SELECT count(*) FROM ops.data_completion_intent),"
                "(SELECT count(*) FROM kb.data_product),(SELECT count(*) FROM ops.data_derivation),"
                "(SELECT count(*) FROM ops.data_publication_receipt)"
            )
            with case.kernel.engine.connect() as connection:
                before = connection.execute(counts).one()
            with pytest.raises(DBAPIError), storage.connection.begin_nested():
                retained(storage, bad)
            with case.kernel.engine.connect() as connection:
                assert connection.execute(counts).one() == before
            attempted.append(payload["request_id"])
        return retained(storage, payload)

    monkeypatch.setattr(DataOperationStorage, "retain_data_completion_intent", intercept)
    # Distinct explicitly asserted relationship meanings require genuine new
    # binding work; changing only downstream capacity would reuse the old binder.
    relation = {
        "promote-standing": "alias-of",
        "invent-author": "compared-with",
        "substitute-carrier": "specializes",
    }[corruption]
    budget = 3 + ("promote-standing", "invent-author", "substitute-carrier").index(corruption)
    _, result = run_intent(
        case.kernel,
        witnessed_retrieval_intent(
            case.kernel,
            case.selection,
            case.query_demand,
            case.query,
            hypotheses=hypotheses(case, ("one",), relation=relation),
            relations=(relation,),
            budget=budget,
        ),
    )
    assert len(attempted) == 1 and result.receipt_count >= 1


def test_current_known_version_keeps_unversioned_targets_and_excludes_conflicts(
    current_contextual_case,
):
    from corpus_structure.semantic.contextual_registry import RegistryTarget

    case = current_contextual_case
    descriptions = tuple(
        RegistryTarget(
            target_id=name,
            label="Ada",
            description="Ada acts",
            type_name="concept",
            effective_version=version,
        )
        for name, version in (
            ("unversioned", None),
            ("matching-v1", "v1"),
            ("conflicting-v2", "v2"),
        )
    )
    names = tuple(value.target_id for value in descriptions)
    target_demand, _ = run_intent(
        case.kernel,
        target_intent(
            case.kernel,
            names,
            targets=descriptions,
            replicate="actual-versioned-target-observations",
        ),
    )
    produced = retained_products(case.kernel, target_demand, "DdoContextualTargetVector")
    assert {value.body["vector"]["object_id"] for value in produced} == set(names)
    inventory_demand, _ = run_intent(
        case.kernel,
        inventory_intent(
            case.kernel, case.query, names, targets=descriptions, effective_version="v1"
        ),
    )
    (inventory,) = retained_products(case.kernel, inventory_demand, "DdoContextualInventory")
    frozen = source_python(inventory.body["inventory"])
    assert frozen["effective_version"] == "v1"
    assert {value["target_id"] for value in frozen["targets"]} == {"unversioned", "matching-v1"}
    vectors = tuple(
        value for value in produced if value.body["vector"]["object_id"] != "conflicting-v2"
    )
    selection = final_selection(
        case.kernel,
        case.query_demand,
        case.query,
        case.query_vector,
        target_demand,
        vectors,
        inventory_demand,
        inventory,
    )
    demand, _ = run_intent(case.kernel, retrieval_intent(case.kernel, selection, budget=2))
    (product,) = retained_products(case.kernel, demand, "DdoContextualRetrievalProduct")
    candidates = source_python(product.body["candidate_list"])
    assert {value["target_id"] for value in candidates["candidates"]} == {
        "unversioned",
        "matching-v1",
    }
    assert candidates["eligible_target_count"] == 2
