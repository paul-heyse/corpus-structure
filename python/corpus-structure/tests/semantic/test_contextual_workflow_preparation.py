"""Real captured source preparation; no native execution or provider claim."""

import pytest

from corpus_structure.semantic.observations import source_value


@pytest.fixture(scope="module")
def prepared_workflow(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("contextual-workflow-source")
    from corpus_structure.semantic.prepare import prepare_release
    from semantic.current_contextual_support import contextual_workflow_recipe, controlled_encoder

    encoder = controlled_encoder(tmp_path / "encoder")
    captured = contextual_workflow_recipe(tmp_path / "recipe", encoder).captured_inputs
    assert captured is not None
    prepared = prepare_release(captured.bundle, captured.dependencies, captured.profile)
    return prepared


def test_current_definition_workflow_has_actual_source_and_consumer_contracts(prepared_workflow):
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from semantic.contextual_native_fixture import COMPONENTS, CUES

    model = bound_data_operation_model(prepared_workflow)
    assert model.operation(CUES).capabilities.prepared_factory is not None
    assert model.operation(COMPONENTS).capabilities.prepared_factory is not None
    applicability = model.operation("structure.definition_applicability/declared")
    assert {role.name for role in applicability.roles if role.direction == "input"} == {
        "source",
        "components",
        "relationship",
    }
    assert {
        (target.output_role, target.path, target.input_role, target.variant)
        for target in applicability.reference_targets
    } == {
        ("result", "/components_input", "components", "product"),
        ("result", "/relationship_input", "relationship", "product"),
    }
    assert {item.input_role: item.records for item in applicability.output_witnesses} == {
        "components": "/definition/readings/*/component_ref",
        "relationship": "/definition/readings/*/link_ref",
    }
    for operation in (
        "retrieve.contextual_query/declared",
        "retrieve.contextual_query/selected-context",
        "retrieve.contextual_targets/components",
        "retrieve.contextual_vectors/selection",
        "retrieve.contextual_scores/declared",
        "retrieve.contextual/declared",
        "retrieve.contextual_inventory/declared",
        "retrieve.contextual_neighborhood/declared",
        "retrieve.contextual_witnesses/declared",
        "retrieve.contextual/with-witnesses",
    ):
        assert model.operation(operation).subject == "original-source-view"
    assert model.subject_definition("original-source-view").scope == "original-source"
    assert model.operation("retrieve.contextual_scores/declared").dependencies == (
        "retrieve.contextual_vectors/selection",
    )
    for operation, subject in (
        ("retrieve.contextual_targets/curated", "contextual-registry"),
        ("retrieve.contextual_target/declared", "contextual-target"),
        ("retrieve.contextual_target_vector/declared", "contextual-target"),
    ):
        assert model.operation(operation).subject == subject
        assert model.subject_definition(subject).scope == "project"


def test_selected_applicability_resolves_original_whole_inputs(prepared_workflow):
    from dataclasses import asdict
    from types import SimpleNamespace

    from pydantic import ValidationError

    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.selected_structural_projection import structural_report
    from corpus_structure.semantic.structural_products import DeclaredDefinitionApplicabilityReport
    from semantic.dossier_semantic_states_support import applicability

    operation = "structure.definition_applicability/declared"
    nominal = "urn:corpus:structural:DeclaredDefinitionApplicabilityReport"
    model = bound_data_operation_model(prepared_workflow)
    contract = next(
        item.key for item in model.identities if item.owner == nominal and item.domain == "kind"
    )
    targets = model.operation(operation).reference_targets
    _, reports = applicability()
    report = reports[0]
    body = report.model_dump(mode="json", exclude_none=True)
    (reading,) = report.definition.readings
    references = {"components": reading.component_ref, "relationship": reading.link_ref}
    originals = {
        role: {"role": role, "product_id": ref.product_id, "position": 0, "multiplicity": 1}
        for role, ref in references.items()
    }
    use = {
        "fate": "fulfilled",
        "derivation_id": "episode",
        "selection": {"inputs": list(originals.values())},
    }
    maps = {
        "ops.demand_use": {"use": use},
        "ops.data_derivation": {"episode": {"release_id": "release"}},
        "sem.data_operation_definition": {
            ("release", operation): {
                "support_contract": {"reference_targets": [asdict(target) for target in targets]},
                "input_roles": [
                    {
                        "name": target.input_role,
                        "kind": target.input_kind,
                        "accepted_kind_contracts": [references[target.input_role].kind_contract],
                    }
                    for target in targets
                ],
            },
        },
        # Authorizing these whole inputs for metadata must not open their bodies.
        "kb.data_product": {
            item.product_id: {"project_id": item.project_id, "kind_contract": item.kind_contract}
            for item in references.values()
        },
        "kb.data_product_member": {},
        "kb.data_product_partition": {},
        "sem.data_kind_contract": {
            reading.component_ref.kind_contract: {
                "kind": "urn:corpus:structural:DeclaredNamedDefinitionComponentsReport"
            },
            reading.link_ref.kind_contract: {
                "kind": next(
                    target.input_kind for target in targets if target.input_role == "relationship"
                )
            },
        },
    }

    def original_edges(relation, *, derivation_id, role):
        assert (relation, derivation_id) == ("ops.data_derivation_input", "episode")
        return (originals[role],)

    scope = SimpleNamespace(
        model=model,
        cut=SimpleNamespace(record={"project_id": reading.link_ref.project_id}),
        index=SimpleNamespace(mapping=lambda relation, _: maps[relation], rows_for=original_edges),
    )
    selected = SimpleNamespace(
        operation_id=operation,
        derivation_id="episode",
        use_id="use",
        output={"role": "result"},
        nominal=nominal,
        reference=SimpleNamespace(member_id=None, kind_contract=contract),
        body=body,
    )
    assert structural_report(scope, selected) == report
    for role in originals:
        use["selection"]["inputs"] = [
            {**edge, "product_id": "equal-content-replacement"} if name == role else edge
            for name, edge in originals.items()
        ]
        with pytest.raises(ValueError, match="unavailable in the exact selected use"):
            structural_report(scope, selected)

    from corpus_structure.semantic.identity import canonical_bytes

    for role, ref in references.items():
        absolute = ref.model_dump(mode="json", exclude={"edge_id", "component_id", "structural_id"})
        absolute["reference"] = canonical_bytes([ref.product_id, None]).decode()
        field = role + "_input"
        with pytest.raises(ValidationError, match=field):
            DeclaredDefinitionApplicabilityReport.model_validate({**body, field: absolute})


def unadmitted_frame(text):
    """Controlled native coordinates; no registered source or receipt is asserted."""
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.declared_record_sources import (
        DeclaredNativeFrameSource,
        DeclaredRecordSource,
    )
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.original_documents import original_document_subject
    from corpus_structure.semantic.source_products import native_projection_identity

    pointer = "#/texts/0"
    items = [dict(self_ref=pointer, label="text", text=text)]
    pieces = [
        dict(kind="native_text", item_ref=pointer, source_field="text", start=0, end=len(text))
    ]
    projection = native_projection_identity(text, pieces, items, (), ())
    coordinate = dict(
        document="unadmitted:document",
        document_subject=original_document_subject("unadmitted:document"),
        projection=projection,
        section_pointer=pointer,
        membership="direct",
    )
    selectors = [dict(projection=projection, native_pointer=pointer, start=0, end=len(text))]
    context = SubjectContext(
        "unadmitted:project",
        "unadmitted:source",
        "unadmitted:document",
        canonical_bytes(dict(source=coordinate, selectors=selectors)),
        subject_definition="original-source-view",
    )
    address = DeclaredRecordSource(
        "unadmitted:document",
        projection,
        pointer,
        "direct",
        context,
        "unadmitted:product",
        "unadmitted:member",
        "unadmitted:source-kind",
    )
    return DeclaredNativeFrameSource.from_retained_record(
        canonical_bytes(
            dict(source=coordinate, selectors=selectors, text=text, pieces=pieces, items=items)
        ).decode(),
        canonical_bytes(address.pin()).decode(),
    ), context


def test_finite_matcher_retains_distinct_same_span_carriers_and_actual_component(prepared_workflow):
    from corpus_structure.semantic.data_operation_cpu_basis import (
        CPUInputRole,
        cpu_authority_value,
        cpu_input_basis,
    )
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.identity import canonical_bytes
    from semantic.contextual_native_fixture import (
        TEXT,
        execute_component_kernel,
        execute_cue_kernel,
    )

    frame, context = unadmitted_frame(TEXT)
    processed = cpu_input_basis(
        "unadmitted:finite-source-control",
        context,
        (
            CPUInputRole(
                "source",
                0,
                1,
                "unadmitted:product",
                "unadmitted:member",
                "unadmitted:source-kind",
                context,
                frame.value,
                (),
                producer_output=None,
            ),
        ),
        parameters=canonical_bytes(semantic_value({})),
        replicate=None,
    )
    reply = execute_cue_kernel(processed, prepared=prepared_workflow, check_active=lambda: None)
    result = cpu_authority_value(canonical_bytes(reply), expected_basis=processed)
    rows = {row["body"]["semantic_type"]: row["body"] for row in result["members"]}
    subject, unrelated, object_ = (
        rows["source_rule." + role] for role in ("subject", "unrelated", "object")
    )
    assert subject["occurrence_id"] == unrelated["occurrence_id"] != object_["occurrence_id"]
    assert len({row["contribution_id"] for row in (subject, unrelated, object_)}) == 3
    from corpus_structure.semantic.data_operation_values import decode_semantic_value

    selected = decode_semantic_value(processed)
    selected["parameters"] = {"purpose": "meaning"}
    component_basis = semantic_value(selected)
    reply = execute_component_kernel(
        component_basis, prepared=prepared_workflow, check_active=lambda: None
    )
    report = cpu_authority_value(canonical_bytes(reply), expected_basis=component_basis)
    (component,) = report["definition_components"]["components"]
    assert component["interpretation"] == "definition" and component["basis"] == "matched_cue"
    assert (component["term"]["start"], component["term"]["end"], component["term"]["text"]) == (
        2,
        7,
        "count",
    )
    assert (
        component["content"]["start"],
        component["content"]["end"],
        component["content"]["text"],
    ) == (16, 22, "number")


@pytest.mark.parametrize(
    "payload",
    [
        dict(
            semantic_type="contextual.relationship",
            value=source_value(dict(relation="defined-by", target="component:12")),
        ),
        dict(semantic_type="contextual.relationship", value={"kind": "invalid"}),
        dict(
            semantic_type="contextual.located_mention",
            value=source_value(
                dict(producer_semantic_type="table.cell_value", producer_value=None)
            ),
        ),
        dict(
            semantic_type="contextual.located_mention",
            value=source_value(dict(producer_semantic_type="table.cell_value")),
        ),
        dict(
            semantic_type="contextual.located_mention",
            value=source_value(
                dict(
                    producer_semantic_type="table.cell_value",
                    producer_value={"kind": "decimal", "lexical": "12"},
                )
            ),
        ),
        dict(
            semantic_type="contextual.located_mention",
            value=source_value(
                dict(
                    producer_semantic_type="structural.located_participant",
                    producer_value=source_value(dict(named_cue=dict(primary_node={}))),
                )
            ),
        ),
        dict(semantic_type="contextual.located_mention", value={"kind": "invalid"}),
        dict(
            semantic_type="contextual.located_mention",
            value=source_value(
                dict(
                    producer_semantic_type="structural.located_participant",
                    producer_value={"kind": "invalid"},
                )
            ),
        ),
        dict(
            semantic_type="contextual.located_mention",
            value=source_value(dict(producer_semantic_type="structural.located_participant")),
        ),
        dict(
            semantic_type="contextual.located_mention",
            value=source_value(
                dict(producer_semantic_type="structural.located_participant", producer_value=None)
            ),
        ),
    ],
)
def test_current_carrier_contract_never_decodes_raw_named_or_unrelated_wrappers(
    prepared_workflow, payload
):
    from corpus_structure.semantic.data_operation_json import json_bytes
    from semantic.test_contextual_witnesses import witness_case

    _, _, roles, _ = witness_case()
    carrier = roles[1].body["carrier"]
    # The exact qualified address is valid on its own. Raw scientific/value
    # wrappers are additional unrequested material, never an evidence shortcut.
    prepared_workflow.validate_json("DdoContextualCarrierInput", json_bytes(carrier))
    with pytest.raises(ValueError):
        prepared_workflow.validate_json(
            "DdoContextualCarrierInput", json_bytes({**carrier, **payload})
        )
