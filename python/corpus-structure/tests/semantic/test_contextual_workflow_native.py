"""Current native source → component → actual occurrence → compatible-edge custody.

The encoder and relationship interpretation kernels are controlled here. Native
completion, source selection, retained-component authentication and replay are real;
this test makes no model/provider or semantic-quality claim.
"""

import json

import pytest
from native_refusals import native_refusal
from sqlalchemy import select, text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.orchestrate import semantic
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.operations import OperationBinding
from semantic.native_record_fixtures import RecordSourceRecipe
from semantic.native_record_fixtures import private_source as private_source
from semantic.witnessed_scenario_support import completed_metadata, completed_relationship_case


@pytest.mark.parametrize(
    "carrier",
    (
        pytest.param(
            {
                "semantic_type": "contextual.relationship",
                "value": source_value({"relation": "defined-by", "target": "component:12"}),
            },
            id="semantic-proposal",
        ),
        pytest.param(
            {"semantic_type": "contextual.relationship", "value": {"kind": "invalid"}},
            id="noncarrier-is-not-decoded",
        ),
        pytest.param(
            {
                "semantic_type": "contextual.located_mention",
                "value": source_value(
                    {
                        "producer_semantic_type": "table.cell_value",
                        "producer_value": None,
                    }
                ),
            },
            id="literal-native-carrier-without-value",
        ),
        pytest.param(
            {
                "semantic_type": "contextual.located_mention",
                "value": source_value({"producer_semantic_type": "table.cell_value"}),
            },
            id="literal-native-carrier-without-value-field",
        ),
        pytest.param(
            {
                "semantic_type": "contextual.located_mention",
                "value": source_value(
                    {
                        "producer_semantic_type": "table.cell_value",
                        "producer_value": {"kind": "decimal", "lexical": "12"},
                    }
                ),
            },
            id="literal-native-decimal-is-not-source-value",
        ),
        pytest.param(
            {
                "semantic_type": "contextual.located_mention",
                "value": source_value(
                    {
                        "producer_semantic_type": "structural.located_participant",
                        "producer_value": source_value({"named_cue": {"primary_node": {}}}),
                    }
                ),
            },
            id="missing-named-role",
        ),
    ),
)
def test_named_source_dispatch_ignores_non_named_evidence(native_read, carrier):
    # No run or source view exists: unrelated products must return before accessing
    # primary layers, and semantic proposals do not have a producer-value wrapper.
    with native_read.begin_nested():
        assert (
            native_read.scalar(
                text(
                    "SELECT ops.contextual_primary_named_cue("
                    "NULL,NULL::kb.source_view,'[]'::jsonb,CAST(:carrier AS jsonb))"
                ),
                {"carrier": json.dumps(carrier)},
            )
            is None
        )


@pytest.mark.parametrize(
    "value,error",
    (
        pytest.param(
            {"kind": "invalid"},
            "unsupported sealed record event JSON",
            id="malformed-outer-wrapper",
        ),
        pytest.param(
            source_value(
                {
                    "producer_semantic_type": "structural.located_participant",
                    "producer_value": {"kind": "invalid"},
                }
            ),
            "unsupported sealed record event JSON",
            id="malformed-named-producer-value",
        ),
        pytest.param(
            source_value({"producer_semantic_type": "structural.located_participant"}),
            "contextual named source lacks an encoded producer value",
            id="missing-named-producer-value",
        ),
        pytest.param(
            source_value(
                {"producer_semantic_type": "structural.located_participant", "producer_value": None}
            ),
            "contextual named source lacks an encoded producer value",
            id="null-named-producer-value",
        ),
    ),
)
def test_named_source_dispatch_rejects_malformed_named_carriers(native_read, value, error):
    carrier = {"semantic_type": "contextual.located_mention", "value": value}
    with (
        native_refusal("23514", message=error),
        native_read.begin_nested(),
    ):
        native_read.scalar(
            text(
                "SELECT ops.contextual_primary_named_cue("
                "NULL,NULL::kb.source_view,'[]'::jsonb,CAST(:carrier AS jsonb))"
            ),
            {"carrier": json.dumps(carrier)},
        )


@pytest.mark.parametrize(
    "private_source", [RecordSourceRecipe()], indirect=True, ids=("record-base",)
)
@pytest.mark.parametrize(
    "mode,expected",
    [
        pytest.param("defining_occurrence", "applicable_definition", id="defining-occurrence"),
        pytest.param("contextual_usage", "unresolved", id="contextual-usage-unknown"),
    ],
)
def test_registered_actual_occurrences_resolve_component_and_retain_compatible_edges(
    private_source, monkeypatch, tmp_path, mode, expected
):
    case = private_source
    linked = completed_relationship_case(case, monkeypatch, tmp_path)
    completed, outcome, body, payload = (
        linked.completed,
        linked.outcome,
        linked.body,
        linked.payload,
    )
    tasks, results, configs, methods = (
        table(n) for n in ("ops.task", "ops.task_result", "ops.method_config", "ops.method")
    )
    finalize_bound_run(case.writer, outcome.run_id, "wce-links")
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.serve.contributions import (
        ContributionRequest,
        export_contribution_selection,
        serve_contributions,
    )

    with read_snapshot(case.writer) as conn:
        page = serve_contributions(
            conn,
            ContributionRequest(
                run_id=outcome.run_id,
                method="retrieve.contextual",
                include_details=True,
                include_interpretation=True,
            ),
        )
        assert page.standing == "retained_private"
        exported = export_contribution_selection(
            conn,
            ContributionRequest(
                run_id=outcome.run_id, method="retrieve.contextual", include_interpretation=True
            ),
            tmp_path / "current-links",
        )
        assert exported
    from corpus_structure.semantic.observations import source_python
    from semantic.native_record_fixtures import contribution_drafts

    # Independently authored meaning of the controlled located definition. Dynamic
    # custody dimensions come from the source supplied to the component producer,
    # rather than the relationship selection or its retained projection.
    source_pin = {
        key: getattr(completed.source, key)
        for key in (
            "project_id",
            "native_product_key",
            "native_content_digest",
            "projection_digest",
            "recipe_digest",
            "coordinate_version",
        )
    }
    citation = {
        "start": 0,
        "end": 2,
        "text": "12",
        "scope": "controlled-source",
        "source": source_pin,
    }
    target = {
        "term": citation,
        "content": citation,
        "interpretation": "definition",
        "scope": "controlled-source",
    }
    supplied = contribution_drafts(case).contributions
    assert supplied is not None
    occurrence = supplied[0]["occurrence_id"]
    expected_edges = sorted(
        (occurrence, relation, json.dumps(target, sort_keys=True), "controlled-source", None)
        for relation in ("denotes", "compared-with", "defined-by")
    )

    def retained_edges(items):
        edges = []
        for item in items:
            row = item["row"]
            if (
                item["population"] != "interpretation"
                or row.get("semantic_type") != "contextual.relationship"
            ):
                continue
            meaning = source_python(row["value"])
            edges.append(
                (
                    row["occurrence_id"],
                    meaning["relation"],
                    json.dumps(meaning["target"], sort_keys=True),
                    meaning["scope"],
                    meaning["effective_version"],
                )
            )
        return sorted(edges)

    assert retained_edges(page.items) == expected_edges
    exported_items = [
        json.loads(line)
        for path in (tmp_path / "current-links").rglob("*.jsonl")
        for line in path.read_text().splitlines()
    ]
    assert retained_edges(exported_items) == expected_edges
    from corpus_structure.methods.definition_applicability import (
        DefinitionApplicabilityConfig,
        DefinitionApplicabilityMethod,
    )
    from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef

    linked_result, linked_revision, linked_runtime = completed_metadata(case, outcome.run_id)
    with case.writer.connect() as conn:
        link_task = (
            conn.execute(
                select(tasks)
                .join(configs, configs.c.id == tasks.c.method_config_id)
                .join(methods, methods.c.id == configs.c.method_id)
                .where(tasks.c.run_id == outcome.run_id, methods.c.name == "retrieve.contextual")
            )
            .mappings()
            .one()
        )
    decision = payload["relationship_decisions"][0]
    edge = next(e for e in decision["selected_edges"] if e["relation"] == "defined-by")
    occurrence = next(
        c
        for c in body["contributions"]
        if c["semantic_type"] == "contextual.located_mention"
        and source_python(c["value"])["producer_semantic_type"] == "table.cell_value"
    )
    link_ref = RetainedRelationshipDecisionRef(
        project_id="private-records",
        run_id=outcome.run_id,
        cut_id=linked_result["cut_id"],
        release_id=case.prepared.release_id,
        result_revision=linked_revision,
        selected_task_id=link_task["id"],
        origin_task_id=link_task["id"],
        runtime_fingerprint=linked_runtime,
        operation_key=body["contribution_operations"][0]["operation_key"],
        decision_id=decision["decision_id"],
        edge_id=edge["edge_id"],
        occurrence_contribution_id=occurrence["contribution_id"],
    )
    app_inputs = completed.inputs.model_copy(
        update={
            "policy_id": "definition-introduction-1"
            if mode == "defining_occurrence"
            else "contextual-usage-1",
            "dependencies": (
                *completed.inputs.dependencies,
                completed.report.product_id,
                decision["decision_id"],
            ),
        }
    )
    app_cfg = DefinitionApplicabilityConfig(
        inputs=app_inputs,
        structural_input_digest=app_inputs.identity,
        usage_id="literal",
        selection_refs=(link_ref,),
        applicability_scope=mode,
    )
    app_run = semantic.run_source_methods(
        case.writer,
        project_id="private-records",
        prepared=case.prepared,
        binding=OperationBinding(case.prepared.release_id, "wce-links", linked_revision, b"{}"),
        registry=MethodRegistry(
            [DefinitionApplicabilityMethod()],
            MethodsFile(
                configs={"structure.definitions": {"default": app_cfg.model_dump(mode="json")}}
            ),
        ),
        graph=Graph(
            ((Stage.ASSEMBLE, (Step("structure.definitions/default"),)),), policy_propose=False
        ),
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    with case.writer.connect() as conn:
        app_body = conn.execute(
            select(results.c.body)
            .join(tasks, tasks.c.id == results.c.task_id)
            .where(tasks.c.run_id == app_run.run_id)
        ).scalar_one()
    assert app_body["structural_product"]["definition"]["readings"][0]["outcome"] == expected
    assert app_body["structural_product"]["standing"] == "private_proposal"
    assert (
        app_body["structural_product"]["definition"]["readings"][0]["link_ref"]["edge_id"]
        == edge["edge_id"]
    )


@pytest.mark.parametrize(
    "private_source", [RecordSourceRecipe()], indirect=True, ids=("record-base",)
)
@pytest.mark.parametrize(
    "reverse",
    (
        pytest.param(False, id="edge-carrier-original-order"),
        pytest.param(True, id="edge-carrier-reversed-order"),
    ),
)
def test_native_same_span_roles_bind_each_edge_to_its_qualifying_carrier(
    private_source, monkeypatch, tmp_path, reverse
):
    from corpus_structure.semantic.observations import source_python

    linked = completed_relationship_case(
        private_source, monkeypatch, tmp_path, overlapping_recipe=reverse
    )
    assert linked.body["outcome"] == "produced"
    mentions = {
        source_python(row["value"])["producer_semantic_type"]: row
        for row in linked.body["contributions"]
        if row["semantic_type"] == "contextual.located_mention"
    }
    subject, unrelated, object_ = (
        mentions["source_rule." + role] for role in ("subject", "unrelated", "object")
    )
    assert subject["occurrence_id"] == unrelated["occurrence_id"] != object_["occurrence_id"]
    assert len(mentions) == 3
    assert linked.payload["product_counts"]["vectors"] == 3
    (proposal,) = (
        row
        for row in linked.body["contributions"]
        if row["semantic_type"] == "contextual.relationship"
    )
    assert proposal["members"] == [subject["contribution_id"]]
    assert proposal["computation_dependencies"][0] == subject["contribution_id"]
    assert proposal["anchors"] == subject["anchors"]
    assert source_python(proposal["value"])["relation"] == "specializes"
    (edge,) = (
        edge
        for decision in linked.payload["relationship_decisions"]
        for edge in decision["selected_edges"]
    )
    (witness,) = edge["witnesses"]
    assert witness["evidence_ids"] == [subject["contribution_id"], object_["contribution_id"]]
    assert unrelated["contribution_id"] not in witness["evidence_ids"]
