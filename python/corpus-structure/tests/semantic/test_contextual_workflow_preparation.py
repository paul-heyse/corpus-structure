"""Real captured source preparation; no native execution or provider claim."""

import pytest
from corpus_structure.semantic.observations import source_value

@pytest.fixture(scope="module")
def prepared_workflow(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("contextual-workflow-source")
    from corpus_structure.semantic.prepare import prepare_release
    from semantic.current_contextual_support import controlled_encoder, contextual_workflow_recipe

    encoder = controlled_encoder(tmp_path / "encoder")
    captured = contextual_workflow_recipe(tmp_path / "recipe", encoder).captured_inputs
    assert captured is not None
    prepared = prepare_release(captured.bundle, captured.dependencies, captured.profile)
    return prepared


def test_current_definition_workflow_has_actual_source_and_consumer_contracts(prepared_workflow):
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from semantic.contextual_native_fixture import CUES, COMPONENTS
    model = bound_data_operation_model(prepared_workflow)
    assert model.operation(CUES).capabilities.prepared_factory is not None
    assert model.operation(COMPONENTS).capabilities.prepared_factory is not None
    applicability = model.operation("structure.definition_applicability/declared")
    assert {role.name for role in applicability.roles if role.direction == "input"} == {
        "source", "components", "relationship"}


def unadmitted_frame(text):
    """Controlled native coordinates; no registered source or receipt is asserted."""
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource, DeclaredRecordSource
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.source_products import native_projection_identity
    from corpus_structure.semantic.original_documents import original_document_subject
    pointer = "#/texts/0"
    items = [dict(self_ref=pointer, label="text", text=text)]
    pieces = [dict(kind="native_text", item_ref=pointer, source_field="text", start=0, end=len(text))]
    projection = native_projection_identity(text, pieces, items, (), ())
    coordinate = dict(document="unadmitted:document", document_subject=original_document_subject("unadmitted:document"), projection=projection, section_pointer=pointer,
        membership="direct")
    selectors = [dict(projection=projection, native_pointer=pointer, start=0, end=len(text))]
    context = SubjectContext("unadmitted:project", "unadmitted:source", "unadmitted:document",
        canonical_bytes(dict(source=coordinate, selectors=selectors)), subject_definition="original-source-view")
    address = DeclaredRecordSource("unadmitted:document", projection, pointer, "direct", context,
        "unadmitted:product", "unadmitted:member", "unadmitted:source-kind")
    return DeclaredNativeFrameSource(canonical_bytes(dict(source=coordinate, selectors=selectors,
        text=text, pieces=pieces, items=items)).decode(), canonical_bytes(address.pin()).decode()), context


def test_finite_matcher_retains_distinct_same_span_carriers_and_actual_component(prepared_workflow):
    from corpus_structure.semantic.data_operation_cpu_basis import CPUInputRole, cpu_authority_value, cpu_input_basis
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.identity import canonical_bytes
    from semantic.contextual_native_fixture import TEXT, execute_cue_kernel, execute_component_kernel
    frame, context = unadmitted_frame(TEXT)
    processed = cpu_input_basis("unadmitted:finite-source-control", context,
        (CPUInputRole("source", 0, 1, "unadmitted:product", "unadmitted:member", "unadmitted:source-kind",
            context, frame.value, ()),), parameters=canonical_bytes(semantic_value({})), replicate=None)
    reply = execute_cue_kernel(processed, prepared=prepared_workflow, check_active=lambda: None)
    result = cpu_authority_value(canonical_bytes(reply), expected_basis=processed)
    rows = {row["body"]["semantic_type"]: row["body"] for row in result["members"]}
    subject, unrelated, object_ = (rows["source_rule."+role] for role in ("subject", "unrelated", "object"))
    assert subject["occurrence_id"] == unrelated["occurrence_id"] != object_["occurrence_id"]
    assert len({row["contribution_id"] for row in (subject, unrelated, object_)}) == 3
    from corpus_structure.semantic.data_operation_identity import decode_semantic_value
    selected = decode_semantic_value(processed)
    selected["parameters"] = {"purpose": "meaning"}
    component_basis = semantic_value(selected)
    reply = execute_component_kernel(component_basis, prepared=prepared_workflow, check_active=lambda: None)
    report = cpu_authority_value(canonical_bytes(reply), expected_basis=component_basis)
    (component,) = report["definition_components"]["components"]
    assert component["interpretation"] == "definition" and component["basis"] == "matched_cue"
    assert (component["term"]["start"], component["term"]["end"], component["term"]["text"]) == (2, 7, "count")
    assert (component["content"]["start"], component["content"]["end"], component["content"]["text"]) == (16, 22, "number")


@pytest.mark.parametrize("payload", [
    dict(semantic_type="contextual.relationship", value=source_value(dict(relation="defined-by", target="component:12"))),
    dict(semantic_type="contextual.relationship", value={"kind": "invalid"}),
    dict(semantic_type="contextual.located_mention", value=source_value(dict(producer_semantic_type="table.cell_value", producer_value=None))),
    dict(semantic_type="contextual.located_mention", value=source_value(dict(producer_semantic_type="table.cell_value"))),
    dict(semantic_type="contextual.located_mention", value=source_value(dict(producer_semantic_type="table.cell_value", producer_value={"kind": "decimal", "lexical": "12"}))),
    dict(semantic_type="contextual.located_mention", value=source_value(dict(producer_semantic_type="structural.located_participant", producer_value=source_value(dict(named_cue=dict(primary_node={})))))) ,
    dict(semantic_type="contextual.located_mention", value={"kind": "invalid"}),
    dict(semantic_type="contextual.located_mention", value=source_value(dict(producer_semantic_type="structural.located_participant", producer_value={"kind": "invalid"}))),
    dict(semantic_type="contextual.located_mention", value=source_value(dict(producer_semantic_type="structural.located_participant"))),
    dict(semantic_type="contextual.located_mention", value=source_value(dict(producer_semantic_type="structural.located_participant", producer_value=None))),
])
def test_current_carrier_contract_never_decodes_raw_named_or_unrelated_wrappers(prepared_workflow, payload):
    from corpus_structure.semantic.data_operation_json import json_bytes
    from semantic.test_contextual_witnesses import witness_case
    _, _, roles, _ = witness_case()
    carrier = roles[1].body["carrier"]
    # The exact qualified address is valid on its own. Raw scientific/value
    # wrappers are additional unrequested material, never an evidence shortcut.
    prepared_workflow.validate_json("DdoContextualCarrierInput", json_bytes(carrier))
    with pytest.raises(ValueError):
        prepared_workflow.validate_json("DdoContextualCarrierInput", json_bytes({**carrier, **payload}))
