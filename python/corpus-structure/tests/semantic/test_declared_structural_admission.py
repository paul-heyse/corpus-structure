"""Independent structural adjudication semantics; no native/provider authority claim."""

from copy import deepcopy
from decimal import Decimal
from typing import Any

import pytest
from pglast import parse_plpgsql, parse_sql

from corpus_structure.evaluate.declared_structural_admission import structural_admission_value
from corpus_structure.semantic.data_operation_identity import body_identity, decode_semantic_value, semantic_value
from corpus_structure.semantic.declared_structural_admission import DdoStructuralAdmission
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_admission import structural_statement
from corpus_structure.semantic.structural_admission_native import structural_admission_native_sql, structural_statement_native_sql
from corpus_structure.semantic.structural_products import DIMENSIONS, DeclaredComparisonReport
from semantic.test_declared_structural_calls import exact_source


def comparison_report():
    sources = (exact_source("original:A", "source:A", "subject:A"), exact_source("original:B", "source:B", "subject:B"))
    context = dict(project_id="p", subject="subject:A", subject_definition="original-source-view",
                   original_source="original:A", analyzed_scope_meaning='["null"]')
    readings = [dict(product_id="reading:" + side, member_id=None, kind_contract="kind:reading",
                     contribution_id="source-contribution:" + digit * 64, **context)
                for side, digit in (("left", "a"), ("right", "b"))]
    dimensions: list[dict[str, Any]] = [dict(dimension=dimension, outcome="unknown", left_group=dict(state="absent"),
                       right_group=dict(state="absent")) for dimension in DIMENSIONS]
    dimensions[0]["left_group"] = dict(state="present", grouping="singleton", members=[dict(
        dimension=DIMENSIONS[0], lexical_value="Ada", evidence=["left"],
        condition=dict(integer=1, floating=1.0, decimal=Decimal("1.00"), nullable=None),
    )])
    return DeclaredComparisonReport.model_validate(dict(
        inputs=dict(question="Compare exact retained operands", scope="selected", inventory_id="actual", policy_id="policy",
                    sources=[source.model_dump() for source in sources],
                    passages=[dict(passage_id=side, source_ref=source.identity, start=0, end=9, text="Ada acts.", scope="selected")
                              for side, source in zip(("left", "right"), sources, strict=True)],
                    dependencies=[reading["contribution_id"] for reading in readings]),
        comparison=dict(left_id="left", right_id="right", left_reading=readings[0], right_reading=readings[1], dimensions=dimensions),
        sources_input=[dict(product_id=source.source_product, member_id=None, kind_contract=source.kind_contract,
                            reference=source.source, project_id="p", subject=source.subject,
                            subject_definition=source.subject_definition, original_source=source.original_source,
                            analyzed_scope_meaning=source.analyzed_scope_meaning) for source in sources],
        reports_input=[dict(**{key: value for key, value in reading.items() if key != "contribution_id"},
                           reference=canonical_bytes([reading["product_id"], None]).decode()) for reading in readings],
    ))


def passes_for(report) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    context = dict(project_id="p", subject="subject:A", subject_definition="original-source-view",
                   original_source="original:A", analyzed_scope_meaning='["null"]')
    reference = dict(product_id="native:actual-comparison", member_id=None, kind_contract="kind:comparison", **context)
    frame = dict(report=reference, inputs=report.model_dump(mode="python")["inputs"],
                 question=report.inputs.question, case_id="whole", operation="qualified_comparison",
                 rubric_version="independent-structural-comparison-1", direction="source_first", exposed_outputs=[])
    statement = canonical_bytes(semantic_value(structural_statement(report))).decode()
    passes: list[dict[str, Any]] = [dict(version="structural-reference-pass-1", frame=frame, pass_kind=kind,
                   actor=dict(principal="author:" + kind, session_id="session:" + kind, basis="authored_attribution"),
                   author_assertion="author:" + kind, parents=[], cases=[dict(
                       case_id="whole", facet="public_statement", path=["public_statement"], judgment="supported",
                       expected_meaning_json=statement, source_passages=["left", "right"],
                   )]) for kind in ("A", "B", "C")]
    references: list[dict[str, Any]] = [{**context, "product_id": "pass:" + kind, "member_id": None, "kind_contract": "kind:reference"} for kind in ("A", "B", "C")]
    passes[2]["parents"] = [dict(reference=reference, body_digest=body_identity(value).key)
                            for reference, value in zip(references[:2], passes[:2], strict=True)]
    return passes, references


def test_independent_exact_statement_retains_numeric_kinds_and_actual_evidence_strength():
    from corpus_structure.semantic.declared_structural_references import DeclaredProductRef

    report = comparison_report()
    passes, references = passes_for(report)
    admitted = structural_admission_value(report.model_dump(mode="python"), passes,
                                         references=tuple(DeclaredProductRef.model_validate(value) for value in references))
    assert admitted.report.product_id == "native:actual-comparison"
    assert admitted.standing == "admitted_structural_statement"
    assert admitted.assessment_basis == "independently_attributed_authored_judgments"
    assert admitted.scientific_truth == "not_established"
    condition = admitted.statement["comparison"]["dimensions"][0]["left_group"]["members"][0]["condition"]
    assert type(condition["integer"]) is int and type(condition["floating"]) is float
    assert type(condition["decimal"]) is Decimal and condition["nullable"] is None
    public = admitted.model_dump(mode="python")
    assert not {"actors", "passes", "frame", "cases", "parents", "claim_id"} & public.keys()
    assert "structural_id" not in public["report"]
    assert decode_semantic_value(semantic_value(public)) == public


@pytest.mark.parametrize("change,match", [
    ("actor", "independently attributed"), ("parent", "exact original A/B"),
    ("frame", "frozen frame"), ("passages", "omits"), ("unsupported", "supported whole"),
    ("statement", "supported whole"),
])
def test_structural_admission_refuses_changed_basis_instead_of_upgrading_support(change, match):
    report = comparison_report()
    passes, _ = passes_for(report)
    changed = deepcopy(passes)
    if change == "actor":
        changed[2]["actor"] = changed[0]["actor"]
        changed[2]["author_assertion"] = changed[0]["author_assertion"]
    elif change == "parent":
        changed[2]["parents"][0]["body_digest"] = "body:foreign"
    elif change == "frame":
        changed[2]["frame"] = {**changed[2]["frame"], "direction": "output_first",
                               "exposed_outputs": [changed[2]["frame"]["report"]]}
    elif change == "passages":
        changed[2]["cases"][0]["source_passages"] = ["left"]
    elif change == "unsupported":
        changed[2]["cases"][0]["judgment"] = "unassessed"
    else:
        changed[2]["cases"][0]["expected_meaning_json"] = canonical_bytes(semantic_value(dict(kind="qualified_comparison"))).decode()
    with pytest.raises(ValueError, match=match):
        structural_admission_value(report.model_dump(mode="python"), changed)


def test_public_statement_encoding_refuses_retagged_or_unversioned_meaning():
    report = comparison_report()
    passes, _ = passes_for(report)
    admitted = structural_admission_value(report.model_dump(mode="python"), passes)
    with pytest.raises(ValueError, match="canonical statement"):
        DdoStructuralAdmission.model_validate({**admitted.model_dump(), "statement_meaning_json": '["mapping",[]]'})
    with pytest.raises(ValueError):
        DdoStructuralAdmission.model_validate({**admitted.model_dump(), "statement_encoding": "plain-json"})


def test_native_structural_admission_sql_has_parseable_closed_definitions():
    # Syntax only. Actual native validation belongs to the integrated target capture.
    assert parse_sql(structural_admission_native_sql())
    assert parse_plpgsql(structural_statement_native_sql())


def test_actual_structural_issuer_compiles_with_protected_inputs_and_one_ordinary_effect():
    import json
    from corpus_structure.evaluate.declared_structural_admission import structural_reference_kind_declarations
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.data_operation_ports import python_port_identity
    from corpus_structure.semantic.declared_structural_admission import (
        ADMISSION_OPERATION, ADMISSION_KIND, REFERENCE_KIND, structural_admission_kind_declarations,
        structural_admission_sources,
    )
    from corpus_structure.semantic.declared_structural_calls import structural_operation_declarations
    from corpus_structure.semantic.python_operation_sources import PythonSourceCollection
    from semantic.test_declared_structural_calls import compiled

    _, bundle, existing = compiled()
    admission = structural_admission_sources()
    sources = PythonSourceCollection(
        tuple({value.module: value for value in (*existing.sources, *admission.sources)}.values()),
        boundary_contracts=(*existing.boundary_contracts, *admission.boundary_contracts),
    )
    model = compile_data_operations(bundle, (structural_operation_declarations(),
                                            structural_admission_kind_declarations(),
                                            structural_reference_kind_declarations()), sources)
    operation = model.operation(ADMISSION_OPERATION)
    assert operation.profile == "command" and len(operation.effects) == 1
    assert [(role.name, role.minimum, role.maximum) for role in operation.roles if role.direction == "output"] == [("admission", 1, 1)]
    assert json.loads(next(kind.facts for kind in model.kinds if kind.semantic_id == REFERENCE_KIND))["universe"] == "evaluator"
    assert json.loads(next(kind.facts for kind in model.kinds if kind.semantic_id == ADMISSION_KIND))["universe"] == "ordinary"
    assert python_port_identity(model, sources, ADMISSION_OPERATION, schema=bundle).recipe


def test_dossier_consumes_exact_admission_statement_without_copying_protected_judgments():
    from types import SimpleNamespace
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralRef
    from corpus_structure.semantic.dossier_products import apply_structural_admissions

    report = comparison_report()
    passes, _ = passes_for(report)
    admission = structural_admission_value(report.model_dump(mode="python"), passes)
    reference = DeclaredStructuralRef(**admission.report.model_dump(), structural_id=report.product_id)
    payload: dict[str, Any] = {"report": report}
    retained = [(reference, payload)]
    apply_structural_admissions(retained, ((SimpleNamespace(product="admission:actual"), admission.model_dump(mode="python")),), project_id="p")
    assertion = payload["public_assertions"][0]
    assert assertion["assessment_id"] == "admission:actual"
    assert assertion["assessment_scope"] == "comparison_statement"
    assert assertion["statement"] == structural_statement(report)
    assert set(assertion) == {"assessment_id", "assessment_scope", "statement"}
    other = admission.model_copy(update={"report": admission.report.model_copy(update={"product_id": "other-native-report"})})
    with pytest.raises(ValueError, match="exact retained native report"):
        apply_structural_admissions([(reference, {"report": report})], ((SimpleNamespace(product="admission:other"), other.model_dump(mode="python")),), project_id="p")


def test_actual_dossier_contract_binds_ordinary_admission_and_exact_output_pins():
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.data_operation_ports import python_port_identity
    from corpus_structure.semantic.declared_structural_admission import structural_admission_kind_declarations
    from corpus_structure.semantic.declared_structural_calls import structural_operation_declarations
    from corpus_structure.semantic.dossier_products import dossier_inputs, dossier_operation_sources
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from semantic.test_declared_structural_calls import compiled

    _, bundle, sources = compiled()
    bundle = dossier_inputs(bundle)
    sources = combine_primary_sources(sources, dossier_operation_sources())
    model = compile_data_operations(bundle, (structural_operation_declarations(), structural_admission_kind_declarations()), sources)
    operation = model.operation("structure.dossier/declared")
    admissions = next(role for role in operation.roles if role.name == "admissions")
    assert admissions.direction == "input" and admissions.minimum == 0
    assert admissions.support is not None and admissions.support.identity_requirements == ("episode",)
    witness = next(witness for witness in operation.output_witnesses if witness.input_role == "admissions")
    assert witness.records == "/admissions_input/*"
    assert {comparison.output_field for comparison in witness.comparisons} >= {"product_id", "kind_contract", "subject_definition", "analyzed_scope_meaning"}
    assert python_port_identity(model, sources, operation.semantic_id, schema=bundle).recipe


def test_supported_gap_examines_complete_membership_and_exact_native_predecessor():
    from types import SimpleNamespace
    from corpus_structure.semantic.authority_leaf import NativeAuthorityLeaf
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralRef
    from corpus_structure.serve.selected_structural_admission import supported_comparison_gap_rows

    report = comparison_report()
    passes, _ = passes_for(report)
    value = structural_admission_value(report.model_dump(mode="python"), passes)
    leaf = NativeAuthorityLeaf.model_validate(dict(
        format="ddo-native-authority-leaf-v1", derivation_id="issuer:actual", use_id=None,
        issuer_operation="structure.admit_comparison", release_id="release:actual", runtime_id="runtime:actual",
        recipe="recipe:actual", product_id="admission:actual", kind_contract="kind:actual", intent_id="intent:actual",
        receipt_id="receipt:actual", standing="valid", protected_dependencies="undisclosed",
    ))
    reference = DeclaredStructuralRef(**value.report.model_dump(), structural_id=report.product_id)
    dossier = SimpleNamespace(predecessors=(reference,), members=[], root_component=reference)
    binding = SimpleNamespace(dossier=dossier, product_id="structural:dossier")
    request = SimpleNamespace(scope="selected")
    row = supported_comparison_gap_rows(request, report, (value, leaf), binding)[0]
    assert row["reason"] == "no_qualifying_root_binding"
    assert set(row["evidence"]["sides"]) == {"left", "right"}
    assert row["evidence"]["assessment_scope"] == "comparison_statement"
    # Display never changes root binding: complete retained membership is examined.
    dossier.members = [SimpleNamespace(comparison_binding=SimpleNamespace(side="left", comparison_ref=reference))]
    assert set(supported_comparison_gap_rows(request, report, (value, leaf), binding)[0]["evidence"]["sides"]) == {"right"}
    dossier.members.append(SimpleNamespace(comparison_binding=SimpleNamespace(side="right", comparison_ref=reference)))
    assert supported_comparison_gap_rows(request, report, (value, leaf), binding) == []
    dossier.predecessors = (reference.model_copy(update={"product_id": "same-statement-other-native-product"}),)
    assert supported_comparison_gap_rows(request, report, (value, leaf), binding)[0]["reason"] == "comparison_outside_binding_selection"
    assert supported_comparison_gap_rows(request, report, None, binding)[0]["status"] == "unavailable"
