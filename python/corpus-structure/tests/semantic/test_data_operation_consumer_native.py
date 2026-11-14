"""Actual consumer selection kernels hydrate only authenticated pinned native members.

The controlled discovery producer publishes independently specified metadata. It
qualifies native selection/hydration, not PDF/NLP provider execution or linguistic truth.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import event

from corpus_structure.semantic.data_operation_admission import (
    acquire_publication_port,
)
from corpus_structure.semantic.data_operation_bindings import (
    PopulationBinding,
    compile_binding,
    execute_binding,
)
from corpus_structure.semantic.data_operation_demands import (
    DiscoverySelection,
    OperationSelection,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_identity import (
    SemanticRequestKey,
    body_identity,
    contextual_product_identity,
    semantic_value,
)
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, SourceSetEntry
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    admitted_data_projection,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import ExternalSourceRef
from semantic.data_operation_demand_support import claim
from semantic.data_operation_kernel_support import CASES, CONSUMERS, KINDS, PREFIX


def _source_reference(index):
    return ExternalSourceRef(
        project_id="ddo-test",
        run_id=1,
        cut_id=2,
        release_id="fixture-reference",
        result_revision=0,
        source_view_id=index,
        native_task_id=index,
        native_product_key="native:" + str(index),
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )


def _records(case: str) -> dict[str, list[tuple[str, str, dict[str, Any]]]]:
    view = dict(
        document_subject="document",
        base_product="base",
        view_key="view-key",
        projection_digest="selected",
        source_recipe="source-recipe",
        analysis_eligible=True,
    )
    if case == "occurrences":
        return {
            "views": [("view", "view", view)],
            "occurrences": [
                (
                    "occurrence:one",
                    "occurrence:one",
                    dict(
                        view_subject="view",
                        occurrence_id="one",
                        contribution_id="contribution:one",
                        semantic_type="definition",
                        contribution_kind="claim",
                        anchors_valid=True,
                        exact_context=True,
                    ),
                ),
                (
                    "occurrence:other",
                    "occurrence:other",
                    dict(
                        view_subject="view",
                        occurrence_id="other",
                        contribution_id="contribution:other",
                        semantic_type="other",
                        contribution_kind="claim",
                        anchors_valid=True,
                        exact_context=True,
                    ),
                ),
            ],
        }
    if case in {"document", "projection"}:
        return {
            "views": [
                ("view:one", "view:one", view),
                (
                    "view:two",
                    "view:two",
                    {**view, "view_key": "second", "projection_digest": "other"},
                ),
            ]
        }
    result = {"passages": [], "readings": []}
    for side, index in (("left", 1), ("right", 2)):
        reference = _source_reference(index)
        result["passages"].append(
            (
                "passage:" + side,
                "passage:" + side,
                dict(
                    input_subject="input",
                    passage_id=side,
                    source_ref=reference.identity,
                    start=0,
                    end=5,
                ),
            )
        )
        result["readings"].append(
            (
                "reading:" + side,
                "reading:" + side,
                dict(
                    input_subject="input",
                    passage_id=side,
                    contribution_id="contribution:" + side,
                    source_ref=reference.identity,
                    producer_operation="read",
                ),
            )
        )
    return result


def _publish(ddo_kernel, demand, root, group, body):
    operation = "urn:consumer-native:" + group
    context = SubjectContext(
        "ddo-test",
        root["subject"],
        root["original_source"],
        canonical_bytes(root["analyzed_scope"]),
    )
    request = SemanticRequestKey(
        ddo_kernel["identities"][operation, "recipe"],
        root["subject"],
        {},
        {"parameters": {}, "replicate": None},
        "inference:test",
        subject_context=context,
    )
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        obligation = storage.invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": operation,
                **root,
                "parameters": {},
            },
        )
        current = storage.invoke("read_demand_result", {"demand_id": demand["demand_id"]})
        attached = storage.invoke(
            "attach_data_request",
            {
                **obligation,
                "request_meaning": json.loads(request.identity.canonical_input),
                "request_key": request.identity.key,
                "replicate": None,
                "binding": {
                    "inputs": [],
                    "support": [],
                    "parameters": semantic_value(request.parameters),
                    "request_inputs": semantic_value({}),
                    "inference": "inference:test",
                    "populations": [],
                    "read_id": current["read_id"],
                },
            },
        )
    fence = claim(ddo_kernel, attached)
    contract = ddo_kernel["identities"][PREFIX + "ConsumerPopulation_" + group, "kind"]
    packets = [{**packet, "body": semantic_value(packet["body"])} for packet in body["members"]]
    with ddo_kernel["engine"].begin() as connection:
        intent = DataOperationStorage(connection).invoke(
            "retain_data_completion_intent",
            {
                **fence,
                "runtime_id": ddo_kernel["runtime"],
                "completion": {
                    "outcome": "success",
                    "implementation_revision": "native-test-source-v1",
                    "inputs": [],
                    "support": [],
                    "outputs": [
                        {
                            "role": "result",
                            "position": 0,
                            "multiplicity": 1,
                            "product": {
                                "kind_contract": contract,
                                "body": semantic_value(body),
                                "members": packets,
                            },
                        }
                    ],
                },
            },
        )
    from corpus_structure.semantic.data_operation_ports import RoleValue

    with ddo_kernel["engine"].begin() as connection:
        port = acquire_publication_port(connection, ddo_kernel["prepared"])
        value = RoleValue(
            "request",
            port.request_kind,
            canonical_bytes({**fence, "intent_id": intent["intent_id"]}),
        )
        completed = port.invoke_json(value)
        receipt = completed.result.value()
        replay = port.invoke_json(value)
        assert replay.receipt_id == completed.receipt_id
        assert replay.derivation_id == completed.derivation_id
        assert replay.result.value()["replayed"] is True
    product = contextual_product_identity(
        kind=contract, context=context, body=body_identity(body).key
    ).key
    with ddo_kernel["engine"].begin() as connection:
        parent = DataOperationStorage(connection).invoke(
            "close_data_population",
            {
                "demand_id": demand["demand_id"],
                "name": "all-" + group,
                "product_id": product,
                "derivation_id": receipt["derivation_id"],
                "member_role": "result",
            },
        )
    return product, parent


@pytest.mark.parametrize(
    ("case", "ddo_kernel"),
    [(case, CONSUMERS[case]) for case in CASES],
    indirect=["ddo_kernel"],
    ids=list(CASES),
)
def test_actual_consumer_selects_exact_native_hydrated_members(ddo_kernel, case):
    prepared, model = ddo_kernel["prepared"], ddo_kernel["model"]
    runtime = ddo_kernel.preparation.runtime
    ids = ddo_kernel["identities"]
    operation, subject, groups = CASES[case]
    scope = {"page": 1}
    root = dict(subject=subject, original_source="source:test", analyzed_scope=scope)
    context = SubjectContext("ddo-test", subject, "source:test", canonical_bytes(scope))
    records = _records(case)
    bodies = {
        group: {
            "complete": True,
            "members": [
                {
                    "member_id": identifier,
                    "kind_contract": ids[PREFIX + KINDS[group], "kind"],
                    "context": {
                        "subject": member_subject,
                        "original_source": "source:test",
                        "analyzed_scope": scope,
                    },
                    "body": body,
                }
                for identifier, member_subject, body in records[group]
            ],
        }
        for group in groups
    }
    source_sets = ()
    if case == "structural":
        entries = []
        for group in groups:
            product = contextual_product_identity(
                kind=ids[PREFIX + "ConsumerPopulation_" + group, "kind"],
                context=context,
                body=body_identity(bodies[group]).key,
            ).key
            for identifier, member_subject, body in records[group]:
                reference = _source_reference(1 if body["passage_id"] == "left" else 2)
                entries.append(
                    SourceSetEntry.from_structural_source(
                        reference,
                        original_source="source:test",
                        subject=member_subject,
                        analyzed_scope=canonical_bytes(scope),
                        product=product,
                        member=identifier,
                    )
                )
        source_sets = (FrozenSourceSet("structural-input-sources", tuple(entries)),)
    parameters: dict[str, Any] = {
        "document": {"base_product": "base"},
        "projection": {"projection_digest": "selected"},
        "occurrences": {
            "source_product": "base",
            "source_projection": "selected",
            "semantic_types": ["definition"],
            "required_occurrence_ids": ["one"],
        },
        "structural": {
            "left_passage_id": "left",
            "right_passage_id": "right",
            "left_reading_id": "contribution:left",
            "right_reading_id": "contribution:right",
        },
    }[case]
    choices = {"source_selection": "projection"} if case == "projection" else {}
    intent = freeze_demand(
        model,
        roots=(RootSubject(subject, "source:test", canonical_bytes(scope)),),
        targets=(operation, *("urn:consumer-native:" + group for group in groups)),
        selections=(
            OperationSelection(
                operation, parameters=canonical_bytes(parameters), choices=canonical_bytes(choices)
            ),
        ),
        discovery=tuple(
            DiscoverySelection("urn:consumer-native:" + group, "result", operation, "all-" + group)
            for group in groups
        ),
        source_sets=source_sets,
        inference="inference:test",
        execution_profile="execution:test",
    ).record
    with ddo_kernel["engine"].begin() as connection:
        demand = DataOperationStorage(connection).invoke(
            "register_data_demand",
            {
                "project_id": "ddo-test",
                "release_id": prepared.release_id,
                "runtime_id": runtime.runtime_id,
                "root": [root],
                "selection": intent,
                "strength": "value",
            },
        )
    parents = {}
    for group in groups:
        _, parents[group] = _publish(ddo_kernel, demand, root, group, bodies[group])
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        obligation = storage.invoke(
            "expand_data_obligation",
            {
                "demand_id": demand["demand_id"],
                "operation_id": operation,
                **root,
                "parameters": parameters,
            },
        )
        snapshot = storage.invoke("read_demand_result", {"demand_id": demand["demand_id"]})
        projections = admitted_data_projection(
            connection,
            demand["demand_id"],
            operation,
            snapshot["trust_snapshot"],
            model,
            read_id=snapshot["read_id"],
            subject=subject,
            original_source="source:test",
            analyzed_scope=scope,
        )
        arguments = dict(
            subject=subject,
            subject_context=context,
            parameters=parameters,
            choices=choices,
            original_source="source:test",
            source_sets=source_sets,
        )
        compiled = compile_binding(model, operation, projections, **arguments)
        declarations = {role.name: role for role in model.operation(operation).roles}
        selected: list[dict[str, Any]] = []
        for role, population_name in compiled.population_roles:
            group = next(
                group for group in groups if PREFIX + KINDS[group] == declarations[role].kind
            )
            receipt = storage.invoke(
                "select_data_population",
                {
                    **obligation,
                    "population_name": population_name,
                    "parent_population_id": parents[group]["population_id"],
                    "read_id": snapshot["read_id"],
                },
            )
            selected.append(receipt)
    with ddo_kernel["engine"].begin() as connection:
        storage = DataOperationStorage(connection)
        snapshot = storage.invoke("read_demand_result", {"demand_id": demand["demand_id"]})
        populations = tuple(
            PopulationBinding(
                row["name"],
                row["semantic_key"],
                row["complete"],
                tuple(member["member_id"] for member in row["members"]),
                canonical_bytes(
                    {**row["evidence"], "population_id": row["population_id"], "name": row["name"]}
                ),
            )
            for row in selected
        )
        projections = admitted_data_projection(
            connection,
            demand["demand_id"],
            operation,
            snapshot["trust_snapshot"],
            model,
            read_id=snapshot["read_id"],
            subject=subject,
            original_source="source:test",
            analyzed_scope=scope,
        )
        binding = execute_binding(
            connection,
            compile_binding(model, operation, projections, populations=populations, **arguments),
        )
        assert binding.sufficient, binding.reasons
        from corpus_structure.methods.contextual_candidates import ContextualCandidates
        from corpus_structure.methods.m1_source import M1Candidates
        from corpus_structure.methods.native_evidence import NativeEvidenceMethod
        from corpus_structure.methods.structural_products import StructuralComparisonMethod

        method = {
            "document": NativeEvidenceMethod,
            "projection": M1Candidates,
            "structural": StructuralComparisonMethod,
            "occurrences": ContextualCandidates,
        }[case]()
        body_queries = []

        def record_body_query(_, __, statement, ___, ____, _____):
            if "ops.data_binding_rows(" in statement:
                body_queries.append(statement)

        event.listen(connection, "before_cursor_execute", record_body_query)
        try:
            result = method.select_bound_native(
                connection,
                model,
                binding,
                demand_id=demand["demand_id"],
                read_id=snapshot["read_id"],
                trust_snapshot=snapshot["trust_snapshot"],
                max_bytes=1024 * 1024,
            )
        finally:
            event.remove(connection, "before_cursor_execute", record_body_query)
        assert len(body_queries) == 1
        assert body_queries[0].count("ops.data_binding_rows(") == 1
        assert "LATERAL" not in body_queries[0]
        if case == "document":
            assert result[0] == "document"
            assert [value.member.member for value in result[1]] == ["view:one", "view:two"]
        elif case == "projection":
            from corpus_structure.semantic.data_operation_consumers import SelectedConsumerValue

            selected_ids = []
            for value in result:
                assert isinstance(value, SelectedConsumerValue)
                selected_ids.append(value.member.member)
            assert selected_ids == ["view:one"]
        elif case == "structural":
            assert (result[0][0].value()["passage_id"], result[1][0].value()["passage_id"]) == (
                "left",
                "right",
            )
        else:
            from corpus_structure.semantic.data_operation_consumers import SelectedConsumerValue

            assert isinstance(result[0], SelectedConsumerValue)
            assert result[0].member.subject == "view"
            assert [value.value()["occurrence_id"] for value in result[1]] == ["one"]
        different = storage.invoke("read_demand_result", {"demand_id": demand["demand_id"]})
        assert different["read_id"] != snapshot["read_id"]
        with pytest.raises(ValueError, match="different native read boundary"):
            method.select_bound_native(
                connection,
                model,
                binding,
                demand_id=demand["demand_id"],
                read_id=different["read_id"],
                trust_snapshot=different["trust_snapshot"],
                max_bytes=1024 * 1024,
            )
        with pytest.raises(ValueError, match="packet capacity"):
            method.select_bound_native(
                connection,
                model,
                binding,
                demand_id=demand["demand_id"],
                read_id=snapshot["read_id"],
                trust_snapshot=snapshot["trust_snapshot"],
                max_bytes=1,
            )
