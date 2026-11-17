"""Actual typed raw/resolved family inputs and exact shared predictor application."""

from corpus_structure.semantic.data_operation_cpu_basis import CPUInputRole
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.declared_candidate_products import candidate_member_id
from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.reading_resolution_products import (
    EVENT_PROCEDURE,
    RECIPE,
    DeclaredReadingFeatureInstance,
    reading_recipe_identity,
    resolve_reading_values,
)
from corpus_structure.semantic.record_contracts import record_family_contract
from corpus_structure.semantic.record_policy import RecordAcceptanceInstance
from corpus_structure.semantic.record_policy_authority import (
    DdoRecordPolicyApplicability,
    policy_authorization_value,
)
from corpus_structure.semantic.rich_cpu_inputs import RichKernelInputs
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichContext,
    DdoRichPacket,
    DdoRichSourceReadingAssertion,
    RichGraphAssembly,
)
from corpus_structure.semantic.rich_reading_admission import rich_reading_decisions
from corpus_structure.semantic.rich_reading_inputs import select_rich_readings
from corpus_structure.semantic.rich_record_readings import rich_source_reading_assertion
from corpus_structure.semantic.rich_value_graph import RichValueGraph
from corpus_structure.semantic.selected_support import ProducerOutputOccurrence
from semantic.record_policy_support import calibrated, fitted
from semantic.test_rich_record_readings import inspected_reading


def actual_inputs():
    from corpus_structure.semantic import prepare_release
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.reading_resolution_products import (
        reading_resolution_declarations,
        reading_resolution_operation_sources,
    )
    from corpus_structure.semantic.record_policy_authority import record_policy_kind_declarations
    from corpus_structure.semantic.rich_knowledge_sources import (
        rich_knowledge_declarations,
        rich_knowledge_schema_inputs,
    )
    from corpus_structure.semantic.types import ResolvedDependencies
    from semantic.record_contracts_support import release_inputs

    bundle, deps = rich_knowledge_schema_inputs(
        release_inputs()[0],
        ResolvedDependencies(),
        qualification_class="StatisticsQualification",
        statement_class="SourceStatement",
    )
    prepared = prepare_release(bundle, deps)
    model = compile_data_operations(
        bundle,
        declarations=(
            *rich_knowledge_declarations(deps),
            reading_resolution_declarations(),
            record_policy_kind_declarations(),
        ),
        python_sources=reading_resolution_operation_sources(),
    )
    ids = {value.owner: value.key for value in model.identities if value.domain == "kind"}
    row, coordinates = inspected_reading("table")
    from copy import deepcopy

    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.original_documents import original_document_subject
    from corpus_structure.semantic.record_contracts import (
        anchor_identity,
        evidence_set_identity,
        interpretation_identity,
        record_identity,
    )

    row = deepcopy(row)
    scope = dict(
        source=dict(
            document=row["pin"]["document"],
            document_subject=original_document_subject(row["pin"]["document"]),
            projection=row["pin"]["projection_digest"],
            section_pointer=row["pin"]["section_pointer"],
            membership=row["pin"]["membership"],
        ),
        selectors=[dict(projection=row["pin"]["projection_digest"])],
    )
    pin = {
        **row["pin"],
        "subject_definition": "original-source-view",
        "analyzed_scope_meaning": canonical_bytes(semantic_value(scope)).decode(),
    }
    anchors = {}
    for anchor in row["anchors"]:
        previous = anchor["anchor_id"]
        anchor["pin"] = pin
        anchor["anchor_id"] = anchor_identity(anchor)
        anchors[previous] = anchor["anchor_id"]
    row["pin"] = pin
    row["occurrence_anchors"] = tuple(anchors[key] for key in row["occurrence_anchors"])
    sets = {}
    for evidence in row["evidence_sets"]:
        previous = evidence["set_id"]
        evidence["anchors"] = tuple(anchors[key] for key in evidence["anchors"])
        evidence["set_id"] = evidence_set_identity(evidence)
        sets[previous] = evidence["set_id"]
    for field in row["fields"]:
        field["evidence_sets"] = tuple(sets[key] for key in field["evidence_sets"])
    row["record_id"] = record_identity(record_family_contract(model, row["contract"]), row)
    row["interpretation_id"] = interpretation_identity(row)
    coordinates = [{**value, "pin": pin} for value in coordinates]
    source = DeclaredStructuralSource.model_validate(row["pin"])
    source_context = SubjectContext(
        source.project_id,
        source.subject,
        source.original_source,
        json_bytes(decode_semantic_value(__import__("json").loads(source.analyzed_scope_meaning))),
        subject_definition=source.subject_definition,
    )
    raw = dict(
        source_pin=row["pin"],
        inspection_outcome="produced",
        standing="private_uncalibrated_candidates",
        members=(
            dict(
                member_id=candidate_member_id("record", row),
                kind_contract=ids[
                    "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceRecord"
                ],
                context=dict(
                    subject=source_context.subject,
                    subject_definition=source_context.subject_definition,
                    original_source=source_context.original_source,
                    analyzed_scope=__import__("json").loads(source_context.analyzed_scope),
                ),
                body=dict(row, candidate_type="record"),
            ),
        ),
        operations=(),
        coordinate_texts=coordinates,
        coverage=(),
        diagnostics_json="{}",
    )
    raw = prepared.validate_json("DdoCandidateInspectionReport", json_bytes(raw)).model_dump(
        mode="python", exclude_unset=True
    )
    feature = fitted()
    policy = dict(
        version="reading-feature-policy-2",
        recipe=RECIPE,
        subset="native-tables",
        feature_instances=source_value(
            [
                DeclaredReadingFeatureInstance(
                    feature=feature,
                    family_contract=record_family_contract(model, row["contract"]),
                    reading_recipe=reading_recipe_identity(model),
                ).model_dump(mode="json")
            ]
        ),
    )
    resolved = resolve_reading_values(prepared, raw, policy, model=model)
    calibration = calibrated(feature).model_copy(update={"event_procedure": EVENT_PROCEDURE})
    instance = RecordAcceptanceInstance(
        feature=feature,
        calibration=calibration,
        threshold=1e-9,
        threshold_procedure="explicit-test-threshold",
        conditioning_assumptions="checked source population",
    )
    auth = policy_authorization_value(
        instance,
        family_contract=record_family_contract(model, row["contract"]),
        reading_recipe=reading_recipe_identity(model),
        judgment_basis_digest="e" * 64,
        applicability=DdoRecordPolicyApplicability(project_id=source.project_id, sources=(source,)),
    )
    context = SubjectContext(
        source.project_id, "knowledge:one", None, b"{}", subject_definition="knowledge-universe"
    )

    def role(name, product, kind, body):
        return CPUInputRole(
            name,
            None,
            1,
            product,
            None,
            ids[kind],
            source_context if name != "policy_authorizations" else context,
            body,
            (
                ComputationalSupportReference(
                    kind="computation",
                    derivation_id="episode:" + product,
                    admission_use_id="use:" + product,
                ),
            ),
            producer_output=ProducerOutputOccurrence(
                member_id=None, role="result", position=0, multiplicity=1
            ),
        )

    raw_role = role(
        "records",
        "raw",
        "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
        raw,
    )
    read_role = role(
        "readings",
        "resolved",
        "https://corpus-structure.dev/semantic/data-operation-reading-resolution/DdoResolvedReadingReport",
        resolved,
    )
    auth_role = role(
        "policy_authorizations",
        "policy",
        "https://corpus-structure.dev/semantic/data-operation-record-policy/DdoRecordPolicyAuthorization",
        auth.model_dump(mode="python"),
    )
    inputs = RichKernelInputs(
        "recipe:rich",
        context,
        (raw_role, read_role, auth_role),
        parameters=b'["mapping",[]]',
        replicate=None,
    )
    selected = select_rich_readings(prepared, inputs)
    assert len(selected) == 1 and selected[0].row is not None
    values = RichValueGraph(prepared, model)
    assertion = rich_source_reading_assertion(
        prepared, model, context=context, selection=selected[0], values=values
    )
    bodies = (*values.values, assertion)
    packets = tuple(
        DdoRichPacket(
            member_id=body.reading_id
            if isinstance(body, DdoRichSourceReadingAssertion)
            else body.value_id,
            kind_contract=ids[
                "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"
                + type(body).__name__
            ],
            context=DdoRichContext(
                subject=context.subject,
                subject_definition=context.subject_definition,
                original_source=None,
                analyzed_scope={},
            ),
            body=body,
        )
        for body in bodies
    )
    graph = RichGraphAssembly(
        members=packets, input_population=(inputs.reference(raw_role), inputs.reference(read_role))
    )
    return prepared, model, inputs, graph, assertion


def test_actual_complete_reading_applies_exact_authorization_without_merging_raw_interpretation():
    prepared, model, inputs, graph, assertion = actual_inputs()
    (decision,) = rich_reading_decisions(prepared, model, inputs=inputs, consolidation=graph)
    assert decision.outcome == "accepted"
    assert decision.assertion_member_id == assertion.reading_id
    assert decision.source_interpretation_id != decision.interpretation_id
    assert decision.original is not None and decision.resolved is not None
    assert decision.original.product_id == "raw" and decision.resolved.product_id == "resolved"
    assert decision.probability_hex is not None
    assert 0 < float.fromhex(decision.probability_hex) <= 1
