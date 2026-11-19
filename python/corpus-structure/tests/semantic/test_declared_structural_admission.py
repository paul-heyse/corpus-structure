"""Independent structural adjudication semantics; no native/provider authority claim."""

from copy import deepcopy
from decimal import Decimal
from typing import Any

import pytest
from pglast import parse_plpgsql, parse_sql

from corpus_structure.evaluate.declared_structural_admission import structural_admission_value
from corpus_structure.semantic.data_operation_identity import body_identity
from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
from corpus_structure.semantic.declared_structural_admission import DdoStructuralAdmission
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.structural_admission import structural_statement
from corpus_structure.semantic.structural_admission_native import (
    structural_admission_native_sql,
    structural_statement_native_sql,
)
from corpus_structure.semantic.structural_products import DIMENSIONS, DeclaredComparisonReport
from semantic.test_declared_structural_calls import exact_source


def comparison_report():
    sources = (
        exact_source("original:A", "source:A", "subject:A"),
        exact_source("original:B", "source:B", "subject:B"),
    )
    context = dict(
        project_id="p",
        subject="subject:A",
        subject_definition="original-source-view",
        original_source="original:A",
        analyzed_scope_meaning='["null"]',
    )
    readings = [
        dict(
            product_id="reading:" + side,
            member_id=None,
            kind_contract="kind:reading",
            contribution_id="source-contribution:" + digit * 64,
            **context,
        )
        for side, digit in (("left", "a"), ("right", "b"))
    ]
    dimensions: list[dict[str, Any]] = [
        dict(
            dimension=dimension,
            outcome="unknown",
            left_group=dict(state="absent"),
            right_group=dict(state="absent"),
        )
        for dimension in DIMENSIONS
    ]
    dimensions[0]["left_group"] = dict(
        state="present",
        grouping="singleton",
        members=[
            dict(
                dimension=DIMENSIONS[0],
                lexical_value="Ada",
                evidence=["left"],
                condition=dict(integer=1, floating=1.0, decimal=Decimal("1.00"), nullable=None),
            )
        ],
    )
    return DeclaredComparisonReport.model_validate(
        dict(
            inputs=dict(
                question="Compare exact retained operands",
                scope="selected",
                inventory_id="actual",
                policy_id="policy",
                sources=[source.model_dump() for source in sources],
                passages=[
                    dict(
                        passage_id=side,
                        source_ref=source.identity,
                        start=0,
                        end=9,
                        text="Ada acts.",
                        scope="selected",
                    )
                    for side, source in zip(("left", "right"), sources, strict=True)
                ],
                dependencies=[reading["contribution_id"] for reading in readings],
            ),
            comparison=dict(
                left_id="left",
                right_id="right",
                left_reading=readings[0],
                right_reading=readings[1],
                dimensions=dimensions,
            ),
            sources_input=[
                dict(
                    product_id=source.source_product,
                    member_id=None,
                    kind_contract=source.kind_contract,
                    reference=source.source,
                    project_id="p",
                    subject=source.subject,
                    subject_definition=source.subject_definition,
                    original_source=source.original_source,
                    analyzed_scope_meaning=source.analyzed_scope_meaning,
                )
                for source in sources
            ],
            reports_input=[
                dict(
                    **{key: value for key, value in reading.items() if key != "contribution_id"},
                    reference=canonical_bytes([reading["product_id"], None]).decode(),
                )
                for reading in readings
            ],
        )
    )


def passes_for(report, *, component_id=None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from corpus_structure.semantic.structural_admission import POLICIES

    context = dict(
        project_id="p",
        subject="subject:A",
        subject_definition="original-source-view",
        original_source="original:A",
        analyzed_scope_meaning='["null"]',
    )
    reference = dict(
        product_id="native:actual-comparison",
        member_id=None,
        kind_contract="kind:comparison",
        **context,
    )
    frame = dict(
        report=reference,
        inputs=report.model_dump(mode="python")["inputs"],
        question=report.inputs.question,
        case_id="whole",
        operation=report.kind,
        component_id=component_id,
        rubric_version=POLICIES[report.kind],
        direction="source_first",
        exposed_outputs=[],
    )
    statement = canonical_bytes(
        semantic_value(structural_statement(report, component_id=component_id))
    ).decode()
    passes: list[dict[str, Any]] = [
        dict(
            version="structural-reference-pass-1",
            frame=frame,
            pass_kind=kind,
            actor=dict(
                principal="author:" + kind,
                session_id="session:" + kind,
                basis="authored_attribution",
            ),
            author_assertion="author:" + kind,
            parents=[],
            cases=[
                dict(
                    case_id="whole",
                    facet="public_statement",
                    path=["public_statement"],
                    judgment="supported",
                    expected_meaning_json=statement,
                    source_passages=[passage.passage_id for passage in report.inputs.passages],
                )
            ],
        )
        for kind in ("A", "B", "C")
    ]
    references: list[dict[str, Any]] = [
        {
            **context,
            "product_id": "pass:" + kind,
            "member_id": None,
            "kind_contract": "kind:reference",
        }
        for kind in ("A", "B", "C")
    ]
    passes[2]["parents"] = [
        dict(reference=reference, body_digest=body_identity(value).key)
        for reference, value in zip(references[:2], passes[:2], strict=True)
    ]
    return passes, references


def test_independent_exact_statement_retains_numeric_kinds_and_actual_evidence_strength():
    from corpus_structure.semantic.declared_structural_references import DeclaredProductRef

    report = comparison_report()
    passes, references = passes_for(report)
    admitted = structural_admission_value(
        report.model_dump(mode="python"),
        passes,
        references=tuple(DeclaredProductRef.model_validate(value) for value in references),
    )
    assert admitted.report.product_id == "native:actual-comparison"
    assert admitted.standing == "admitted_structural_statement"
    assert admitted.assessment_basis == "independently_attributed_authored_judgments"
    assert admitted.scientific_truth == "not_established"
    condition = admitted.statement["comparison"]["dimensions"][0]["left_group"]["members"][0][
        "condition"
    ]
    assert type(condition["integer"]) is int and type(condition["floating"]) is float
    assert type(condition["decimal"]) is Decimal and condition["nullable"] is None
    public = admitted.model_dump(mode="python")
    assert not {"actors", "passes", "frame", "cases", "parents", "claim_id"} & public.keys()
    assert "structural_id" not in public["report"]
    assert decode_semantic_value(semantic_value(public)) == public


@pytest.mark.parametrize(
    "change,match",
    [
        ("actor", "independently attributed"),
        ("parent", "exact original A/B"),
        ("frame", "frozen frame"),
        ("passages", "omits"),
        ("unsupported", "supported whole"),
        ("statement", "supported whole"),
    ],
)
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
        changed[2]["frame"] = {
            **changed[2]["frame"],
            "direction": "output_first",
            "exposed_outputs": [changed[2]["frame"]["report"]],
        }
    elif change == "passages":
        changed[2]["cases"][0]["source_passages"] = ["left"]
    elif change == "unsupported":
        changed[2]["cases"][0]["judgment"] = "unassessed"
    else:
        changed[2]["cases"][0]["expected_meaning_json"] = canonical_bytes(
            semantic_value(dict(kind="qualified_comparison"))
        ).decode()
    with pytest.raises(ValueError, match=match):
        structural_admission_value(report.model_dump(mode="python"), changed)


def test_public_statement_encoding_refuses_retagged_or_unversioned_meaning():
    report = comparison_report()
    passes, _ = passes_for(report)
    admitted = structural_admission_value(report.model_dump(mode="python"), passes)
    with pytest.raises(ValueError, match="canonical statement"):
        DdoStructuralAdmission.model_validate(
            {**admitted.model_dump(), "statement_meaning_json": '["mapping",[]]'}
        )
    with pytest.raises(ValueError):
        DdoStructuralAdmission.model_validate(
            {**admitted.model_dump(), "statement_encoding": "plain-json"}
        )


def test_native_structural_admission_sql_has_parseable_closed_definitions():
    # Syntax only. Actual native validation belongs to the integrated target capture.
    assert parse_sql(structural_admission_native_sql(get_metadata()))
    assert parse_plpgsql(structural_statement_native_sql())


def test_actual_structural_issuer_compiles_with_protected_inputs_and_one_ordinary_effect():
    import json

    from corpus_structure.evaluate.declared_structural_admission import (
        structural_reference_kind_declarations,
    )
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.data_operation_ports import python_port_identity
    from corpus_structure.semantic.declared_structural_admission import (
        ADMISSION_KIND,
        ADMISSION_OPERATION,
        REFERENCE_KIND,
        structural_admission_kind_declarations,
        structural_admission_sources,
    )
    from corpus_structure.semantic.declared_structural_calls import (
        structural_operation_declarations,
    )
    from corpus_structure.semantic.python_operation_sources import PythonSourceCollection
    from semantic.test_declared_structural_calls import compiled

    _, bundle, existing = compiled()
    admission = structural_admission_sources()
    sources = PythonSourceCollection(
        tuple({value.module: value for value in (*existing.sources, *admission.sources)}.values()),
        boundary_contracts=(*existing.boundary_contracts, *admission.boundary_contracts),
    )
    model = compile_data_operations(
        bundle,
        (
            structural_operation_declarations(),
            structural_admission_kind_declarations(),
            structural_reference_kind_declarations(),
        ),
        sources,
    )
    operation = model.operation(ADMISSION_OPERATION)
    assert operation.profile == "command" and len(operation.effects) == 1
    assert [
        (role.name, role.minimum, role.maximum)
        for role in operation.roles
        if role.direction == "output"
    ] == [("admission", 1, 1)]
    assert (
        json.loads(next(kind.facts for kind in model.kinds if kind.semantic_id == REFERENCE_KIND))[
            "universe"
        ]
        == "evaluator"
    )
    assert (
        json.loads(next(kind.facts for kind in model.kinds if kind.semantic_id == ADMISSION_KIND))[
            "universe"
        ]
        == "ordinary"
    )
    assert python_port_identity(model, sources, ADMISSION_OPERATION, schema=bundle).recipe


def test_dossier_consumes_exact_admission_statement_without_copying_protected_judgments():
    from types import SimpleNamespace

    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralRef
    from corpus_structure.semantic.dossier_products import apply_structural_admissions

    report = comparison_report()
    passes, _ = passes_for(report)
    admission = structural_admission_value(report.model_dump(mode="python"), passes)
    reference = DeclaredStructuralRef(
        **admission.report.model_dump(), structural_id=report.product_id
    )
    payload: dict[str, Any] = {"report": report}
    retained = [(reference, payload)]
    apply_structural_admissions(
        retained,
        ((SimpleNamespace(product="admission:actual"), admission.model_dump(mode="python")),),
        project_id="p",
    )
    assertion = payload["public_assertions"][0]
    assert assertion["assessment_id"] == "admission:actual"
    assert assertion["assessment_scope"] == "comparison_statement"
    assert assertion["statement"] == structural_statement(report)
    assert set(assertion) == {"assessment_id", "assessment_scope", "statement"}
    other = admission.model_copy(
        update={"report": admission.report.model_copy(update={"product_id": "other-native-report"})}
    )
    with pytest.raises(ValueError, match="exact retained native report"):
        apply_structural_admissions(
            [(reference, {"report": report})],
            ((SimpleNamespace(product="admission:other"), other.model_dump(mode="python")),),
            project_id="p",
        )


def test_actual_dossier_contract_binds_ordinary_admission_and_exact_output_pins():
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.data_operation_ports import python_port_identity
    from corpus_structure.semantic.declared_structural_admission import (
        structural_admission_kind_declarations,
    )
    from corpus_structure.semantic.declared_structural_calls import (
        structural_operation_declarations,
    )
    from corpus_structure.semantic.dossier_products import dossier_inputs, dossier_operation_sources
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from semantic.test_declared_structural_calls import compiled

    _, bundle, sources = compiled()
    bundle = dossier_inputs(bundle)
    sources = combine_primary_sources(sources, dossier_operation_sources())
    model = compile_data_operations(
        bundle,
        (structural_operation_declarations(), structural_admission_kind_declarations()),
        sources,
    )
    operation = model.operation("structure.dossier/declared")
    admissions = next(role for role in operation.roles if role.name == "admissions")
    assert admissions.direction == "input" and admissions.minimum == 0
    assert admissions.support is not None and admissions.support.identity_requirements == (
        "episode",
    )
    witness = next(
        witness for witness in operation.output_witnesses if witness.input_role == "admissions"
    )
    assert witness.records == "/admissions_input/*"
    assert {comparison.output_field for comparison in witness.comparisons} >= {
        "product_id",
        "kind_contract",
        "subject_definition",
        "analyzed_scope_meaning",
    }
    assert python_port_identity(model, sources, operation.semantic_id, schema=bundle).recipe


def test_supported_gap_examines_complete_membership_and_exact_native_predecessor():
    from types import SimpleNamespace

    from corpus_structure.semantic.authority_leaf import NativeAuthorityLeaf
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralRef
    from corpus_structure.serve.selected_structural_admission import supported_comparison_gap_rows

    report = comparison_report()
    passes, _ = passes_for(report)
    value = structural_admission_value(report.model_dump(mode="python"), passes)
    leaf = NativeAuthorityLeaf.model_validate(
        dict(
            format="ddo-native-authority-leaf-v1",
            derivation_id="issuer:actual",
            use_id=None,
            issuer_operation="structure.admit",
            release_id="release:actual",
            runtime_id="runtime:actual",
            recipe="recipe:actual",
            product_id="admission:actual",
            kind_contract="kind:actual",
            intent_id="intent:actual",
            receipt_id="receipt:actual",
            standing="valid",
            protected_dependencies="undisclosed",
        )
    )
    reference = DeclaredStructuralRef(**value.report.model_dump(), structural_id=report.product_id)
    dossier = SimpleNamespace(predecessors=(reference,), members=[], root_component=reference)
    binding = SimpleNamespace(dossier=dossier, product_id="structural:dossier")
    request = SimpleNamespace(scope="selected")
    row = supported_comparison_gap_rows(request, report, (value, leaf), binding)[0]
    assert row["reason"] == "no_qualifying_root_binding"
    assert set(row["evidence"]["sides"]) == {"left", "right"}
    assert row["evidence"]["assessment_scope"] == "comparison_statement"
    # Display never changes root binding: complete retained membership is examined.
    dossier.members = [
        SimpleNamespace(comparison_binding=SimpleNamespace(side="left", comparison_ref=reference))
    ]
    assert set(
        supported_comparison_gap_rows(request, report, (value, leaf), binding)[0]["evidence"][
            "sides"
        ]
    ) == {"right"}
    dossier.members.append(
        SimpleNamespace(comparison_binding=SimpleNamespace(side="right", comparison_ref=reference))
    )
    assert supported_comparison_gap_rows(request, report, (value, leaf), binding) == []
    dossier.predecessors = (
        reference.model_copy(update={"product_id": "same-statement-other-native-product"}),
    )
    assert (
        supported_comparison_gap_rows(request, report, (value, leaf), binding)[0]["reason"]
        == "comparison_outside_binding_selection"
    )
    assert (
        supported_comparison_gap_rows(request, report, None, binding)[0]["status"] == "unavailable"
    )


def finite_report(variant):
    from corpus_structure.semantic.structural_products import (
        DeclaredConditionReport,
        DeclaredDefinitionComponentsReport,
        declared_definition_component,
    )

    base = comparison_report()
    text = "If ready, Ada acts."
    inputs = base.inputs.model_dump(mode="python")
    inputs["sources"] = inputs["sources"][:1]
    inputs["passages"] = [
        dict(
            passage_id="whole",
            source_ref=base.inputs.sources[0].identity,
            start=0,
            end=len(text),
            text=text,
            scope="selected",
        )
    ]
    pin = base.sources_input[0].model_dump(mode="python")
    if variant == "condition_qualification":
        reference = base.comparison.left_reading.model_dump(mode="python")
        return DeclaredConditionReport.model_validate(
            dict(
                inputs=inputs,
                source_input=pin,
                report_input=base.reports_input[0].model_dump(mode="python"),
                condition_qualification=dict(
                    relation="condition",
                    attachment=reference,
                    qualifier=[
                        dict(
                            source_pointer="#/texts/0",
                            span=dict(passage_id="whole", start=0, end=8, text="If ready"),
                        )
                    ],
                    host_predicate=[
                        dict(
                            source_pointer="#/texts/0",
                            span=dict(passage_id="whole", start=14, end=18, text="acts"),
                        )
                    ],
                ),
            )
        ), None
    component = declared_definition_component(
        term=dict(passage_id="whole", start=10, end=13, text="Ada"),
        content=dict(passage_id="whole", start=14, end=18, text="acts"),
        interpretation="unresolved",
        basis="unqualified",
        scope="selected",
        evidence=("whole",),
        reason="Pure located proposal has no interpretation authority",
    )
    return DeclaredDefinitionComponentsReport.model_validate(
        dict(
            inputs=inputs,
            sources_input=[pin],
            reports_input=[],
            definition_components=dict(components=[component.model_dump(mode="python")], stages=[]),
        )
    ), component.component_id


@pytest.mark.parametrize("variant", ["condition_qualification", "definition_components"])
def test_finite_report_roles_require_exact_whole_meaning_and_component_selection(variant):
    report, selector = finite_report(variant)
    passes, _ = passes_for(report, component_id=selector)
    admitted = structural_admission_value(report.model_dump(mode="python"), passes)
    assert admitted.statement["kind"] == variant
    assert admitted.component_id == selector
    if variant == "condition_qualification":
        assert admitted.statement[variant]["qualifier"][0]["passage"]["text"] == "If ready"
        assert admitted.statement[variant]["host_predicate"][0]["passage"]["text"] == "acts"
    else:
        assert admitted.statement["definition_component"]["term"]["text"] == "Ada"
        assert admitted.statement["definition_component"]["content"]["text"] == "acts"
        with pytest.raises(ValueError, match="missing or duplicated"):
            structural_statement(report, "f" * 64)
    changed = deepcopy(passes)
    changed[2]["cases"][0]["expected_meaning_json"] = canonical_bytes(
        semantic_value({**admitted.statement, "scope": None})
    ).decode()
    with pytest.raises(ValueError, match="supported whole"):
        structural_admission_value(report.model_dump(mode="python"), changed)
    from corpus_structure.evaluate.declared_structural_admission import DdoStructuralAssessmentFrame

    for update in (
        {"component_id": None if selector else "f" * 64},
        {"rubric_version": "independent-structural-comparison-1"},
    ):
        with pytest.raises(ValueError):
            DdoStructuralAssessmentFrame.model_validate({**passes[2]["frame"], **update})


@pytest.mark.parametrize(
    "change",
    [
        "null_to_missing",
        "swapped_roles",
        "foreign_source",
        "duplicate_case",
        "source_first_exposure",
    ],
)
def test_current_whole_statement_refuses_changed_meaning_or_assessment_frame(change):
    report = comparison_report()
    passes, _ = passes_for(report)
    changed = deepcopy(passes)
    if change == "null_to_missing":
        expected = deepcopy(structural_statement(report))
        del expected["comparison"]["dimensions"][0]["left_group"]["members"][0]["condition"][
            "nullable"
        ]
        changed[2]["cases"][0]["expected_meaning_json"] = canonical_bytes(
            semantic_value(expected)
        ).decode()
    elif change == "swapped_roles":
        expected = structural_statement(report)
        expected["comparison"]["left"], expected["comparison"]["right"] = (
            expected["comparison"]["right"],
            expected["comparison"]["left"],
        )
        changed[2]["cases"][0]["expected_meaning_json"] = canonical_bytes(
            semantic_value(expected)
        ).decode()
    elif change == "foreign_source":
        changed[2]["frame"] = deepcopy(changed[2]["frame"])
        changed[2]["frame"]["inputs"]["sources"][0]["project_id"] = "foreign"
    elif change == "duplicate_case":
        changed[2]["cases"].append(deepcopy(changed[2]["cases"][0]))
    else:
        changed[2]["frame"] = {
            **changed[2]["frame"],
            "exposed_outputs": [changed[2]["frame"]["report"]],
        }
    with pytest.raises(ValueError):
        structural_admission_value(report.model_dump(mode="python"), changed)


def report_support_rows():
    """Controlled captured rows for pure edge interpretation, not native evidence."""
    from corpus_structure.semantic.authority_leaf import NativeAuthorityLeaf
    from corpus_structure.semantic.declared_structural_admission import ADMISSION_KIND

    report = comparison_report()
    passes, _ = passes_for(report)
    value = structural_admission_value(report.model_dump(mode="python"), passes)
    reference = value.report
    product = dict(
        id=reference.product_id,
        kind_contract=reference.kind_contract,
        project_id=reference.project_id,
        subject=reference.subject,
        subject_definition=reference.subject_definition,
        original_source=reference.original_source,
        analyzed_scope=None,
        canonical_body=semantic_value(report.model_dump(mode="python")),
    )
    conclusion = dict(
        id="ordinary:admission",
        kind_contract="kind:admission",
        project_id="p",
        canonical_body=semantic_value(value.model_dump(mode="python")),
    )
    leaf = NativeAuthorityLeaf(
        format="ddo-native-authority-leaf-v1",
        derivation_id="episode:issuer",
        use_id="use:issuer",
        issuer_operation="structure.admit",
        release_id="release",
        runtime_id="runtime",
        recipe="issuer-recipe",
        product_id=conclusion["id"],
        kind_contract=conclusion["kind_contract"],
        intent_id="intent:issuer",
        receipt_id="receipt:issuer",
        standing="valid",
        protected_dependencies="undisclosed",
    )
    edge = dict(
        derivation_id=leaf.derivation_id,
        role="comparison",
        position=0,
        support_derivation_id="episode:report",
        admission_use_id="use:report",
        scope="scope:original:A",
        epoch=0,
        occurrence=0,
    )
    episode = dict(
        id="episode:report",
        request_id="request:report",
        release_id="release",
        runtime_id="runtime",
        intent_id="intent:report",
        recipe="report-recipe",
        outcome="success",
    )
    output = dict(
        derivation_id=episode["id"],
        role="result",
        position=0,
        multiplicity=1,
        member_id=None,
        product_id=product["id"],
    )
    definition = dict(
        profile="derivation",
        recipe=episode["recipe"],
        implementation_revision="implementation-slice:report",
        support_contract=dict(
            effects=[],
            capabilities=dict(
                prepared_factory=dict(
                    entrypoint="corpus_structure.methods.structural_declared.DeclaredStructuralComparison.acquire_port",
                    source_digest="a" * 64,
                )
            ),
        ),
    )
    return edge, dict(
        leaf=leaf,
        products={product["id"]: product, conclusion["id"]: conclusion},
        kinds={
            reference.kind_contract: dict(
                kind="urn:corpus:structural:DeclaredComparisonReport", universe="ordinary"
            ),
            conclusion["kind_contract"]: dict(kind=ADMISSION_KIND, universe="ordinary"),
        },
        uses={"use:report": dict(id="use:report", fate="fulfilled", derivation_id=episode["id"])},
        episodes={episode["id"]: episode},
        outputs=[output],
        requests={
            "request:report": dict(operation_id="structure.compare/declared", project_id="p")
        },
        definitions={("release", "structure.compare/declared"): definition},
        intents={
            "intent:report": dict(
                payload=dict(
                    implementation_revision="implementation-slice:report",
                    execution_evidence=dict(cpu_receipts=[{}]),
                )
            )
        },
        receipts=[dict(derivation_id=episode["id"], intent_id="intent:report")],
    )


def test_authenticated_report_support_keeps_the_actual_prior_use_without_frontier_alias():
    from corpus_structure.semantic.declared_structural_admission import (
        validate_structural_report_support,
    )

    edge, rows = report_support_rows()
    value, use, episode, output = validate_structural_report_support(edge, **rows)
    assert value.report.product_id == "native:actual-comparison"
    assert use["id"] == "use:report" and episode["id"] == "episode:report"
    assert output["role"] == "result"
    assert rows["leaf"].protected_dependencies == "undisclosed"


@pytest.mark.parametrize(
    "change",
    [
        "unrelated_report",
        "wrong_use",
        "private_kind",
        "foreign_context",
        "wrong_factory",
        "missing_receipt",
        "withdrawn",
        "copied_conclusion",
        "protected_edge",
    ],
)
def test_ordinary_report_edge_refuses_unrelated_private_copied_or_unavailable_custody(change):
    from corpus_structure.semantic.declared_structural_admission import (
        validate_structural_report_support,
    )

    edge, rows = deepcopy(report_support_rows())
    if change == "unrelated_report":
        rows["outputs"][0]["product_id"] = "unrelated:actual-product"
    elif change == "wrong_use":
        edge["admission_use_id"] = "unselected:use"
    elif change == "private_kind":
        rows["kinds"]["kind:comparison"]["universe"] = "evaluator"
    elif change == "foreign_context":
        rows["products"]["native:actual-comparison"]["project_id"] = "foreign"
    elif change == "wrong_factory":
        rows["definitions"]["release", "structure.compare/declared"]["support_contract"][
            "capabilities"
        ]["prepared_factory"]["entrypoint"] = "controlled.same_shape"
    elif change == "missing_receipt":
        rows["receipts"] = []
    elif change == "withdrawn":
        rows["leaf"] = rows["leaf"].model_copy(update={"standing": "unavailable"})
    elif change == "copied_conclusion":
        rows["leaf"] = rows["leaf"].model_copy(update={"issuer_operation": "authored-copy"})
    else:
        edge["role"] = "passes"
    with pytest.raises(ValueError):
        validate_structural_report_support(edge, **rows)
